"""Offline governance checks for the authorized R10N-H implementation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from market_intel.foundation.nse_fno_candidate import (
    LIFECYCLE_STATE,
    MII_EXPIRY_ENCODING,
    OHLC_SEMANTICS_CONTRACT,
    OHLC_SEMANTICS_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "investigations" / "r10n_h" / "implementation_v1"


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_owner_authorized_only_separate_implementation() -> None:
    owner = _load("owner_authorization.json")
    assert owner["owner_answer"] == "YES_SEPARATE_R10N_H"
    assert owner["authorized"] is True
    assert owner["source_qualification_authorized"] is False
    assert owner["production_activation_authorized"] is False


def test_versioned_contract_and_decoder_are_explicit() -> None:
    implemented = _load("implemented_rule_contract.json")
    expiry = _load("expiry_encoding_decision.json")
    assert implemented["schema_version"] == OHLC_SEMANTICS_VERSION
    assert dict(OHLC_SEMANTICS_CONTRACT)["price_mutation_or_imputation"] is False
    assert expiry["decoder_version"] == MII_EXPIRY_ENCODING
    assert expiry["origin"] == "1980-01-01T00:00:00"
    assert expiry["timezone_rule"].startswith("TIMEZONE_FREE")


def test_official_evidence_is_nse_only_and_no_market_report_url_was_accessed() -> None:
    inventory = _load("official_expiry_evidence_inventory.json")
    assert inventory["market_report_urls_accessed"] == 0
    assert inventory["new_market_report_payloads_downloaded"] == 0
    for source in inventory["sources"]:
        assert re.fullmatch(r"https://nsearchives\.nseindia\.com/.*", source["url"])
        assert "/content/fo/" not in source["url"]
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])


def test_three_package_regression_is_expiry_complete_and_not_qualification() -> None:
    result = _load("three_package_regression_results.json")
    assert [row["trading_date"] for row in result["packages"]] == [
        "2026-09-09", "2026-09-10", "2025-07-08",
    ]
    assert sum(row["expiry_agreement"]["matched"] for row in result["packages"]) == 99026
    assert all(row["expiry_agreement"]["mismatched"] == 0 for row in result["packages"])
    assert all(row["price_immutability"]["exact_match"] for row in result["packages"])
    trigger = result["packages"][1]
    assert trigger["diagnostic_counts"]["CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS"] == 2
    assert result["source_qualified"] is False


def test_lifecycle_and_research_gates_remain_closed() -> None:
    lifecycle = _load("lifecycle_non_authorization.json")
    assert lifecycle["adapter_state"] == LIFECYCLE_STATE
    assert lifecycle["production_provider_registered"] is False
    assert lifecycle["research_fingerprint_refreshed"] is False
    assert lifecycle["research_fingerprint_expected_state"] == "STALE_FAIL_CLOSED"


def test_evidence_is_sanitized_and_root_manifest_is_complete() -> None:
    encoded = "\n".join(path.read_text(encoding="utf-8") for path in EVIDENCE.glob("*.json")).lower()
    for marker in ("c:\\users\\", "/users/", "/home/", "authorization:", "cookie:", "bearer ", "tckrsymb"):
        assert marker not in encoded
    manifest = _load("root_manifest.json")
    expected = sorted(path.name for path in EVIDENCE.glob("*.json") if path.name != "root_manifest.json")
    assert [item["path"] for item in manifest["artifacts"]] == expected
    for item in manifest["artifacts"]:
        payload = (EVIDENCE / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_completion_is_ready_only_for_separate_offline_requalification() -> None:
    completion = _load("completion.json")
    assert completion["completion_decision"] == "R10N_H_IMPLEMENTED_READY_FOR_OFFLINE_REQUALIFICATION"
    assert completion["source_qualified"] is False
