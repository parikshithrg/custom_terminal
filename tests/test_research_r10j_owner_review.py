from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs/project_status/pre_research_review_record_v6.json"


def _load() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_review_binds_the_exact_published_r10j_evidence() -> None:
    record = _load()
    for prefix in ("pdf", "source", "structured_status", "completion", "manifest"):
        assert _sha(record[f"{prefix}_path"]) == record[f"{prefix}_sha256"]
    assert record["summarized_source_commit"] == "b7c6124c6e6a353b61078a950652b763db3467bf"
    assert record["report_delivery_commit"] == "b874c3ffc6f8a892be06d7f1e22d7c9abca76276"


def test_report_and_next_stage_are_separate_explicit_decisions() -> None:
    record = _load()
    answers = record["reviewer_questions"]
    assert answers[0]["answer"] == "confirmed"
    assert answers[0]["decision"] == "REPORT_ACCURACY_CONFIRMED"
    assert answers[1]["answer"] == "approved"
    assert answers[1]["decision"] == "NEXT_MILESTONE_SEPARATELY_APPROVED"
    assert record["review_status"] == "REPORT_REVIEWED_CONFIRMED_ACCURATE"


def test_authority_is_only_bounded_read_only_qualification() -> None:
    record = _load()
    scope = record["authorized_scope"]
    assert scope["id"] == "LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1"
    assert scope["status"] == "AUTHORIZED_NOT_STARTED"
    assert scope["read_only_database_open"] is True
    assert scope["bounded_schema_and_metadata_inspection"] is True
    assert all(value is False for value in record["prohibited_actions_authorized"].values())


def test_original_report_remains_unmodified_and_unrecorded_at_generation() -> None:
    status = json.loads((ROOT / "docs/project_status/consolidated_pre_real_data_status_v1.json").read_text(encoding="utf-8"))
    assert status["owner_review"]["report_accuracy_approval"] == "UNRECORDED"
    assert status["owner_review"]["next_milestone_approval"] == "UNRECORDED"
    assert _load()["statement"].startswith("R.10J report accuracy and the next-stage decision were answered separately.")
