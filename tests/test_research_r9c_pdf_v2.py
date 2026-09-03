from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from market_intel.foundation import local_fno_audit as audit
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import (
    PreResearchReviewError,
    compute_research_state_fingerprint,
    validate_review_record,
)


ROOT = Path(__file__).resolve().parents[1]
V1_RECORD = ROOT / "docs" / "project_status" / "pre_research_review_record_v1.json"
V2_RECORD = ROOT / "docs" / "project_status" / "pre_research_review_record_v2.json"
POLICY = ROOT / "specs" / "pre_research_review_policy_v1.json"
EXPECTED_FINGERPRINT = "9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31"
V1_PDF_HASH = "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _v2_preregistration(record: dict) -> dict:
    scope = record["covered_future_scope"][0]
    return {
        "proposed_research_scope": scope,
        "pre_research_review": {
            "report_id": record["report_id"],
            "report_version": record["report_version"],
            "pdf_sha256": record["pdf_sha256"],
            "research_state_fingerprint": record["research_state_fingerprint"],
            "review_record_path": record["record_path"],
            "covered_scope": scope,
            "external_repository_bindings": record["external_repository_bindings"],
        },
    }


def test_v1_is_preserved_as_reviewed_stale_superseded_evidence():
    record = _load(V1_RECORD)
    assert sha256_file(ROOT / record["pdf_path"]) == V1_PDF_HASH
    assert record["pdf_sha256"] == V1_PDF_HASH
    assert record["review_status"] == "REPORT_STALE"
    assert record["reviewer_approval"]["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert record["superseded_by"] == (
        "docs/project_status/pre_research_review_record_v2.json"
    )
    assert record["staleness"]["status"] == (
        "REVIEWED_PDF_STALE_AFTER_AUDITOR_IMPLEMENTATION"
    )


def test_v2_bytes_and_historical_fingerprint_binding_are_exact():
    record = _load(V2_RECORD)
    assert sha256_file(ROOT / record["pdf_path"]) == record["pdf_sha256"]
    assert sha256_file(ROOT / record["source_path"]) == record["source_sha256"]
    assert record["summarized_source_commit"] == (
        "a87cedc7ad5db14adaba0661bf44fd3346e399ab"
    )
    state = compute_research_state_fingerprint(ROOT, _load(POLICY))
    assert state["sha256"] != EXPECTED_FINGERPRINT
    assert record["research_state_fingerprint"] == EXPECTED_FINGERPRINT
    assert record["staleness"]["current_research_state_fingerprint"] == (
        "f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38"
    )
    assert state["sha256"] != record["staleness"]["current_research_state_fingerprint"]
    version2 = record["external_repository_bindings"][1]
    assert version2["commit"] == "f9a6eaec2cab1dd9e85d284e48b9863cae0b1298"
    assert version2["tree"] == "ad3c21fb2244f0acd7680bd0bdc4958d2516b16f"


