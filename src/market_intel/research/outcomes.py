"""Explicit executable outcome contract for the momentum experiment."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from market_intel.simulation.costs import DeliveryCostDefinition, round_trip_cost


@dataclass(frozen=True)
class OutcomeDefinition:
    outcome_id: str = "next_open_21_session_excess"
    version: str = "next_open_21_session_excess_v1"
    decision_clock: str = "NSE_CLOSE"
    entry_convention: str = "NEXT_SESSION_OPEN"
    exit_convention: str = "OPEN_AFTER_21_SESSIONS_FROM_ENTRY"
    holding_sessions: int = 21
    target: str = "BENCHMARK_RELATIVE_NET_RETURN"
    corporate_action_treatment: str = "Exchange OHLC; no inferred adjustment inside holding window"
    missing_price_treatment: str = "Explicit MISSING_ENTRY or MISSING_EXIT; never drop silently"
    delisting_treatment: str = "UNRESOLVED_DELISTING; blocks validation gate pending terminal-value source"
    mae_mfe: bool = True

    def parameters(self) -> dict:
        return asdict(self)


def materialize_outcomes(
    ranked: pd.DataFrame,
    open_: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    benchmark_open: pd.Series,
    definition: OutcomeDefinition,
    costs: DeliveryCostDefinition,
    target_value: float,
) -> pd.DataFrame:
    calendar = open_.index
    positions = {date: i for i, date in enumerate(calendar)}
    rows: list[dict] = []
    for record in ranked.to_dict("records"):
        decision_time = pd.Timestamp(record["decision_time"])
        instrument = record["instrument_id"]
        pos = positions.get(decision_time)
        base = dict(record)
        if pos is None or pos + 1 >= len(calendar):
            rows.append({**base, "outcome_status": "MISSING_ENTRY", "entry_time": pd.NaT, "exit_time": pd.NaT})
            continue
        entry_pos = pos + 1
        exit_pos = entry_pos + definition.holding_sessions
        entry_time = calendar[entry_pos]
        if exit_pos >= len(calendar):
            rows.append({**base, "outcome_status": "RIGHT_CENSORED", "entry_time": entry_time, "exit_time": pd.NaT})
            continue
        exit_time = calendar[exit_pos]
        entry_price = open_.at[entry_time, instrument]
        exit_price = open_.at[exit_time, instrument]
        if pd.isna(entry_price) or entry_price <= 0:
            rows.append({**base, "outcome_status": "MISSING_ENTRY", "entry_time": entry_time, "exit_time": exit_time})
            continue
        if pd.isna(exit_price) or exit_price <= 0:
            rows.append({**base, "outcome_status": "UNRESOLVED_DELISTING", "entry_time": entry_time, "exit_time": exit_time})
            continue
        shares = int(target_value // entry_price)
        if shares < 1:
            rows.append({**base, "outcome_status": "UNFILLABLE_PRICE", "entry_time": entry_time, "exit_time": exit_time})
            continue
        entry_value, exit_value = entry_price * shares, exit_price * shares
        cost_inr = round_trip_cost(entry_value, exit_value, costs)
        gross_pct = (exit_price / entry_price - 1.0) * 100.0
        cost_pct = cost_inr / entry_value * 100.0
        net_pct = gross_pct - cost_pct
        benchmark_entry = benchmark_open.get(entry_time, np.nan)
        benchmark_exit = benchmark_open.get(exit_time, np.nan)
        benchmark_pct = (
            (benchmark_exit / benchmark_entry - 1.0) * 100.0
            if pd.notna(benchmark_entry) and pd.notna(benchmark_exit) and benchmark_entry > 0
            else np.nan
        )
        window_high = high.loc[entry_time:exit_time, instrument]
        window_low = low.loc[entry_time:exit_time, instrument]
        mfe = (window_high.max() / entry_price - 1.0) * 100.0
        mae = (window_low.min() / entry_price - 1.0) * 100.0
        rows.append({
            **base, "outcome_status": "RESOLVED", "entry_time": entry_time,
            "exit_time": exit_time, "entry_price": entry_price, "exit_price": exit_price,
            "gross_return_pct": gross_pct, "cost_pct": cost_pct,
            "net_return_pct": net_pct, "benchmark_return_pct": benchmark_pct,
            "net_excess_return_pct": net_pct - benchmark_pct,
            "mae_pct": mae, "mfe_pct": mfe, "shares": shares,
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    # Compatibility with the legacy trade lifecycle: a symbol cannot receive
    # another implemented entry while its earlier selected trade is open.
    # Predictions/outcomes remain available for research; `trade_executed`
    # controls only the realizable economic/portfolio layer.
    result["trade_executed"] = False
    busy_until: dict[str, pd.Timestamp] = {}
    ordered = result.sort_values(["decision_time", "instrument_id"], kind="stable")
    for idx, row in ordered.iterrows():
        if not bool(row["selected"]):
            continue
        instrument = row["instrument_id"]
        blocked = busy_until.get(instrument)
        if blocked is not None and pd.Timestamp(row["decision_time"]) < blocked:
            continue
        result.at[idx, "trade_executed"] = True
        if row["outcome_status"] == "RESOLVED":
            busy_until[instrument] = pd.Timestamp(row["exit_time"])
        elif row["outcome_status"] in ("UNRESOLVED_DELISTING", "RIGHT_CENSORED"):
            busy_until[instrument] = pd.Timestamp.max
    return result
