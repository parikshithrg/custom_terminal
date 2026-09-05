"""Offline preservation and artifact-graph checks for recorded R.10A evidence."""
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from market_intel.foundation.raw_ingestion import verify_raw_object
from market_intel.research.validation import verify_artifact_hashes

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs" / "investigations" / "r10a" / "run_v1"


def test_recorded_root_manifest_and_all_artifact_hashes_reconcile():
    manifest = json.loads((RUN / "root_run_manifest.json").read_text(encoding="utf-8"))
    verify_artifact_hashes(RUN, manifest["output_artifact_hashes"])
    assert manifest["source_commit"] == "17f317187b00b489e3eda52ddcfe4ac48cdef2cd"
    assert manifest["dirty_worktree"] is True
    assert manifest["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert manifest["lifecycle"] == "SYNTHETIC_VALIDATED_NONCANONICAL"
    assert not manifest["canonical"] and not manifest["promotion_eligible"]


def test_raw_manifests_are_portable_immutable_and_synthetic():
    manifest = json.loads((RUN / "root_run_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["raw_manifests"]) == {
        "daily_equity", "security_master", "corporate_actions", "benchmark_history"}
    for reference in manifest["raw_manifests"].values():
        assert not Path(reference).is_absolute()
        path = RUN / reference
        assert verify_raw_object(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["licensing_retention_notes"] == "GENERATED_SYNTHETIC_RETAINABLE"
        assert raw["retention_classification"] == "GENERATED_SYNTHETIC_RETAINABLE"
        assert raw["data_classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
        assert raw["retrieval_timestamp"] == "2022-01-03T00:00:00+00:00"


def test_daily_bar_parquet_has_typed_temporal_revision_contract():
    frame = pd.read_parquet(RUN / "dataset_snapshot.parquet")
    required = {
        "instrument_id", "listing_id", "event_time", "session_date", "published_at",
        "retrieved_at", "available_at", "open", "high", "low", "close", "volume",
        "source_id", "source_record_id", "revision_number", "supersedes_record_id",
        "raw_payload_hash", "parser_version", "quality_flags",
    }
    assert required <= set(frame.columns)
    assert len(frame) == 16835
    assert frame["source_record_id"].is_unique
    assert (frame["available_at"] >= frame["published_at"]).all()
    quarantine = pd.read_parquet(RUN / "quarantine.parquet")
    assert len(quarantine) == 3 and (quarantine["quality_flags"] != "[]").all()


def test_recorded_known_answers_and_holdout_separation():
    summary = json.loads((RUN / "validation_summary.json").read_text(encoding="utf-8"))
    assert summary["engineering_oracle_not_market_edge"] is True
    assert summary["known_answers"] == {
        "oos_fold_count": 4,
        "outcome_status_counts": {"MISSING_ENTRY": 6, "RESOLVED": 394, "UNRESOLVED_DELISTING": 2},
        "quarantine_rows": 3,
        "round_trip_cost_10000_11000": 33.76818,
    }
    oos = pd.read_parquet(RUN / "oos_predictions.parquet")
    assert oos["decision_time"].max() < pd.Timestamp("2021-01-01")
    holdout = pd.read_parquet(RUN / "holdout_fixture.parquet")
    assert holdout["session_date"].min() >= pd.Timestamp("2021-01-01")
    actions = pd.read_parquet(RUN / "corporate_actions.parquet")
    assert actions.iloc[0]["treatment"] == "MARKER_ONLY_NO_ADJUSTMENT"


def test_protected_momentum_r9p_and_production_files_are_unchanged():
    expected = {
        "docs/investigations/r9p/manifest_v1.json": "f0f7b7e8842783c1df2c6ade2dea2ad8cd0c496958361b1cce134e9de0cd0e56",
        "docs/investigations/r9p/results_v1.json": "67ef77317f418e402bd5853b10648617971bebf8c3df81482d9e63a99e32a2d2",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "src/market_intel/foundation/fno_production_boundary.py": "dcde3cbf1cd2cb1d5e70527cacb7066daf50e9cf6e48eb6fe44df45af8fc11ea",
        "pyproject.toml": "a6fcded2b042f3ab65769a158f84ba44a3b646c1390fc2667e07c556c5265664",
        "requirements.txt": "654e2ca20bb0f2dac0fc5e2041e5f65ce808b7c1f401ad3cdbe46524dec841ab",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    assert "apsw" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()


def test_recorded_package_contains_no_private_path_or_secret_assignment():
    text = "\n".join(path.read_text(encoding="utf-8") for path in RUN.rglob("*.json"))
    text += (ROOT / "reports/RESEARCH_R10A_REPORT.md").read_text(encoding="utf-8")
    assert not re.search(r"(?i)(api[_-]?secret|access[_-]?token|password)\s*[:=]\s*\S+", text)
    assert "C:\\Users\\" not in text and "private_fno_binding" not in text
