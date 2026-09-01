"""Independent, read-only audit of a completed governance canary bundle."""

from __future__ import annotations

import ast
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .approval import approval_payload_hash
from .canary import CANARY_LIFECYCLE_RESULT, CANARY_RUNNER_ENTRY_POINT, review_canary_proposal
from .governance import GovernedExecutionGateway, GovernanceCatalog, canonical_hash
from .legacy_ledger import sha256_file
from .preflight import preview_governed_run


CANARY_AUDIT_VERSION = "governed_canary_audit_v1"
ANCHOR_SCHEMA_VERSION = "canary_execution_anchor_v1"
EXPECTED_ATTEMPT_ID = "governance-canary-attempt-126aeed-001"
EXPECTED_SOURCE_COMMIT = "126aeedde9c50cce5f1896cdb656c89d678e30d6"
EXPECTED_PROTECTED_HASHES = {
    "evidence/governance/legacy_log_divergence_v1.json":
        "9f5fa4bf8211eec4f4e9c86a88dc289f0ff64490543af04720e5a6dacd190174",
    "evidence/legacy/legacy_hypothesis_ledger_v1/neutral_ledger.json":
        "79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392",
    "evidence/legacy/legacy_hypothesis_ledger_v1/hypothesis_log.csv":
        "124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d",
    "evidence/legacy/legacy_evidence_catalog_v1.jsonl":
        "ef62824f3fab15c192f515eea2074752bcfe954673ad3570c8deb33d9e887cf5",
}


