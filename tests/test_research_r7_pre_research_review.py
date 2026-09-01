from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research_contracts.governance import (
    GovernanceCatalog,
    GovernanceError,
    lock_preregistration,
    validate_preregistration,
)
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import (
    PreResearchReviewError,
    compute_research_state_fingerprint,
    is_market_research_family,
    validate_review_record,
    validate_review_record_path,
)


ROOT = Path(__file__).resolve().parents[1]


def _policy() -> dict:
    return {
        "policy_version": "pre_research_review_policy_v1",
        "review_record_required_fields": [
            "schema_version", "record_path", "report_id", "report_version",
            "pdf_path", "pdf_sha256", "source_path", "source_sha256",
            "summarized_source_commit", "research_state_fingerprint",
            "generation_timestamp", "rendered_page_count",
            "visual_verification_result", "covered_future_scope", "review_status",
            "report_current", "superseded_by", "reviewer_approval",
            "research_execution_status",
        ],
        "research_state": {
            "include_globs": ["research/**/*.txt"],
            "exclude_globs": ["docs/**", "README.md"],
        },
    }


def _fixture(tmp_path: Path) -> tuple[dict, dict, dict]:
    (tmp_path / "research").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "research" / "engine.txt").write_text("version one", encoding="utf-8")
    source = tmp_path / "docs" / "status.md"
    pdf = tmp_path / "docs" / "status.pdf"
    source.write_text("owner report source", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\nsynthetic offline fixture\n%%EOF\n")
    fingerprint = compute_research_state_fingerprint(tmp_path, _policy())["sha256"]
    record = {
        "schema_version": "pre_research_review_record_v1",
        "record_path": "docs/review.json",
        "report_id": "market_system_status",
        "report_version": "v1",
        "pdf_path": "docs/status.pdf",
        "pdf_sha256": sha256_file(pdf),
        "source_path": "docs/status.md",
        "source_sha256": sha256_file(source),
        "summarized_source_commit": "bc3f11f",
        "research_state_fingerprint": fingerprint,
        "generation_timestamp": "2026-09-01T08:00:00+00:00",
        "rendered_page_count": 12,
        "visual_verification_result": "PASS",
        "covered_future_scope": ["BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING"],
        "review_status": "REPORT_REVIEWED_APPROVED",
        "report_current": True,
        "superseded_by": None,
        "reviewer_approval": {
            "approved_at": "2026-09-01T09:00:00+00:00",
            "approval_kind": "EXPLICIT_POST_REPORT_REVIEW",
            "approval_statement": "I reviewed this report and approve the covered planning scope.",
            "reviewer_classification": "PROJECT_OWNER",
        },
        "research_execution_status": "BLOCKED_SEPARATE_RUN_APPROVAL_REQUIRED",
    }
    prereg = {
        "proposed_research_scope": "BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING",
        "pre_research_review": {
            "report_id": record["report_id"],
            "report_version": record["report_version"],
            "pdf_sha256": record["pdf_sha256"],
            "research_state_fingerprint": fingerprint,
            "review_record_path": record["record_path"],
            "covered_scope": "BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING",
        },
    }
    return record, prereg, _policy()


def test_market_research_fails_without_report(tmp_path):
    _, prereg, _ = _fixture(tmp_path)
    with pytest.raises(PreResearchReviewError, match="review record is missing"):
        validate_review_record_path(
            tmp_path / "docs" / "missing.json",
            preregistration=prereg,
            repository_root=tmp_path,
            policy_path=ROOT / "specs" / "pre_research_review_policy_v1.json",
        )


def test_pending_review_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    record["review_status"] = "REPORT_GENERATED_PENDING_REVIEW"
    record["reviewer_approval"] = {
        "approved_at": None, "approval_kind": None,
        "approval_statement": None, "reviewer_classification": None,
    }
    with pytest.raises(PreResearchReviewError, match="not been explicitly reviewed"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


@pytest.mark.parametrize("field,value", [
    ("report_current", False),
    ("superseded_by", "market_system_status_v2"),
])
def test_stale_or_superseded_report_fails(tmp_path, field, value):
    record, prereg, policy = _fixture(tmp_path)
    record[field] = value
    with pytest.raises(PreResearchReviewError, match="stale or superseded"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_changed_research_state_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    (tmp_path / "research" / "engine.txt").write_text("version two", encoding="utf-8")
    with pytest.raises(PreResearchReviewError, match="fingerprint changed"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_pdf_hash_mismatch_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    (tmp_path / "docs" / "status.pdf").write_bytes(b"changed")
    with pytest.raises(PreResearchReviewError, match="PDF hash mismatch"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_approval_predating_generation_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    record["reviewer_approval"]["approved_at"] = "2026-09-01T07:59:59+00:00"
    with pytest.raises(PreResearchReviewError, match="after PDF generation"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_uncovered_research_scope_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    prereg["proposed_research_scope"] = "CROSS_SECTIONAL_ALPHA"
    prereg["pre_research_review"]["covered_scope"] = "CROSS_SECTIONAL_ALPHA"
    with pytest.raises(PreResearchReviewError, match="not covered"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_generic_conversational_approval_fails(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    record["reviewer_approval"]["approval_kind"] = "GENERIC_CONVERSATIONAL_APPROVAL"
    with pytest.raises(PreResearchReviewError, match="generic conversational"):
        validate_review_record(record, preregistration=prereg,
                               repository_root=tmp_path, policy=policy)


def test_exact_review_satisfies_only_pdf_gate(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    result = validate_review_record(record, preregistration=prereg,
                                    repository_root=tmp_path, policy=policy)
    assert result["gate_state"] == "RESEARCH_EXECUTION_PERMITTED_BY_REPORT_GATE"
    assert result["report_gate_satisfied"] is True
    assert result["research_execution_authorized"] is False
    assert result["separate_run_approval_required"] is True


def test_documentation_only_excluded_change_does_not_stale(tmp_path):
    record, prereg, policy = _fixture(tmp_path)
    before = compute_research_state_fingerprint(tmp_path, policy)["sha256"]
    (tmp_path / "README.md").write_text("documentation-only change", encoding="utf-8")
    after = compute_research_state_fingerprint(tmp_path, policy)["sha256"]
    assert before == after
    assert validate_review_record(record, preregistration=prereg,
                                  repository_root=tmp_path, policy=policy)[
                                      "report_gate_satisfied"
                                  ] is True


def test_market_preregistration_cannot_lock_without_review(tmp_path):
    family = json.loads(
        (ROOT / "tests" / "fixtures" / "research_r3" / "synthetic_family_v1.json")
        .read_text(encoding="utf-8")
    )
    family["hypothesis_category"] = "MARKET_RESEARCH"
    family_path = tmp_path / "family.json"
    family_path.write_text(json.dumps(family), encoding="utf-8")
    prereg = json.loads(
        (ROOT / "tests" / "fixtures" / "research_r3" / "synthetic_preregistration_v1.json")
        .read_text(encoding="utf-8")
    )
    with pytest.raises(GovernanceError, match="approved current status PDF"):
        lock_preregistration(
            prereg,
            family_path=family_path,
            prereg_root=tmp_path / "prereg",
            catalog=GovernanceCatalog(tmp_path / "catalog.jsonl"),
            actor="TEST",
        )
    assert not (tmp_path / "prereg").exists()
    assert not (tmp_path / "catalog.jsonl").exists()


def test_completed_infrastructure_canary_is_not_retroactively_invalidated():
    prereg = json.loads(
        (ROOT / "proposals" / "first_governed_run" / "preregistration_candidate_v1.json")
        .read_text(encoding="utf-8")
    )
    family = json.loads(
        (ROOT / "proposals" / "first_governed_run" / "family_definition_candidate_v1.json")
        .read_text(encoding="utf-8")
    )
    validate_preregistration(prereg)
    assert is_market_research_family(family) is False
    anchor = json.loads(
        (ROOT / "evidence" / "governance" / "canary_execution_anchor_v1.json")
        .read_text(encoding="utf-8")
    )
    assert anchor["validation_decision"] == "PASS"
    assert anchor["promotion_eligible"] is False


def test_current_review_record_hashes_and_fingerprint_are_exact_but_pending():
    record_path = ROOT / "docs" / "project_status" / "pre_research_review_record_v1.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    policy = json.loads(
        (ROOT / "specs" / "pre_research_review_policy_v1.json").read_text(encoding="utf-8")
    )
    assert sha256_file(ROOT / record["pdf_path"]) == record["pdf_sha256"]
    assert sha256_file(ROOT / record["source_path"]) == record["source_sha256"]
    state = compute_research_state_fingerprint(ROOT, policy)
    assert state["sha256"] == record["research_state_fingerprint"]
    assert state["file_count"] == 229
    assert record["review_status"] == "REPORT_GENERATED_PENDING_REVIEW"
    assert all(value is None for value in record["reviewer_approval"].values())


def test_current_status_pdf_structure_and_required_text():
    fitz = pytest.importorskip("fitz")
    path = ROOT / "output" / "pdf" / "market_system_status_pre_research_review_v1.pdf"
    document = fitz.open(path)
    assert document.page_count == 15
    texts = [page.get_text() for page in document]
    assert all(text.strip() for text in texts)
    combined = "\n".join(texts)
    assert "PENDING USER REVIEW" in combined
    assert "NO MARKET ANALYSIS" in combined
    assert "Decisions requested from the owner" in combined
    assert "BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING" in combined
    assert "f40ba4e841fdc8839a039e29ed7deff03cf57b21b9ae303bbc03ac8ac0176c70" in combined


def test_current_status_pdf_has_no_machine_path_or_secret_marker():
    fitz = pytest.importorskip("fitz")
    path = ROOT / "output" / "pdf" / "market_system_status_pre_research_review_v1.pdf"
    text = "\n".join(page.get_text() for page in fitz.open(path))
    assert "C:\\Users" not in text
    assert "access_token" not in text.lower()
    assert "api_secret" not in text.lower()
    assert "authorization: bearer" not in text.lower()


def test_r7_entrypoint_inventory_delta_is_balanced_and_nonresearch():
    delta = json.loads(
        (ROOT / "specs" / "research_r7_entrypoint_delta_v1.json").read_text(encoding="utf-8")
    )
    assert delta["base_commit"] == "bc3f11f"
    assert delta["removed_entrypoints"] == []
    assert delta["effective_totals"] == {
        "CANONICAL_GOVERNED": 4,
        "DEVELOPMENT_ONLY_NONCANONICAL": 65,
        "DEPRECATED": 2,
        "UNSAFE_BYPASS": 0,
        "TOTAL": 71,
    }
    added = delta["added_executable_entrypoints"]
    assert len(added) == 1
    assert added[0]["execution_capability"] == "DOCUMENT_GENERATION_ONLY"
