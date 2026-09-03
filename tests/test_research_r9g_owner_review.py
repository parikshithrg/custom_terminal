from __future__ import annotations

import json
from pathlib import Path

from market_intel.foundation import fno_production_boundary as boundary
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import (
    compute_research_state_fingerprint,
    validate_review_record,
)


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs/project_status/pre_research_review_record_v4.json"
POLICY = ROOT / "specs/pre_research_review_policy_v1.json"
SCOPE = "EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v4_owner_review_binds_exact_generated_report():
    record = _load(RECORD)
    assert record["review_status"] == "REPORT_REVIEWED_APPROVED"
    assert record["report_current"] is True
    assert record["covered_future_scope"] == [SCOPE]
    assert sha256_file(ROOT / record["pdf_path"]) == record["pdf_sha256"]
    assert sha256_file(ROOT / record["source_path"]) == record["source_sha256"]
    assert sha256_file(ROOT / record["generation_manifest_path"]) == record[
        "generation_manifest_sha256"
    ]
    assert record["reviewer_approval"]["approved_at"] > record["generation_timestamp"]


def test_v4_owner_answers_are_complete_and_fallback_is_conservative():
    record = _load(RECORD)
    assert len(record["reviewer_questions"]) == 7
    assert all(item["answer"] and item["decision"] for item in record["reviewer_questions"])
    policy = record["alternative_source_policy"]
    assert "NSE F&O bhavcopies" in policy["example_candidate"]
    assert policy["acquisition_authorized_by_this_review"] is False
    constraints = " ".join(policy["constraints"])
    assert "Do not bypass" in constraints
    assert "complete historical security population" in constraints
    assert "Separate approval" in constraints or "separate approval" in constraints


def test_v4_authorizes_only_proposal_preparation():
    authority = _load(RECORD)["execution_authority"]
    assert authority["interlock_removal_proposal_preparation_authorized"] is True
    assert all(value is False for key, value in authority.items() if key != (
        "interlock_removal_proposal_preparation_authorized"
    ))
    assert _load(RECORD)["deliberate_interlock"] == boundary.DELIBERATE_INTERLOCK


def test_v4_record_satisfies_report_gate_without_execution_authority():
    record = _load(RECORD)
    policy = _load(POLICY)
    policy["external_repository_bindings"] = record["external_repository_bindings"]
    preregistration = {
        "proposed_research_scope": SCOPE,
        "pre_research_review": {
            "report_id": record["report_id"],
            "report_version": record["report_version"],
            "pdf_sha256": record["pdf_sha256"],
            "research_state_fingerprint": record["research_state_fingerprint"],
            "review_record_path": record["record_path"],
            "external_repository_bindings": record["external_repository_bindings"],
            "covered_scope": SCOPE,
        },
    }
    result = validate_review_record(
        record, preregistration=preregistration, repository_root=ROOT, policy=policy
    )
    assert result["report_gate_satisfied"] is True
    assert result["research_execution_authorized"] is False
    assert result["separate_run_approval_required"] is True


def test_v4_review_preserves_research_fingerprint_and_prior_pdf_bytes():
    record = _load(RECORD)
    state = compute_research_state_fingerprint(ROOT, _load(POLICY))
    assert state["sha256"] == record["research_state_fingerprint"]
    assert state["file_count"] == record["research_state_file_count"] == 242
    expected = {
        "v1": "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c",
        "v2": "765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf",
        "v3": "75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2",
        "v4": "02a76f6d46bc74a69b7f0b10331ae26da1d07d60934091ce9d31c0abe8cdaec9",
    }
    for version, digest in expected.items():
        assert sha256_file(
            ROOT / f"output/pdf/market_system_status_pre_research_review_{version}.pdf"
        ) == digest
