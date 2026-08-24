"""Dependence-aware uncertainty for repeated cross-sectional observations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def decision_date_block_bootstrap(
    frame: pd.DataFrame,
    *,
    value_column: str,
    date_column: str = "decision_time",
    block_length: int = 2,
    replications: int = 2000,
    seed: int = 42,
) -> dict:
    """Moving-block bootstrap over decision dates, retaining each full cross-section.

    Whole decision-date cross-sections preserve contemporaneous dependence. Blocks
    preserve short serial dependence from overlapping holding windows; repeated
    securities remain inside their original cross-sections.
    """
    if block_length < 1 or replications < 1:
        raise ValueError("block_length and replications must be positive")
    grouped = frame.dropna(subset=[value_column]).groupby(date_column)[value_column].mean().sort_index()
    values = grouped.to_numpy(dtype=float)
    if not len(values):
        return {"estimate": np.nan, "ci95_low": np.nan, "ci95_high": np.nan, "n_dates": 0}
    block_length = min(block_length, len(values))
    starts = np.arange(len(values) - block_length + 1)
    blocks_needed = int(np.ceil(len(values) / block_length))
    rng = np.random.default_rng(seed)
    draws = np.empty(replications)
    for i in range(replications):
        sample = np.concatenate([values[s:s + block_length] for s in rng.choice(starts, blocks_needed)])[:len(values)]
        draws[i] = sample.mean()
    return {
        "method": "moving_decision_date_block_bootstrap",
        "estimate": float(values.mean()),
        "ci95_low": float(np.quantile(draws, 0.025)),
        "ci95_high": float(np.quantile(draws, 0.975)),
        "n_dates": int(len(values)),
        "block_length": int(block_length),
        "replications": int(replications),
        "seed": int(seed),
    }
