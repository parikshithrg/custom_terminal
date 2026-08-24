"""Versioned, point-in-time liquidity universe with exclusion evidence."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


UNIVERSE_VERSION = "liquidity_monthly_200_250_v1"


@dataclass(frozen=True)
class UniverseDefinition:
    version: str = UNIVERSE_VERSION
    size: int = 200
    buffer_size: int = 250
    lookback_sessions: int = 63
    minimum_history_sessions: int = 252
    maximum_staleness_days: int = 5
    minimum_price: float = 5.0


@dataclass(frozen=True)
class UniverseMaterialization:
    membership: pd.DataFrame
    decisions: pd.DataFrame
    definition: UniverseDefinition
    input_dataset_version: str


def month_end_sessions(calendar: pd.DatetimeIndex) -> list[pd.Timestamp]:
    values = pd.Series(calendar, index=calendar)
    return sorted(values.groupby([calendar.year, calendar.month]).max().tolist())


def _rank(values: pd.Series) -> pd.Index:
    frame = pd.DataFrame({"value": values.to_numpy(), "instrument_id": values.index})
    frame = frame.sort_values(
        ["value", "instrument_id"], ascending=[False, True], kind="stable"
    )
    return pd.Index(frame["instrument_id"])


def materialize_liquidity_universe(
    close: pd.DataFrame,
    turnover: pd.DataFrame,
    definition: UniverseDefinition,
    input_dataset_version: str,
) -> UniverseMaterialization:
    if definition.buffer_size < definition.size:
        raise ValueError("buffer_size must be >= size")
    if not close.index.equals(turnover.index) or not close.columns.equals(turnover.columns):
        raise ValueError("close and turnover panels must align")
    calendar = close.index
    live = close.notna()
    history = live.cumsum()
    idx = pd.Series(calendar, index=calendar)
    last_seen = live.apply(lambda col: idx.where(col).ffill())
    staleness = last_seen.apply(lambda col: (idx - col).dt.days)
    trailing_turnover = turnover.rolling(
        definition.lookback_sessions,
        min_periods=max(1, definition.lookback_sessions // 2),
    ).median()
    rebalances = month_end_sessions(calendar)
    membership = pd.DataFrame(False, index=calendar, columns=close.columns)
    incumbents: set[str] = set()
    rows: list[dict] = []

    for i, decision_time in enumerate(rebalances):
        reasons: dict[str, list[str]] = {instrument: [] for instrument in close.columns}
        for instrument in close.columns:
            if history.at[decision_time, instrument] < definition.minimum_history_sessions:
                reasons[instrument].append("INSUFFICIENT_HISTORY")
            stale = staleness.at[decision_time, instrument]
            if pd.isna(stale) or stale > definition.maximum_staleness_days:
                reasons[instrument].append("STALE_OR_NOT_TRADING")
            price = close.at[decision_time, instrument]
            if pd.isna(price) or price < definition.minimum_price:
                reasons[instrument].append("PRICE_BELOW_MINIMUM_OR_MISSING")
            liquidity = trailing_turnover.at[decision_time, instrument]
            if pd.isna(liquidity) or liquidity <= 0:
                reasons[instrument].append("LIQUIDITY_MISSING_OR_ZERO")

        eligible = [instrument for instrument, why in reasons.items() if not why]
        ranked = _rank(trailing_turnover.loc[decision_time, eligible].dropna())
        top = set(ranked[: definition.size])
        buffer = set(ranked[: definition.buffer_size])
        selected = top | (incumbents & buffer)
        ordered_selected = [instrument for instrument in ranked if instrument in selected]
        selected = set(ordered_selected[: definition.buffer_size])

        for rank, instrument in enumerate(ranked, start=1):
            rows.append({
                "decision_time": decision_time,
                "instrument_id": instrument,
                "eligible": instrument in selected,
                "eligibility_reason": "SELECTED" if instrument in selected else "OUTSIDE_LIQUIDITY_CUTOFF",
                "liquidity_rank": rank,
                "universe_version": definition.version,
                "input_dataset_version": input_dataset_version,
            })
        for instrument, why in reasons.items():
            if why:
                rows.append({
                    "decision_time": decision_time, "instrument_id": instrument,
                    "eligible": False, "eligibility_reason": "|".join(why),
                    "liquidity_rank": np.nan, "universe_version": definition.version,
                    "input_dataset_version": input_dataset_version,
                })

        next_end = rebalances[i + 1] if i + 1 < len(rebalances) else calendar[-1]
        active_days = calendar[(calendar > decision_time) & (calendar <= next_end)]
        if selected:
            membership.loc[active_days, sorted(selected)] = True
        incumbents = selected

    return UniverseMaterialization(
        membership=membership,
        decisions=pd.DataFrame(rows),
        definition=definition,
        input_dataset_version=input_dataset_version,
    )

