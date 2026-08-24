from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from market_intel.foundation.artifacts import frame_hash
from market_intel.research.momentum import MomentumFeatureDefinition, calculate_momentum


FIXTURE = Path(__file__).parent / "fixtures" / "momentum_golden_v1"


def test_golden_feature_is_stable():
    expected = json.loads((FIXTURE / "expected.json").read_text())
    prices = pd.read_parquet(FIXTURE / "prices.parquet")
    close = prices.pivot(index="date", columns="instrument_id", values="close").sort_index()
    feature = calculate_momentum(close, MomentumFeatureDefinition(), close.index.max())
    assert frame_hash(feature) == expected["hashes"]["legacy_feature"]

