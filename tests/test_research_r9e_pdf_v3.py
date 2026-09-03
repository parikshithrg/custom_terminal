from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from market_intel.foundation import fno_production_boundary as boundary
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import (
    PreResearchReviewError,
    compute_research_state_fingerprint,
    validate_review_record,
)


ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "docs/project_status/pre_research_review_record_v1.json"
V2 = ROOT / "docs/project_status/pre_research_review_record_v2.json"
V3 = ROOT / "docs/project_status/pre_research_review_record_v3.json"
POLICY = ROOT / "specs/pre_research_review_policy_v1.json"
EXPECTED_STATE = "f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38"
EXPECTED_PDF_V2 = "765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v1_and_v2_are_preserved_as_historical_review_evidence():
    v1 = _load(V1)
    v2 = _load(V2)
    assert v1["reviewer_approval"]["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert v2["reviewer_approval"]["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert v2["review_status"] == "REPORT_STALE"
    assert v2["report_current"] is False
    assert sha256_file(ROOT / v2["pdf_path"]) == EXPECTED_PDF_V2


def test_v3_supersession_chain_is_explicit_through_current_v4_review():
    v2 = _load(V2)
    v3 = _load(V3)
    assert v2["superseded_by"] == v3["record_path"]
    assert v3["supersedes"] == v2["record_path"]
    assert v3["superseded_by"] == (
        "docs/project_status/pre_research_review_record_v4.json"
    )


def test_v3_source_and_pdf_hashes_and_structure_are_exact():
    record = _load(V3)
    assert sha256_file(ROOT / record["source_path"]) == record["source_sha256"]
    assert sha256_file(ROOT / record["pdf_path"]) == record["pdf_sha256"]
    payload = (ROOT / record["pdf_path"]).read_bytes()
    assert payload.startswith(b"%PDF-") and payload.rstrip().endswith(b"%%EOF")
    assert max(map(int, re.findall(rb"/Count\s+(\d+)", payload))) == (
        record["rendered_page_count"]
    ) == 16
    assert b"/Encrypt" not in payload


def test_v3_preserves_the_exact_r9d_binding_but_is_stale_after_r9f():
    record = _load(V3)
    state = compute_research_state_fingerprint(ROOT, _load(POLICY))
    assert record["research_state_fingerprint"] == EXPECTED_STATE
    assert record["research_state_file_count"] == 237
    assert record["staleness"]["current_research_state_fingerprint"] == (
        "6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db"
    )
    assert state["sha256"] == "1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef"
    assert state["sha256"] != EXPECTED_STATE
    assert state["file_count"] == 252
    assert record["summarized_source_commit"] == (
        "450e976ae472fa440a704c74ad959b60f1113219"
    )


def test_v3_preserves_exact_owner_review_scope_and_completed_lifecycle():
    record = _load(V3)
    assert record["review_status"] == "REPORT_STALE"
    assert record["report_current"] is False
    approval = record["reviewer_approval"]
    assert approval["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert approval["reviewer_classification"] == "PROJECT_OWNER"
    assert approval["approved_at"] > record["generation_timestamp"]
    assert record["covered_future_scope"] == [
        "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION"
    ]
    assert len(record["reviewer_questions"]) == 9
    assert all(item["answer"] and item["decision"] != "UNRESOLVED"
               for item in record["reviewer_questions"])
    assert record["authorized_scope_completion"]["state"] == "COMPLETED_NONACTIVATING"
    assert record["authorized_scope_completion"]["completed_without_database_connection"] is True


def test_pending_v3_fails_the_review_gate():
    record = _load(V3)
    record["review_status"] = "REPORT_GENERATED_PENDING_REVIEW"
    record["reviewer_approval"] = None
    policy = _load(POLICY)
    policy["external_repository_bindings"] = record["external_repository_bindings"]
    preregistration = {
        "proposed_research_scope": "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION",
        "pre_research_review": {
            "report_id": record["report_id"],
            "report_version": "v3",
            "pdf_sha256": record["pdf_sha256"],
            "research_state_fingerprint": record["research_state_fingerprint"],
            "review_record_path": record["record_path"],
            "external_repository_bindings": record["external_repository_bindings"],
            "covered_scope": "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION",
        },
    }
    with pytest.raises(PreResearchReviewError, match="not been explicitly reviewed"):
        validate_review_record(
            record, preregistration=preregistration, repository_root=ROOT, policy=policy
        )


def test_stale_v3_cannot_authorize_any_later_execution():
    record = _load(V3)
    policy = _load(POLICY)
    policy["external_repository_bindings"] = record["external_repository_bindings"]
    preregistration = {
        "proposed_research_scope": "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION",
        "pre_research_review": {
            "report_id": record["report_id"],
            "report_version": "v3",
            "pdf_sha256": record["pdf_sha256"],
            "research_state_fingerprint": record["research_state_fingerprint"],
            "review_record_path": record["record_path"],
            "external_repository_bindings": record["external_repository_bindings"],
            "covered_scope": "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION",
        },
    }
    with pytest.raises(PreResearchReviewError, match="not been explicitly reviewed"):
        validate_review_record(
            record, preregistration=preregistration, repository_root=ROOT, policy=policy
        )


def test_v3_authorizes_only_bounded_locator_binding_preparation():
    authority = _load(V3)["execution_authority"]
    assert authority["later_exact_audit_approval_required"] is True
    assert authority["locator_binding_preparation_authorized"] is True
    assert authority["configuration_value_read_authorized"] is True
    assert authority["filesystem_identity_pass_authorized"] is True
    for key in (
        "sqlite_access_authorized",
        "audit_execution_authorized",
        "market_row_access_authorized",
        "scoring_or_backtesting_authorized",
        "broker_actions_authorized",
        "trading_authorized",
    ):
        assert authority[key] is False


def test_locator_resolution_and_production_activation_remain_impossible(monkeypatch):
    called = {"configuration": 0, "sqlite": 0}

    def config_reader():
        called["configuration"] += 1
        raise AssertionError("configuration must not be read")

    def connect(*args, **kwargs):
        called["sqlite"] += 1
        raise AssertionError("SQLite must not be opened")

    monkeypatch.setattr(boundary.sqlite3, "connect", connect)
    with pytest.raises(boundary.ProductionBoundaryError, match=boundary.PRODUCTION_LOCATOR_STATE):
        boundary.execute_production_stage_1_3_audit(configuration_reader=config_reader)
    assert called == {"configuration": 0, "sqlite": 0}
    result = boundary.evaluate_production_interlocks(
        boundary.ProductionInterlockEvidence(**{
            field: True
            for field in boundary.ProductionInterlockEvidence.__dataclass_fields__
        })
    )
    assert result["permitted"] is False
    assert result["database_access_authorized"] is False
    assert result["audit_execution_authorized"] is False


def test_v3_source_contains_required_scope_prohibitions_and_questions():
    record = _load(V3)
    text = (ROOT / record["source_path"]).read_text(encoding="utf-8")
    required = (
        "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION",
        "Production access is still impossible.",
        boundary.PRODUCTION_LOCATOR_STATE,
        boundary.DELIBERATE_INTERLOCK,
        "sqlite3.connect",
        "268,435,556 bytes",
        "later exact approval is still required before the first database connection",
        "PRE_RESEARCH_PDF_V3_READY_FOR_OWNER_REVIEW",
    )
    assert all(value in text for value in required)


def test_v3_external_binding_is_unchanged_and_reference_only():
    external = _load(V3)["external_repository_bindings"][1]
    assert external == {
        "repository": "version2.0",
        "url": "https://github.com/parikshithrg/version2.0.git",
        "branch": "master",
        "commit": "f9a6eaec2cab1dd9e85d284e48b9863cae0b1298",
        "tree": "ad3c21fb2244f0acd7680bd0bdc4958d2516b16f",
        "role": "PRODUCT_DASHBOARD_CURRENT_DISPLAYS_EXPLORATORY_NONCANONICAL_TOOLS",
    }
    assert _load(V3)["external_reference_result"] == (
        "UNCHANGED_READ_ONLY_NO_CLONE_NO_EXECUTION"
    )
