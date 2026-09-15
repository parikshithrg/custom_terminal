"""Sanitized fail-closed evidence checks for the bounded R10N-E execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "investigations" / "r10n_e" / "qualification_v1"
REPORT = ROOT / "reports" / "NSE_FNO_R10NE_MULTI_DATE_QUALIFICATION.md"


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_owner_scope_and_retention_are_exact() -> None:
    owner = _load("owner_authorization.json")
    assert owner["authorization_state"] == "COMPLETE_FOR_EXACT_AMENDED_SCOPE"
    assert owner["dates"] == ["2026-09-10", "2025-07-08"]
    assert owner["retention_deadlines"] == {
        "2026-09-10": "2026-12-31", "2025-07-08": "2026-12-31",
    }
    assert owner["future_default_authorizes_access_or_acquisition"] is False


def test_request_budget_is_exact_and_bounded() -> None:
    ledger = _load("request_budget_ledger.json")
    assert ledger["approved"] == ledger["used"] == {
        "direct_head": 4, "direct_get": 4, "total": 8,
    }
    assert ledger["responses"] == {"direct_http_200": 8, "redirects": 0}
    assert ledger["retries"] == ledger["fallbacks"] == ledger["date_enumeration"] == 0
    assert ledger["anchor_reacquisition_requests"] == 0


def test_acquisition_is_complete_but_qualification_fails_closed() -> None:
    acquisition = _load("acquisition_outcomes.json")
    assert [item["state"] for item in acquisition["packages"]] == [
        "TRANSACTIONALLY_PUBLISHED", "TRANSACTIONALLY_PUBLISHED",
    ]
    per_date = _load("per_date_qualification.json")["dates"]
    assert per_date[0]["state"] == "QUALIFIED_BY_ADAPTER"
    assert per_date[1]["failure_code"] == "OHLC_INCONSISTENT"
    assert per_date[2]["state"] == "NOT_EVALUATED_AFTER_FIRST_DEVIATION"
    assert all(item["partial_acceptance"] is False for item in per_date[1:])


def test_no_cross_date_or_partial_acceptance_is_claimed() -> None:
    matrix = _load("acceptance_matrix_results.json")
    completion = _load("completion.json")
    assert matrix["overall"] == "FAIL_CLOSED"
    assert matrix["multi_date_schema_stability_qualified"] is False
    assert completion["partial_acceptance_produced"] is False
    assert completion["cross_date_comparison_completed"] is False
    assert completion["completion_decision"] == "MULTI_DATE_SOURCE_NOT_QUALIFIED"


def test_lifecycle_boundaries_remain_closed() -> None:
    state = _load("lifecycle_non_authorization.json")
    assert state["adapter_state"] == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    forbidden = [key for key in state if key.endswith("_authorized")]
    assert forbidden and all(state[key] is False for key in forbidden)
    assert state["local_fno_database_accessed"] is False
    assert state["holdouts_accessed"] is False


def test_root_manifest_binds_every_sibling_artifact() -> None:
    manifest = _load("root_manifest.json")
    expected = sorted(path.name for path in EVIDENCE.glob("*.json") if path.name != "root_manifest.json")
    assert [item["path"] for item in manifest["artifacts"]] == expected
    for item in manifest["artifacts"]:
        payload = (EVIDENCE / item["path"]).read_bytes()
        assert item["byte_length"] == len(payload)
        assert item["sha256"] == hashlib.sha256(payload).hexdigest()


def test_tracked_evidence_is_sanitized() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in EVIDENCE.glob("*.json"))
    lowered = combined.lower()
    assert "c:\\users\\" not in lowered
    assert "/users/" not in lowered and "/home/" not in lowered
    for secret in ("authorization:", "cookie:", "password:", "bearer "):
        assert secret not in lowered
    assert "MULTI_DATE_SOURCE_NOT_QUALIFIED" in REPORT.read_text(encoding="utf-8")
