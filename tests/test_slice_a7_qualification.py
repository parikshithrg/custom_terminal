from datetime import date

import pandas as pd
import pytest

from market_intel.foundation.archive_pilot import PilotGate, evaluate_pilot, pilot_readiness, validate_benchmark_pair
from market_intel.foundation.official_evidence import (
    CostEntry, Resolution, mark_conflicting_assertions, normalize_lifecycle_rows,
    terminal_economic_resolution, uncovered_cost_intervals,
)
from market_intel.foundation.population_qualification import compare_snapshots, reconcile_snapshot


def _evidence(**overrides):
    row = {"case_id": "C1", "event_type": "SYMBOL_CHANGE", "exchange": "NSE",
           "source_organization": "NSE", "source_url": "https://nse.example/c1.pdf",
           "document_hash": "a" * 64, "retrieved_at": "2026-08-24T00:00:00Z",
           "parser_version": "manual_v1", "resolution_status": "QUALIFIED",
           "old_symbol": "OLD", "new_symbol": "NEW", "effective_date": "2023-01-01"}
    row.update(overrides)
    return row


def test_lifecycle_normalization_preserves_provenance_and_dates():
    frame = normalize_lifecycle_rows([_evidence()])
    assert frame.loc[0, "source_organization"] == "NSE"
    assert frame.loc[0, "effective_date"] == pd.Timestamp("2023-01-01")


def test_conflicting_official_evidence_is_not_silently_resolved():
    frame = normalize_lifecycle_rows([_evidence(), _evidence(source_organization="BSE", new_symbol="OTHER")])
    result = mark_conflicting_assertions(frame, ["new_symbol"])
    assert set(result.resolution_status) == {Resolution.CONFLICT}
    assert len(result) == 2


def test_final_quote_does_not_resolve_terminal_consideration():
    assert terminal_economic_resolution({"final_tradable_price": 10.0}) == Resolution.UNRESOLVED
    assert terminal_economic_resolution({"authoritative_terminal_document": True,
                                         "cash_consideration": 12.5}) == Resolution.QUALIFIED


def test_population_reconciliation_retains_nontrading_and_unresolved():
    securities = pd.DataFrame([
        {"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "INA"},
        {"exchange": "NSE", "symbol": "B", "series": "EQ", "isin": "INB"},
    ])
    prices = pd.DataFrame([
        {"exchange": "NSE", "exchange_symbol": "A", "series": "EQ"},
        {"exchange": "NSE", "exchange_symbol": "C", "series": "EQ"},
    ])
    result = reconcile_snapshot(securities, prices, cash_series={"EQ"})
    assert (result.non_trading_security_count, result.unresolved_price_count, result.status) == (1, 1, "FAIL")


def test_snapshot_changes_are_not_causally_inferred():
    old = pd.DataFrame([{"exchange": "NSE", "symbol": "A", "series": "EQ", "isin": "INA"}])
    new = pd.DataFrame([{"exchange": "NSE", "symbol": "B", "series": "EQ", "isin": "INA"}])
    changes = compare_snapshots(old, new)
    assert changes["additions"] and changes["removals"]


def test_pri_tri_cannot_be_substituted():
    validate_benchmark_pair({"index_id": "NIFTY50_PRI", "return_classification": "PRI"},
                            {"index_id": "NIFTY50_TRI", "return_classification": "TRI"})
    with pytest.raises(ValueError):
        validate_benchmark_pair({"index_id": "NIFTY50", "return_classification": "PRI"},
                                {"index_id": "NIFTY50", "return_classification": "TRI"})


def test_dated_cost_schedule_exposes_uncovered_components():
    entries = [CostEntry("STT", date(2024, 1, 1), date(2024, 12, 31), .001,
                         "sell consideration", "SELL", "official", "stt_v1")]
    gaps = uncovered_cost_intervals(entries, {"STT", "STAMP_DUTY"}, date(2024, 1, 1), date(2024, 12, 31))
    assert "STAMP_DUTY" in gaps and "STT" not in gaps


def test_pilot_readiness_and_abort_conditions():
    status, missing = pilot_readiness({"historical_security_snapshots": False, "daily_prices": True})
    assert status == "BLOCKED" and missing == ["historical_security_snapshots"]
    status, failures = evaluate_pilot(PilotGate(250, 250, 249, 250, 250, True))
    assert status == "ABORT" and failures == ["security_sessions=249/250"]


def test_access_quarantine_and_schema_changes_abort_pilot():
    status, failures = evaluate_pilot(PilotGate(1, 1, 1, 1, 1, True, access_quarantines=1, schema_failures=1))
    assert status == "ABORT"
    assert "access_quarantines=1" in failures and "schema_failures=1" in failures
