"""Historical security-snapshot and price-population reconciliation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PopulationResult:
    security_count: int
    price_count: int
    non_trading_security_count: int
    unresolved_price_count: int
    duplicate_security_keys: int
    duplicate_price_keys: int
    status: str


def reconcile_snapshot(securities: pd.DataFrame, prices: pd.DataFrame, *, cash_series: set[str]) -> PopulationResult:
    required_security = {"exchange", "symbol", "series", "isin"}
    required_price = {"exchange", "exchange_symbol", "series"}
    if required_security - set(securities) or required_price - set(prices):
        raise ValueError("population inputs do not satisfy canonical keys")
    sec = securities[securities.series.isin(cash_series)].copy()
    px = prices[prices.series.isin(cash_series)].copy()
    sec_keys = ["exchange", "symbol", "series"]
    px_keys = ["exchange", "exchange_symbol", "series"]
    duplicate_sec = int(sec.duplicated(sec_keys).sum())
    duplicate_px = int(px.duplicated(px_keys).sum())
    sec_set = set(map(tuple, sec[sec_keys].astype(str).to_numpy()))
    px_set = set(map(tuple, px[px_keys].astype(str).to_numpy()))
    nontrading = len(sec_set - px_set)
    unresolved = len(px_set - sec_set)
    status = "PASS" if not (duplicate_sec or duplicate_px or unresolved) else "FAIL"
    return PopulationResult(len(sec_set), len(px_set), nontrading, unresolved,
                            duplicate_sec, duplicate_px, status)


def compare_snapshots(previous: pd.DataFrame, current: pd.DataFrame) -> dict[str, list[tuple[str, str, str, str]]]:
    """Report additions/removals/identity changes without inferring causes."""
    key = ["exchange", "symbol", "series", "isin"]
    before = set(map(tuple, previous[key].fillna("").astype(str).to_numpy()))
    after = set(map(tuple, current[key].fillna("").astype(str).to_numpy()))
    return {"additions": sorted(after - before), "removals": sorted(before - after)}
