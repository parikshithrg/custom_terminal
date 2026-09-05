"""Expanding walk-forward folds with explicit purge and embargo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    purge_sessions: int
    embargo_sessions: int


def expanding_folds(
    calendar: pd.DatetimeIndex,
    *,
    minimum_train_years: int,
    validation_years: int,
    step_years: int,
    purge_sessions: int,
    embargo_sessions: int,
) -> list[WalkForwardFold]:
    if purge_sessions < 1 or embargo_sessions < 1:
        raise ValueError("purge and embargo must be positive")
    start = calendar.min()
    first_validation = start + pd.DateOffset(years=minimum_train_years)
    folds: list[WalkForwardFold] = []
    cursor = first_validation
    n = 1
    while cursor <= calendar.max():
        val_candidates = calendar[calendar >= cursor]
        if len(val_candidates) == 0:
            break
        validation_start_raw = val_candidates[0]
        raw_pos = calendar.get_loc(validation_start_raw)
        validation_pos = raw_pos + embargo_sessions
        if validation_pos >= len(calendar):
            break
        validation_start = calendar[validation_pos]
        desired_end = validation_start + pd.DateOffset(years=validation_years) - pd.Timedelta(days=1)
        end_candidates = calendar[calendar <= desired_end]
        if len(end_candidates) == 0:
            break
        validation_end = end_candidates[-1]
        train_end_pos = raw_pos - purge_sessions - 1
        if train_end_pos < 0:
            cursor += pd.DateOffset(years=step_years)
            continue
        folds.append(WalkForwardFold(
            fold_id=f"wf_{n:02d}", train_start=calendar[0], train_end=calendar[train_end_pos],
            validation_start=validation_start, validation_end=validation_end,
            purge_sessions=purge_sessions, embargo_sessions=embargo_sessions,
        ))
        cursor += pd.DateOffset(years=step_years)
        n += 1
    return folds


def assert_no_label_overlap(outcomes: pd.DataFrame, fold: WalkForwardFold) -> None:
    train = outcomes[
        (outcomes["decision_time"] >= fold.train_start)
        & (outcomes["decision_time"] <= fold.train_end)
        & (outcomes["outcome_status"] == "RESOLVED")
    ]
    if not train.empty and pd.to_datetime(train["exit_time"]).max() >= fold.validation_start:
        raise AssertionError(f"training label overlaps validation in {fold.fold_id}")


def validate_fold_provenance(
    fold: WalkForwardFold,
    *,
    fitted_through: pd.Timestamp | None,
    input_snapshot_hash: str,
    prediction_decision_times: Iterable[pd.Timestamp],
    holding_sessions: int,
) -> dict[str, object]:
    """Fail closed when an OOS fold uses validation-fitted or misbound inputs."""
    if fold.purge_sessions < holding_sessions + 1 or fold.embargo_sessions < holding_sessions + 1:
        raise AssertionError("PURGE_EMBARGO_SHORTER_THAN_OUTCOME_WINDOW")
    if fitted_through is not None and pd.Timestamp(fitted_through) > fold.train_end:
        raise AssertionError("VALIDATION_FITTED_TRANSFORMATION")
    if not input_snapshot_hash:
        raise AssertionError("MISSING_FOLD_INPUT_SNAPSHOT")
    decisions = pd.to_datetime(list(prediction_decision_times))
    if len(decisions) and ((decisions < fold.validation_start) | (decisions > fold.validation_end)).any():
        raise AssertionError("PREDICTION_OUTSIDE_OOS_FOLD")
    return {
        "fold_id": fold.fold_id,
        "fit_scope": "NO_FITTED_PARAMETERS" if fitted_through is None else "TRAINING_ONLY",
        "fitted_through": None if fitted_through is None else pd.Timestamp(fitted_through),
        "input_snapshot_hash": input_snapshot_hash,
    }
