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


@dataclass(frozen=True)
class AsOfRequest:
    """Dataset-neutral causal snapshot request with an explicit market clock."""

    knowledge_cutoff: pd.Timestamp
    decision_clock: str
    dataset_version: str

    def __post_init__(self) -> None:
        cutoff = pd.Timestamp(self.knowledge_cutoff)
        if cutoff.tzinfo is None:
            raise ValueError("knowledge_cutoff must be timezone-aware; date-only cutoffs are prohibited")
        if self.decision_clock not in {"SESSION_OPEN", "SESSION_CLOSE", "INTRADAY"}:
            raise ValueError("unsupported decision_clock")
        if not self.dataset_version:
            raise ValueError("dataset_version is required")


def materialize_as_of(
    frame: pd.DataFrame,
    request: AsOfRequest,
    *,
    observation_keys: tuple[str, ...] = ("instrument_id", "event_time"),
) -> pd.DataFrame:
    """Return the causally latest valid revision without mutating older vintages."""
    required = {*observation_keys, "published_at", "available_at", "revision_number",
                "source_record_id", "supersedes_record_id", "dataset_version"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing temporal columns: {sorted(missing)}")
    if set(frame["dataset_version"].dropna().astype(str)) != {request.dataset_version}:
        raise ValueError("dataset version mismatch")
    work = frame.copy()
    for column in ("event_time", "published_at", "available_at", "retrieved_at"):
        if column in work:
            work[column] = pd.to_datetime(work[column], utc=True, errors="coerce")
            if work[column].isna().any():
                raise ValueError(f"invalid timezone-aware timestamp: {column}")
    if (work["available_at"] < work["published_at"]).any():
        raise ValueError("available_at cannot precede published_at")
    if "retrieved_at" in work and (work["retrieved_at"] < work["published_at"]).any():
        raise ValueError("retrieved_at cannot precede published_at")
    if work["source_record_id"].duplicated().any():
        raise ValueError("duplicate revision identity")
    known = set(work["source_record_id"].astype(str))
    missing_parent = set(work["supersedes_record_id"].dropna().astype(str)) - known
    if missing_parent:
        raise ValueError("invalid supersession chain")
    records = {str(row.source_record_id): row for row in work.itertuples()}
    for row in work.itertuples():
        parent_id = None if pd.isna(row.supersedes_record_id) else str(row.supersedes_record_id)
        if row.revision_number < 1 or (row.revision_number == 1 and parent_id is not None):
            raise ValueError("invalid supersession chain")
        if row.revision_number > 1:
            parent = records.get(parent_id)
            same_observation = parent is not None and all(
                getattr(parent, key) == getattr(row, key) for key in observation_keys
            )
            if (not same_observation or parent.revision_number != row.revision_number - 1
                    or parent.published_at >= row.published_at):
                raise ValueError("invalid supersession chain")
    cutoff = pd.Timestamp(request.knowledge_cutoff).tz_convert("UTC")
    eligible = work[(work["published_at"] <= cutoff) & (work["available_at"] <= cutoff)]
    if eligible.empty:
        return eligible.sort_values([*observation_keys, "revision_number"], kind="stable").reset_index(drop=True)
    return (
        eligible.sort_values([*observation_keys, "published_at", "available_at",
                              "revision_number", "source_record_id"], kind="stable")
        .drop_duplicates(list(observation_keys), keep="last")
        .sort_values([*observation_keys], kind="stable")
        .reset_index(drop=True)
    )


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
