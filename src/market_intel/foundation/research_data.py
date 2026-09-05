"""Typed point-in-time daily bars and stable identity helpers for research."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

import pandas as pd

from .artifacts import frame_hash
from .contracts import AsOfRequest, DatasetSnapshot, materialize_as_of
from .prices import PricePanels


PIT_DAILY_BAR_VERSION = "pit_daily_bar_v1"
NORMALIZATION_POLICY_VERSION = "synthetic_daily_bar_quality_v1"
PIT_DAILY_BAR_COLUMNS = (
    "instrument_id", "listing_id", "event_time", "session_date", "published_at",
    "retrieved_at", "available_at", "open", "high", "low", "close", "volume",
    "turnover", "source_id", "source_record_id", "revision_number",
    "supersedes_record_id", "raw_payload_hash", "parser_version", "dataset_version",
    "quality_flags",
)


@dataclass(frozen=True)
class NormalizedBars:
    accepted: pd.DataFrame
    quarantine: pd.DataFrame
    policy_version: str = NORMALIZATION_POLICY_VERSION


def _flags(row: pd.Series) -> list[str]:
    flags: list[str] = []
    values = [row.get(name) for name in ("open", "high", "low", "close")]
    present = [value for value in values if pd.notna(value)]
    if len(present) < 4:
        flags.append("MISSING_OHLC")
    if present and any(float(value) <= 0 for value in present):
        flags.append("NON_POSITIVE_PRICE")
    if len(present) not in (0, 4):
        flags.append("PARTIAL_OHLC")
    if len(present) == 4:
        open_, high, low, close = map(float, values)
        if high < max(open_, low, close) or low > min(open_, high, close):
            flags.append("IMPOSSIBLE_OHLC")
    if pd.notna(row.get("volume")) and float(row["volume"]) < 0:
        flags.append("NEGATIVE_VOLUME")
    if pd.isna(row.get("volume")):
        flags.append("MISSING_VOLUME")
    if pd.isna(row.get("turnover")):
        flags.append("MISSING_TURNOVER")
    return flags


def normalize_daily_bars(
    rows: Iterable[dict], *, dataset_version: str, parser_version: str,
    valid_instruments: set[str] | dict[str, str], raw_payload_hash: str,
) -> NormalizedBars:
    """Normalize all rows, retaining rejected records with named quality flags."""
    if not dataset_version or not parser_version:
        raise ValueError("dataset and parser versions are required")
    if not re.fullmatch(r"[0-9a-f]{64}", raw_payload_hash):
        raise ValueError("raw_payload_hash must be a lowercase SHA-256")
    frame = pd.DataFrame(list(rows))
    required = set(PIT_DAILY_BAR_COLUMNS) - {"quality_flags", "dataset_version",
                                             "parser_version", "raw_payload_hash"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"daily bars missing fields: {sorted(missing)}")
    frame = frame.copy()
    for name in ("event_time", "published_at", "retrieved_at", "available_at"):
        parsed = pd.to_datetime(frame[name], utc=True, errors="coerce")
        if parsed.isna().any():
            raise ValueError(f"invalid timestamp: {name}")
        frame[name] = parsed
    frame["session_date"] = pd.to_datetime(frame["session_date"], errors="coerce").dt.normalize()
    if frame["session_date"].isna().any():
        raise ValueError("invalid session_date")
    for name in ("open", "high", "low", "close", "volume", "turnover"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    frame["revision_number"] = pd.to_numeric(frame["revision_number"], errors="raise").astype("int64")
    frame["supersedes_record_id"] = frame["supersedes_record_id"].where(
        pd.notna(frame["supersedes_record_id"]), None)
    frame["dataset_version"] = dataset_version
    frame["parser_version"] = parser_version
    frame["raw_payload_hash"] = raw_payload_hash
    listing_map = valid_instruments if isinstance(valid_instruments, dict) else None
    instrument_ids = set(valid_instruments)
    reasons = [[] for _ in range(len(frame))]
    for position, (_, row) in enumerate(frame.iterrows()):
        reasons[position].extend(_flags(row))
        if row["instrument_id"] not in instrument_ids:
            reasons[position].append("UNRESOLVED_INSTRUMENT")
        elif listing_map is not None and listing_map[row["instrument_id"]] != row["listing_id"]:
            reasons[position].append("INVALID_LISTING_LINKAGE")
        if row["available_at"] < row["published_at"]:
            reasons[position].append("AVAILABLE_BEFORE_PUBLICATION")
        if row["retrieved_at"] < row["published_at"]:
            reasons[position].append("RETRIEVED_BEFORE_PUBLICATION")
        if row["published_at"] < row["event_time"]:
            reasons[position].append("PUBLISHED_BEFORE_EVENT")
        if row["event_time"].date() != row["session_date"].date():
            reasons[position].append("EVENT_SESSION_MISMATCH")
        for name in ("instrument_id", "listing_id", "source_id", "source_record_id"):
            if pd.isna(row[name]) or not str(row[name]).strip():
                reasons[position].append("MISSING_" + name.upper())
        if row["revision_number"] < 1:
            reasons[position].append("INVALID_REVISION_NUMBER")
    duplicates = frame["source_record_id"].duplicated(keep=False)
    duplicate_revisions = frame.duplicated(
        ["instrument_id", "event_time", "revision_number"], keep=False)
    for position in range(len(frame)):
        if bool(duplicates.iloc[position]):
            reasons[position].append("DUPLICATE_SOURCE_RECORD_ID")
        if bool(duplicate_revisions.iloc[position]):
            reasons[position].append("DUPLICATE_REVISION_IDENTITY")
    by_record = {str(row.source_record_id): row for row in frame.itertuples()}
    for position, row in enumerate(frame.itertuples()):
        parent_id = None if pd.isna(row.supersedes_record_id) else row.supersedes_record_id
        if row.revision_number == 1 and parent_id is not None:
            reasons[position].append("INVALID_SUPERSESSION_CHAIN")
        if row.revision_number > 1:
            parent = by_record.get(str(parent_id))
            if (parent is None or parent.instrument_id != row.instrument_id
                    or pd.Timestamp(parent.event_time) != pd.Timestamp(row.event_time)
                    or parent.revision_number != row.revision_number - 1
                    or pd.Timestamp(parent.published_at) >= pd.Timestamp(row.published_at)):
                reasons[position].append("INVALID_SUPERSESSION_CHAIN")
    frame["quality_flags"] = [json.dumps(sorted(set(items)), separators=(",", ":")) for items in reasons]
    frame = frame[list(PIT_DAILY_BAR_COLUMNS)].sort_values(
        ["instrument_id", "event_time", "revision_number", "source_record_id"], kind="stable"
    ).reset_index(drop=True)
    rejected = frame[frame["quality_flags"] != "[]"].copy()
    accepted = frame[frame["quality_flags"] == "[]"].copy()
    return NormalizedBars(accepted=accepted.reset_index(drop=True),
                          quarantine=rejected.reset_index(drop=True))


def validate_aliases(aliases: pd.DataFrame) -> pd.DataFrame:
    required = {"instrument_id", "listing_id", "symbol", "valid_from", "valid_to"}
    if required - set(aliases.columns):
        raise ValueError("alias fields missing")
    result = aliases.copy()
    result["valid_from"] = pd.to_datetime(result["valid_from"], utc=True)
    result["valid_to"] = pd.to_datetime(result["valid_to"], utc=True, errors="coerce")
    if (result["valid_to"].notna() & (result["valid_to"] <= result["valid_from"])).any():
        raise ValueError("invalid alias interval")
    ordered = result.sort_values(["listing_id", "symbol", "valid_from"], kind="stable")
    for (_, symbol), group in ordered.groupby(["listing_id", "symbol"], sort=False):
        rows = list(group.itertuples())
        for previous, row in zip(rows, rows[1:]):
            if pd.isna(previous.valid_to) or row.valid_from < previous.valid_to:
                raise ValueError(f"overlapping alias validity: {symbol}")
    return ordered.reset_index(drop=True)


def resolve_alias(aliases: pd.DataFrame, *, symbol: str, when: pd.Timestamp) -> str:
    when = pd.Timestamp(when)
    if when.tzinfo is None:
        raise ValueError("alias resolution requires timezone-aware instant")
    checked = validate_aliases(aliases)
    matches = checked[(checked["symbol"] == symbol)
                      & (checked["valid_from"] <= when)
                      & (checked["valid_to"].isna() | (when < checked["valid_to"]))]
    if len(matches) != 1:
        raise LookupError("alias is unresolved or ambiguous at requested instant")
    return str(matches.iloc[0]["instrument_id"])


def bars_as_panels(
    bars: pd.DataFrame, aliases: pd.DataFrame, request: AsOfRequest,
    *, survivorship_safe: bool = True,
) -> PricePanels:
    latest = materialize_as_of(bars, request)
    latest = latest[latest["quality_flags"] == "[]"].copy()
    index = pd.DatetimeIndex(sorted(latest["session_date"].unique()))
    columns = sorted(latest["instrument_id"].unique())
    panels = {}
    for field in ("open", "high", "low", "close", "volume", "turnover"):
        panels[field] = latest.pivot(index="session_date", columns="instrument_id", values=field).reindex(index=index, columns=columns)
    snapshot_hash = frame_hash(latest)
    snapshot = DatasetSnapshot(
        dataset_id="synthetic_daily_bars", version=request.dataset_version,
        source_id="synthetic_formula_provider", knowledge_cutoff=request.knowledge_cutoff,
        retrieved_at=latest["retrieved_at"].max() if not latest.empty else request.knowledge_cutoff,
        content_hash=snapshot_hash, parser_version=PIT_DAILY_BAR_VERSION,
        survivorship_safe=survivorship_safe, paths=(), quality_flags=(CLASSIFICATION_NOTICE,),
    )
    provenance = latest[["instrument_id", "event_time", "published_at", "available_at",
                         "retrieved_at", "source_id", "source_record_id", "revision_number",
                         "raw_payload_hash", "parser_version", "quality_flags"]].copy()
    return PricePanels(**panels, aliases=validate_aliases(aliases), provenance=provenance, snapshot=snapshot)


CLASSIFICATION_NOTICE = "SYNTHETIC_ONLY_NONCANONICAL"
