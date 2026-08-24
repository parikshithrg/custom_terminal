"""Historical security-snapshot and price-population reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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


class PairStatus(StrEnum):
    QUALIFIED = "QUALIFIED"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AcquisitionProvenance:
    method: str
    source_url: str
    retrieved_at: str
    content_hash: str
    parser_version: str
    official_source: bool
    current_list_substitute: bool = False

    def __post_init__(self) -> None:
        if self.method not in {"AUTOMATED", "MANUAL_DOWNLOAD"}:
            raise ValueError("unsupported acquisition method")
        if not self.official_source or len(self.content_hash) != 64:
            raise ValueError("official source and SHA-256 are mandatory")
        if self.current_list_substitute:
            raise ValueError("a current security list cannot substitute for a historical snapshot")


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


def qualify_pair(securities: pd.DataFrame | None, prices: pd.DataFrame | None, *,
                 cash_series: set[str], security_provenance: AcquisitionProvenance | None = None,
                 price_provenance: AcquisitionProvenance | None = None) -> dict:
    if securities is None or prices is None or security_provenance is None or price_provenance is None:
        return {"status": PairStatus.INCOMPLETE, "reason": "both immutable official objects are required"}
    result = reconcile_snapshot(securities, prices, cash_series=cash_series)
    sec = securities[securities.series.isin(cash_series)]
    missing_isin = int(sec["isin"].isna().sum() + sec["isin"].astype("string").str.strip().eq("").sum())
    invalid_isin = int((~sec["isin"].fillna("").astype(str).str.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$") &
                        sec["isin"].fillna("").astype(str).ne("")).sum())
    identifier_conflicts = int((sec.groupby(["exchange", "symbol", "series"], dropna=False)["isin"].nunique() > 1).sum())
    stable = sec.get("listing_id", pd.Series(index=sec.index, dtype="string")).notna().sum()
    pair_status = PairStatus.QUALIFIED if result.status == "PASS" and identifier_conflicts == 0 else PairStatus.INCOMPLETE
    return {**result.__dict__, "status": pair_status,
            "missing_isin_count": missing_isin, "invalid_isin_count": invalid_isin,
            "conflicting_symbol_series_isin_count": identifier_conflicts,
            "isin_coverage": 0.0 if len(sec) == 0 else float((len(sec) - missing_isin - invalid_isin) / len(sec)),
            "stable_identifier_coverage": 0.0 if len(sec) == 0 else float(stable / len(sec))}


def event_reconstruction_status(*, starting_snapshot: bool, interval_events_complete: bool,
                                unresolved_transitions: int) -> str:
    return "PASS" if starting_snapshot and interval_events_complete and unresolved_transitions == 0 else "FAIL"


def partial_sample_trust(date_results: list[dict], expected_dates: int) -> dict[str, str]:
    qualified = sum(str(row.get("status")) in {"QUALIFIED", PairStatus.QUALIFIED} for row in date_results)
    complete = len(date_results) == expected_dates and qualified == expected_dates
    return {"historical_population_sample": "PASS" if complete else "FAIL",
            "historical_universe_reconstructible": "UNKNOWN" if complete else "FAIL",
            "survivorship_safe": "UNKNOWN",
            "note": "Sample success cannot promote production coverage."}
