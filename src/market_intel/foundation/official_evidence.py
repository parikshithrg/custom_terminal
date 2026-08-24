"""Conservative contracts for manually qualified official evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Iterable

import pandas as pd


class Resolution(StrEnum):
    QUALIFIED = "QUALIFIED"
    CONFLICT = "CONFLICT"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class EvidenceReference:
    organization: str
    url: str
    document_hash: str
    retrieved_at: str
    parser_version: str
    publication_time: str | None = None

    def __post_init__(self) -> None:
        if not self.organization or not self.url or len(self.document_hash) != 64:
            raise ValueError("official evidence requires organization, URL, and SHA-256")


def normalize_lifecycle_rows(rows: Iterable[dict]) -> pd.DataFrame:
    """Normalize without merging conflicting source assertions."""
    frame = pd.DataFrame(rows)
    required = {"case_id", "event_type", "exchange", "source_organization", "source_url",
                "document_hash", "retrieved_at", "parser_version", "resolution_status"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"lifecycle evidence missing fields: {sorted(missing)}")
    allowed = {"SPLIT", "BONUS", "DIVIDEND", "RIGHTS", "MERGER", "DEMERGER",
               "SYMBOL_CHANGE", "ISIN_CHANGE", "NAME_CHANGE", "LISTING_TRANSITION",
               "SUSPENSION", "DELISTING", "TERMINATION"}
    if (~frame.event_type.isin(allowed)).any():
        raise ValueError("unrecognized lifecycle event")
    if (~frame.resolution_status.isin(set(Resolution))).any():
        raise ValueError("invalid resolution status")
    for column in ("announcement_at", "ex_date", "record_date", "effective_date"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame.sort_values(["case_id", "source_organization"], kind="stable").reset_index(drop=True)


def mark_conflicting_assertions(frame: pd.DataFrame, fields: Iterable[str]) -> pd.DataFrame:
    """Retain every official assertion and mark, never pick a preferred value."""
    result = frame.copy()
    conflict_cases: set[str] = set()
    for case_id, group in result.groupby("case_id"):
        if any(group[field].dropna().astype(str).nunique() > 1 for field in fields if field in group):
            conflict_cases.add(case_id)
    result.loc[result.case_id.isin(conflict_cases), "resolution_status"] = Resolution.CONFLICT
    return result


def terminal_economic_resolution(row: dict) -> Resolution:
    """A quote is not delisting consideration; authoritative economics are required."""
    authoritative = bool(row.get("authoritative_terminal_document"))
    consideration = any(row.get(key) not in (None, "") for key in
                        ("cash_consideration", "security_consideration", "successor_instrument_id"))
    return Resolution.QUALIFIED if authoritative and consideration else Resolution.UNRESOLVED


@dataclass(frozen=True)
class CostEntry:
    component: str
    effective_from: date
    effective_to: date | None
    rate: float
    calculation_base: str
    applicability: str
    source_reference: str
    schedule_version: str
    statutory: bool = True


def uncovered_cost_intervals(entries: Iterable[CostEntry], components: set[str], start: date, end: date) -> dict[str, list[tuple[date, date]]]:
    """Return explicit uncovered intervals; never carry current rates backward."""
    result: dict[str, list[tuple[date, date]]] = {}
    by_component: dict[str, list[CostEntry]] = {c: [] for c in components}
    for entry in entries:
        if entry.component in by_component:
            by_component[entry.component].append(entry)
    for component, schedules in by_component.items():
        cursor = start
        gaps: list[tuple[date, date]] = []
        for item in sorted(schedules, key=lambda x: x.effective_from):
            item_end = item.effective_to or end
            if item_end < start or item.effective_from > end:
                continue
            if item.effective_from > cursor:
                gaps.append((cursor, min(end, item.effective_from)))
            cursor = max(cursor, item_end)
        if cursor < end:
            gaps.append((cursor, end))
        if gaps:
            result[component] = gaps
    return result