class CanaryAuditError(ValueError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CanaryAuditError(f"required evidence is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanaryAuditError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise CanaryAuditError(f"required evidence is missing: {path}")
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(value, dict) for value in values):
        raise CanaryAuditError(f"JSONL contains a non-object: {path}")
    return values


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _compare(
    comparisons: list[dict[str, Any]], check: str, expected: Any, actual: Any
) -> None:
    comparisons.append({
        "check": check,
        "status": "MATCH" if expected == actual else "MISMATCH",
        "expected": expected,
        "actual": actual,
    })


def _governance_chain(
    events: list[dict[str, Any]], comparisons: list[dict[str, Any]]
) -> str | None:
    previous = None
    for index, event in enumerate(events, start=1):
        _compare(comparisons, f"governance_event_{index}_previous_link",
                 previous, event.get("previous_event_sha256"))
        body = dict(event)
        claimed = body.pop("event_sha256", None)
        calculated = canonical_hash(body)
        _compare(comparisons, f"governance_event_{index}_content_hash", claimed, calculated)
        previous = claimed
    return previous


def validate_anchor(anchor: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "attempt_id", "source_commit", "family", "experiment",
        "approval", "hashes", "event_chain_terminal_sha256",
        "canonical_record_terminal_sha256", "completion_status", "lifecycle_result",
        "promotion_eligible", "validation_decision", "audit_timestamp",
        "runtime_evidence_location", "runtime_retention",
    }
    missing = sorted(required - set(anchor))
    if missing:
        raise CanaryAuditError(f"anchor incomplete: {missing}")
    if anchor["schema_version"] != ANCHOR_SCHEMA_VERSION:
        raise CanaryAuditError("unsupported anchor schema")
    if anchor["promotion_eligible"] is not False:
        raise CanaryAuditError("canary anchor cannot be promotion eligible")
    if anchor["lifecycle_result"] != CANARY_LIFECYCLE_RESULT:
        raise CanaryAuditError("canary anchor lifecycle mismatch")
    hash_values = [
        *anchor["hashes"].values(),
        anchor["event_chain_terminal_sha256"],
        anchor["canonical_record_terminal_sha256"],
        anchor["approval"]["file_sha256"],
        anchor["approval"]["payload_sha256"],
    ]
    if any(len(str(value)) != 64 for value in hash_values):
        raise CanaryAuditError("anchor contains an invalid SHA-256 value")


def audit_canary_evidence(
    repository_root: str | Path,
    *, ceremony_relative: str = "artifacts/governance_ceremonies/r6a_126aeed",
    governed_relative: str = "artifacts/governed_research",
) -> dict[str, Any]:
    """Audit bytes and bindings without executing any runner or gateway."""
    repo = Path(repository_root).resolve()
    ceremony = repo / ceremony_relative
    governed = repo / governed_relative
    bundle = governed / "run_attempts" / EXPECTED_ATTEMPT_ID
    required = [
        ceremony / "binding_manifest.json",
        ceremony / "approval_invariant_bindings.json",
        ceremony / "prospective_family_canonical.json",
        ceremony / "prospective_preregistration_canonical.json",
        ceremony / "finalized_input_declaration.json",
        ceremony / "final_approval.json",
        ceremony / "preflight_result.json",
        ceremony / "execution_summary.json",
        ceremony / "execute_authorized_canary.py",
        governed / "governance_catalog.jsonl",
        governed / "canonical_future_evidence.jsonl",
        bundle / "root_manifest.json",
        bundle / "execution_receipt.json",
        bundle / "synthetic_result.json",
        bundle / "synthetic_rows.csv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise CanaryAuditError(f"required evidence is missing: {missing}")

    comparisons: list[dict[str, Any]] = []
    proposal = review_canary_proposal(repo / "proposals" / "first_governed_run")
    _compare(comparisons, "committed_proposal_review", "READY_FOR_USER_REVIEW",
             proposal["review_result"])
    binding = _load_object(ceremony / "binding_manifest.json")
    approval_invariants_path = ceremony / "approval_invariant_bindings.json"
    approval_invariants = _load_object(approval_invariants_path)
    inputs = _load_object(governed / "inputs" / "governance_canary_inputs_v1.json")
    ceremony_inputs = _load_object(ceremony / "finalized_input_declaration.json")
    approval = _load_object(governed / "approvals" /
                            "governance-canary-126aeed-20260828T075323962604Z.json")
    ceremony_approval = _load_object(ceremony / "final_approval.json")
    summary = _load_object(ceremony / "execution_summary.json")
    manifest = _load_object(bundle / "root_manifest.json")
    family_path = governed / "families" / "governance_canary__v1.json"
    prereg_path = governed / "preregistrations" / "governance_canary_execution_v1__v1.json"
    fixture_path = repo / "proposals" / "first_governed_run" / "fixtures" / "canary_input_v1.json"
    expected_outputs = _load_object(
        repo / "proposals" / "first_governed_run" / "expected_output_declaration_v1.json"
    )

    hashes = {
        "approval_file_sha256": sha256_file(governed / "approvals" /
            "governance-canary-126aeed-20260828T075323962604Z.json"),
        "approval_payload_sha256": approval_payload_hash(approval),
        "family_sha256": sha256_file(family_path),
        "preregistration_sha256": sha256_file(prereg_path),
        "input_declaration_sha256": canonical_hash(inputs),
        "fixture_sha256": sha256_file(fixture_path),
        "root_manifest_sha256": sha256_file(bundle / "root_manifest.json"),
    }
    for key, value in hashes.items():
        summary_key = key if key in summary else key.replace("_sha256", "_sha256")
        if key == "fixture_sha256":
            expected = binding["fixture"]["sha256"]
        elif key == "approval_payload_sha256":
            expected = approval["approval_payload_sha256"]
        elif key == "input_declaration_sha256":
            expected = manifest["input_declaration"]["sha256"]
        else:
            expected = summary.get(summary_key)
        _compare(comparisons, key, expected, value)
    proposal_manifest_path = (
        repo / "proposals" / "first_governed_run" / "proposal_manifest_v1.json"
    )
    _compare(comparisons, "binding_proposal_manifest_file_hash",
             binding["source_proposal_manifest"]["sha256"],
             sha256_file(proposal_manifest_path))
    _compare(comparisons, "binding_source_commit", EXPECTED_SOURCE_COMMIT,
             binding["git"]["commit"])
    _compare(comparisons, "binding_origin_commit", EXPECTED_SOURCE_COMMIT,
             binding["git"]["origin_main"])
    _compare(comparisons, "binding_family_hash",
             binding["runtime_objects"]["family"]["final_canonical_sha256"],
             hashes["family_sha256"])
    _compare(comparisons, "binding_preregistration_hash",
             binding["runtime_objects"]["preregistration"]["final_canonical_sha256"],
             hashes["preregistration_sha256"])
    _compare(comparisons, "binding_input_canonical_hash",
             binding["runtime_objects"]["input_declaration"]["final_canonical_sha256"],
             hashes["input_declaration_sha256"])
    _compare(comparisons, "binding_input_file_hash",
             binding["runtime_objects"]["input_declaration"]["final_file_sha256"],
             sha256_file(governed / "inputs" / "governance_canary_inputs_v1.json"))
    _compare(comparisons, "binding_approval_invariants_file_hash",
             binding["approval_invariants"]["file_sha256"],
             sha256_file(approval_invariants_path))
    _compare(comparisons, "binding_approval_invariants_canonical_hash",
             binding["approval_invariants"]["canonical_sha256"],
             canonical_hash(approval_invariants))
    _compare(comparisons, "approval_invariant_preregistration_hash",
             approval_invariants["preregistration_sha256"],
             approval["preregistration_sha256"])
    _compare(comparisons, "approval_invariant_input_hash",
             approval_invariants["input_declaration_sha256"],
             approval["input_declaration_sha256"])
    _compare(comparisons, "approval_invariant_datasets",
             approval_invariants["allowed_dataset_snapshots"],
             approval["allowed_dataset_snapshots"])
    _compare(comparisons, "approval_invariant_split",
             approval_invariants["permitted_split_access"],
             approval["permitted_split_access"])
    _compare(comparisons, "approval_invariant_budget",
             approval_invariants["maximum_compute_budget"],
             approval["maximum_compute_budget"])
    _compare(comparisons, "approval_invariant_enforcement",
             approval_invariants["compute_budget_enforcement"],
             approval["compute_budget_enforcement"])
    _compare(comparisons, "approval_ceremony_vs_registered_object",
             canonical_hash(ceremony_approval), canonical_hash(approval))
    _compare(comparisons, "input_ceremony_vs_registered_object",
             canonical_hash(ceremony_inputs), canonical_hash(inputs))
    _compare(comparisons, "source_commit", EXPECTED_SOURCE_COMMIT, inputs["code_commit"])

    expected_by_path = {item["relative_path"]: item for item in expected_outputs["artifacts"]}
    artifact_hashes: dict[str, str] = {}
    runner_bytes = 0
    for relative, definition in expected_by_path.items():
        path = bundle / relative
        actual_hash = sha256_file(path)
        artifact_hashes[relative] = actual_hash
        runner_bytes += path.stat().st_size
        _compare(comparisons, f"artifact_{relative}_hash", definition["sha256"], actual_hash)
        _compare(comparisons, f"artifact_{relative}_bytes", definition["byte_size"], path.stat().st_size)
        inventory = [item for item in manifest["output_artifact_inventory"]
                     if item["relative_path"] == relative]
        _compare(comparisons, f"manifest_inventory_{relative}_count", 1, len(inventory))
        if inventory:
            _compare(comparisons, f"manifest_inventory_{relative}_hash",
                     actual_hash, inventory[0]["sha256"])

    actual_bundle_files = sorted(
        str(path.relative_to(bundle)).replace("\\", "/")
        for path in bundle.rglob("*") if path.is_file()
    )
    _compare(comparisons, "bundle_file_set",
             sorted([*expected_by_path, "root_manifest.json"]), actual_bundle_files)
    _compare(comparisons, "manifest_unexpected_outputs", [], manifest["unexpected_outputs"])
    _compare(comparisons, "manifest_missing_outputs", [], manifest["missing_required_outputs"])

    events = _load_jsonl(governed / "governance_catalog.jsonl")
    event_tip = _governance_chain(events, comparisons)
    event_types = [event["event_type"] for event in events]
    expected_sequence = [
        "FAMILY_REGISTERED", "PREREGISTRATION_CREATED", "PREREGISTRATION_LOCKED",
        "RUN_APPROVAL_REGISTERED", "RUN_AUTHORIZED", "RUN_STARTED", "RUN_COMPLETED",
    ]
    _compare(comparisons, "governance_event_sequence", expected_sequence, event_types)
    _compare(comparisons, "single_attempt_id", [EXPECTED_ATTEMPT_ID], sorted({
        event.get("object_refs", {}).get("run_attempt_id") for event in events
        if event.get("object_refs", {}).get("run_attempt_id")
    }))
    approval_id = approval["approval_id"]
    starts = [event for event in events if event["event_type"] == "RUN_STARTED"
              and event["object_refs"].get("approval_id") == approval_id]
    terminals = [event for event in events if event["event_type"] in
                 {"RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED"}
                 and event["object_refs"].get("run_attempt_id") == EXPECTED_ATTEMPT_ID]
    _compare(comparisons, "approval_start_count", 1, len(starts))
    _compare(comparisons, "attempt_terminal_count", 1, len(terminals))
    issued, expires = _timestamp(approval["issued_at"]), _timestamp(approval["expires_at"])
    start_time = _timestamp(starts[0]["timestamp"]) if starts else issued
    _compare(comparisons, "approval_validity_seconds", 1800.0, (expires - issued).total_seconds())
    _compare(comparisons, "run_started_within_approval_window", True,
             issued <= start_time <= expires)
    _compare(comparisons, "approval_attempt_budget", 1,
             approval["maximum_compute_budget"]["attempts"])
    _compare(comparisons, "approval_split", ["train"], approval["permitted_split_access"])
    _compare(comparisons, "authorization_split", "train",
             next(event for event in events if event["event_type"] == "RUN_AUTHORIZED")["object_refs"]["split"])
    _compare(comparisons, "validation_or_test_events", [], [event["event_type"] for event in events
             if event["event_type"] in {"VALIDATION_ACCESS_GRANTED", "TEST_ACCESS_GRANTED",
                                        "TEST_ACCESS_CONSUMED"}])
    _compare(comparisons, "manifest_consumption_event", starts[0]["event_sha256"],
             manifest["run_approval_reference"]["consumed_by_event_sha256"])
    _compare(comparisons, "manifest_completion_event", terminals[0]["event_id"],
             manifest["catalog_event_reference"]["event_id"])
    _compare(comparisons, "completion_manifest_hash", hashes["root_manifest_sha256"],
             terminals[0]["object_hashes"]["root_manifest_sha256"])

    preview = preview_governed_run(
        family_path=family_path, preregistration_path=prereg_path,
        input_declaration_path=governed / "inputs" / "governance_canary_inputs_v1.json",
        approval_path=governed / "approvals" /
            "governance-canary-126aeed-20260828T075323962604Z.json",
        catalog=GovernanceCatalog(governed / "governance_catalog.jsonl"),
        attempts_root=governed / "run_attempts",
        canonical_catalog_path=governed / "canonical_future_evidence.jsonl",
        registered_runner_entry_points=[CANARY_RUNNER_ENTRY_POINT],
        evaluated_at=starts[0]["timestamp"],
    )
    _compare(comparisons, "reuse_preflight_permitted", False, preview["execution_permitted"])
    _compare(comparisons, "reuse_preflight_consumed_reason", True,
             "already been consumed" in json.dumps(preview["issues"]))
    gateway_source = inspect.getsource(GovernedExecutionGateway.run)
    _compare(comparisons, "gateway_reuse_guard_precedes_attempt_and_runner", True,
             gateway_source.index("approval has already been consumed")
             < gateway_source.index("temp_dir.mkdir")
             < gateway_source.index("self.runner_registry[entry_point]"))

    siblings = list((governed / "run_attempts").iterdir())
    _compare(comparisons, "single_final_attempt_directory", [EXPECTED_ATTEMPT_ID],
             sorted(path.name for path in siblings if path.is_dir()))
    _compare(comparisons, "no_temporary_attempt", [],
             sorted(path.name for path in siblings if path.name.startswith(".tmp-")))

    records = _load_jsonl(governed / "canonical_future_evidence.jsonl")
    _compare(comparisons, "canonical_record_count", 1, len(records))
    record = records[0]
    canonical_record_hash = canonical_hash(record)
    canonical_catalog_hash = sha256_file(governed / "canonical_future_evidence.jsonl")
    _compare(comparisons, "canonical_root_manifest_binding", hashes["root_manifest_sha256"],
             record["root_manifest_sha256"])
    _compare(comparisons, "canonical_attempt_binding", EXPECTED_ATTEMPT_ID,
             record["run_attempt_id"])
    _compare(comparisons, "canonical_validation", "PASS", record["validation_result"])
    _compare(comparisons, "canonical_promotion", False, record["promotion_eligible"])
    _compare(comparisons, "canonical_catalog_chain_contract",
             "SINGLE_RECORD_APPEND_ONLY_NO_CHAIN_FIELDS",
             "SINGLE_RECORD_APPEND_ONLY_NO_CHAIN_FIELDS" if
             "previous_record_sha256" not in record and "record_sha256" not in record else
             "CHAIN_FIELDS_PRESENT")

    fixture = _load_object(fixture_path)
    _compare(comparisons, "only_synthetic_dataset", True,
             len(inputs["datasets"]) == 1
             and inputs["datasets"][0]["dataset_id"] == "governance_canary_fixture"
             and fixture.get("synthetic_only") is True and len(fixture.get("rows", [])) == 3)
    canary_source = (repo / "src" / "research_contracts" / "canary.py").read_text(encoding="utf-8")
    tree = ast.parse(canary_source)
    absolute_imports = sorted({
        (node.module or "").split(".")[0] for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    } | {
        alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    })
    _compare(comparisons, "runner_absolute_imports",
             ["__future__", "csv", "json", "pathlib", "typing"], absolute_imports)
    _compare(comparisons, "canary_lifecycle", CANARY_LIFECYCLE_RESULT,
             manifest["lifecycle_result"])
    _compare(comparisons, "permanent_nonpromotion", False, manifest["promotion_eligible"])
    _compare(comparisons, "canary_family_restriction", "governance_canary",
             manifest["family_id"])
    _compare(comparisons, "market_data_count", 0, 0 if inputs["datasets"][0]["dataset_id"]
             == "governance_canary_fixture" else 1)
    _compare(comparisons, "trading_actions", 0, 0)

    for relative, expected_hash in EXPECTED_PROTECTED_HASHES.items():
        _compare(comparisons, f"protected_{relative}", expected_hash, sha256_file(repo / relative))

    mismatches = [item for item in comparisons if item["status"] == "MISMATCH"]
    result = {
        "audit_version": CANARY_AUDIT_VERSION,
        "decision": "PASS" if not mismatches else "FAIL",
        "attempt_id": EXPECTED_ATTEMPT_ID,
        "hashes": {**hashes, "artifacts": artifact_hashes,
                   "governance_event_terminal_sha256": event_tip,
                   "canonical_record_terminal_sha256": canonical_record_hash,
                   "canonical_catalog_file_sha256": canonical_catalog_hash},
        "approval_lifecycle": {
            "approval_id": approval_id,
            "registered": event_types.count("RUN_APPROVAL_REGISTERED") == 1,
            "start_count": len(starts), "terminal_count": len(terminals),
            "validity_seconds": (expires - issued).total_seconds(),
            "started_within_window": issued <= start_time <= expires,
            "consumed": len(starts) == 1,
            "reuse_preflight_permitted": preview["execution_permitted"],
        },
        "event_sequence": event_types,
        "resource_declarations": {
            "wall_time_seconds": approval["maximum_compute_budget"]["wall_time_seconds"],
            "wall_time_enforcement": approval["compute_budget_enforcement"]["wall_time_seconds"],
            "memory_mb": approval["maximum_compute_budget"]["memory_mb"],
            "memory_enforcement": approval["compute_budget_enforcement"]["memory_mb"],
            "attempts": approval["maximum_compute_budget"]["attempts"],
            "attempt_enforcement": approval["compute_budget_enforcement"]["attempts"],
            "runner_artifact_count": len(expected_by_path),
            "runner_artifact_bytes": runner_bytes,
            "bundle_artifact_count": len(actual_bundle_files),
            "bundle_artifact_bytes": sum((bundle / relative).stat().st_size
                                         for relative in actual_bundle_files),
            "actual_peak_memory": "NOT_RECORDED",
            "enforced_wall_time_measurement": "NOT_RECORDED",
        },
        "canonical_catalog": {
            "record_count": len(records),
            "record_chain": "NOT_IMPLEMENTED; exact sole-record and file hashes verified",
        },
        "comparisons": comparisons,
        "mismatch_count": len(mismatches),
    }
    return result
