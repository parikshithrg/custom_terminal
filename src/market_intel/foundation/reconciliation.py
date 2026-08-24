"""Source-to-canonical integrity checks used by every provider."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .identity_resolution import alias_conflicts


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    count: int
    evidence: str


def _result(check_id: str, count: int, evidence: str, unknown: bool = False) -> CheckResult:
    return CheckResult(check_id, "UNKNOWN" if unknown else ("PASS" if count == 0 else "FAIL"), int(count), evidence)


def reconcile_daily(prices: pd.DataFrame) -> list[CheckResult]:
    keys = ["listing_id", "trade_date"]
    duplicate = int(prices.duplicated(keys).sum())
    impossible = int(((prices["high"] < prices[["open", "close", "low"]].max(axis=1)) |
                      (prices["low"] > prices[["open", "close", "high"]].min(axis=1))).sum())
    nonpositive = int((prices[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    zero_volume = int((prices["volume"] <= 0).sum())
    missing_turnover = int(prices["exchange_turnover"].isna().sum())
    return [_result("duplicate_trade_dates", duplicate, "unique listing/date required"),
            _result("impossible_ohlc", impossible, "low <= open/close <= high"),
            _result("non_positive_prices", nonpositive, "OHLC must be positive"),
            _result("zero_or_missing_volume", zero_volume + int(prices.volume.isna().sum()), "unexpected for equity sessions"),
            _result("missing_exchange_turnover", missing_turnover, "provider exchange turnover required")]


def reconcile_listing_gaps(prices: pd.DataFrame, benchmarks: pd.DataFrame) -> CheckResult:
    calendar = pd.DatetimeIndex(pd.to_datetime(benchmarks["date"].drop_duplicates()).sort_values())
    gaps = 0
    for _, group in prices.groupby("listing_id"):
        observed = pd.DatetimeIndex(pd.to_datetime(group.trade_date).drop_duplicates())
        expected = calendar[(calendar >= observed.min()) & (calendar <= observed.max())]
        gaps += len(expected.difference(observed))
    return _result("gaps_within_observed_listing_periods", gaps, "benchmark sessions absent inside first/last observed listing dates")


def reconcile_identity(master: pd.DataFrame, aliases: pd.DataFrame) -> list[CheckResult]:
    isin_conflicts = (master.dropna(subset=["isin"]).groupby("isin")["instrument_id"].nunique() > 1).sum()
    listing_conflicts = (master.groupby("listing_id")["instrument_id"].nunique() > 1).sum()
    overlaps = len(alias_conflicts(aliases)) if not aliases.empty else 0
    unresolved = int(master["instrument_id"].isna().sum() + master["listing_id"].isna().sum()
                     + master["status"].astype(str).str.contains("UNRESOLVED", case=False).sum())
    return [_result("isin_instrument_conflicts", int(isin_conflicts), "one ISIN must not silently map to multiple instruments"),
            _result("listing_instrument_conflicts", int(listing_conflicts), "stable listing identity must be unique"),
            _result("overlapping_alias_validity", overlaps, "same exchange/symbol cannot overlap across instruments"),
            _result("unresolved_stable_identity", unresolved, "listing and instrument IDs required")]


def reconcile_terminal(master: pd.DataFrame, terminals: pd.DataFrame) -> list[CheckResult]:
    ended = master[master["end_date"].notna()]
    terminal_ids = set(terminals["instrument_id"].dropna()) if not terminals.empty else set()
    missing = int((~ended["instrument_id"].isin(terminal_ids)).sum())
    unresolved = int((terminals["resolution_status"] != "RESOLVED").sum()) if not terminals.empty else 0
    return [_result("terminated_without_terminal_record", missing, "every ended listing needs terminal evidence"),
            _result("unresolved_terminal_treatment", unresolved, "authoritative treatment required")]


def reconcile_corporate_actions(actions: pd.DataFrame, aliases: pd.DataFrame) -> list[CheckResult]:
    valid_types = {"SPLIT", "BONUS", "DIVIDEND", "RIGHTS", "MERGER", "DEMERGER", "SYMBOL_CHANGE", "ISIN_CHANGE"}
    bad_types = int((~actions["action_type"].isin(valid_types)).sum()) if not actions.empty else 0
    continuity_types = {"MERGER", "DEMERGER", "SYMBOL_CHANGE", "ISIN_CHANGE"}
    continuity = actions[actions["action_type"].isin(continuity_types)] if not actions.empty else actions
    missing_links = int((continuity["old_identifier"].isna() | continuity["new_identifier"].isna()).sum()) if not continuity.empty else 0
    symbol_changes = actions[actions["action_type"] == "SYMBOL_CHANGE"] if not actions.empty else actions
    known_alias_symbols = set(aliases["symbol"]) if not aliases.empty else set()
    missing_aliases = int((~symbol_changes["new_identifier"].isin(known_alias_symbols)).sum()) if not symbol_changes.empty else 0
    return [_result("unknown_corporate_action_type", bad_types, "unclassified discontinuities remain unresolved"),
            _result("corporate_action_identifier_continuity", missing_links, "transformative actions need old/new identifiers"),
            _result("symbol_change_without_alias_transition", missing_aliases, "symbol changes require dated aliases")]


def reconcile_benchmarks(benchmarks: pd.DataFrame) -> list[CheckResult]:
    allowed = {"PRI", "TRI"}
    ambiguous = int((~benchmarks["return_classification"].isin(allowed)).sum())
    return [_result("benchmark_pri_tri_classification", ambiguous, "every index row must declare PRI or TRI")]


def reconcile_costs(costs: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[CheckResult]:
    gaps = 0
    for _, group in costs.sort_values("effective_from").groupby("component"):
        cursor = pd.Timestamp(start)
        for row in group.to_dict("records"):
            if pd.Timestamp(row["effective_from"]) > cursor:
                gaps += 1
            cursor = pd.Timestamp(end) if pd.isna(row["effective_to"]) else max(cursor, pd.Timestamp(row["effective_to"]))
        if cursor < pd.Timestamp(end):
            gaps += 1
    return [_result("dated_cost_schedule_gaps", gaps, f"coverage required {pd.Timestamp(start).date()}..{pd.Timestamp(end).date()}")]


def population_by_year(master: pd.DataFrame, reference_counts: pd.DataFrame | None = None) -> pd.DataFrame:
    starts = pd.to_datetime(master["listing_date"])
    ends = pd.to_datetime(master["end_date"])
    min_year = int(starts.dropna().dt.year.min()) if starts.notna().any() else 0
    max_year = int(max(starts.dropna().dt.year.max(), pd.Timestamp.today().year)) if starts.notna().any() else 0
    rows = []
    for year in range(min_year, max_year + 1):
        year_end = pd.Timestamp(f"{year}-12-31")
        listed = (starts <= year_end) & (ends.isna() | (ends > year_end))
        new = starts.dt.year == year
        terminated = ends.dt.year == year
        row = {"year": year, "listed_securities": int(listed.sum()), "newly_listed": int(new.sum()),
               "terminated_delisted": int(terminated.sum()), "surviving": int(listed.sum()),
               "unresolved": int(master.loc[listed, "instrument_id"].isna().sum())}
        if reference_counts is not None and not reference_counts.empty:
            match = reference_counts[reference_counts["year"] == year]
            row["independent_reference_count"] = int(match.iloc[0]["listed_securities"]) if len(match) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
