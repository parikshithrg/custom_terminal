from pathlib import Path

import pandas as pd
import pytest

from market_intel.foundation.acceptance import CanonicalDatasetBundle, assess_bundle
from market_intel.foundation.canonical_schemas import (BENCHMARK_SCHEMA, CORPORATE_ACTION_SCHEMA,
                                                       COST_SCHEDULE_SCHEMA, DAILY_EQUITY_SCHEMA,
                                                       SECURITY_MASTER_SCHEMA, TERMINAL_OUTCOME_SCHEMA)
from market_intel.foundation.corporate_action_integrity import adjustment_factors, classify_price_discontinuities
from market_intel.foundation.identity_resolution import ResolutionStatus, alias_conflicts, resolve_identity
from market_intel.foundation.providers import AcquisitionRequest, DatasetKind, ProviderObject
from market_intel.foundation.raw_ingestion import acquire_immutable, verify_raw_object
from market_intel.foundation.reconciliation import population_by_year, reconcile_benchmarks, reconcile_costs, reconcile_terminal


def _daily():
    return pd.DataFrame({"trade_date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
        "instrument_id": ["I1", "I1"], "listing_id": ["L1", "L1"], "exchange_symbol": ["A", "A"],
        "series": ["EQ", "EQ"], "open": [10., 20.], "high": [11., 21.], "low": [9., 19.],
        "close": [10., 20.], "previous_close": [pd.NA, 10.], "volume": [100., 100.],
        "exchange_turnover": [1000., 2000.], "trade_count": [10., 10.],
        "published_at": pd.to_datetime(["2020-01-01 18:00", "2020-01-02 18:00"]),
        "retrieved_at": pd.to_datetime(["2020-01-03", "2020-01-03"]), "source_id": ["p", "p"],
        "raw_payload_hash": ["h", "h"]})


def _master(status="ACTIVE", end=pd.NaT):
    return SECURITY_MASTER_SCHEMA.validate(pd.DataFrame([{"issuer_id": "E1", "instrument_id": "I1",
        "listing_id": "L1", "exchange": "NSE", "segment_series": "EQ", "symbol": "A",
        "isin": "INE000000001", "valid_from": "2019-01-01", "valid_to": pd.NaT,
        "listing_date": "2019-01-01", "end_date": end, "status": status}]))


def _aliases():
    return pd.DataFrame([{"instrument_id": "I1", "exchange": "NSE", "symbol": "A",
                          "valid_from": pd.Timestamp("2019-01-01"), "valid_to": pd.NaT}])


def _empty(schema):
    return schema.validate(pd.DataFrame({c: pd.Series(dtype=d) for c, d in schema.columns.items()}))


