"""Prospective governance contracts and execution gateway for future research.

This module is dependency-neutral: it imports neither ``dtest`` nor
``market_intel``. It governs synthetic and future laboratory runners through
explicit, immutable artifacts. It does not execute any legacy hypothesis.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .legacy_ledger import canonical_json_bytes, sha256_bytes, sha256_file


GOVERNANCE_VERSION = "future_research_governance_v1"
FAMILY_CONTRACT_VERSION = "family_registry_contract_v1"
PREREGISTRATION_CONTRACT_VERSION = "preregistration_contract_v1"
INPUT_CONTRACT_VERSION = "input_declaration_contract_v1"
ROOT_MANIFEST_CONTRACT_VERSION = "root_run_manifest_contract_v1"
GOVERNED_EVIDENCE_CLASS = "GOVERNED_FUTURE_RESEARCH_EVIDENCE"
UNGOVERNED_CLASS = "UNGOVERNED_NONCANONICAL_OUTPUT"

EVENT_TYPES = {
    "FAMILY_REGISTERED", "PREREGISTRATION_CREATED", "PREREGISTRATION_LOCKED",
    "RUN_AUTHORIZED", "RUN_STARTED", "RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED",
    "VALIDATION_ACCESS_GRANTED", "TEST_ACCESS_GRANTED", "TEST_ACCESS_CONSUMED",
    "REPLICATION_REGISTERED", "PROMOTION_REJECTED", "PROMOTION_APPROVED",
    "FAMILY_SUPERSEDED", "FAMILY_RETIRED",
}

FAMILY_REQUIRED = (
    "family_id", "version", "economic_mechanism", "hypothesis_category",
    "parent_family", "registered_variants", "allowed_diagnostic_scope", "primary_metric",
    "outcome_horizon_sessions", "multiplicity_method", "significance_threshold",
    "minimum_effective_sample_size", "minimum_placebo_count", "declared_datasets",
    "required_capabilities", "allowed_research_splits", "current_lifecycle",
    "creation_event", "supersedes", "retirement_state",
)
PREREG_REQUIRED = (
    "experiment_id", "version", "family_id", "family_version", "economic_story",
    "selection_rule", "decision_clock", "entry_rule", "holding_horizon_sessions",
    "exit_overlay", "portfolio_construction", "benchmark_version",
    "cost_schedule_version", "population_scope", "security_identity_requirements",
    "corporate_action_requirements", "terminal_outcome_policy",
    "dataset_capability_requirements", "split_requested", "primary_metric",
    "secondary_diagnostics", "placebo_design", "permutation_draws",
    "dependence_treatment", "multiplicity_treatment", "promotion_threshold",
    "expected_artifacts", "code_entry_point", "expected_configuration",
    "research_classification", "seeds", "limited_data_non_promotable",
)
INPUT_REQUIRED = (
    "input_declaration_id", "version", "datasets", "security_master_version",
    "population_capability_assessment", "corporate_action_evidence_version",
    "terminal_outcome_policy_version", "benchmark_version", "cost_schedule_version",
    "calendar_version", "configuration_hash", "code_commit",
    "dirty_worktree", "dirty_worktree_fingerprint", "environment",
    "environment_fingerprint", "parser_versions", "feature_versions",
    "dataset_split_version",
)
ROOT_MANIFEST_REQUIRED = (
    "manifest_contract_version", "evidence_classification", "run_attempt_id",
    "experiment_id", "experiment_version", "family_id", "family_version",
    "preregistration_sha256", "authorization_event_sha256", "split_access_event",
    "code_commit", "dirty_worktree", "dirty_worktree_fingerprint",
    "environment_fingerprint", "configuration_hash", "input_declaration",
    "deterministic_seeds", "started_at", "completed_at", "runner_entry_point",
    "output_artifact_inventory", "unexpected_outputs", "completion_status",
    "sanitized_failure_category", "lifecycle_result", "promotion_eligible",
    "catalog_event_reference",
)
FORBIDDEN_HISTORICAL_INPUT_TOKENS = (
    "kite", "current_market", "current_tradable_only", "current quote",
    "current instrument",
)


class GovernanceError(ValueError):
    pass


class GovernedAbort(RuntimeError):
    """A runner may raise this to create an explicit aborted attempt."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def environment_declaration() -> dict[str, Any]:
    value = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable_name": Path(sys.executable).name,
    }
    return {"values": value, "sha256": canonical_hash(value)}