def test_v2_preserves_exact_owner_review_and_is_stale_after_r9d():
    record = _load(V2_RECORD)
    assert record["review_status"] == "REPORT_STALE"
    assert record["report_current"] is False
    assert record["superseded_by"] == (
        "docs/project_status/pre_research_review_record_v3.json"
    )
    approval = record["reviewer_approval"]
    assert approval["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert approval["reviewer_classification"] == "PROJECT_OWNER"
    assert approval["approved_at"] > record["generation_timestamp"]
    assert [item["question"] for item in record["reviewer_questions"]] == list(range(1, 8))
    assert all(item["answer"] and item["decision"] for item in record["reviewer_questions"])
    decisions = {item["question"]: item["decision"] for item in record["reviewer_questions"]}
    assert decisions[2] == "CONFIRMED"
    assert decisions[6] == "NO_CORRECTIONS"
    assert decisions[7] == "DOCUMENT_LIMITATION"


def test_stale_v2_no_longer_satisfies_the_report_gate():
    record = _load(V2_RECORD)
    policy = _load(POLICY)
    policy["external_repository_bindings"] = record["external_repository_bindings"]
    with pytest.raises(PreResearchReviewError, match="not been explicitly reviewed"):
        validate_review_record(
            record,
            preregistration=_v2_preregistration(record),
            repository_root=ROOT,
            policy=policy,
        )


def test_pdf_approval_cannot_authorize_audit_execution():
    record = copy.deepcopy(_load(V2_RECORD))
    policy = _load(POLICY)
    policy["external_repository_bindings"] = record["external_repository_bindings"]
    record["review_status"] = "REPORT_REVIEWED_APPROVED"
    record["report_current"] = True
    record["superseded_by"] = None
    record["research_state_fingerprint"] = compute_research_state_fingerprint(
        ROOT, policy
    )["sha256"]
    result = validate_review_record(
        record,
        preregistration=_v2_preregistration(record),
        repository_root=ROOT,
        policy=policy,
    )
    assert result["report_gate_satisfied"] is True
    assert result["research_execution_authorized"] is False
    assert result["separate_run_approval_required"] is True
    assert audit.AUDIT_APPROVAL_TYPE == "LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1"


def test_real_database_and_research_remain_blocked_after_review():
    record = _load(V2_RECORD)
    condition = record["real_database_access_condition"]
    assert condition["currently_authorized"] is False
    assert condition["synthetic_testing_required_first"] is True
    assert condition["synthetic_testing_completion_is_sufficient_authority"] is False
    assert condition["later_required_gates"] == [
        "PRODUCTION_ENABLEMENT_IMPLEMENTATION_REVIEW",
        "EXACT_DATABASE_BINDING",
        "EXACT_REGISTERED_ONE_USE_AUDIT_APPROVAL",
    ]
    assert record["future_action_candidates"] == [
        "MARKET_ANALYSIS_SUBJECT_TO_SEPARATE_RESEARCH_GOVERNANCE",
        "SCORING_SUBJECT_TO_SEPARATE_RESEARCH_GOVERNANCE",
        "RECOMMENDATIONS_SUBJECT_TO_SEPARATE_RESEARCH_GOVERNANCE",
    ]
    assert "NO_BROKER_ACTION_OR_TRADING" in record["execution_prohibitions"]


def test_v2_scope_is_design_only_and_excludes_real_database_access():
    record = _load(V2_RECORD)
    assert record["covered_future_scope"] == [
        "FNO_PRODUCTION_ENABLEMENT_DESIGN_AND_SYNTHETIC_TESTING"
    ]
    prohibitions = set(record["execution_prohibitions"])
    assert "NO_REAL_FNO_DATABASE_LOCATION_OR_ACCESS" in prohibitions
    assert "NO_AUDIT_EXECUTION" in prohibitions
    assert "NO_BROKER_ACTION_OR_TRADING" in prohibitions


def test_production_locator_remains_rejected_and_dry_run_resolves_nothing(monkeypatch):
    monkeypatch.setattr(Path, "resolve", lambda *args, **kwargs: pytest.fail("path resolved"))
    monkeypatch.setattr(audit.sqlite3, "connect", lambda *args, **kwargs: pytest.fail("connected"))
    result = audit.execute_approved_stage_1_3_audit()
    assert result.status == "BLOCKED"
    assert result.attempt is None
    source = inspect.getsource(audit.validate_audit_approval)
    assert 'approved_locator_key == "paths.fno_db"' in source
    assert "production F&O locator is disabled in R.9B" in source


def test_v2_pdf_structure_content_and_visual_record():
    fitz = pytest.importorskip("fitz")
    record = _load(V2_RECORD)
    document = fitz.open(ROOT / record["pdf_path"])
    assert document.page_count == 17
    texts = [page.get_text() for page in document]
    assert all(text.strip() for text in texts)
    combined = "\n".join(texts)
    normalized = " ".join(combined.split())
    for required in (
        "Version 2",
        "The real F&O database has never been located, opened, hashed, inspected, or queried.",
        "FNO_PRODUCTION_ENABLEMENT_DESIGN_AND_SYNTHETIC_TESTING",
        "REPORT_GENERATED_PENDING_REVIEW",
        "Do you approve PDF v2 as an accurate summary",
        "Do you want the two Windows symlink tests",
        "PRE_RESEARCH_PDF_V2_READY_FOR_OWNER_REVIEW",
    ):
        assert required in normalized
    assert "[PAGE BREAK]" not in combined
    assert "```" not in combined
    assert "C:\\Users" not in combined
    assert "api_secret" not in combined.lower()
    assert record["visual_verification_result"] == "PASS_17_PAGES_NO_MATERIAL_DEFECTS"


def test_protected_evidence_hashes_remain_exact():
    expected = {
        "evidence/governance/canary_execution_anchor_v1.json": (
            "01e6bc77af74180d970802f6fb8a5d1c5533cd392d7ceb042cf5e4b27a16c698"
        ),
        "evidence/governance/family_registry_anchor_v1.json": (
            "5b5decd498c1ad8af6aaeda23f004a9b1543f60cce9b718c80a8d7fba5abba25"
        ),
        "tests/fixtures/momentum_golden_v1/expected.json": (
            "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f"
        ),
    }
    assert {path: sha256_file(ROOT / path) for path in expected} == expected


def test_r9c_report_has_exact_terminal_decision():
    report = (ROOT / "reports" / "RESEARCH_R9C_REPORT.md").read_text(encoding="utf-8")
    assert report.rstrip().endswith("PRE_RESEARCH_PDF_V2_READY_FOR_OWNER_REVIEW")
