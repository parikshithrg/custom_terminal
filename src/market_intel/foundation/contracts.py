"""Typed temporal and identity contracts required by the momentum slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class InstrumentAlias:
    instrument_id: str
    source_id: str
    symbol: str
    effective_from: pd.Timestamp
    effective_to: pd.Timestamp | None = None

    def valid_at(self, when: pd.Timestamp) -> bool:
        when = pd.Timestamp(when)
        return self.effective_from <= when and (
            self.effective_to is None or when < self.effective_to
        )


@dataclass(frozen=True)
class MarketObservation:
    instrument_id: str
    event_time: pd.Timestamp
    published_at: pd.Timestamp
    retrieved_at: pd.Timestamp
    source_id: str
    revision_number: int
    raw_payload_hash: str
    parser_version: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float
    effective_from: pd.Timestamp | None = None
    effective_to: pd.Timestamp | None = None
    quality_flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.published_at < self.event_time:
            raise ValueError("published_at cannot precede event_time")
        if self.retrieved_at < self.published_at:
            raise ValueError("retrieved_at cannot precede published_at")
        if self.revision_number < 1:
            raise ValueError("revision_number must be positive")


@dataclass(frozen=True)
class DatasetSnapshot:
    dataset_id: str
    version: str
    source_id: str
    knowledge_cutoff: pd.Timestamp
    retrieved_at: pd.Timestamp
    content_hash: str
    parser_version: str
    survivorship_safe: bool
    paths: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()


def as_of_latest(frame: pd.DataFrame, knowledge_cutoff: pd.Timestamp) -> pd.DataFrame:
    """Return the latest published vintage per instrument/event by cutoff.

    Earlier vintages remain in storage; this function never mutates or globally
    deduplicates them. A revision only supersedes the old value after its own
    publication time.
    """
    required = {"instrument_id", "event_time", "published_at", "revision_number"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing temporal columns: {sorted(missing)}")
    eligible = frame[pd.to_datetime(frame["published_at"]) <= pd.Timestamp(knowledge_cutoff)]
    if eligible.empty:
        return eligible.copy()
    return (
        eligible.sort_values(
            ["instrument_id", "event_time", "published_at", "revision_number"],
            kind="stable",
        )
        .drop_duplicates(["instrument_id", "event_time"], keep="last")
        .reset_index(drop=True)
    )


def stable_instrument_id(exchange: str, symbol: str, listing_start: str = "unknown") -> str:
    """Minimal stable listing identity; alias changes do not change the ID.

    Real migrations must replace `unknown` with security-master evidence. The
    explicit suffix prevents pretending the current ticker alone is permanent.
    """
    import hashlib

    key = f"{exchange.upper()}|{symbol.upper()}|{listing_start}"
    return "ins_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

