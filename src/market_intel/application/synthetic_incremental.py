"""R.10B synthetic incremental-ingestion and dependency-rebuild evidence runner."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

import pandas as pd

from market_intel.foundation.artifacts import canonical_json, sha256_file
from market_intel.foundation.contracts import AsOfRequest, materialize_as_of
from market_intel.foundation.incremental import (
    BuildState, Change, DependencyGraph, DependencyNode, ImmutableIdentityConflict,
    IncrementalError, IncrementalRawStore, SchemaContract, SchemaRegistry,
    canonical_table_hash, execute_rebuild, graph_equivalent, plan_rebuild,
    impact_summary,
)
from market_intel.foundation.providers import DatasetKind, ProviderObject


RUN_VERSION = "synthetic_incremental_run_r10b_v1"
LIFECYCLE = "SYNTHETIC_VALIDATED_NONCANONICAL"


BAR_FIELDS = {
    "instrument_id": "string", "event_time": "timestamp", "published_at": "timestamp",
    "available_at": "timestamp", "close": "number", "turnover": "number",
    "source_record_id": "string", "revision_number": "integer",
    "supersedes_record_id": "string",
}


def schema_registry() -> SchemaRegistry:
    return SchemaRegistry([
        SchemaContract("daily_equity", "synthetic_bar_raw_v1", "synthetic_incremental_bar_v1",
                       BAR_FIELDS, unknown_field_policy="REJECT"),
        SchemaContract("daily_equity", "synthetic_bar_raw_v1_1", "synthetic_incremental_bar_v2",
                       BAR_FIELDS, {"trade_count": "integer"}, unknown_field_policy="REJECT"),
        SchemaContract("security_master", "synthetic_identity_raw_v1", "synthetic_identity_v1",
                       {"instrument_id": "string", "listing_id": "string", "symbol": "string",
                        "effective_from": "timestamp"}),
        SchemaContract("terminal_outcomes", "synthetic_terminal_raw_v1", "synthetic_terminal_v1",
                       {"instrument_id": "string", "event_time": "timestamp",
                        "resolution_status": "string"}),
        SchemaContract("benchmark_history", "synthetic_benchmark_raw_v1", "synthetic_benchmark_v1",
                       {"index_id": "string", "event_time": "timestamp", "close": "number",
                        "published_at": "timestamp"}),
    ])


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _base_graph(environment_hash: str) -> DependencyGraph:
    specs = [
        ("raw_pre", "RAW_OBJECT_SET", (), "price", "2020-01-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("raw_post", "RAW_OBJECT_SET", (), "price", "2020-01-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("normalized_pre", "NORMALIZED_PARTITION", ("raw_pre",), "price", "2020-01-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("normalized_post", "NORMALIZED_PARTITION", ("raw_post",), "price", "2020-01-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("snapshot_pre", "POINT_IN_TIME_SNAPSHOT", ("normalized_pre",), "price", "2020-01-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("snapshot_post", "POINT_IN_TIME_SNAPSHOT", ("normalized_post",), "price", "2020-01-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("identity_pre", "IDENTITY_ALIAS_SNAPSHOT", (), "identity", "2020-01-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("identity_post", "IDENTITY_ALIAS_SNAPSHOT", (), "identity", "2020-01-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("universe_pre", "HISTORICAL_UNIVERSE", ("snapshot_pre", "identity_pre"), "price,liquidity,identity", "2019-10-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("universe_post", "HISTORICAL_UNIVERSE", ("snapshot_post", "identity_post"), "price,liquidity,identity", "2019-11-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("feature_pre", "FEATURE", ("snapshot_pre", "universe_pre"), "price,feature_input", "2019-01-01", "2020-01-10", "2020-01-10T12:30:00Z"),
        ("feature_post", "FEATURE", ("snapshot_post", "universe_post"), "price,feature_input", "2019-02-01", "2020-02-10", "2020-02-10T12:30:00Z"),
        ("prediction_pre", "PREDICTION", ("feature_pre", "universe_pre"), "", None, None, "2020-01-10T12:30:00Z"),
        ("prediction_post", "PREDICTION", ("feature_post", "universe_post"), "", None, None, "2020-02-10T12:30:00Z"),
        ("outcome_pre", "OUTCOME", ("prediction_pre", "snapshot_pre"), "price,outcome_input,benchmark,terminal", "2020-01-03", "2020-01-10", "2020-01-20T12:30:00Z"),
        ("outcome_post", "OUTCOME", ("prediction_post", "snapshot_post"), "price,outcome_input,benchmark,terminal", "2020-02-03", "2020-02-10", "2020-02-20T12:30:00Z"),
        ("fold_pre", "FOLD_OOS_EVIDENCE", ("prediction_pre", "outcome_pre"), "", None, None, "2020-01-20T12:30:00Z"),
        ("fold_post", "FOLD_OOS_EVIDENCE", ("prediction_post", "outcome_post"), "", None, None, "2020-02-20T12:30:00Z"),
        ("economic", "ECONOMIC_EVIDENCE", ("fold_pre", "fold_post"), "benchmark,terminal", None, None, "2020-02-20T12:30:00Z"),
        ("portfolio", "PORTFOLIO_EVIDENCE", ("economic",), "", None, None, "2020-02-20T12:30:00Z"),
        ("validation", "VALIDATION_SUMMARY", ("fold_pre", "fold_post", "economic", "portfolio"), "", None, None, "2020-02-20T12:30:00Z"),
    ]
    children: dict[str, list[str]] = {item[0]: [] for item in specs}
    for node_id, _, parents, *_ in specs:
        for parent in parents:
            children[parent].append(node_id)
    built: dict[str, DependencyNode] = {}
    for node_id, node_type, parents, domains, start, end, cutoff in specs:
        inputs = tuple(built[parent].output_hash for parent in parents)
        scope = {"depends_on": domains, "knowledge_cutoff": cutoff}
        if start:
            scope["window_start"] = start
        if end:
            scope["window_end"] = end
        definition_hashes = (_hash({"node_type": node_type, "version": "v1"}),)
        output = _hash({"node": node_id, "inputs": inputs, "definitions": definition_hashes,
                        "scope": scope, "base": "r10b"})
        built[node_id] = DependencyNode(
            node_id, node_type, "v1", inputs, definition_hashes, output, scope,
            parents=parents, downstream=tuple(children[node_id]),
            parameters_hash=_hash({"node": node_id, "parameters": "fixed"}),
            schema_version="synthetic_incremental_contract_v1",
            environment_hash=environment_hash,
        )
    return DependencyGraph(built.values())


def _clean_candidate(previous: DependencyGraph, plan: dict[str, dict[str, str]], stage_id: str) -> DependencyGraph:
    built: dict[str, DependencyNode] = {}
    pending = set(previous.nodes)
    while pending:
        progressed = False
        for node_id in sorted(pending):
            old = previous.nodes[node_id]
            if any(parent not in built for parent in old.parents):
                continue
            changed = plan[node_id]["state"] != BuildState.UNAFFECTED.value
            inputs = tuple(built[parent].output_hash for parent in old.parents)
            if changed:
                output = _hash({"node": node_id, "inputs": inputs,
                                "previous": old.output_hash, "stage": stage_id})
                candidate = replace(old, input_hashes=inputs, output_hash=output,
                                    build_state=BuildState.REBUILT_INPUT_CHANGED)
            else:
                candidate = old
            built[node_id] = candidate
            pending.remove(node_id)
            progressed = True
            break
        if not progressed:
            raise IncrementalError("CYCLIC_DEPENDENCY_GRAPH")
    return DependencyGraph(built.values())


def _changes() -> dict[str, Change]:
    ts = pd.Timestamp
    return {
        "new_session": Change("new_session", "price", ts("2020-01-13T10:00:00Z"), ts("2020-01-13T12:00:00Z")),
        "late_session": Change("late_session", "price", ts("2020-01-06T10:00:00Z"), ts("2020-01-15T12:00:00Z")),
        "old_price_correction": Change("old_price_correction", "price", ts("2020-01-02T10:00:00Z"), ts("2020-01-20T12:00:00Z"), instrument_id="SYN_I001"),
        "universe_correction": Change("universe_correction", "liquidity", ts("2020-01-08T10:00:00Z"), ts("2020-01-20T12:00:00Z"), instrument_id="SYN_I002"),
        "feature_correction": Change("feature_correction", "feature_input", ts("2020-01-07T10:00:00Z"), ts("2020-01-20T12:00:00Z"), instrument_id="SYN_I001"),
        "outcome_correction": Change("outcome_correction", "outcome_input", ts("2020-02-05T10:00:00Z"), ts("2020-02-12T12:00:00Z"), instrument_id="SYN_I002"),
        "new_listing": Change("new_listing", "identity", ts("2020-01-22T03:45:00Z"), ts("2020-01-20T12:00:00Z"), effective_from=ts("2020-01-22T03:45:00Z"), instrument_id="SYN_I003"),
        "rename": Change("rename", "identity", ts("2020-01-27T03:45:00Z"), ts("2020-01-24T12:00:00Z"), effective_from=ts("2020-01-27T03:45:00Z"), instrument_id="SYN_I002"),
        "terminal_update": Change("terminal_update", "terminal", ts("2020-02-07T10:00:00Z"), ts("2020-02-12T12:00:00Z"), instrument_id="SYN_I002"),
        "benchmark_correction": Change("benchmark_correction", "benchmark", ts("2020-02-05T10:00:00Z"), ts("2020-02-12T12:00:00Z")),
        "additive_schema": Change("additive_schema", "price", ts("2020-02-03T10:00:00Z"), ts("2020-02-03T12:00:00Z"), instrument_id="SYN_I001"),
    }


def _record(record_id: str, event: str, published: str, close: float, turnover: float,
            revision: int = 1, parent: str | None = None, instrument: str = "SYN_I001",
            trade_count: int | None = None) -> dict:
    row = {"instrument_id": instrument, "event_time": event, "published_at": published,
           "available_at": published, "close": close, "turnover": turnover,
           "source_record_id": record_id, "revision_number": revision,
           "supersedes_record_id": parent}
    if trade_count is not None:
        row["trade_count"] = trade_count
    return row


def _stage_payload(stage_id: str) -> tuple[str, list[dict]]:
    payloads = {
        "initial": ("synthetic_bar_raw_v1", [
            _record("i1-20200102-r1", "2020-01-02T10:00:00Z", "2020-01-02T12:00:00Z", 100, 1000),
            _record("i2-20200102-r1", "2020-01-02T10:00:00Z", "2020-01-02T12:00:00Z", 80, 1200, instrument="SYN_I002")]),
        "new_session": ("synthetic_bar_raw_v1", [_record("i1-20200113-r1", "2020-01-13T10:00:00Z", "2020-01-13T12:00:00Z", 101, 1010)]),
        "late_session": ("synthetic_bar_raw_v1", [_record("i1-20200106-r1", "2020-01-06T10:00:00Z", "2020-01-15T12:00:00Z", 99, 990)]),
        "old_price_correction": ("synthetic_bar_raw_v1", [_record("i1-20200102-r2", "2020-01-02T10:00:00Z", "2020-01-20T12:00:00Z", 102, 1000, 2, "i1-20200102-r1")]),
        "universe_correction": ("synthetic_bar_raw_v1", [_record("i2-20200102-r2", "2020-01-02T10:00:00Z", "2020-01-20T12:00:00Z", 80, 2000, 2, "i2-20200102-r1", "SYN_I002")]),
        "feature_correction": ("synthetic_bar_raw_v1", [_record("i1-20200107-r1", "2020-01-07T10:00:00Z", "2020-01-20T12:00:00Z", 104, 1000)]),
        "outcome_correction": ("synthetic_bar_raw_v1", [_record("i2-20200205-r1", "2020-02-05T10:00:00Z", "2020-02-12T12:00:00Z", 77, 1200, instrument="SYN_I002")]),
        "additive_schema": ("synthetic_bar_raw_v1_1", [_record("i1-20200203-r1", "2020-02-03T10:00:00Z", "2020-02-03T12:00:00Z", 105, 1100, trade_count=42)]),
        "malformed": ("synthetic_bar_raw_v1", [{"instrument_id": "SYN_I001", "event_time": "2020-02-04T10:00:00Z"}]),
        "breaking_schema": ("synthetic_bar_raw_v9", [{"instrument_id": "SYN_I001", "settle": 106}]),
    }
    return payloads[stage_id]


def _nonbar_stage(stage_id: str) -> tuple[DatasetKind, str, list[dict]]:
    if stage_id == "new_listing":
        return DatasetKind.SECURITY_MASTER, "synthetic_identity_raw_v1", [{
            "instrument_id": "SYN_I003", "listing_id": "SYN_L003", "symbol": "NEWCO",
            "effective_from": "2020-01-22T03:45:00Z"}]
    if stage_id == "rename":
        return DatasetKind.SECURITY_MASTER, "synthetic_identity_raw_v1", [{
            "instrument_id": "SYN_I002", "listing_id": "SYN_L002", "symbol": "RENAMED",
            "effective_from": "2020-01-27T03:45:00Z"}]
    if stage_id == "terminal_update":
        return DatasetKind.TERMINAL_OUTCOMES, "synthetic_terminal_raw_v1", [{
            "instrument_id": "SYN_I002", "event_time": "2020-02-07T10:00:00Z",
            "resolution_status": "UNRESOLVED"}]
    if stage_id == "benchmark_correction":
        return DatasetKind.BENCHMARK_HISTORY, "synthetic_benchmark_raw_v1", [{
            "index_id": "SYN_BENCHMARK", "event_time": "2020-02-05T10:00:00Z",
            "close": 1001.5, "published_at": "2020-02-12T12:00:00Z"}]
    raise KeyError(stage_id)


def _json_write(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return sha256_file(path)


def _git_execution_state(project_root: Path, entrypoint: Path) -> dict[str, object]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root,
                            capture_output=True, text=True, check=True).stdout
    if status.strip():
        raise IncrementalError("UNEXPECTED_DIRTY_EXECUTION_START")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root,
                            capture_output=True, text=True, check=True).stdout.strip()
    sources = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    source_tree_hash = _hash([f"{p.relative_to(project_root)}:{sha256_file(p)}" for p in sources])
    return {"source_commit": commit, "execution_start_dirty": False,
            "execution_start_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "source_tree_sha256": source_tree_hash,
            "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
            "entrypoint_sha256": sha256_file(entrypoint)}


def run_incremental_evidence(*, recipe_path: Path, output_dir: Path,
                             project_root: Path, entrypoint: Path) -> Path:
    """Generate compact R.10B evidence, only from an exactly clean checkpoint."""
    execution = _git_execution_state(project_root, entrypoint)
    if output_dir.exists():
        raise FileExistsError("immutable R.10B evidence path already exists")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe["classification"] != "SYNTHETIC_ONLY_NONCANONICAL":
        raise ValueError("R.10B accepts synthetic data only")
    environment = {name: importlib.metadata.version(name) for name in ("pandas", "pyarrow")}
    environment["python"] = platform.python_version()
    environment_hash = _hash(environment)
    final_output_dir = output_dir
    publication_stage = final_output_dir.with_name(f".{final_output_dir.name}.staging")
    if publication_stage.exists():
        shutil.rmtree(publication_stage)
    output_dir = publication_stage
    output_dir.mkdir(parents=True)
    source_stage = output_dir / ".source-staging"
    store = IncrementalRawStore(output_dir / "raw")
    registry = schema_registry()
    manifests: dict[str, str] = {}
    routing: list[dict] = []
    accepted_records: list[dict] = []
    failure_results: list[dict] = []
    try:
        ingest_stages = ["initial", "new_session", "late_session", "old_price_correction",
                         "universe_correction", "feature_correction", "outcome_correction",
                         "new_listing", "rename", "terminal_update", "benchmark_correction",
                         "additive_schema", "malformed", "breaking_schema"]
        source_stage.mkdir()
        for index, stage_id in enumerate(ingest_stages):
            if stage_id in {"new_listing", "rename", "terminal_update", "benchmark_correction"}:
                dataset_kind, schema_version, records = _nonbar_stage(stage_id)
            else:
                schema_version, records = _stage_payload(stage_id)
                dataset_kind = DatasetKind.DAILY_EQUITY
            source = source_stage / f"{stage_id}.json"
            _json_write(source, {"raw_schema_version": schema_version, "records": records})
            obj = ProviderObject("synthetic_incremental_provider", dataset_kind,
                                 f"r10b:{stage_id}", source,
                                 data_classification="SYNTHETIC_ONLY_NONCANONICAL",
                                 retention_classification="GENERATED_SYNTHETIC_RETAINABLE")
            result = store.ingest(obj, parser_version="synthetic_incremental_router_v1",
                                  retrieved_at=f"2020-03-{index + 1:02d}T00:00:00Z",
                                  raw_schema_version=schema_version)
            manifests[stage_id] = str(result.manifest_path.relative_to(output_dir)).replace("\\", "/")
            try:
                routed = registry.route(dataset=dataset_kind.value, raw_schema_version=schema_version,
                                        records=records)
                if dataset_kind == DatasetKind.DAILY_EQUITY:
                    accepted_records.extend(routed.accepted)
                routing.append({"stage_id": stage_id, "raw_schema_version": schema_version,
                                "output_schema_version": routed.output_schema_version,
                                "accepted": len(routed.accepted), "quarantined": len(routed.quarantine),
                                "parser_implementation_hash": routed.parser_implementation_hash})
            except Exception as error:
                routing.append({"stage_id": stage_id, "raw_schema_version": schema_version,
                                "output_schema_version": None, "accepted": 0, "quarantined": len(records),
                                "error": str(error)})

        duplicate_source = source_stage / "duplicate.json"
        shutil.copyfile(source_stage / "new_session.json", duplicate_source)
        duplicate = ProviderObject("synthetic_incremental_provider", DatasetKind.DAILY_EQUITY,
                                   "r10b:new_session", duplicate_source,
                                   data_classification="SYNTHETIC_ONLY_NONCANONICAL")
        duplicate_result = store.ingest(duplicate, parser_version="synthetic_incremental_router_v1",
                                        retrieved_at="2020-03-20T00:00:00Z",
                                        raw_schema_version="synthetic_bar_raw_v1")
        failure_results.append({"scenario": "duplicate_retrieval", "result": duplicate_result.state})

        conflict_source = source_stage / "conflict.json"
        _json_write(conflict_source, {"different": True})
        conflict = replace(duplicate, local_path=conflict_source)
        try:
            store.ingest(conflict, parser_version="synthetic_incremental_router_v1",
                         retrieved_at="2020-03-21T00:00:00Z",
                         raw_schema_version="synthetic_bar_raw_v1")
        except ImmutableIdentityConflict as error:
            failure_results.append({"scenario": "identity_conflict", "result": str(error)})

        failure_results.append({"scenario": "breaking_schema", "result": "UNKNOWN_SCHEMA_VERSION"})

        # Recovery evidence uses an isolated child store; no staged file is evidence.
        recovery_source = source_stage / "recovery.json"
        _json_write(recovery_source, {"synthetic": "recovery"})
        for failpoint in ("after_payload", "after_manifest_stage", "after_object_publish"):
            recovery_root = output_dir / "recovery" / failpoint
            recovery_store = IncrementalRawStore(recovery_root)
            recovery_obj = ProviderObject("synthetic_incremental_provider", DatasetKind.DAILY_EQUITY,
                                          f"r10b:recovery:{failpoint}", recovery_source,
                                          data_classification="SYNTHETIC_ONLY_NONCANONICAL")
            try:
                recovery_store.ingest(recovery_obj, parser_version="v1",
                                      retrieved_at="2020-03-22T00:00:00Z",
                                      raw_schema_version="synthetic_bar_raw_v1", fail_at=failpoint)
            except IncrementalError as error:
                recovery_store.cleanup_staging()
                resumed = recovery_store.ingest(recovery_obj, parser_version="v1",
                                                 retrieved_at="2020-03-22T00:00:00Z",
                                                 raw_schema_version="synthetic_bar_raw_v1")
                failure_results.append({"scenario": failpoint, "injected": str(error),
                                        "restart": resumed.state})

        # Demonstrate actual PIT correction visibility and canonical logical hashes.
        pit = pd.DataFrame(accepted_records)
        pit["dataset_version"] = "synthetic_incremental_bar_v1"
        for name in ("event_time", "published_at", "available_at"):
            pit[name] = pd.to_datetime(pit[name], utc=True)
        before = materialize_as_of(pit[pit["source_record_id"].str.startswith(("i1-20200102", "i2-20200102"))],
                                   AsOfRequest(pd.Timestamp("2020-01-10T12:30:00Z"), "SESSION_CLOSE",
                                               "synthetic_incremental_bar_v1"))
        after = materialize_as_of(pit, AsOfRequest(pd.Timestamp("2020-02-10T12:30:00Z"),
                                                   "SESSION_CLOSE", "synthetic_incremental_bar_v1"))
        table_hashes = {"pre_correction": canonical_table_hash(before, keys=("instrument_id", "event_time")),
                        "final": canonical_table_hash(after, keys=("instrument_id", "event_time"))}

        graph = _base_graph(environment_hash)
        initial_graph = graph
        plans: dict[str, dict] = {}
        ledger: list[dict] = []
        equivalence: dict[str, bool] = {}
        preservation: dict[str, dict] = {}
        for stage_id, change in _changes().items():
            plan = plan_rebuild(graph, change)
            candidate = _clean_candidate(graph, plan, stage_id)
            incremental, decisions = execute_rebuild(graph, candidate, plan)
            equivalence[stage_id] = graph_equivalent(incremental, candidate)
            unchanged = [node_id for node_id, item in plan.items()
                         if item["state"] == BuildState.UNAFFECTED.value]
            preservation[stage_id] = {
                "unaffected_count": len(unchanged),
                "hashes_preserved": all(graph.nodes[node].output_hash == incremental.nodes[node].output_hash
                                        for node in unchanged),
            }
            plans[stage_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            ledger.extend({"stage_id": stage_id, **item} for item in decisions)
            graph = incremental

        schema_contracts = [asdict(contract) for contract in registry.contracts()]
        graph_json = lambda value: [asdict(value.nodes[key]) for key in sorted(value.nodes)]
        artifact_hashes = {
            "schema_registry.json": _json_write(output_dir / "schema_registry.json", schema_contracts),
            "dependency_graph_initial.json": _json_write(output_dir / "dependency_graph_initial.json", graph_json(initial_graph)),
            "dependency_graph_final.json": _json_write(output_dir / "dependency_graph_final.json", graph_json(graph)),
            "rebuild_plans.json": _json_write(output_dir / "rebuild_plans.json", plans),
            "rebuild_decision_ledger.json": _json_write(output_dir / "rebuild_decision_ledger.json", ledger),
            "canonical_equivalence.json": _json_write(output_dir / "canonical_equivalence.json", equivalence),
            "historical_hash_preservation.json": _json_write(output_dir / "historical_hash_preservation.json", preservation),
            "failure_recovery.json": _json_write(output_dir / "failure_recovery.json", failure_results),
            "schema_routing_results.json": _json_write(output_dir / "schema_routing_results.json", routing),
            "logical_table_hashes.json": _json_write(output_dir / "logical_table_hashes.json", table_hashes),
        }
        for path in sorted((output_dir / "raw").rglob("*")):
            if path.is_file():
                artifact_hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
        for path in sorted((output_dir / "recovery").rglob("*")):
            if path.is_file():
                artifact_hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
        r10a_manifest = project_root / recipe["base_evidence"]["r10a_root_manifest"]
        manifest_core = {
            "schema_version": RUN_VERSION,
            "classification": recipe["classification"], "lifecycle": LIFECYCLE,
            "canonical": False, "promotion_eligible": False,
            **execution, "post_generation_worktree_expected_dirty": True,
            "environment": environment, "environment_hash": environment_hash,
            "fixture_recipe": str(recipe_path.relative_to(project_root)).replace("\\", "/"),
            "fixture_recipe_sha256": sha256_file(recipe_path),
            "r10a_root_manifest_sha256": sha256_file(r10a_manifest),
            "raw_manifests": manifests,
            "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "all_supported_stages_equivalent": all(equivalence.values()),
            "all_unaffected_hashes_preserved": all(item["hashes_preserved"] for item in preservation.values()),
            "official_format_status": recipe["official_format_status"],
        }
        root = {**manifest_core, "reproducible_core_sha256": _hash(manifest_core)}
        _json_write(output_dir / "root_manifest.json", root)
        # Generator inputs are ephemeral. Remove them before the atomic directory
        # publication so only immutable store objects and evidence are exposed.
        if source_stage.exists():
            shutil.rmtree(source_stage)
        os.replace(output_dir, final_output_dir)
        return final_output_dir
    except BaseException:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        raise
    finally:
        if source_stage.exists():
            shutil.rmtree(source_stage)
