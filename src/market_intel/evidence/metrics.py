"""Three-layer evidence reports for cross-sectional momentum."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from market_intel.evidence.inference import decision_date_block_bootstrap


def prediction_report(outcomes: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    resolved = outcomes[outcomes["outcome_status"] == "RESOLVED"].copy()
    per_date = []
    for decision_time, group in resolved.groupby("decision_time"):
        if len(group) >= 3:
            ic = stats.spearmanr(group["feature_value"], group["net_excess_return_pct"]).statistic
            per_date.append({"decision_time": decision_time, "rank_ic": ic, "n": len(group)})
    ic_frame = pd.DataFrame(per_date)
    resolved["bucket"] = pd.qcut(resolved["percentile"], 5, labels=False, duplicates="drop")
    buckets = resolved.groupby("bucket", observed=True).agg(
        n=("net_excess_return_pct", "size"),
        mean_net_excess_pct=("net_excess_return_pct", "mean"),
        mean_net_pct=("net_return_pct", "mean"),
    ).reset_index()
    mean_ic = float(ic_frame["rank_ic"].mean()) if not ic_frame.empty else float("nan")
    clustered = decision_date_block_bootstrap(
        ic_frame, value_column="rank_ic", block_length=2, replications=2000, seed=42
    )
    report = {
        "n_observations": len(resolved), "effective_decision_dates": len(ic_frame),
        "mean_rank_ic": mean_ic, "rank_ic_ci95_low": clustered["ci95_low"],
        "rank_ic_ci95_high": clustered["ci95_high"],
        "uncertainty_method": clustered,
        "bucket_monotonic": bool(buckets["mean_net_excess_pct"].is_monotonic_increasing),
    }
    return report, buckets


def economic_report(outcomes: pd.DataFrame) -> dict:
    resolved = outcomes[outcomes["outcome_status"] == "RESOLVED"]
    selected = resolved[resolved["selected"] & resolved["trade_executed"]]
    unresolved = outcomes[outcomes["outcome_status"] != "RESOLVED"]
    return {
        "n_selected_resolved": len(selected),
        "mean_gross_return_pct": float(selected["gross_return_pct"].mean()),
        "mean_cost_pct": float(selected["cost_pct"].mean()),
        "mean_net_return_pct": float(selected["net_return_pct"].mean()),
        "mean_benchmark_return_pct": float(selected["benchmark_return_pct"].mean()),
        "mean_net_excess_return_pct": float(selected["net_excess_return_pct"].mean()),
        "mean_mae_pct": float(selected["mae_pct"].mean()),
        "mean_mfe_pct": float(selected["mfe_pct"].mean()),
        "estimated_round_trip_turnover_pct_per_rebalance": 200.0,
        "cost_sensitivity_mean_net_pct": {
            "0_bps_per_side": float((selected["net_return_pct"] + selected["cost_pct"] - (selected["cost_pct"] - 0.1)).mean()),
            "5_bps_per_side": float(selected["net_return_pct"].mean()),
            "10_bps_per_side": float((selected["net_return_pct"] - 0.1).mean()),
        },
        "unresolved_count": len(unresolved),
        "unresolved_by_reason": unresolved["outcome_status"].value_counts().to_dict(),
    }


def portfolio_report(outcomes: pd.DataFrame, initial_capital: float = 50_000.0) -> tuple[dict, pd.DataFrame]:
    selected = outcomes[(outcomes["outcome_status"] == "RESOLVED") & outcomes["selected"] & outcomes["trade_executed"]].copy()
    monthly = selected.groupby("decision_time")["net_return_pct"].mean().sort_index() / 100.0
    benchmark_monthly = selected.groupby("decision_time")["benchmark_return_pct"].mean().sort_index() / 100.0
    equity = initial_capital * (1.0 + monthly).cumprod()
    benchmark_equity = initial_capital * (1.0 + benchmark_monthly).cumprod()
    curve = pd.DataFrame({"date": equity.index, "equity": equity.values,
                          "benchmark_equity": benchmark_equity.reindex(equity.index).values})
    if equity.empty:
        return {"n_rebalances": 0, "max_drawdown_pct": float("nan")}, curve
    drawdown = equity / equity.cummax() - 1.0
    benchmark_drawdown = benchmark_equity / benchmark_equity.cummax() - 1.0
    max_names = int(selected.groupby("decision_time").size().max())
    return {
        "n_rebalances": len(equity), "ending_equity": float(equity.iloc[-1]),
        "total_return_pct": float((equity.iloc[-1] / initial_capital - 1.0) * 100.0),
        "benchmark_ending_equity": float(benchmark_equity.iloc[-1]),
        "benchmark_total_return_pct": float((benchmark_equity.iloc[-1] / initial_capital - 1.0) * 100.0),
        "terminal_excess_wealth_inr": float(equity.iloc[-1] - benchmark_equity.iloc[-1]),
        "max_drawdown_pct": float(drawdown.min() * 100.0),
        "benchmark_max_drawdown_pct": float(benchmark_drawdown.min() * 100.0),
        "mean_names_per_rebalance": float(selected.groupby("decision_time").size().mean()),
        "maximum_names_per_rebalance": max_names,
        "maximum_single_name_weight_pct": 100.0 / max_names if max_names else float("nan"),
        "gross_exposure_pct": 100.0,
        "implementation_note": "Equal-weight rebalance approximation; legacy slot-constrained portfolio retained for compatibility comparison",
    }, curve
