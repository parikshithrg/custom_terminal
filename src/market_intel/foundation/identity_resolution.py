"""Deterministic security identity resolution with ambiguity preservation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class IdentityResolution:
    source_record_id: str
    instrument_id: str | None
    method: str | None
    status: ResolutionStatus
    candidates: tuple[str, ...] = ()


def resolve_identity(record: dict, master: pd.DataFrame, aliases: pd.DataFrame) -> IdentityResolution:
    record_id = str(record.get("source_record_id", "unknown"))
    listing_id = record.get("listing_id")
    isin = record.get("isin")
    symbol = record.get("symbol") or record.get("exchange_symbol")
    when = pd.Timestamp(record.get("event_date") or record.get("trade_date"))
    candidates: pd.DataFrame
    if listing_id and pd.notna(listing_id):
        candidates = master[master["listing_id"] == listing_id]
        method = "STABLE_LISTING_ID"
    elif isin and pd.notna(isin):
        candidates = master[master["isin"] == isin]
        method = "ISIN"
    elif symbol and pd.notna(symbol):
        valid_from = pd.to_datetime(aliases["valid_from"])
        valid_to = pd.to_datetime(aliases["valid_to"])
        candidates = aliases[(aliases["symbol"] == symbol) & (valid_from <= when) & (valid_to.isna() | (when < valid_to))]
        method = "DATED_SYMBOL_ALIAS"
    else:
        return IdentityResolution(record_id, None, None, ResolutionStatus.UNRESOLVED)
    ids = tuple(sorted(candidates["instrument_id"].dropna().astype(str).unique()))
    if len(ids) == 1:
        return IdentityResolution(record_id, ids[0], method, ResolutionStatus.RESOLVED, ids)
    if len(ids) > 1:
        return IdentityResolution(record_id, None, method, ResolutionStatus.AMBIGUOUS, ids)
    # Company-name/ticker similarity is intentionally not a fallback.
    return IdentityResolution(record_id, None, method, ResolutionStatus.UNRESOLVED)


def alias_conflicts(aliases: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ordered = aliases.sort_values(["exchange", "symbol", "valid_from"], kind="stable")
    for (exchange, symbol), group in ordered.groupby(["exchange", "symbol"]):
        records = list(group.to_dict("records"))
        for left, right in zip(records, records[1:]):
            left_end = pd.Timestamp.max if pd.isna(left["valid_to"]) else pd.Timestamp(left["valid_to"])
            if pd.Timestamp(right["valid_from"]) < left_end:
                rows.append({"exchange": exchange, "symbol": symbol, "left_instrument_id": left["instrument_id"],
                             "right_instrument_id": right["instrument_id"], "issue": "OVERLAPPING_ALIAS_VALIDITY"})
    return pd.DataFrame(rows)
