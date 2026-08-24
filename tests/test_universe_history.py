from __future__ import annotations

import pandas as pd

from market_intel.research.universe import UniverseDefinition, materialize_liquidity_universe


def test_universe_is_decided_historically_and_effective_next_session():
    dates = pd.bdate_range("2020-01-01", periods=90)
    close = pd.DataFrame({"A": 10.0, "B": 10.0}, index=dates)
    turnover = pd.DataFrame({"A": 100.0, "B": 1.0}, index=dates)
    definition = UniverseDefinition(size=1, buffer_size=1, lookback_sessions=5,
                                    minimum_history_sessions=5, maximum_staleness_days=5)
    result = materialize_liquidity_universe(close, turnover, definition, "fixture-v1")
    first_decision = result.decisions["decision_time"].min()
    first_next = dates[dates > first_decision][0]
    assert not result.membership.loc[first_decision].any()
    assert result.membership.at[first_next, "A"]
    assert not result.membership.at[first_next, "B"]
    assert set(result.decisions["input_dataset_version"]) == {"fixture-v1"}


def test_future_disappearance_does_not_remove_prior_historical_eligibility():
    dates = pd.bdate_range("2020-01-01", periods=90)
    close = pd.DataFrame({"DIES_LATER": 10.0, "SURVIVES": 10.0}, index=dates)
    turnover = pd.DataFrame({"DIES_LATER": 100.0, "SURVIVES": 1.0}, index=dates)
    close.loc[dates[70]:, "DIES_LATER"] = float("nan")
    turnover.loc[dates[70]:, "DIES_LATER"] = float("nan")
    definition = UniverseDefinition(size=1, buffer_size=1, lookback_sessions=5,
                                    minimum_history_sessions=5, maximum_staleness_days=5)
    result = materialize_liquidity_universe(close, turnover, definition, "fixture-v1")
    early = result.decisions[(result.decisions.instrument_id == "DIES_LATER") & result.decisions.eligible]
    late = result.decisions[(result.decisions.instrument_id == "DIES_LATER") &
                            result.decisions.eligibility_reason.str.contains("STALE_OR_NOT_TRADING")]
    assert not early.empty
    assert not late.empty
