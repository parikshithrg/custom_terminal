"""Provider-neutral incremental ingestion, schema routing, and rebuild planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Iterable, Mapping

import pandas as pd

from .artifacts import canonical_json, sha256_file
from .providers import ProviderObject


class IncrementalError(RuntimeError):
    """Base class for named fail-closed incremental errors."""


class ImmutableIdentityConflict(IncrementalError):
    pass


class PartialPublicationConflict(IncrementalError):
    pass


class SchemaDriftError(IncrementalError):
    pass


class BuildState(StrEnum):
    REUSED_HASH_IDENTICAL = "REUSED_HASH_IDENTICAL"
    REBUILT_INPUT_CHANGED = "REBUILT_INPUT_CHANGED"
    REBUILT_DEFINITION_CHANGED = "REBUILT_DEFINITION_CHANGED"
    QUARANTINED_SCHEMA_DRIFT = "QUARANTINED_SCHEMA_DRIFT"
    BLOCKED_DEPENDENCY_INVALID = "BLOCKED_DEPENDENCY_INVALID"
    NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"
    UNAFFECTED = "UNAFFECTED"


@dataclass(frozen=True)
class IncrementalRawResult:
    state: str
    manifest_path: Path
    content_hash: str
    source_identity: str


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


class IncrementalRawStore:
    """Immutable multi-object store with explicit source-identity conflict detection."""

    manifest_version = "incremental_raw_object_v1"

    def __init__(self, root: Path):
        self.root = Path(root)

    def _identity_path(self, obj: ProviderObject) -> Path:
        identity_hash = hashlib.sha256(obj.source_identity.encode("utf-8")).hexdigest()
        return self.root / "identity" / obj.provider / obj.dataset.value / f"{identity_hash}.json"

    def ingest(self, obj: ProviderObject, *, parser_version: str, retrieved_at: str,
               raw_schema_version: str, fail_at: str | None = None) -> IncrementalRawResult:
        if not obj.local_path.is_file():
            raise FileNotFoundError("source object does not exist")
        content_hash = sha256_file(obj.local_path)
        identity_path = self._identity_path(obj)
        if identity_path.exists():
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            if identity["content_hash"] != content_hash:
                raise ImmutableIdentityConflict("IMMUTABLE_SOURCE_IDENTITY_CONFLICT")
        target = self.root / "objects" / obj.provider / obj.dataset.value / content_hash
        manifest_path = target / "manifest.json"
        payload_name = "payload" + (obj.local_path.suffix or ".bin")
        payload_path = target / payload_name
        if target.exists():
            if not manifest_path.is_file() or not payload_path.is_file():
                raise PartialPublicationConflict("CONFLICTING_PARTIAL_RAW_OBJECT")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if sha256_file(payload_path) != content_hash or manifest["content_hash"] != content_hash:
                raise PartialPublicationConflict("CONFLICTING_PARTIAL_RAW_OBJECT")
            if not identity_path.exists():
                _atomic_json(identity_path, {"source_identity": obj.source_identity,
                                             "content_hash": content_hash,
                                             "manifest": str(manifest_path.relative_to(self.root)).replace("\\", "/")})
            return IncrementalRawResult("REUSED_IDENTICAL_BYTES", manifest_path, content_hash,
                                        obj.source_identity)

        stage = self.root / ".staging" / f"{content_hash}-{hashlib.sha256(obj.source_identity.encode()).hexdigest()[:12]}"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        staged_payload = stage / payload_name
        shutil.copyfile(obj.local_path, staged_payload)
        if sha256_file(staged_payload) != content_hash:
            raise IncrementalError("SOURCE_CHANGED_DURING_COPY")
        if fail_at == "after_payload":
            raise IncrementalError("INJECTED_AFTER_PAYLOAD")
        manifest = {
            "manifest_version": self.manifest_version,
            "provider": obj.provider,
            "dataset": obj.dataset.value,
            "source_identity": obj.source_identity,
            "retrieved_at": retrieved_at,
            "content_hash": content_hash,
            "byte_size": staged_payload.stat().st_size,
            "parser_version": parser_version,
            "raw_schema_version": raw_schema_version,
            "request_parameters": obj.request_parameters,
            "expected_event_date": obj.expected_event_date,
            "retention_classification": obj.retention_classification,
            "data_classification": obj.data_classification,
            "stored_payload": payload_name,
            "state": "SUCCEEDED",
        }
        _atomic_json(stage / "manifest.json", manifest)
        if fail_at == "after_manifest_stage":
            raise IncrementalError("INJECTED_AFTER_MANIFEST_STAGE")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, target)
        if fail_at == "after_object_publish":
            raise IncrementalError("INJECTED_AFTER_OBJECT_PUBLISH")
        _atomic_json(identity_path, {"source_identity": obj.source_identity,
                                     "content_hash": content_hash,
                                     "manifest": str(manifest_path.relative_to(self.root)).replace("\\", "/")})
        return IncrementalRawResult("INGESTED", manifest_path, content_hash, obj.source_identity)

    def cleanup_staging(self) -> int:
        staging = self.root / ".staging"
        if not staging.exists():
            return 0
        removed = len([path for path in staging.iterdir()])
        shutil.rmtree(staging)
        return removed


@dataclass(frozen=True)
class SchemaContract:
    dataset: str
    raw_schema_version: str
    output_schema_version: str
    required_fields: Mapping[str, str]
    optional_fields: Mapping[str, str] = field(default_factory=dict)
    coercion_policy: str = "STRICT"
    unknown_field_policy: str = "REJECT"
    quality_policy: str = "QUARANTINE_INVALID_ROWS"
    availability_policy: str = "PUBLISHED_AND_AVAILABLE_BY_CUTOFF"
    parser_implementation_hash: str = ""

    def __post_init__(self) -> None:
        if not self.parser_implementation_hash:
            payload = {key: value for key, value in asdict(self).items()
                       if key != "parser_implementation_hash"}
            object.__setattr__(self, "parser_implementation_hash",
                               hashlib.sha256(canonical_json(payload).encode()).hexdigest())


@dataclass(frozen=True)
class RoutedBatch:
    raw_schema_version: str
    output_schema_version: str
    accepted: tuple[dict, ...]
    quarantine: tuple[dict, ...]
    parser_implementation_hash: str


def _valid_type(value: object, declared: str) -> bool:
    if value is None or value is pd.NA:
        return True
    if declared == "string":
        return isinstance(value, str)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "timestamp":
        try:
            return pd.Timestamp(value).tzinfo is not None
        except (TypeError, ValueError):
            return False
    if declared == "boolean":
        return isinstance(value, bool)
    raise SchemaDriftError(f"UNKNOWN_DECLARED_TYPE:{declared}")


class SchemaRegistry:
    def __init__(self, contracts: Iterable[SchemaContract] = ()):
        self._contracts: dict[tuple[str, str], SchemaContract] = {}
        for contract in contracts:
            self.register(contract)

    def register(self, contract: SchemaContract) -> None:
        key = (contract.dataset, contract.raw_schema_version)
        if key in self._contracts and self._contracts[key] != contract:
            raise SchemaDriftError("CONFLICTING_SCHEMA_REGISTRATION")
        self._contracts[key] = contract

    def route(self, *, dataset: str, raw_schema_version: str,
              records: Iterable[Mapping[str, object]], strict: bool | None = None) -> RoutedBatch:
        contract = self._contracts.get((dataset, raw_schema_version))
        if contract is None:
            raise SchemaDriftError("UNKNOWN_SCHEMA_VERSION")
        reject_unknown = contract.unknown_field_policy == "REJECT" if strict is None else strict
        allowed = set(contract.required_fields) | set(contract.optional_fields)
        accepted: list[dict] = []
        quarantine: list[dict] = []
        for record in records:
            row = dict(record)
            reasons: list[str] = []
            missing = set(contract.required_fields) - set(row)
            if missing:
                reasons.append("MISSING_REQUIRED_FIELDS:" + ",".join(sorted(missing)))
            unknown = set(row) - allowed
            if unknown and reject_unknown:
                reasons.append("UNKNOWN_FIELDS:" + ",".join(sorted(unknown)))
            for name, declared in {**contract.required_fields, **contract.optional_fields}.items():
                if name in row and not _valid_type(row[name], declared):
                    reasons.append(f"TYPE_MISMATCH:{name}:{declared}")
            if reasons:
                quarantine.append({"record": row, "quality_flags": sorted(reasons)})
            else:
                accepted.append({name: row.get(name) for name in sorted(allowed)})
        return RoutedBatch(raw_schema_version, contract.output_schema_version,
                           tuple(accepted), tuple(quarantine), contract.parser_implementation_hash)

    def route_mixed(self, objects: Iterable[tuple[str, Iterable[Mapping[str, object]]]],
                    *, dataset: str) -> tuple[RoutedBatch, ...]:
        return tuple(self.route(dataset=dataset, raw_schema_version=version, records=records)
                     for version, records in objects)

    def contracts(self) -> tuple[SchemaContract, ...]:
        return tuple(self._contracts[key] for key in sorted(self._contracts))


def publish_artifact_set(
    target: Path,
    artifacts: Mapping[str, bytes],
    root_manifest: bytes,
    *,
    fail_at: str | None = None,
) -> Path:
    """Publish a complete immutable directory; the root manifest is always last."""
    target = Path(target)
    if target.exists():
        raise FileExistsError(f"immutable artifact set already exists: {target}")
    stage = target.with_name(f".{target.name}.staging")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        for index, (relative, content) in enumerate(sorted(artifacts.items())):
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if fail_at == f"after_artifact_{index}":
                raise IncrementalError("INJECTED_DURING_ARTIFACT_PUBLICATION")
        if fail_at == "before_root_manifest":
            raise IncrementalError("INJECTED_BEFORE_ROOT_MANIFEST")
        (stage / "root_manifest.json").write_bytes(root_manifest)
        os.replace(stage, target)
        return target
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def canonical_table_hash(frame: pd.DataFrame, *, keys: Iterable[str]) -> str:
    """Hash logical table content, including schema, nulls, timezone and row ordering."""
    keys = tuple(keys)
    if set(keys) - set(frame.columns):
        raise ValueError("canonical hash keys are missing")
    columns = sorted(frame.columns)
    ordered = frame[columns].sort_values(list(keys), kind="stable", na_position="last").reset_index(drop=True)
    schema = {name: str(ordered[name].dtype) for name in columns}
    values = pd.util.hash_pandas_object(ordered, index=False).to_numpy().tobytes()
    return hashlib.sha256(canonical_json(schema).encode() + values).hexdigest()


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    node_type: str
    version: str
    input_hashes: tuple[str, ...]
    definition_hashes: tuple[str, ...]
    output_hash: str
    scope: Mapping[str, str]
    parents: tuple[str, ...] = ()
    downstream: tuple[str, ...] = ()
    build_state: BuildState = BuildState.UNAFFECTED
    parameters_hash: str = ""
    availability_policy: str = "PUBLISHED_AND_AVAILABLE_BY_CUTOFF"
    schema_version: str = ""
    environment_hash: str = ""


class DependencyGraph:
    def __init__(self, nodes: Iterable[DependencyNode]):
        materialized = list(nodes)
        self.nodes = {node.node_id: node for node in materialized}
        if len(self.nodes) != len(materialized):
            raise ValueError("duplicate dependency node")
        for node in self.nodes.values():
            missing = (set(node.parents) | set(node.downstream)) - set(self.nodes)
            if missing:
                raise ValueError(f"unknown dependency nodes: {sorted(missing)}")

    def descendants(self, seeds: Iterable[str]) -> set[str]:
        result = set(seeds)
        pending = list(seeds)
        while pending:
            current = pending.pop()
            for child in self.nodes[current].downstream:
                if child not in result:
                    result.add(child)
                    pending.append(child)
        return result


@dataclass(frozen=True)
class Change:
    change_id: str
    domain: str
    event_time: pd.Timestamp
    available_at: pd.Timestamp
    effective_from: pd.Timestamp | None = None
    instrument_id: str | None = None


def _stamp(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    result = pd.Timestamp(value)
    return result.tz_localize("UTC") if result.tzinfo is None else result


def directly_affected(node: DependencyNode, change: Change) -> bool:
    domains = set(filter(None, node.scope.get("depends_on", "").split(",")))
    if change.domain not in domains:
        return False
    cutoff = _stamp(node.scope.get("knowledge_cutoff"))
    if cutoff is not None and cutoff < change.available_at:
        return False
    start = _stamp(node.scope.get("window_start"))
    end = _stamp(node.scope.get("window_end"))
    if start is not None and change.event_time < start:
        return False
    if end is not None and change.event_time > end:
        return False
    effective = change.effective_from or change.event_time
    scope_start = _stamp(node.scope.get("effective_start"))
    scope_end = _stamp(node.scope.get("effective_end"))
    if scope_start is not None and effective < scope_start:
        return False
    if scope_end is not None and effective >= scope_end:
        return False
    scoped_instrument = node.scope.get("instrument_id")
    if scoped_instrument and change.instrument_id and scoped_instrument != change.instrument_id:
        return False
    return True


def plan_rebuild(graph: DependencyGraph, change: Change) -> dict[str, dict[str, str]]:
    direct = {node.node_id for node in graph.nodes.values() if directly_affected(node, change)}
    affected = graph.descendants(direct)
    plan: dict[str, dict[str, str]] = {}
    for node_id, node in sorted(graph.nodes.items()):
        if node_id in direct:
            state = BuildState.REBUILT_INPUT_CHANGED
            reason = f"DIRECT_{change.domain}_CHANGE_AVAILABLE_{change.available_at.isoformat()}"
        elif node_id in affected:
            state = BuildState.REBUILT_INPUT_CHANGED
            reason = "UPSTREAM_DEPENDENCY_CHANGED"
        else:
            state = BuildState.UNAFFECTED
            reason = "NO_CAUSAL_DEPENDENCY_INTERSECTION"
        plan[node_id] = {"state": state.value, "reason": reason}
    return plan


def impact_summary(graph: DependencyGraph, change: Change) -> dict[str, str | None]:
    plan = plan_rebuild(graph, change)
    cutoffs = []
    for node_id, decision in plan.items():
        node = graph.nodes[node_id]
        if (decision["state"] != BuildState.UNAFFECTED.value
                and node.node_type not in {"RAW_OBJECT_SET", "NORMALIZED_PARTITION"}
                and node.scope.get("knowledge_cutoff")):
            cutoffs.append(pd.Timestamp(node.scope["knowledge_cutoff"]))
    earliest = min(cutoffs) if cutoffs else None
    return {
        "change_id": change.change_id,
        "earliest_economic_time": change.event_time.isoformat(),
        "availability_time": change.available_at.isoformat(),
        "earliest_affected_downstream_time": None if earliest is None else earliest.isoformat(),
    }


def reusable(previous: DependencyNode, candidate: DependencyNode) -> bool:
    return (
        previous.node_type == candidate.node_type
        and previous.version == candidate.version
        and previous.input_hashes == candidate.input_hashes
        and previous.definition_hashes == candidate.definition_hashes
        and previous.parameters_hash == candidate.parameters_hash
        and previous.availability_policy == candidate.availability_policy
        and previous.schema_version == candidate.schema_version
        and previous.environment_hash == candidate.environment_hash
        and previous.output_hash == candidate.output_hash
    )


def execute_rebuild(
    previous: DependencyGraph,
    clean_candidate: DependencyGraph,
    plan: Mapping[str, Mapping[str, str]],
) -> tuple[DependencyGraph, tuple[dict[str, str], ...]]:
    """Apply a plan while proving every reuse against the clean candidate."""
    if set(previous.nodes) != set(clean_candidate.nodes) or set(plan) != set(clean_candidate.nodes):
        raise IncrementalError("DEPENDENCY_GRAPH_SHAPE_CHANGED")
    selected: list[DependencyNode] = []
    ledger: list[dict[str, str]] = []
    for node_id in sorted(clean_candidate.nodes):
        old = previous.nodes[node_id]
        candidate = clean_candidate.nodes[node_id]
        requested = BuildState(plan[node_id]["state"])
        if requested == BuildState.UNAFFECTED:
            if not reusable(old, candidate):
                raise IncrementalError(f"BLOCKED_DEPENDENCY_INVALID:{node_id}")
            selected.append(old)
            final_state = BuildState.REUSED_HASH_IDENTICAL
        else:
            selected.append(candidate)
            final_state = requested
        ledger.append({"node_id": node_id, "state": final_state.value,
                       "reason": plan[node_id]["reason"]})
    return DependencyGraph(selected), tuple(ledger)


def graph_equivalent(left: DependencyGraph, right: DependencyGraph) -> bool:
    """Compare canonical node outputs and all contract-relevant bindings."""
    if set(left.nodes) != set(right.nodes):
        return False
    return all(reusable(left.nodes[node_id], right.nodes[node_id])
               for node_id in left.nodes)
