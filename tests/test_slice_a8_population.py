import gzip
from pathlib import Path

import pandas as pd
import pytest

from market_intel.foundation.nse_population_normalization import normalize_bhavcopy, normalize_mii_security
from market_intel.foundation.population_qualification import (
    AcquisitionProvenance, PairStatus, compare_snapshots, event_reconstruction_status,
    partial_sample_trust, qualify_pair,
)


def _prov(kind="AUTOMATED", current=False):
    return AcquisitionProvenance(kind, "https://official.test/date", "2026-08-24T00:00:00Z",
                                 "a" * 64, "v1", True, current)


def test_valid_pair_preserves_security_only_and_price_only():
    sec = pd.DataFrame([{"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "INE000A00001", "listing_id": "NSE:1"},
                        {"exchange": "NSE", "symbol": "B", "series": "EQ", "isin": "INE000A00002", "listing_id": "NSE:2"}])
    px = pd.DataFrame([{"exchange": "NSE", "exchange_symbol": "A", "series": "EQ"},
                       {"exchange": "NSE", "exchange_symbol": "C", "series": "EQ"}])
    result = qualify_pair(sec, px, cash_series={"EQ"}, security_provenance=_prov(), price_provenance=_prov())
    assert result["non_trading_security_count"] == 1 and result["unresolved_price_count"] == 1
    assert result["status"] == PairStatus.INCOMPLETE


def test_duplicate_and_missing_or_invalid_isin_fail_metrics():
    sec = pd.DataFrame([{"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "", "listing_id": "1"},
                        {"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "BAD", "listing_id": "2"}])
    px = pd.DataFrame([{"exchange": "NSE", "exchange_symbol": "A", "series": "EQ"}])
    result = qualify_pair(sec, px, cash_series={"EQ"}, security_provenance=_prov(), price_provenance=_prov())
    assert result["duplicate_security_keys"] == 1
    assert result["missing_isin_count"] == 1 and result["invalid_isin_count"] == 1


def test_conflicting_symbol_series_isin_is_explicit():
    sec = pd.DataFrame([{"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "INE000A00001", "listing_id": "1"},
                        {"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "INE000A00002", "listing_id": "2"}])
    px = pd.DataFrame([{"exchange": "NSE", "exchange_symbol": "A", "series": "EQ"}])
    result = qualify_pair(sec, px, cash_series={"EQ"}, security_provenance=_prov(), price_provenance=_prov())
    assert result["conflicting_symbol_series_isin_count"] == 1
    assert result["status"] == PairStatus.INCOMPLETE


def test_manual_provenance_and_current_list_prohibition():
    assert _prov("MANUAL_DOWNLOAD").method == "MANUAL_DOWNLOAD"
    with pytest.raises(ValueError, match="current security list"):
        _prov(current=True)


def test_incomplete_pair_and_partial_sample_do_not_pass_trust():
    assert qualify_pair(None, None, cash_series={"EQ"})["status"] == PairStatus.INCOMPLETE
    trust = partial_sample_trust([{"status": "QUALIFIED"}], 12)
    assert trust["historical_population_sample"] == "FAIL"
    assert trust["historical_universe_reconstructible"] == "FAIL"


def test_event_reconstruction_requires_complete_ledger():
    assert event_reconstruction_status(starting_snapshot=True, interval_events_complete=False,
                                       unresolved_transitions=0) == "FAIL"


def test_snapshot_comparison_does_not_infer_symbol_transition():
    old = pd.DataFrame([{"exchange": "NSE", "symbol": "OLD", "series": "EQ", "isin": "INE000A00001"}])
    new = pd.DataFrame([{"exchange": "NSE", "symbol": "NEW", "series": "EQ", "isin": "INE000A00001"}])
    result = compare_snapshots(old, new)
    assert len(result["additions"]) == len(result["removals"]) == 1


def test_typed_normalizers_and_schema_change(tmp_path):
    security_csv = ("FinInstrmId,TckrSymb,SctySrs,ISIN,Xchg,Sts,FinInstrmNm\n"
                    "1,A,EQ,INE000A00001,NSE,ACTIVE,Alpha\n").encode()
    sec_path = tmp_path / "security.gz"
    sec_path.write_bytes(gzip.compress(security_csv))
    sec = normalize_mii_security(sec_path, snapshot_date="2024-06-04", content_hash="a" * 64)
    assert sec.loc[0, "listing_id"] == "NSE:1"
    price_path = tmp_path / "prices.csv"
    price_path.write_text("SYMBOL,SERIES\nA,EQ\n", encoding="utf-8")
    px = normalize_bhavcopy(price_path, trade_date="2024-06-04", content_hash="b" * 64)
    assert px.loc[0, "exchange_symbol"] == "A"
    bad = tmp_path / "bad.gz"
    bad.write_bytes(gzip.compress(b"x,y\n1,2\n"))
    with pytest.raises(ValueError, match="unrecognized MII"):
        normalize_mii_security(bad, snapshot_date="2024-06-04", content_hash="c" * 64)
