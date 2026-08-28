"""Deterministic, non-substantive infrastructure canary proposal support.

Nothing in this module registers governance objects, issues approval, executes
the gateway, imports evidence, accesses a network, or touches a trading system.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping

from .governance import (
    GovernanceError,
    canonical_hash,
    lifecycle_result_is_promotion_eligible,
    validate_family,
    validate_input_declaration,
    validate_preregistration,
)
from .legacy_ledger import canonical_json_bytes, sha256_file


CANARY_RUNNER_VERSION = "governance_canary_runner_v1"
CANARY_RUNNER_ENTRY_POINT = "research_contracts.canary:run_governance_canary"
CANARY_FAMILY_ID = "governance_canary"
CANARY_EXPERIMENT_ID = "governance_canary_execution_v1"
CANARY_LIFECYCLE_RESULT = "INFRASTRUCTURE_CANARY_COMPLETED"
CANARY_PROMOTION_ELIGIBLE = False
PROPOSAL_MANIFEST_VERSION = "first_governed_canary_proposal_v1"
CANARY_PREREGISTRATION_SHA256 = "29f5bc780cdc4fcdbce58657e65d03695ea6b2ffeef9c449cd7af22e58a0f1a0"
CANARY_CONFIGURATION_SHA256 = "43dc37000406641c8fbf284ab1fe24b7ffe41224af52dbc451b4e5a108245072"

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_RELATIVE_PATH = "proposals/first_governed_run/fixtures/canary_input_v1.json"
_EXPECTED_ARTIFACTS = {
    "synthetic_result.json",
    "synthetic_rows.csv",
    "execution_receipt.json",
}


def can_promote_lifecycle_result(lifecycle_result: str) -> bool:
    """Infrastructure-canary completion is permanently nonpromotable."""
    return lifecycle_result_is_promotion_eligible(lifecycle_result)


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GovernanceError(f"expected JSON object: {path.name}")
    return value


def run_governance_canary(
    attempt_root: Path, preregistration: Mapping[str, Any],
    input_declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Write the three declared deterministic artifacts for the synthetic canary."""
    if preregistration.get("family_id") != CANARY_FAMILY_ID:
        raise GovernanceError("canary runner rejects a non-canary family")
    if preregistration.get("experiment_id") != CANARY_EXPERIMENT_ID:
        raise GovernanceError("canary runner rejects a different experiment")
    if preregistration.get("code_entry_point") != CANARY_RUNNER_ENTRY_POINT:
        raise GovernanceError("canary runner entry-point binding mismatch")
    if canonical_hash(preregistration) != CANARY_PREREGISTRATION_SHA256:
        raise GovernanceError("canary runner rejects a changed preregistration")
    if input_declaration.get("input_declaration_id") != "governance_canary_inputs_v1":
        raise GovernanceError("canary runner rejects a different input declaration")
    stable_input_contract = {
        "version": "v1",
        "security_master_version": "not_applicable_canary_v1",
        "population_capability_assessment": {"synthetic_fixture_integrity": "PASS"},
        "corporate_action_evidence_version": "not_applicable_canary_v1",
        "terminal_outcome_policy_version": "not_applicable_canary_v1",
        "benchmark_version": "not_applicable_canary_v1",
        "cost_schedule_version": "not_applicable_canary_v1",
        "calendar_version": "not_applicable_canary_v1",
        "configuration_hash": CANARY_CONFIGURATION_SHA256,
        "parser_versions": {"governance_canary_fixture": "v1"},
        "feature_versions": {"none": "not_applicable_canary_v1"},
        "dataset_split_version": "synthetic_canary_train_v1",
    }
    for field, expected in stable_input_contract.items():
        if input_declaration.get(field) != expected:
            raise GovernanceError(f"canary runner stable input binding mismatch: {field}")
    datasets = input_declaration.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 1:
        raise GovernanceError("canary runner requires exactly one synthetic fixture")
    dataset = datasets[0]
    if dataset.get("dataset_id") != "governance_canary_fixture":
        raise GovernanceError("canary runner rejects an unknown dataset")
    if dataset.get("version") != "v1" or dataset.get("path") != _FIXTURE_RELATIVE_PATH:
        raise GovernanceError("canary runner fixture identity mismatch")

    fixture_path = (_REPOSITORY_ROOT / _FIXTURE_RELATIVE_PATH).resolve()
    try:
        fixture_path.relative_to(_REPOSITORY_ROOT.resolve())
    except ValueError as exc:
        raise GovernanceError("canary fixture path escaped the repository") from exc
    if not fixture_path.is_file():
        raise GovernanceError("canary fixture is unavailable")
    if sha256_file(fixture_path) != dataset.get("snapshot_sha256"):
        raise GovernanceError("canary fixture hash mismatch")
    fixture = _load_object(fixture_path)
    if fixture.get("fixture_id") != "governance_canary_input_v1":
        raise GovernanceError("canary fixture identifier mismatch")
    rows = fixture.get("rows")
    if not isinstance(rows, list) or rows != [
        {"row_id": "CANARY_A", "value": 1},
        {"row_id": "CANARY_B", "value": 2},
        {"row_id": "CANARY_C", "value": 3},
    ]:
        raise GovernanceError("canary fixture content differs from the declared synthetic rows")

    attempt_root.mkdir(parents=True, exist_ok=True)
    result = {
        "canary_result": CANARY_LIFECYCLE_RESULT,
        "input_row_count": 3,
        "promotion_eligible": False,
        "runner_version": CANARY_RUNNER_VERSION,
        "synthetic_only": True,
    }
    (attempt_root / "synthetic_result.json").write_bytes(canonical_json_bytes(result))
    with (attempt_root / "synthetic_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["row_id", "input_value", "deterministic_value"])
        for row in rows:
            writer.writerow([row["row_id"], row["value"], row["value"] * 2])
    receipt = {
        "configuration_hash": CANARY_CONFIGURATION_SHA256,
        "dataset_snapshot_sha256": dataset["snapshot_sha256"],
        "experiment_id": CANARY_EXPERIMENT_ID,
        "runner_entry_point": CANARY_RUNNER_ENTRY_POINT,
        "runner_version": CANARY_RUNNER_VERSION,
        "synthetic_only": True,
    }
    (attempt_root / "execution_receipt.json").write_bytes(canonical_json_bytes(receipt))
    return {"lifecycle_result": CANARY_LIFECYCLE_RESULT}


def validate_canary_output_directory(
    output_root: str | Path, expected_output_declaration: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless the canary output set and bytes are exactly declared."""
    root = Path(output_root)
    actual = {
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*") if path.is_file()
    }
    if actual != _EXPECTED_ARTIFACTS:
        raise GovernanceError(
            f"canary output set mismatch: missing={sorted(_EXPECTED_ARTIFACTS - actual)}, "
            f"unexpected={sorted(actual - _EXPECTED_ARTIFACTS)}"
        )
    declared = {
        item["relative_path"]: item
        for item in expected_output_declaration.get("artifacts", [])
    }
    if set(declared) != _EXPECTED_ARTIFACTS:
        raise GovernanceError("canary expected-output declaration is incomplete")
    for relative, definition in declared.items():
        path = root / relative
        if sha256_file(path) != definition.get("sha256"):
            raise GovernanceError(f"canary artifact hash mismatch: {relative}")
        if path.stat().st_size != definition.get("byte_size"):
            raise GovernanceError(f"canary artifact size mismatch: {relative}")
    return {
        "validation_result": "PASS",
        "lifecycle_result": CANARY_LIFECYCLE_RESULT,
        "promotion_eligible": False,
        "artifact_count": len(actual),
    }


def review_canary_proposal(proposal_root: str | Path) -> dict[str, Any]:
    """Read and validate a quarantined proposal without producing side effects."""
    root = Path(proposal_root)
    manifest = _load_object(root / "proposal_manifest_v1.json")
    if manifest.get("proposal_manifest_version") != PROPOSAL_MANIFEST_VERSION:
        raise GovernanceError("unknown canary proposal manifest")
    if manifest.get("proposal_only") is not True or manifest.get("execution_authorized") is not False:
        raise GovernanceError("canary proposal quarantine markers are invalid")
    for item in manifest.get("objects", []):
        path = root / item["relative_path"]
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise GovernanceError(f"proposal object hash mismatch: {item['relative_path']}")

    family = _load_object(root / "family_definition_candidate_v1.json")
    prereg = _load_object(root / "preregistration_candidate_v1.json")
    inputs = _load_object(root / "synthetic_input_declaration_candidate_v1.json")
    approval = _load_object(root / "proposed_approval_payload_v1.json")
    validate_family(family)
    validate_preregistration(prereg)
    validate_input_declaration(inputs, prereg)
    candidate_hashes = manifest.get("canonical_candidate_hashes", {})
    if candidate_hashes.get("family_definition_sha256") != canonical_hash(family):
        raise GovernanceError("canonical family candidate hash mismatch")
    if candidate_hashes.get("preregistration_sha256") != canonical_hash(prereg):
        raise GovernanceError("canonical preregistration candidate hash mismatch")
    if candidate_hashes.get("input_declaration_sha256_before_runtime_binding") != canonical_hash(inputs):
        raise GovernanceError("canonical input candidate hash mismatch")
    fixture_path = root / _FIXTURE_RELATIVE_PATH.split("proposals/first_governed_run/", 1)[1]
    if candidate_hashes.get("synthetic_dataset_snapshot_sha256") != sha256_file(fixture_path):
        raise GovernanceError("proposal fixture snapshot hash mismatch")
    if approval.get("template_only") is not True:
        raise GovernanceError("proposal approval payload must remain a non-executable template")
    if approval.get("approval_payload_sha256") != "NOT_SEALED_PROPOSAL_ONLY":
        raise GovernanceError("proposal must not contain a usable approval payload hash")
    if manifest.get("family_id") != CANARY_FAMILY_ID:
        raise GovernanceError("proposal family identity mismatch")
    if manifest.get("experiment_id") != CANARY_EXPERIMENT_ID:
        raise GovernanceError("proposal experiment identity mismatch")
    return {
        "review_result": "READY_FOR_USER_REVIEW",
        "proposal_only": True,
        "execution_authorized": False,
        "family_id": CANARY_FAMILY_ID,
        "experiment_id": CANARY_EXPERIMENT_ID,
        "promotion_eligible": False,
        "side_effects": "NONE",
    }
