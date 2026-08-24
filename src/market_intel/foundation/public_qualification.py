"""Sample-level official evidence checks, separate from production trust."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class SampleStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class QualificationCheck:
    check_id: str
    status: SampleStatus
    evidence: str


def validate_alias_intervals(aliases: pd.DataFrame) -> QualificationCheck:
    if aliases.empty:
        return QualificationCheck("alias_validity", SampleStatus.UNKNOWN, "No official alias sample")
    bad = pd.to_datetime(aliases["valid_to"]).notna() & (pd.to_datetime(aliases["valid_to"]) <= pd.to_datetime(aliases["valid_from"]))
    return QualificationCheck("alias_validity", SampleStatus.FAIL if bad.any() else SampleStatus.PASS,
                              f"invalid_intervals={int(bad.sum())}")


def reject_later_published_information(frame: pd.DataFrame, decision_time: pd.Timestamp) -> pd.DataFrame:
    if "published_at" not in frame:
        raise ValueError("published_at required for point-in-time filtering")
    return frame[pd.to_datetime(frame["published_at"]) <= pd.Timestamp(decision_time)].copy()


def compare_raw_normalized(raw: pd.DataFrame, normalized: pd.DataFrame,
                           mapping: dict[str, str]) -> QualificationCheck:
    left = raw[list(mapping)].rename(columns=mapping).reset_index(drop=True)
    right = normalized[list(mapping.values())].reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(left, right, check_dtype=False)
        return QualificationCheck("raw_row_reproduction", SampleStatus.PASS, f"rows={len(left)}")
    except AssertionError as exc:
        return QualificationCheck("raw_row_reproduction", SampleStatus.FAIL, str(exc).splitlines()[0])


def coverage_decision(*, full_population: SampleStatus, identity: SampleStatus,
                      corporate_actions: SampleStatus, terminal_outcomes: SampleStatus,
                      shorter_interval_proven: bool) -> str:
    required = (full_population, identity, corporate_actions, terminal_outcomes)
    if all(value == SampleStatus.PASS for value in required):
        return "public sources support full required ingestion"
    if shorter_interval_proven and all(value == SampleStatus.PASS for value in required[1:]):
        return "public sources support a shorter defensible interval"
    if any(value == SampleStatus.UNKNOWN for value in required):
        return "public sources remain insufficient without manual evidence collection"
    return "public sources remain insufficient for trustworthy cross-sectional research"
