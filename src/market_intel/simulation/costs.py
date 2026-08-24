"""Deterministic Indian delivery-equity cost contract for Slice A."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DeliveryCostDefinition:
    version: str = "india_delivery_2026_08_13_slippage_5bps_v1"
    brokerage_pct_per_side: float = 0.0
    brokerage_cap_inr: float = 20.0
    stt_buy_pct: float = 0.1
    stt_sell_pct: float = 0.1
    exchange_txn_pct_per_side: float = 0.00297
    sebi_pct_per_side: float = 0.0001
    stamp_duty_buy_pct: float = 0.015
    gst_pct: float = 18.0
    slippage_bps_per_side: float = 5.0
    effective_from: str = "2026-08-13"
    effective_to: str | None = None
    historical_accuracy: str = "COMPATIBILITY_APPROXIMATION_NOT_A_HISTORICAL_SCHEDULE"


@dataclass(frozen=True)
class DatedCostSchedule:
    """Date-effective schedule wrapper; Slice A v1 remains its sole entry."""

    version: str
    entries: tuple[DeliveryCostDefinition, ...]

    def at(self, trade_date: pd.Timestamp) -> DeliveryCostDefinition:
        when = pd.Timestamp(trade_date)
        matches = [entry for entry in self.entries if pd.Timestamp(entry.effective_from) <= when and
                   (entry.effective_to is None or when < pd.Timestamp(entry.effective_to))]
        if len(matches) != 1:
            raise LookupError(f"expected exactly one cost schedule at {when.date()}, found {len(matches)}")
        return matches[0]


def leg_cost(value: float, side: str, definition: DeliveryCostDefinition) -> float:
    brokerage = min(value * definition.brokerage_pct_per_side / 100.0, definition.brokerage_cap_inr)
    stt_rate = definition.stt_buy_pct if side == "buy" else definition.stt_sell_pct
    stt = value * stt_rate / 100.0
    exchange = value * definition.exchange_txn_pct_per_side / 100.0
    sebi = value * definition.sebi_pct_per_side / 100.0
    stamp = value * definition.stamp_duty_buy_pct / 100.0 if side == "buy" else 0.0
    gst = (brokerage + exchange + sebi) * definition.gst_pct / 100.0
    slippage = value * definition.slippage_bps_per_side / 10_000.0
    return brokerage + stt + exchange + sebi + stamp + gst + slippage


def round_trip_cost(entry_value: float, exit_value: float, definition: DeliveryCostDefinition) -> float:
    return leg_cost(entry_value, "buy", definition) + leg_cost(exit_value, "sell", definition)