def _require_fields(value: Mapping[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in value]
    unresolved = [
        field for field in fields
        if field in value and (value[field] is None or value[field] == "")
    ]
    if missing or unresolved:
        raise GovernanceError(f"{label} incomplete: missing={missing}, unresolved={unresolved}")


def _require_presence(value: Mapping[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise GovernanceError(f"{label} incomplete: missing={missing}")


def _is_sha256(value: Any) -> bool:
    text = str(value)
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text.lower())


def _reject_current_market(value: Any) -> None:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    if any(token in text for token in FORBIDDEN_HISTORICAL_INPUT_TOKENS):
        raise GovernanceError("current Kite/current-market data cannot be historical evidence")


def validate_family(family: Mapping[str, Any]) -> None:
    _require_presence(family, FAMILY_REQUIRED, "family")
    _require_fields(
        family, tuple(field for field in FAMILY_REQUIRED if field not in {"parent_family", "supersedes"}),
        "family",
    )
    if int(family["outcome_horizon_sessions"]) < 1:
        raise GovernanceError("family outcome horizon must be positive")
    if int(family["minimum_placebo_count"]) < 1:
        raise GovernanceError("family placebo count must be positive")
    if not 0 < float(family["significance_threshold"]) < 1:
        raise GovernanceError("family significance threshold must be between zero and one")
    if not isinstance(family["registered_variants"], list) or not family["registered_variants"]:
        raise GovernanceError("family requires registered variants")
    if not isinstance(family["allowed_research_splits"], list) or not family["allowed_research_splits"]:
        raise GovernanceError("family requires allowed research splits")
    if family["current_lifecycle"] in {"RETIRED", "SUPERSEDED"}:
        raise GovernanceError("a retired or superseded family is not execution eligible")


def validate_preregistration(prereg: Mapping[str, Any]) -> None:
    _require_fields(prereg, PREREG_REQUIRED, "preregistration")
    if prereg["research_classification"] not in {"EXPLORATORY", "DIAGNOSTIC", "CONFIRMATORY"}:
        raise GovernanceError("invalid research classification")
    if int(prereg["holding_horizon_sessions"]) < 1:
        raise GovernanceError("holding horizon must be positive")
    if int(prereg["permutation_draws"]) < 1:
        raise GovernanceError("permutation draw count must be positive")
    if not isinstance(prereg["expected_artifacts"], list) or not prereg["expected_artifacts"]:
        raise GovernanceError("preregistration requires declared artifacts")
    paths = [str(item.get("relative_path", "")) for item in prereg["expected_artifacts"]]
    if any(not path for path in paths) or len(paths) != len(set(paths)):
        raise GovernanceError("expected artifact paths must be present and unique")
    if not isinstance(prereg["seeds"], list) or not prereg["seeds"]:
        raise GovernanceError("deterministic seeds are required")


def validate_input_declaration(
    declaration: Mapping[str, Any], prereg: Mapping[str, Any]
) -> bool:
    """Return whether dataset gates pass; limited exploratory scopes may continue."""
    _require_fields(declaration, INPUT_REQUIRED, "input declaration")
    _reject_current_market(declaration)
    datasets = declaration["datasets"]
    if not isinstance(datasets, list) or not datasets:
        raise GovernanceError("at least one immutable dataset declaration is required")
    for dataset in datasets:
        _require_fields(dataset, ("dataset_id", "version", "snapshot_sha256"), "dataset")
        if not _is_sha256(dataset["snapshot_sha256"]):
            raise GovernanceError("dataset snapshot hash is missing or invalid")
        if dataset.get("path") and not dataset.get("snapshot_sha256"):
            raise GovernanceError("mutable dataset paths require content hashes")
    for field in ("configuration_hash", "dirty_worktree_fingerprint", "environment_fingerprint"):
        if not _is_sha256(declaration[field]):
            raise GovernanceError(f"{field} must be SHA-256")
    if not isinstance(declaration["dirty_worktree"], bool):
        raise GovernanceError("dirty_worktree must be an explicit boolean")
    if declaration["environment_fingerprint"] != canonical_hash(declaration["environment"]):
        raise GovernanceError("environment fingerprint differs from the declared environment")
    for field in ("parser_versions", "feature_versions"):
        if not isinstance(declaration[field], Mapping) or not declaration[field]:
            raise GovernanceError(f"{field} must be a non-empty version mapping")
    expected_config = canonical_hash(prereg["expected_configuration"])
    if declaration["configuration_hash"] != expected_config:
        raise GovernanceError("input configuration hash differs from preregistration")
    if declaration["benchmark_version"] != prereg["benchmark_version"]:
        raise GovernanceError("benchmark version differs from preregistration")
    if declaration["cost_schedule_version"] != prereg["cost_schedule_version"]:
        raise GovernanceError("cost schedule differs from preregistration")
    required = list(prereg["dataset_capability_requirements"])
    statuses = declaration["population_capability_assessment"]
    failed = {name: statuses.get(name, "UNKNOWN") for name in required if statuses.get(name) != "PASS"}
    if not failed:
        return True
    limited = (
        prereg["research_classification"] == "EXPLORATORY"
        and prereg["limited_data_non_promotable"] is True
    )
    if not limited:
        raise GovernanceError(f"required dataset capabilities failed or unknown: {failed}")
    return False


class GovernanceCatalog:
    """Append-only JSONL event chain; detectable, not tamper-proof."""

    def __init__(self, path: str | Path, *, event_id_factory: Callable[[], str] | None = None):
        self.path = Path(path)
        self.event_id_factory = event_id_factory or (lambda: uuid.uuid4().hex)

    def allocate_event_id(self) -> str:
        return self.event_id_factory()

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        values = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise GovernanceError("governance catalog contains a non-object event")
                values.append(event)
        return values

    @staticmethod
    def verify(events: list[Mapping[str, Any]]) -> str | None:
        previous = None
        seen_ids: set[str] = set()
        for event in events:
            if event.get("event_id") in seen_ids:
                raise GovernanceError("duplicate governance event ID")
            seen_ids.add(str(event.get("event_id")))
            if event.get("previous_event_sha256") != previous:
                raise GovernanceError("governance hash-chain sequence break")
            body = dict(event)
            claimed = body.pop("event_sha256", None)
            calculated = canonical_hash(body)
            if claimed != calculated:
                raise GovernanceError("governance event hash mismatch")
            previous = claimed
        GovernanceCatalog._verify_event_sequence(events)
        return previous

    @staticmethod
    def _verify_event_sequence(events: list[Mapping[str, Any]]) -> None:
        by_type: dict[str, list[Mapping[str, Any]]] = {}
        for event in events:
            by_type.setdefault(str(event.get("event_type")), []).append(event)
            event_type = str(event.get("event_type"))
            refs = event.get("object_refs", {})
            prior = events[:events.index(event)]
            if event_type == "PREREGISTRATION_LOCKED" and not any(
                p.get("event_type") == "PREREGISTRATION_CREATED"
                and p.get("object_refs", {}).get("experiment_key") == refs.get("experiment_key")
                for p in prior
            ):
                raise GovernanceError("preregistration lock lacks creation event")
            if event_type == "RUN_AUTHORIZED" and not any(
                p.get("event_type") == "PREREGISTRATION_LOCKED"
                and p.get("object_refs", {}).get("experiment_key") == refs.get("experiment_key")
                for p in prior
            ):
                raise GovernanceError("run authorization lacks locked preregistration")
            if event_type == "RUN_STARTED" and not any(
                p.get("event_type") == "RUN_AUTHORIZED"
                and p.get("object_refs", {}).get("run_attempt_id") == refs.get("run_attempt_id")
                for p in prior
            ):
                raise GovernanceError("run start lacks authorization")
            if event_type in {"RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED"} and not any(
                p.get("event_type") == "RUN_STARTED"
                and p.get("object_refs", {}).get("run_attempt_id") == refs.get("run_attempt_id")
                for p in prior
            ):
                raise GovernanceError("run final event lacks start event")
            if event_type == "TEST_ACCESS_CONSUMED":
                authorization_id = refs.get("authorization_id")
                grants = [
                    p for p in prior if p.get("event_type") == "TEST_ACCESS_GRANTED"
                    and p.get("object_refs", {}).get("authorization_id") == authorization_id
                ]
                consumed = [
                    p for p in prior if p.get("event_type") == "TEST_ACCESS_CONSUMED"
                    and p.get("object_refs", {}).get("authorization_id") == authorization_id
                ]
                if len(grants) != 1 or consumed:
                    raise GovernanceError("test access is missing, ambiguous, or already consumed")

    def append(
        self, *, event_type: str, actor_classification: str,
        object_refs: Mapping[str, Any], object_hashes: Mapping[str, str],
        reason: str, resulting_state: str, timestamp: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise GovernanceError(f"unsupported governance event: {event_type}")
        existing = self.events()
        previous = self.verify(existing)
        event = {
            "event_id": event_id or self.allocate_event_id(),
            "timestamp": timestamp or utc_now(),
            "event_type": event_type,
            "actor_classification": actor_classification,
            "previous_event_sha256": previous,
            "object_refs": dict(object_refs),
            "object_hashes": dict(object_hashes),
            "reason": reason,
            "resulting_state": resulting_state,
        }
        event["event_sha256"] = canonical_hash(event)
        candidate = [*existing, event]
        self.verify(candidate)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json_bytes(event))
        return event


def _immutable_json(path: Path, value: Mapping[str, Any]) -> tuple[str, bool]:
    payload = canonical_json_bytes(value)
    if path.exists():
        if path.read_bytes() != payload:
            raise GovernanceError(f"immutable governed object differs: {path.name}")
        return sha256_bytes(payload), False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload), True


def register_family(
    family: Mapping[str, Any], *, registry_root: str | Path,
    catalog: GovernanceCatalog, actor: str, timestamp: str | None = None,
) -> tuple[Path, str]:
    validate_family(family)
    key = f"{family['family_id']}__{family['version']}"
    path = Path(registry_root) / f"{key}.json"
    object_hash, created = _immutable_json(path, family)
    if created:
        catalog.append(
            event_type="FAMILY_REGISTERED", actor_classification=actor,
            object_refs={"family_key": key}, object_hashes={"family_sha256": object_hash},
            reason="versioned family registration", resulting_state=family["current_lifecycle"],
            timestamp=timestamp,
        )
    return path, object_hash


def lock_preregistration(
    prereg: Mapping[str, Any], *, family_path: str | Path, prereg_root: str | Path,
    catalog: GovernanceCatalog, actor: str, timestamp: str | None = None,
) -> tuple[Path, str]:
    validate_preregistration(prereg)
    family = json.loads(Path(family_path).read_text(encoding="utf-8"))
    validate_family(family)
    if (prereg["family_id"], prereg["family_version"]) != (family["family_id"], family["version"]):
        raise GovernanceError("preregistration family does not match registry")
    if prereg["split_requested"] not in family["allowed_research_splits"]:
        raise GovernanceError("requested split is not registered for the family")
    if prereg["primary_metric"] != family["primary_metric"]:
        raise GovernanceError("preregistration primary metric differs from family")
    key = f"{prereg['experiment_id']}__{prereg['version']}"
    path = Path(prereg_root) / f"{key}.json"
    object_hash, created = _immutable_json(path, prereg)
    if created:
        refs = {"experiment_key": key, "family_key": f"{family['family_id']}__{family['version']}"}
        catalog.append(
            event_type="PREREGISTRATION_CREATED", actor_classification=actor,
            object_refs=refs, object_hashes={"preregistration_sha256": object_hash},
            reason="complete preregistration created", resulting_state="PREREGISTERED",
            timestamp=timestamp,
        )
        catalog.append(
            event_type="PREREGISTRATION_LOCKED", actor_classification=actor,
            object_refs=refs, object_hashes={"preregistration_sha256": object_hash},
            reason="preregistration locked before execution authorization",
            resulting_state="LOCKED", timestamp=timestamp,
        )
    return path, object_hash


def authorize_split_access(
    *, catalog: GovernanceCatalog, family: Mapping[str, Any], prereg: Mapping[str, Any],
    preregistration_sha256: str, dataset_split_version: str, split: str,
    reason: str, actor: str, timestamp: str | None = None,
    authorization_id: str | None = None,
) -> dict[str, Any]:
    if split not in {"validation", "test", "replication"}:
        raise GovernanceError("explicit access authorization is for validation/test/replication")
    family_key = f"{family['family_id']}__{family['version']}"
    experiment_key = f"{prereg['experiment_id']}__{prereg['version']}"
    if not any(
        event.get("event_type") == "PREREGISTRATION_LOCKED"
        and event.get("object_refs", {}).get("experiment_key") == experiment_key
        and event.get("object_hashes", {}).get("preregistration_sha256") == preregistration_sha256
        for event in catalog.events()
    ):
        raise GovernanceError("split access requires the exact locked preregistration")
    if split == "test" and any(
        event.get("event_type") == "TEST_ACCESS_GRANTED"
        and event.get("object_refs", {}).get("family_key") == family_key
        for event in catalog.events()
    ):
        raise GovernanceError("one-time test access already granted for this family version")
    event_type = {
        "validation": "VALIDATION_ACCESS_GRANTED",
        "test": "TEST_ACCESS_GRANTED",
        "replication": "REPLICATION_REGISTERED",
    }[split]
    auth_id = authorization_id or uuid.uuid4().hex
    return catalog.append(
        event_type=event_type, actor_classification=actor,
        object_refs={
            "authorization_id": auth_id, "family_key": family_key,
            "experiment_key": experiment_key, "split": split,
            "dataset_split_version": dataset_split_version,
        },
        object_hashes={"preregistration_sha256": preregistration_sha256},
        reason=reason, resulting_state=f"{split.upper()}_ACCESS_AUTHORIZED",
        timestamp=timestamp,
    )


def _matching_split_event(
    *, catalog: GovernanceCatalog, family_key: str, experiment_key: str,
    split: str, prereg_hash: str, dataset_split_version: str,
) -> dict[str, Any] | None:
    if split == "train":
        return None
    event_type = {
        "validation": "VALIDATION_ACCESS_GRANTED", "test": "TEST_ACCESS_GRANTED",
        "replication": "REPLICATION_REGISTERED",
    }.get(split)
    if event_type is None:
        raise GovernanceError(f"unsupported split: {split}")
    matches = [
        event for event in catalog.events()
        if event.get("event_type") == event_type
        and event.get("object_refs", {}).get("family_key") == family_key
        and event.get("object_refs", {}).get("experiment_key") == experiment_key
        and event.get("object_refs", {}).get("dataset_split_version") == dataset_split_version
        and event.get("object_hashes", {}).get("preregistration_sha256") == prereg_hash
    ]
    if len(matches) != 1:
        raise GovernanceError(f"{split} access requires one exact authorization event")
    if split == "test":
        auth_id = matches[0]["object_refs"]["authorization_id"]
        if any(
            event.get("event_type") == "TEST_ACCESS_CONSUMED"
            and event.get("object_refs", {}).get("authorization_id") == auth_id
            for event in catalog.events()
        ):
            raise GovernanceError("test authorization has already been consumed")
    return matches[0]


def _artifact_row_count(path: Path) -> int | None:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return sum(1 for _ in csv.reader(handle)) - 1
    if path.suffix.lower() == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return None


class GovernedExecutionGateway:
    def __init__(
        self, *, catalog: GovernanceCatalog, attempts_root: str | Path,
        runner_registry: Mapping[str, Callable[[Path, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]],
        actor: str = "LOCAL_RESEARCH_OPERATOR", clock: Callable[[], str] = utc_now,
        attempt_id_factory: Callable[[], str] | None = None,
    ):
        self.catalog = catalog
        self.attempts_root = Path(attempts_root)
        self.runner_registry = dict(runner_registry)
        self.actor = actor
        self.clock = clock
        self.attempt_id_factory = attempt_id_factory or (lambda: uuid.uuid4().hex)

    def run(
        self, *, family_path: str | Path, preregistration_path: str | Path,
        input_declaration_path: str | Path,
    ) -> Path:
        family = json.loads(Path(family_path).read_text(encoding="utf-8"))
        prereg = json.loads(Path(preregistration_path).read_text(encoding="utf-8"))
        inputs = json.loads(Path(input_declaration_path).read_text(encoding="utf-8"))
        validate_family(family)
        validate_preregistration(prereg)
        if (prereg["family_id"], prereg["family_version"]) != (family["family_id"], family["version"]):
            raise GovernanceError("family/preregistration mismatch")
        if prereg["split_requested"] not in family["allowed_research_splits"]:
            raise GovernanceError("split is not authorized by the family")
        prereg_hash = sha256_file(preregistration_path)
        family_hash = sha256_file(family_path)
        input_hash = canonical_hash(inputs)
        experiment_key = f"{prereg['experiment_id']}__{prereg['version']}"
        family_key = f"{family['family_id']}__{family['version']}"
        locked = [
            event for event in self.catalog.events()
            if event.get("event_type") == "PREREGISTRATION_LOCKED"
            and event.get("object_refs", {}).get("experiment_key") == experiment_key
            and event.get("object_hashes", {}).get("preregistration_sha256") == prereg_hash
        ]
        if len(locked) != 1:
            raise GovernanceError("execution requires one locked preregistration event")
        capability_pass = validate_input_declaration(inputs, prereg)
        split_event = _matching_split_event(
            catalog=self.catalog, family_key=family_key, experiment_key=experiment_key,
            split=prereg["split_requested"], prereg_hash=prereg_hash,
            dataset_split_version=inputs["dataset_split_version"],
        )
        entry_point = prereg["code_entry_point"]
        if entry_point not in self.runner_registry:
            raise GovernanceError("declared runner entry point is not registered")

        attempt_id = self.attempt_id_factory()
        temp_dir = self.attempts_root / f".tmp-{attempt_id}"
        final_dir = self.attempts_root / attempt_id
        if temp_dir.exists() or final_dir.exists() or any(
            event.get("object_refs", {}).get("run_attempt_id") == attempt_id
            for event in self.catalog.events()
        ):
            raise GovernanceError("duplicate run-attempt ID")
        temp_dir.mkdir(parents=True)
        authorization = self.catalog.append(
            event_type="RUN_AUTHORIZED", actor_classification=self.actor,
            object_refs={"run_attempt_id": attempt_id, "experiment_key": experiment_key,
                         "family_key": family_key, "split": prereg["split_requested"]},
            object_hashes={"preregistration_sha256": prereg_hash,
                           "family_sha256": family_hash, "input_declaration_sha256": input_hash},
            reason="governed preflight passed", resulting_state="AUTHORIZED",
            timestamp=self.clock(),
        )
        if prereg["split_requested"] == "test" and split_event is not None:
            split_event = self.catalog.append(
                event_type="TEST_ACCESS_CONSUMED", actor_classification=self.actor,
                object_refs={**split_event["object_refs"], "run_attempt_id": attempt_id},
                object_hashes={"preregistration_sha256": prereg_hash},
                reason="one-time test authorization consumed by governed attempt",
                resulting_state="TEST_ACCESS_CONSUMED", timestamp=self.clock(),
            )
        started_at = self.clock()
        self.catalog.append(
            event_type="RUN_STARTED", actor_classification=self.actor,
            object_refs={"run_attempt_id": attempt_id, "experiment_key": experiment_key,
                         "family_key": family_key},
            object_hashes={"authorization_event_sha256": authorization["event_sha256"]},
            reason="declared runner started", resulting_state="RUNNING", timestamp=started_at,
        )

        completion_status = "COMPLETED"
        failure_category = None
        result: Mapping[str, Any] = {}
        try:
            result = self.runner_registry[entry_point](temp_dir, prereg, inputs) or {}
        except GovernedAbort:
            completion_status = "ABORTED"
            failure_category = "RUNNER_DECLARED_ABORT"
        except Exception:
            completion_status = "FAILED"
            failure_category = "SANITIZED_RUNNER_FAILURE"

        declared_paths = {str(item["relative_path"]): item for item in prereg["expected_artifacts"]}
        inventory = []
        missing_required = []
        for relative, definition in declared_paths.items():
            path = (temp_dir / relative).resolve()
            try:
                path.relative_to(temp_dir.resolve())
            except ValueError as exc:
                raise GovernanceError("declared output escapes attempt directory") from exc
            if not path.is_file():
                if definition.get("required", True):
                    missing_required.append(relative)
                continue
            inventory.append({
                "name": definition.get("name", relative), "relative_path": relative,
                "sha256": sha256_file(path), "byte_size": path.stat().st_size,
                "row_count": _artifact_row_count(path), "canonical": True,
            })
        if completion_status == "COMPLETED" and missing_required:
            completion_status = "FAILED"
            failure_category = "DECLARED_ARTIFACT_MISSING"
        all_files = [
            path for path in temp_dir.rglob("*") if path.is_file() and path.name != "root_manifest.json"
        ]
        unexpected = sorted(
            str(path.relative_to(temp_dir)).replace("\\", "/")
            for path in all_files
            if str(path.relative_to(temp_dir)).replace("\\", "/") not in declared_paths
        )
        final_event_type = {
            "COMPLETED": "RUN_COMPLETED", "FAILED": "RUN_FAILED", "ABORTED": "RUN_ABORTED"
        }[completion_status]
        final_event_id = self.catalog.allocate_event_id()
        promotion_eligible = False
        lifecycle_result = str(result.get("lifecycle_result", "PRODUCTION_INELIGIBLE"))
        manifest = {
            "manifest_contract_version": ROOT_MANIFEST_CONTRACT_VERSION,
            "evidence_classification": GOVERNED_EVIDENCE_CLASS,
            "run_attempt_id": attempt_id,
            "experiment_id": prereg["experiment_id"], "experiment_version": prereg["version"],
            "family_id": family["family_id"], "family_version": family["version"],
            "preregistration_sha256": prereg_hash,
            "authorization_event_sha256": authorization["event_sha256"],
            "split_access_event": None if split_event is None else {
                "event_id": split_event["event_id"], "event_sha256": split_event["event_sha256"]
            },
            "code_commit": inputs["code_commit"],
            "dirty_worktree": inputs["dirty_worktree"],
            "dirty_worktree_fingerprint": inputs["dirty_worktree_fingerprint"],
            "environment_fingerprint": inputs["environment_fingerprint"],
            "configuration_hash": inputs["configuration_hash"],
            "input_declaration": {"sha256": input_hash, "value": inputs},
            "deterministic_seeds": list(prereg["seeds"]),
            "started_at": started_at, "completed_at": self.clock(),
            "runner_entry_point": entry_point,
            "output_artifact_inventory": sorted(inventory, key=lambda item: item["relative_path"]),
            "missing_required_outputs": sorted(missing_required),
            "unexpected_outputs": unexpected,
            "completion_status": completion_status,
            "sanitized_failure_category": failure_category,
            "lifecycle_result": lifecycle_result,
            "dataset_capability_gate_passed": capability_pass,
            "promotion_eligible": promotion_eligible,
            "catalog_event_reference": {"event_id": final_event_id, "event_type": final_event_type},
        }
        _require_presence(manifest, ROOT_MANIFEST_REQUIRED, "root manifest")
        manifest_path = temp_dir / "root_manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        manifest_hash = sha256_file(manifest_path)
        self.attempts_root.mkdir(parents=True, exist_ok=True)
        os.replace(temp_dir, final_dir)
        self.catalog.append(
            event_type=final_event_type, actor_classification=self.actor,
            object_refs={"run_attempt_id": attempt_id, "experiment_key": experiment_key,
                         "family_key": family_key, "manifest_relative_path": f"{attempt_id}/root_manifest.json"},
            object_hashes={"root_manifest_sha256": manifest_hash},
            reason=f"governed attempt {completion_status.lower()}",
            resulting_state=completion_status, timestamp=manifest["completed_at"],
            event_id=final_event_id,
        )
        return final_dir


def label_ungoverned_output(path: str | Path, *, reason: str) -> Path:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / "noncanonical_output.json"
    value = {"classification": UNGOVERNED_CLASS, "reason": reason, "promotion_eligible": False}
    if marker.exists() and json.loads(marker.read_text(encoding="utf-8")) != value:
        raise GovernanceError("ungoverned output marker cannot be silently changed")
    if not marker.exists():
        marker.write_bytes(canonical_json_bytes(value))
    return marker
