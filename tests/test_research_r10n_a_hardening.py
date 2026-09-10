"""Offline governance checks for R.10N-A downloader hardening."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from tools.download_nse_fno_reports import build_plan


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10n_a/hardening_v1"
R10M = ROOT / "docs/investigations/r10m/source_route_v1"


def test_recorded_dry_run_is_exactly_the_code_plan_and_non_authorizing() -> None:
    recorded = json.loads((RUN / "dry_run_plan.json").read_text(encoding="utf-8"))
    plan = build_plan(date(2026, 9, 9), "both")
    assert recorded["baseline_commit"] == "b9a1339598a611c916905455a107103bf169ff43"
    assert recorded["acquisition_mode"] == "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION"
    assert recorded["files"] == [
        {"key": item.key, "role": item.role, "filename": item.filename, "url": item.url}
        for item in plan
    ]
    assert recorded["network_requests"] == 0
    assert recorded["payloads_retained"] == 0
    assert recorded["output_target_created"] is False
    assert recorded["acknowledgement_flag_used"] is False
    assert recorded["acquisition_authorized"] is False


def test_owner_report_covers_official_pages_scope_ambiguity_and_decision() -> None:
    report = (ROOT / "reports/NSE_FNO_OWNER_RETENTION_DECISION.md").read_text(encoding="utf-8")
    for url in (
        "https://www.nseindia.com/static/nse-terms-of-use",
        "https://www.nseindia.com/static/nse-copyright",
        "https://www.nseindia.com/static/market-data/nse-data-policy",
        "https://www.nseindia.com/all-reports-derivatives",
        "https://www.nseindia.com/static/resources/forms-formats-members",
    ):
        assert url in report
    assert "Availability is not permission" in report
    assert "unresolved policy ambiguity" in report
    assert "READY_FOR_OWNER_RETENTION_DECISION" in report
    assert "Do not execute it merely because it appears in this report." in report
    assert "--date 2026-09-09 --report both --acknowledge-nse-terms" in report


def test_sealed_r10m_evidence_still_matches_its_manifest() -> None:
    manifest = json.loads((R10M / "root_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["artifact_hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
