"""Preregistered, decision-time-safe cross-sectional baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_distributions(
    outcomes: pd.DataFrame, *, seeds: list[int], portfolio_size_column: str = "selected"
) -> tuple[dict, pd.DataFrame]:
    resolved = outcomes[outcomes["outcome_status"] == "RESOLVED"].copy()
    if resolved.empty:
        return {}, pd.DataFrame()
    benchmark = float(resolved["benchmark_return_pct"].mean())
    universe = float(resolved.groupby("decision_time")["net_return_pct"].mean().mean())
    selected_sizes = resolved.groupby("decision_time")[portfolio_size_column].sum().astype(int)
    rows = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        random_returns = []
        placebo_returns = []
        for date, group in resolved.groupby("decision_time", sort=True):
            n = min(int(selected_sizes.get(date, 0)), len(group))
            if n < 1:
                continue
            take = rng.choice(len(group), n, replace=False)
            random_returns.append(group.iloc[take]["net_return_pct"].mean())
            # Permute ranks within the same decision date, preserving date and outcomes.
            order = rng.permutation(len(group))[:n]
            placebo_returns.append(group.iloc[order]["net_excess_return_pct"].mean())
        rows.append({"seed": seed, "random_matched_mean_net_pct": np.mean(random_returns),
                     "neutral_rank_placebo_mean_excess_pct": np.mean(placebo_returns)})
    distribution = pd.DataFrame(rows)
    summary = {
        "benchmark_mean_return_pct": benchmark,
        "eligible_universe_equal_weight_mean_net_pct": universe,
        "random_matched": distribution["random_matched_mean_net_pct"].describe(percentiles=[.025, .5, .975]).to_dict(),
        "neutral_rank_placebo": distribution["neutral_rank_placebo_mean_excess_pct"].describe(percentiles=[.025, .5, .975]).to_dict(),
        "seeds": seeds,
    }
    return summary, distribution
