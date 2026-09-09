"""Offline, static verification of the non-executable R.10L plan."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from market_intel.foundation.fno_production_boundary import (
    DELIBERATE_INTERLOCK,
    ProductionInterlockEvidence,
    evaluate_production_interlocks,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10l/plan_v1"
REPORT = ROOT / "reports/FNO_PRODUCTION_BOUNDARY_REMEDIATION_AND_REAUTHORIZATION_PLAN.md"


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_plan_artifact_is_non_executable_and_grants_no_access() -> None:
    for path in RUN.glob("*.json"):
        if path.name in {"completion.json", "root_manifest.json"}:
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        assert "NON_EXECUTABLE" in value.get("classification", "") or path.name in {
            "blocker_reproduction.json", "r9l_v6_test_reconciliation.json"
        }
    assert load("proposed_locator_contract.json")["usable"] is False
    assert load("proposed_one_use_approval_schema.json")["grants_authority"] is False
    assert load("proposed_production_activation_contract.json")["activation_authorized"] is False
    assert load("dependency_adoption_decision.json")["adopted_now"] is False


def test_all_seven_r10k_blockers_reproduce_without_target_access() -> None:
    result = load("blocker_reproduction.json")
    assert result["all_r10k_blockers_reproduced"] is True
    assert len(result["checks"]) == 7
    assert {row["result"] for row in result["checks"]} == {"CONFIRMED"}
    assert result["locator_resolved"] is False
    assert result["database_opened"] is False
    locator = json.loads((ROOT / "specs/fno_production_locator_contract_v1.json").read_text())
    activation = json.loads((ROOT / "specs/fno_production_activation_template_v1.json").read_text())
    assert locator["template_only"] and not locator["usable"]
    assert activation["template_only"] and not activation["usable"]
    values = {name: True for name in ProductionInterlockEvidence.__dataclass_fields__}
    values["deliberate_r9d_interlock_removed_by_reviewed_commit"] = False
    interlocks = evaluate_production_interlocks(ProductionInterlockEvidence(**values))
    assert not interlocks["permitted"] and DELIBERATE_INTERLOCK in interlocks["failures"]


def test_option_a_is_the_only_recommendation_and_c_is_fail_closed_fallback() -> None:
    value = load("option_comparison.json")
    assert value["recommended_option"] == "A_RESTRICTED_APSW_VFS"
    assert value["fallback_option"] == "C_ABANDON_LOCAL_DATABASE"
    decisions = {row["id"]: row["decision"] for row in value["options"]}
    assert decisions == {
        "A_RESTRICTED_APSW_VFS": "RECOMMENDED_CONDITIONALLY_NOT_ADOPTED",
        "B_STANDARD_LIBRARY_SQLITE3": "REJECTED_FOR_CURRENT_BOUNDARY",
        "C_ABANDON_LOCAL_DATABASE": "FALLBACK_IF_OPTION_A_ACCEPTANCE_FAILS",
    }
    assert value["implementation_authorized"] is False
    assert value["database_access_authorized"] is False


def test_locator_and_one_use_approval_are_exact_but_unusable_templates() -> None:
    locator = load("proposed_locator_contract.json")
    assert locator["sanitized_alias"] == "PRIVATE_FNO_DATABASE_V1"
    assert all(locator["resolution_requirements"].values())
    assert locator["identity_binding"]["silent_refresh_prohibited"] is True
    assert locator["grants_locator_resolution"] is False
    approval = load("proposed_one_use_approval_schema.json")
    required = approval["required_bindings"]
    for key in (
        "owner_reviewed_plan_sha256", "owner_review_record_sha256",
        "locator_binding_id", "expected_database_identity", "attempt_id",
        "executable_path", "source_commit", "wheel_sha256",
        "resource_envelope_sha256", "sidecar_policy_sha256",
        "output_contract_sha256", "expires_at",
    ):
        assert key in required
    assert approval["atomic_consumption"]["must_commit_before_target_connection"]
    assert approval["atomic_consumption"]["replay_rejected"]


def test_activation_requires_every_binding_and_keeps_r9d_closed() -> None:
    value = load("proposed_production_activation_contract.json")
    assert value["r9d_interlock_state"] == "REMAINS_ACTIVE"
    assert value["current_artifact_can_activate"] is False
    assert value["partial_match_is_authority"] is False
    assert len(value["all_required_conditions"]) == 10


def test_resource_limits_name_enforcer_and_failure_for_every_dimension() -> None:
    limits = load("resource_envelope_contract.json")["limits"]
    expected = {
        "target_filesystem_bytes_delegated", "logical_sqlite_bytes_requested",
        "statements", "returned_rows", "serialized_output",
        "process_committed_memory", "aggregate_job_committed_memory",
        "attempt_elapsed_time", "statement_elapsed_time",
        "query_plan_complexity", "temporary_storage",
    }
    assert set(limits) == expected
    for item in limits.values():
        assert item["maximum"] >= 0
        assert item["enforced_by"]
        assert item["failure"]
    assert limits["temporary_storage"]["maximum"] == 0
    assert limits["logical_sqlite_bytes_requested"]["mmap_policy"] == "PROHIBITED"


def test_sidecar_and_privacy_policies_fail_closed() -> None:
    sidecars = load("sidecar_decision_policy.json")
    decisions = {row["state"]: row["decision"] for row in sidecars["rules"]}
    assert decisions["WAL_OR_SHM_PRESENT"] == "ABORT"
    assert decisions["ROLLBACK_JOURNAL_PRESENT"] == "ABORT"
    assert sidecars["continuous_quiescence_claimed"] is False
    privacy = load("evidence_privacy_contract.json")
    assert "raw market rows" in privacy["prohibited_evidence"]
    assert privacy["publication_controls"]["success_output_after_any_failure"] is False
    assert privacy["abort_evidence_required"] is True


def test_dependency_remains_uninstalled_and_acceptance_is_all_or_nothing() -> None:
    dependency = load("dependency_adoption_decision.json")
    assert dependency["recommendation"] == "CONDITIONALLY_ADOPT_FOR_DEDICATED_PRODUCTION_BOUNDARY_ONLY"
    assert dependency["adopted_now"] is False
    assert dependency["evaluated_pin"]["wheel_sha256"] == "13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5"
    matrix = load("implementation_acceptance_matrix.json")
    assert matrix["all_required"] is True
    assert len(matrix["criteria"]) == 17
    assert matrix["any_failure_result"] == "IMPLEMENTATION_NOT_ACCEPTED"
    assert matrix["real_database_access_after_pass"] is False


def test_r9l_historical_bytes_and_forward_v6_authority_coexist() -> None:
    reconciliation = load("r9l_v6_test_reconciliation.json")
    generation = json.loads((ROOT / "docs/project_status/pre_research_generation_manifest_v6.json").read_text())
    review = json.loads((ROOT / "docs/project_status/pre_research_review_record_v6.json").read_text())
    assert sha(ROOT / "tests/test_research_r9l_pdf_v6.py") == "11433b539d098cd7a057175ff26393ca45e50718fe8cd4459392a69c4582f3a5"
    assert generation["owner_review_recorded"] is False
    assert all(value is False for value in generation["execution_authority"].values())
    assert review["review_status"] == "REPORT_REVIEWED_CONFIRMED_ACCURATE"
    assert review["reviewed_at"] > generation["generation_timestamp"]
    assert reconciliation["historical_state"]["source_test_modified"] is False
    assert reconciliation["pytest_resolution"]["unexpected_pass_is_failure"] is True


def test_report_contains_decision_risks_sequence_and_owner_questions() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "FNO_PRODUCTION_BOUNDARY_PLAN_READY_FOR_OWNER_REVIEW",
        "restricted APSW/VFS boundary", "Option B", "Option C",
        "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE",
        "Exact owner decisions required", "Product sequence",
        "Proposed only; not authorized",
    ):
        assert phrase in text
    assert not re.search(r"[A-Za-z]:[\\/]", text)
    assert "database opens, SQL statements, and market rows\n  during R10L: zero" in text


def test_completion_and_manifest_validate() -> None:
    completion = load("completion.json")
    manifest = load("root_manifest.json")
    assert completion["completion_state"] == "FNO_PRODUCTION_BOUNDARY_PLAN_READY_FOR_OWNER_REVIEW"
    assert completion["database_opened"] is False
    for relative, expected in manifest["artifact_hashes"].items():
        assert sha(ROOT / relative) == expected
    body = dict(manifest)
    expected_payload = body.pop("payload_sha256")
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == expected_payload
