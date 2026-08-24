from __future__ import annotations

import pandas as pd

from market_intel.research.outcomes import OutcomeDefinition, materialize_outcomes
from market_intel.simulation.costs import DeliveryCostDefinition, round_trip_cost


def _ranked(date):
    return pd.DataFrame([{"decision_time": date, "instrument_id": "A", "feature_value": 1.0,
                          "rank": 1, "percentile": 1.0, "selected": True}])


def test_outcome_starts_strictly_after_decision_and_cost_is_deterministic():
    dates = pd.bdate_range("2020-01-01", periods=30)
    open_ = pd.DataFrame({"A": range(100, 130)}, index=dates, dtype=float)
    high, low = open_ + 1, open_ - 1
    definition = OutcomeDefinition(holding_sessions=3)
    costs = DeliveryCostDefinition()
    result = materialize_outcomes(_ranked(dates[5]), open_, high, low,
                                  pd.Series(range(200, 230), index=dates, dtype=float),
                                  definition, costs, 10_000)
    row = result.iloc[0]
    assert row["entry_time"] == dates[6]
    assert row["exit_time"] == dates[9]
    assert row["entry_time"] > row["decision_time"]
    assert round_trip_cost(10_000, 11_000, costs) == round_trip_cost(10_000, 11_000, costs)


def test_missing_exit_is_explicit_delisting_state():
    dates = pd.bdate_range("2020-01-01", periods=10)
    open_ = pd.DataFrame({"A": 100.0}, index=dates)
    open_.loc[dates[5], "A"] = float("nan")
    result = materialize_outcomes(_ranked(dates[1]), open_, open_ + 1, open_ - 1,
                                  pd.Series(200.0, index=dates), OutcomeDefinition(holding_sessions=3),
                                  DeliveryCostDefinition(), 10_000)
    assert result.iloc[0]["outcome_status"] == "UNRESOLVED_DELISTING"

