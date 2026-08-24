from __future__ import annotations

import pandas as pd

from market_intel.foundation.contracts import as_of_latest
from market_intel.research.momentum import MomentumFeatureDefinition, calculate_momentum


def test_revision_does_not_replace_earlier_vintage_before_publication():
    frame = pd.DataFrame([
        {"instrument_id": "A", "event_time": "2020-03-31", "published_at": "2020-05-01", "revision_number": 1, "value": 10.0},
        {"instrument_id": "A", "event_time": "2020-03-31", "published_at": "2020-08-01", "revision_number": 2, "value": 7.0},
    ])
    may = as_of_latest(frame, pd.Timestamp("2020-06-01"))
    august = as_of_latest(frame, pd.Timestamp("2020-08-02"))
    assert may.iloc[0]["value"] == 10.0
    assert august.iloc[0]["value"] == 7.0


def test_feature_cannot_use_data_after_knowledge_cutoff():
    index = pd.bdate_range("2020-01-01", periods=300)
    close = pd.DataFrame({"A": range(1, 301)}, index=index, dtype=float)
    definition = MomentumFeatureDefinition(lookback_sessions=20, skip_sessions=5, minimum_history_sessions=26)
    cutoff = index[100]
    baseline = calculate_momentum(close, definition, cutoff)
    mutated = close.copy()
    mutated.loc[index > cutoff, "A"] = 1_000_000
    assert baseline.equals(calculate_momentum(mutated, definition, cutoff))
    assert baseline.index.max() == cutoff

