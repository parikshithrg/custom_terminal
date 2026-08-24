from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_intel.application.runner import run_momentum
from market_intel.foundation.contracts import DatasetSnapshot
from market_intel.foundation.artifacts import canonical_json, frame_hash
from market_intel.foundation.prices import PricePanels
from market_intel.research.universe import UniverseDefinition


def test_hashes_are_stable_and_sensitive():
    frame = pd.DataFrame({"b": [2.0], "a": [1.0]}, index=[pd.Timestamp("2020-01-01")])
    assert frame_hash(frame) == frame_hash(frame[["a", "b"]])
    changed = frame.copy()
    changed.iloc[0, 0] += 1e-12
    assert frame_hash(frame) != frame_hash(changed)
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})


def test_complete_run_manifest_reproducible_core_is_identical(tmp_path):
    import json
    import numpy as np

    dates = pd.bdate_range("2010-01-01", periods=900)
    columns = ["A", "B", "C"]
    close = pd.DataFrame({c: 100 + np.arange(len(dates)) * (i + 1) / 100 for i, c in enumerate(columns)}, index=dates)
    open_ = close * 1.001
    volume = pd.DataFrame(1_000_000.0, index=dates, columns=columns)
    snapshot = DatasetSnapshot(
        dataset_id="fixture", version="fixture-v1", source_id="test",
        knowledge_cutoff=dates[-1], retrieved_at=dates[-1], content_hash="abc",
        parser_version="test-v1", survivorship_safe=True,
    )
    panels = PricePanels(
        open=open_, high=open_ * 1.01, low=open_ * 0.99, close=close,
        volume=volume, turnover=close * volume,
        aliases=pd.DataFrame({"instrument_id": columns, "symbol": columns}),
        provenance=pd.DataFrame({"instrument_id": columns, "raw_payload_hash": ["1", "2", "3"]}),
        snapshot=snapshot,
    )
    spec = {
        "experiment_id": "manifest_test", "research_family_id": "test", "research_start": str(dates[0].date()),
        "research_end": str(dates[-1].date()), "lookback_sessions": 20, "skip_sessions": 5,
        "holding_sessions": 5, "top_fraction": 0.34, "target_value_per_trade": 10_000,
        "fold_plan": {"minimum_train_years": 1, "validation_years": 1, "step_years": 1,
                      "purge_sessions": 6, "embargo_sessions": 6},
        "acceptance_gates": {"minimum_oos_decision_dates": 1,
                             "positive_fold_fraction_minimum": 0.0},
        "non_actionable": True,
    }
    definition = UniverseDefinition(size=3, buffer_size=3, lookback_sessions=5,
                                    minimum_history_sessions=10)
    first = run_momentum(panels=panels, benchmark_open=open_["A"], spec=spec,
                         output_root=tmp_path / "one" / "runs", project_root=Path.cwd(),
                         universe_definition=definition)
    second = run_momentum(panels=panels, benchmark_open=open_["A"], spec=spec,
                          output_root=tmp_path / "two" / "runs", project_root=Path.cwd(),
                          universe_definition=definition)
    first_manifest = json.loads((first / "manifest.json").read_text())
    second_manifest = json.loads((second / "manifest.json").read_text())
    assert first_manifest["reproducible_core_hash"] == second_manifest["reproducible_core_hash"]
    assert first_manifest["output_artifact_hashes"] == second_manifest["output_artifact_hashes"]
