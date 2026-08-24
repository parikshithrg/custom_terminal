from __future__ import annotations

import pandas as pd

from market_intel.research.folds import assert_no_label_overlap, expanding_folds


def test_purge_and_embargo_are_derived_and_non_overlapping():
    calendar = pd.bdate_range("2010-01-01", "2020-12-31")
    folds = expanding_folds(calendar, minimum_train_years=5, validation_years=1,
                            step_years=1, purge_sessions=22, embargo_sessions=22)
    assert folds
    for fold in folds:
        train_end_pos = calendar.get_loc(fold.train_end)
        validation_start_pos = calendar.get_loc(fold.validation_start)
        assert validation_start_pos - train_end_pos > 22
        outcomes = pd.DataFrame([{
            "decision_time": fold.train_end, "exit_time": calendar[train_end_pos + 21],
            "outcome_status": "RESOLVED",
        }])
        assert_no_label_overlap(outcomes, fold)

