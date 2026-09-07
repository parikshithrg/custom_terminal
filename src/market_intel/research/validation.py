"""Shared fail-closed validation rules for point-in-time research artifacts."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from market_intel.foundation.exchange_calendar import CalendarError, DecisionReference


class ResearchValidationError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def require_historical_universe(decisions: pd.DataFrame, *, decision_time: pd.Timestamp,
                                knowledge_cutoff: pd.Timestamp) -> None:
    if decisions.empty:
        raise ResearchValidationError("MISSING_HISTORICAL_UNIVERSE")
    times = pd.to_datetime(decisions["decision_time"])
    if (times > pd.Timestamp(decision_time)).any():
        raise ResearchValidationError("FUTURE_UNIVERSE_MEMBERSHIP")
    if "knowledge_cutoff" not in decisions or not (
        pd.to_datetime(decisions["knowledge_cutoff"], utc=True) == pd.Timestamp(knowledge_cutoff)
    ).all():
        raise ResearchValidationError("UNIVERSE_SNAPSHOT_CUTOFF_MISMATCH")


def assert_outcome_accounting(predictions: pd.DataFrame, outcomes: pd.DataFrame) -> None:
    keys = ["decision_time", "instrument_id"]
    expected = predictions[keys].sort_values(keys, kind="stable").reset_index(drop=True)
    if not set(keys + ["outcome_status"]).issubset(outcomes.columns):
        raise ResearchValidationError("OUTCOME_STATUS_MISSING")
    actual = outcomes[keys].sort_values(keys, kind="stable").reset_index(drop=True)
    if len(actual) != len(expected) or not actual.equals(expected):
        raise ResearchValidationError("SILENT_OUTCOME_DROP")
    if outcomes["outcome_status"].isna().any():
        raise ResearchValidationError("UNRESOLVED_OUTCOME_UNLABELED")


def assert_holdout_unconsumed(decisions: pd.Series, *, holdout_start: pd.Timestamp) -> None:
    if len(decisions) and (pd.to_datetime(decisions) >= pd.Timestamp(holdout_start)).any():
        raise ResearchValidationError("SYNTHETIC_HOLDOUT_CONSUMED")


def verify_artifact_hashes(root: Path, hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ResearchValidationError("ARTIFACT_HASH_MISMATCH")


def require_shared_decision_clock(decisions: pd.DataFrame, calendar_view: pd.DataFrame) -> None:
    """Require one exact session/cutoff for every cross-sectional decision group."""
    required = {"decision_time", "calendar_version", "venue", "session_id", "decision_clock"}
    missing = required - set(decisions)
    if missing:
        raise ResearchValidationError("MISSING_CALENDAR_DECISION_BINDING")
    for decision_time, group in decisions.groupby("decision_time", sort=False):
        bindings = group[["calendar_version", "venue", "session_id", "decision_clock"]].drop_duplicates()
        if len(bindings) != 1:
            raise ResearchValidationError("CROSS_SECTIONAL_CLOCK_MISMATCH")
        binding = bindings.iloc[0]
        try:
            DecisionReference(
                str(binding.calendar_version), str(binding.venue), str(binding.session_id),
                binding.decision_clock, pd.Timestamp(decision_time),
            ).validate(calendar_view)
        except (CalendarError, ValueError) as exc:
            raise ResearchValidationError(f"INVALID_DECISION_CLOCK_BINDING:{exc}") from exc