def test_raw_acquisition_is_immutable_and_hash_verified(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    obj = ProviderObject("fake", DatasetKind.DAILY_EQUITY, "fixture", source)
    _, manifest = acquire_immutable(obj, raw_root=tmp_path / "raw", parser_version="v1")
    manifest_path = Path(manifest.stored_payload).parent / "manifest.json"
    assert verify_raw_object(manifest_path)
    Path(manifest.stored_payload).write_text("mutated", encoding="utf-8")
    assert not verify_raw_object(manifest_path)
    with pytest.raises(FileExistsError):
        acquire_immutable(obj, raw_root=tmp_path / "raw", parser_version="v1")


def test_typed_normalization_coerces_and_rejects_missing_columns():
    typed = DAILY_EQUITY_SCHEMA.validate(_daily().astype({"volume": "int64"}))
    assert str(typed.trade_date.dtype) == "datetime64[ns]"
    with pytest.raises(ValueError):
        DAILY_EQUITY_SCHEMA.validate(_daily().drop(columns="listing_id"))


def test_alias_overlap_and_identity_priority_are_deterministic():
    aliases = pd.DataFrame([{"instrument_id": "I1", "exchange": "NSE", "symbol": "A", "valid_from": "2020-01-01", "valid_to": "2021-01-01"},
                            {"instrument_id": "I2", "exchange": "NSE", "symbol": "A", "valid_from": "2020-06-01", "valid_to": pd.NaT}])
    assert len(alias_conflicts(aliases)) == 1
    resolution = resolve_identity({"source_record_id": "r", "listing_id": "L1", "isin": "WRONG",
                                   "symbol": "A", "event_date": "2020-07-01"}, _master(), aliases)
    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.method == "STABLE_LISTING_ID"


def test_ambiguous_or_name_only_identity_stays_unresolved():
    resolution = resolve_identity({"source_record_id": "r", "company_name": "Similar Name",
                                   "event_date": "2020-01-01"}, _master(), _aliases())
    assert resolution.status == ResolutionStatus.UNRESOLVED


def test_terminal_reconciliation_requires_record_for_ended_listing():
    checks = reconcile_terminal(_master(end="2020-02-01"), _empty(TERMINAL_OUTCOME_SCHEMA))
    assert checks[0].status == "FAIL"


def test_corporate_actions_preserve_raw_prices_and_separate_factors():
    prices = _daily()
    actions = CORPORATE_ACTION_SCHEMA.validate(pd.DataFrame([{"action_id": "X", "action_type": "SPLIT",
        "instrument_id": "I1", "announcement_date": "2019-12-01", "published_at": "2019-12-01",
        "ex_date": "2020-01-02", "record_date": "2020-01-03", "effective_date": "2020-01-02",
        "ratio": 2., "cash_amount": pd.NA, "old_identifier": pd.NA, "new_identifier": pd.NA,
        "predecessor_instrument_id": pd.NA, "successor_instrument_id": pd.NA}]))
    before = prices.close.copy()
    classified = classify_price_discontinuities(prices, actions, threshold=.35)
    assert classified.iloc[0].classification == "SPLIT"
    assert adjustment_factors(actions).iloc[0].adjustment_factor == .5
    pd.testing.assert_series_equal(before, prices.close)


def test_ordinary_move_and_unexplained_jump_remain_distinct():
    prices = pd.concat([_daily(), _daily().iloc[[1]].assign(trade_date=pd.Timestamp("2020-01-03"), close=21.,
                                                           open=21., high=22., low=20.)], ignore_index=True)
    empty_actions = _empty(CORPORATE_ACTION_SCHEMA)
    classified = classify_price_discontinuities(prices, empty_actions, threshold=.35)
    assert set(classified.classification) == {"UNRESOLVED_DISCONTINUITY", "ORDINARY_PRICE_MOVE"}


def test_population_counts_include_new_terminated_and_surviving():
    master = pd.concat([_master(), _master(end="2020-06-01").assign(instrument_id="I2", listing_id="L2",
                                                                     symbol="B", isin="INE000000002")])
    result = population_by_year(master)
    row = result[result.year == 2020].iloc[0]
    assert row.terminated_delisted == 1


def test_benchmark_classification_and_cost_gaps_are_explicit():
    benchmark = pd.DataFrame({"return_classification": ["UNKNOWN"]})
    assert reconcile_benchmarks(benchmark)[0].status == "FAIL"
    costs = COST_SCHEDULE_SCHEMA.validate(pd.DataFrame([{"component": "STT", "effective_from": "2021-01-01",
        "effective_to": pd.NaT, "rate": .1, "rate_base": "turnover", "source_reference": "x", "schedule_version": "v1"}]))
    assert reconcile_costs(costs, pd.Timestamp("2020-01-01"), pd.Timestamp("2022-01-01"))[0].status == "FAIL"


def test_acceptance_harness_rejects_incomplete_local_style_bundle():
    prices = DAILY_EQUITY_SCHEMA.validate(_daily().assign(exchange_turnover=pd.NA, published_at=pd.NaT))
    benchmark = BENCHMARK_SCHEMA.validate(pd.DataFrame({"date": prices.trade_date, "index_id": "NIFTY50",
        "return_classification": "PRI", "open": [100., 101.], "close": [100., 101.],
        "methodology_version": [pd.NA, pd.NA], "source_id": ["p", "p"]}))
    costs = COST_SCHEDULE_SCHEMA.validate(pd.DataFrame([{"component": "STT", "effective_from": "2020-01-02",
        "effective_to": pd.NaT, "rate": .1, "rate_base": "turnover", "source_reference": "x", "schedule_version": "v1"}]))
    contract, _, _, _ = assess_bundle(CanonicalDatasetBundle("x", "v1", prices,
        _master(status="UNRESOLVED_IDENTITY"), _aliases(), _empty(CORPORATE_ACTION_SCHEMA),
        _empty(TERMINAL_OUTCOME_SCHEMA), benchmark, costs, population_reference_complete=False))
    assert contract.price_history_complete == "FAIL"
    assert contract.exchange_turnover_available == "FAIL"
    assert contract.stable_security_identity_verified == "FAIL"


def test_provider_is_replaceable_behind_same_contract(tmp_path):
    class FakeProvider:
        provider_id = "fake"
        def discover(self, request):
            return []
        def parser_version(self, dataset):
            return "fake_v1"
    def foundation_consumer(provider):
        return provider.provider_id, provider.discover(AcquisitionRequest(DatasetKind.DAILY_EQUITY))
    assert foundation_consumer(FakeProvider()) == ("fake", [])
