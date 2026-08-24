"""Minimal, evidence-preserving equity identity model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class IdentityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class SecurityRecord:
    issuer_id: str | None
    instrument_id: str
    exchange: str
    listing_id: str | None
    isin: str | None
    listing_date: pd.Timestamp | None
    end_date: pd.Timestamp | None
    status: str
    identity_status: IdentityStatus
    predecessor_instrument_id: str | None = None
    successor_instrument_id: str | None = None


@dataclass(frozen=True)
class SymbolAlias:
    instrument_id: str
    exchange: str
    symbol: str
    valid_from: pd.Timestamp | None
    valid_to: pd.Timestamp | None
    source_id: str
    identity_status: IdentityStatus


def unresolved_identity_report(securities: pd.DataFrame, aliases: pd.DataFrame) -> pd.DataFrame:
    unresolved = securities[securities["identity_status"] != IdentityStatus.VERIFIED].copy()
    alias_counts = aliases.groupby("instrument_id").size().rename("alias_count")
    unresolved = unresolved.merge(alias_counts, on="instrument_id", how="left")
    unresolved["alias_count"] = unresolved["alias_count"].fillna(0).astype(int)
    return unresolved.sort_values(["identity_status", "instrument_id"], kind="stable")
