"""Non-destructive discontinuity classification and adjustment-factor records."""

from __future__ import annotations

import pandas as pd


ACTION_TYPES = {"SPLIT", "BONUS", "DIVIDEND", "RIGHTS", "MERGER", "DEMERGER", "SYMBOL_CHANGE", "ISIN_CHANGE"}


def classify_price_discontinuities(prices: pd.DataFrame, actions: pd.DataFrame, threshold: float = 0.35) -> pd.DataFrame:
    """Classify candidates without changing raw OHLC or inventing actions."""
    ordered = prices.sort_values(["instrument_id", "trade_date"], kind="stable").copy()
    ordered["close_return"] = ordered.groupby("instrument_id")["close"].pct_change(fill_method=None)
    observations = ordered[ordered["close_return"].notna()]
    action_lookup = {}
    for row in actions.to_dict("records"):
        key = (row["instrument_id"], pd.Timestamp(row.get("ex_date") or row.get("effective_date")))
        action_lookup.setdefault(key, []).append(row["action_type"])
    rows = []
    for row in observations.to_dict("records"):
        types = action_lookup.get((row["instrument_id"], pd.Timestamp(row["trade_date"])), [])
        classification = types[0] if len(types) == 1 and types[0] in ACTION_TYPES else (
            "AMBIGUOUS_MULTIPLE_ACTIONS" if len(types) > 1 else
            "UNRESOLVED_DISCONTINUITY" if abs(row["close_return"]) >= threshold else "ORDINARY_PRICE_MOVE")
        rows.append({"instrument_id": row["instrument_id"], "trade_date": row["trade_date"],
                     "raw_close_return": row["close_return"], "classification": classification,
                     "raw_price_preserved": True})
    return pd.DataFrame(rows)


def adjustment_factors(actions: pd.DataFrame) -> pd.DataFrame:
    """Derived factors are stored separately; raw prices are never rewritten."""
    eligible = actions[actions["action_type"].isin({"SPLIT", "BONUS"}) & actions["ratio"].notna()].copy()
    if eligible.empty:
        return pd.DataFrame(columns=["instrument_id", "effective_date", "action_id", "adjustment_factor"])
    eligible["adjustment_factor"] = 1.0 / eligible["ratio"].astype(float)
    return eligible[["instrument_id", "effective_date", "action_id", "adjustment_factor"]]
