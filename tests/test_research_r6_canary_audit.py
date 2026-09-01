from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from research_contracts import canonical_hash
from research_contracts.canary_audit import (
    CanaryAuditError,
    _governance_chain,
    audit_canary_evidence,
    validate_anchor,
)


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "artifacts" / "governed_research"
ANCHOR = ROOT / "evidence" / "governance" / "canary_execution_anchor_v1.json"


def _anchor() -> dict:
    return json.loads(ANCHOR.read_text(encoding="utf-8"))


@pytest.mark.skipif(not RUNTIME.is_dir(), reason="ignored local canary evidence is not present")
def test_local_canary_evidence_independently_audits_without_mismatch():
    result = audit_canary_evidence(ROOT)
    assert result["decision"] == "PASS"
    assert result["mismatch_count"] == 0
    assert all(item["status"] == "MATCH" for item in result["comparisons"])
    assert result["approval_lifecycle"]["start_count"] == 1
    assert result["approval_lifecycle"]["reuse_preflight_permitted"] is False


@pytest.mark.skipif(not RUNTIME.is_dir(), reason="ignored local canary evidence is not present")
def test_local_audit_records_exact_resources_and_catalog_limitation():
    result = audit_canary_evidence(ROOT)
    resources = result["resource_declarations"]
    assert resources["runner_artifact_count"] == 3
    assert resources["runner_artifact_bytes"] == 618
    assert resources["bundle_artifact_count"] == 4
    assert resources["bundle_artifact_bytes"] == 5017
    assert resources["wall_time_enforcement"] == "DECLARED_NOT_ENFORCED"
    assert resources["memory_enforcement"] == "DECLARED_NOT_ENFORCED"
    assert result["canonical_catalog"]["record_count"] == 1
    assert result["canonical_catalog"]["record_chain"].startswith("NOT_IMPLEMENTED")


@pytest.mark.skipif(not RUNTIME.is_dir(), reason="ignored local canary evidence is not present")
def test_tracked_anchor_matches_recomputed_runtime_evidence():
    result = audit_canary_evidence(ROOT)
    anchor = _anchor()
    assert anchor["attempt_id"] == result["attempt_id"]
    assert anchor["approval"]["file_sha256"] == result["hashes"]["approval_file_sha256"]
    assert anchor["approval"]["payload_sha256"] == result["hashes"]["approval_payload_sha256"]
    for anchor_key, result_key in {
        "family_sha256": "family_sha256",
        "preregistration_sha256": "preregistration_sha256",
        "input_declaration_sha256": "input_declaration_sha256",
        "fixture_sha256": "fixture_sha256",
        "root_manifest_sha256": "root_manifest_sha256",
    }.items():
        assert anchor["hashes"][anchor_key] == result["hashes"][result_key]
    for name, digest in result["hashes"]["artifacts"].items():
        anchor_key = name.replace(".", "_").replace("_json", "_sha256").replace(
            "_csv", "_sha256"
        )
        assert anchor["hashes"][anchor_key] == digest
    assert (
        anchor["event_chain_terminal_sha256"]
        == result["hashes"]["governance_event_terminal_sha256"]
    )
    assert (
        anchor["canonical_record_terminal_sha256"]
        == result["hashes"]["canonical_record_terminal_sha256"]
    )


def test_missing_runtime_evidence_fails_closed(tmp_path):
    with pytest.raises(CanaryAuditError, match="required evidence is missing"):
        audit_canary_evidence(tmp_path)


def test_governance_chain_recomputation_detects_tampering():
    first = {
        "event_id": "one", "event_type": "FAMILY_REGISTERED",
        "previous_event_sha256": None, "object_refs": {}, "object_hashes": {},
    }
    first["event_sha256"] = canonical_hash(first)
    second = {
        "event_id": "two", "event_type": "PREREGISTRATION_CREATED",
        "previous_event_sha256": first["event_sha256"],
        "object_refs": {}, "object_hashes": {},
    }
    second["event_sha256"] = canonical_hash(second)
    comparisons: list[dict] = []
    assert _governance_chain([first, second], comparisons) == second["event_sha256"]
    assert all(item["status"] == "MATCH" for item in comparisons)
    tampered = copy.deepcopy(second)
    tampered["object_refs"] = {"changed": True}
    comparisons = []
    _governance_chain([first, tampered], comparisons)
    assert any(item["status"] == "MISMATCH" for item in comparisons)


def test_sanitized_anchor_satisfies_versioned_contract():
    validate_anchor(_anchor())


@pytest.mark.parametrize("mutation", ["promotion", "lifecycle", "hash", "missing"])
def test_anchor_validation_fails_closed(mutation):
    anchor = _anchor()
    if mutation == "promotion":
        anchor["promotion_eligible"] = True
    elif mutation == "lifecycle":
        anchor["lifecycle_result"] = "TRAIN_CONFIRMED"
    elif mutation == "hash":
        anchor["hashes"]["family_sha256"] = "short"
    else:
        anchor.pop("attempt_id")
    with pytest.raises(CanaryAuditError):
        validate_anchor(anchor)


def test_auditor_has_no_execution_or_registration_call():
    path = ROOT / "src" / "research_contracts" / "canary_audit.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_names = {
        "run_governance_canary", "register_family", "lock_preregistration",
        "register_run_approval", "register_bundle",
    }
    called_names = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    called_attributes = {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not (forbidden_names & called_names)
    assert "run" not in called_attributes


def test_anchor_contains_no_machine_path_or_raw_catalog():
    text = ANCHOR.read_text(encoding="utf-8")
    assert "C:\\Users" not in text
    assert "RUN_STARTED" not in text
    assert "approving_identity" not in text
    assert _anchor()["runtime_evidence_location"] == (
        "artifacts/governed_research/run_attempts/"
        "governance-canary-attempt-126aeed-001"
    )


def test_r6_entrypoint_inventory_delta_is_read_only_and_balanced():
    delta = json.loads(
        (ROOT / "specs" / "research_r6_entrypoint_delta_v1.json").read_text(encoding="utf-8")
    )
    assert delta["base_commit"] == "126aeed"
    assert delta["removed_entrypoints"] == []
    assert delta["effective_totals"] == {
        "CANONICAL_GOVERNED": 3,
        "DEVELOPMENT_ONLY_NONCANONICAL": 65,
        "DEPRECATED": 2,
        "UNSAFE_BYPASS": 0,
        "TOTAL": 70,
    }
    added = delta["added_callable_entrypoints"]
    assert len(added) == 1
    assert added[0]["callable"] == "audit_canary_evidence"
    assert added[0]["execution_capability"] == "READ_ONLY_AUDIT"
