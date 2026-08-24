"""Registered 12-1 cross-sectional momentum feature."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class MomentumFeatureDefinition:
    feature_id: str = "momentum_12_1"
    version: str = "momentum_12_1_v1"
    economic_meaning: str = "Trailing price performance excluding the recent reversal month"
    lookback_sessions: int = 252
    skip_sessions: int = 21
    minimum_history_sessions: int = 274
    input_dataset: str = "nse_cash_daily.close"
    availability_assumption: str = "Decision after NSE close; close at T is public by decision time"
    null_policy: str = "Require a complete lookback and positive start/end prices"
    staleness_policy: str = "Universe staleness gate applies before ranking"
    code_version: str = "momentum_feature_v1"

    def parameters(self) -> dict:
        return asdict(self)


def calculate_momentum(
    close: pd.DataFrame,
    definition: MomentumFeatureDefinition,
    knowledge_cutoff: pd.Timestamp,
) -> pd.DataFrame:
    """Calculate without reading any row after the declared cutoff."""
    safe = close.loc[close.index <= pd.Timestamp(knowledge_cutoff)]
    recent = safe.shift(definition.skip_sessions)
    start = safe.shift(definition.skip_sessions + definition.lookback_sessions)
    result = recent / start - 1.0
    result[(recent <= 0) | (start <= 0)] = float("nan")
    return result


def rank_at_decisions(
    feature: pd.DataFrame,
    membership: pd.DataFrame,
    decision_times: list[pd.Timestamp],
    top_fraction: float,
) -> pd.DataFrame:
    rows: list[dict] = []
    for decision_time in decision_times:
        if decision_time not in feature.index or decision_time not in membership.index:
            continue
        eligible = membership.columns[membership.loc[decision_time].to_numpy()]
        values = feature.loc[decision_time, eligible].dropna()
        if values.empty:
            continue
        ordered = (
            pd.DataFrame({"feature_value": values.to_numpy(), "instrument_id": values.index})
            .sort_values(["feature_value", "instrument_id"], ascending=[False, True], kind="stable")
            .reset_index(drop=True)
        )
        ordered["rank"] = range(1, len(ordered) + 1)
        ordered["percentile"] = 1.0 - (ordered["rank"] - 1) / len(ordered)
        n_top = max(1, int(__import__("math").ceil(len(ordered) * top_fraction)))
        ordered["selected"] = ordered["rank"] <= n_top
        ordered["decision_time"] = decision_time
        rows.extend(ordered.to_dict("records"))
    return pd.DataFrame(rows)

