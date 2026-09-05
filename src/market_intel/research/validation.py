"""Shared fail-closed validation rules for point-in-time research artifacts."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


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
