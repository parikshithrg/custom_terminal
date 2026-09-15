"""Governance and evidence checks for the R10N-F diagnostic milestone."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "investigations" / "r10n_f" / "diagnosis_v1"
R10NE = ROOT / "docs" / "investigations" / "r10n_e" / "qualification_v1"


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_failure_is_exactly_reproduced_without_adapter_change() -> None:
    failure = _load("failure_reproduction.json")
    source = ROOT / "src" / "market_intel" / "foundation" / "nse_fno_candidate.py"
    assert failure["result"] == "REPRODUCED"
    assert failure["error_code"] == "OHLC_INCONSISTENT"
    assert failure["csv_row_number"] == 4724
    assert failure["individual_trigger"] == "HIGH_BELOW_CLOSE_ONLY"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == failure["unchanged_adapter_sha256"]


def test_source_integrity_and_offline_boundary_are_recorded() -> None:
    integrity = _load("source_integrity_reconciliation.json")
    assert integrity["verified_before_row_access"] is True
    assert len(integrity["packages"]) == 3
    assert all(item["manifest_sizes_and_hashes"] == "MATCH" for item in integrity["packages"])
    assert all(item["udiff_zip_crc"] == "PASS" for item in integrity["packages"])
    assert all(item["mii_gzip_complete_decompression_and_crc"] == "PASS" for item in integrity["packages"])
    assert integrity["network_requests"] == 0


def test_predicate_counts_reconcile_and_do_not_qualify_source() -> None:
    rows = {item["trading_date"]: item for item in _load("predicate_aggregate_counts.json")["dates"]}
    assert set(rows) == {"2026-09-09", "2026-09-10", "2025-07-08"}
    for item in rows.values():
        assert item["total_rows"] == item["zero_volume_rows"] + item["nonzero_volume_rows"]
        assert item["high_below_open"] == item["high_below_low"] == 0
        assert item["low_above_open"] == item["low_above_close"] == 0
    assert rows["2026-09-10"]["violating_nonzero_volume_rows"] == 2
    assert rows["2026-09-09"]["violating_nonzero_volume_rows"] == 0
    assert rows["2025-07-08"]["violating_nonzero_volume_rows"] == 0
    assert _load("completion.json")["source_qualified"] is False


def test_examples_are_bounded_hashed_and_contain_no_direct_identity() -> None:
    evidence = _load("sanitized_bounded_examples.json")
    assert len(evidence["examples"]) == evidence["sanitization"]["examples_retained"] == 2
    assert len(evidence["examples"]) <= evidence["sanitization"]["example_limit"]
    for item in evidence["examples"]:
        assert len(item["financial_instrument_id_sha256"]) == 64
        assert item["failed_predicates"] == ["high_below_close"]
        assert item["identity_assessment"]["contributed_to_ohlc_predicate"] is False
    text = json.dumps(evidence).lower()
    assert "ticker" in text
    assert '"ticker_retained": false' in text
    assert "tckrsymb" not in text


def test_documentation_gap_drives_separate_remediation_decision() -> None:
    semantics = _load("documented_vs_assumed_semantics.json")
    decision = _load("adapter_change_decision.json")
    assert semantics["official_evidence_state"] == "PENDING_OFFICIAL_FORMAT_EVIDENCE"
    assert semantics["authoritative_local_statement_that_close_must_be_within_high_low"] is False
    assert decision["decision"] == "ADAPTER_OHLC_RULE_SEMANTICS_REQUIRE_REMEDIATION"
    assert decision["adapter_modified"] is decision["threshold_relaxed"] is False
    assert decision["r10ng_required_before_any_remediation"] is True


def test_lifecycle_and_prior_evidence_remain_closed() -> None:
    lifecycle = _load("lifecycle_non_authorization.json")
    assert lifecycle["adapter_state"] == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert lifecycle["source_state"] == "MULTI_DATE_SOURCE_NOT_QUALIFIED"
    assert lifecycle["sealed_r10na_through_r10ne_evidence_modified"] is False
    assert lifecycle["retained_packages_deleted"] is False
    prior_manifest = json.loads((R10NE / "root_manifest.json").read_text(encoding="utf-8"))
    for item in prior_manifest["artifacts"]:
        payload = (R10NE / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_root_manifest_binds_all_sibling_artifacts() -> None:
    manifest = _load("root_manifest.json")
    expected = sorted(path.name for path in EVIDENCE.glob("*.json") if path.name != "root_manifest.json")
    assert [item["path"] for item in manifest["artifacts"]] == expected
    for item in manifest["artifacts"]:
        payload = (EVIDENCE / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_tracked_diagnostic_evidence_has_no_private_paths_or_raw_rows() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in EVIDENCE.glob("*.json")).lower()
    assert "c:\\users\\" not in text and "/users/" not in text and "/home/" not in text
    for marker in ("authorization:", "cookie:", "password:", "bearer ", "tckrsymb"):
        assert marker not in text
