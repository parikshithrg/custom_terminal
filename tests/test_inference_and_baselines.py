import pandas as pd

from market_intel.evidence.baselines import baseline_distributions
from market_intel.evidence.inference import decision_date_block_bootstrap


def test_block_bootstrap_is_deterministic_and_counts_dates_not_rows():
    frame = pd.DataFrame({"decision_time": list(pd.date_range("2020-01-01", periods=5).repeat(4)),
                          "value": range(20)})
    one = decision_date_block_bootstrap(frame, value_column="value", replications=100, seed=7)
    two = decision_date_block_bootstrap(frame, value_column="value", replications=100, seed=7)
    assert one == two
    assert one["n_dates"] == 5


def test_baselines_preserve_decision_dates_sizes_and_seed_distribution():
    rows = []
    for date in pd.date_range("2020-01-01", periods=3):
        for i in range(5):
            rows.append({"decision_time": date, "instrument_id": str(i), "outcome_status": "RESOLVED",
                         "selected": i < 2, "net_return_pct": float(i), "benchmark_return_pct": 1.0,
                         "net_excess_return_pct": float(i - 1)})
    frame = pd.DataFrame(rows)
    summary, draws = baseline_distributions(frame, seeds=[1, 2, 3])
    assert summary["seeds"] == [1, 2, 3]
    assert len(draws) == 3
    assert set(draws.seed) == {1, 2, 3}
