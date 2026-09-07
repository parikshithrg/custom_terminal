"""Static integrity tests for the R.10E evidence package."""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10e/run_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_root_records_clean_noncanonical_no_decision_checkpoint():
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert root["source_commit"] == "5febba77436ea577db5bc53ecd21fe0c742a134d"
    assert root["execution_start_dirty"] is False
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert root["canonical"] is False and root["promotion_eligible"] is False
    assert root["decision"] == "NO_DECISION"
    assert root["r10a_holdout_state"] == "UNCONSUMED_SYNTHETIC_HOLDOUT"


def test_all_twenty_declared_artifact_hashes_reconcile():
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert len(root["artifact_hashes"]) == 20
    for relative, digest in root["artifact_hashes"].items():
        assert _sha(RUN / relative) == digest


def test_feature_family_shapes_and_negative_results_are_retained():
    features = pd.read_parquet(RUN / "materialized_features.parquet")
    oracle = pd.read_parquet(RUN / "oracle_rows.parquet")
    attempts = pd.read_parquet(RUN / "attempt_ledger.parquet")
    assert len(features) == 800 and features.feature_id.nunique() == 10
    assert len(oracle) == 80 and len(attempts) == 16
    assert "deterministic_noise" in set(attempts.attempt_id)
    assert attempts.set_index("attempt_id").at["deterministic_noise", "result"] == "RETAINED_NEGATIVE"


def test_known_score_calibration_combination_and_confidence_answers():
    known = json.loads((RUN / "known_answers.json").read_text())
    assert known["tie_score_for_2"] == 40.0
    assert known["below_range_score"] == 0.0 and known["above_range_score"] == 100.0
    assert known["expected_outcome"]["expected_outcome"] == 1.8
    assert known["expected_outcome"]["positive_outcome_probability"] == 1.0
    assert known["dropped_redundant"] == ["momentum_redundant"]
    assert known["combination_validation_mse"] < 1e-20
    assert known["naive_validation_mse"] > 10
    assert known["confidence"]["confidence"] == "LOW"
    assert known["lifecycle"] == "SYNTHETIC_VALIDATED_NONCANONICAL"


def test_snapshot_never_becomes_recommendation():
    snapshot = json.loads((RUN / "asset_evidence_snapshot.json").read_text())
    assert snapshot["decision"] == "NO_DECISION"
    assert snapshot["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert snapshot["score_0_100"] == 15.0
    assert snapshot["positive_outcome_probability"] == 1.0
    assert snapshot["confidence"] == "LOW"
    assert "not probability" in snapshot["score_definition"]


def test_incremental_equivalence_and_preservation_are_complete():
    equivalent = json.loads((RUN / "incremental_equivalence.json").read_text())
    preserved = json.loads((RUN / "historical_hash_preservation.json").read_text())
    ledger = json.loads((RUN / "incremental_rebuild_ledger.json").read_text())
    assert len(equivalent) == len(preserved) == 7
    assert all(equivalent.values()) and all(preserved.values())
    assert len(ledger) == 245
    assert sum(row["state"] == "REBUILT_INPUT_CHANGED" for row in ledger) == 51
    assert sum(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger) == 194


def test_failure_matrix_holdout_and_prior_roots_are_bound():
    failure = json.loads((RUN / "failure_matrix.json").read_text())
    assert len(failure) == 18 and set(failure.values()) == {"PASS_FAIL_CLOSED"}
    access = json.loads((RUN / "holdout_access_log.json").read_text())
    assert access == [{"classification": "SYNTHETIC_ONLY_NONCANONICAL",
                       "holdout_id": "disposable_r10e_holdout_v1",
                       "purpose": "DECLARED_SYNTHETIC_TEST_PATH"}]
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert root["references"]["r10a_root"] == "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580"
    assert root["references"]["r10d_root"] == "2f9ca92b086625d10904475254f17fe2cae135d7488d99e40738a05b618fca75"


def test_json_is_strict_and_contains_no_private_paths_or_secrets():
    texts = []
    for path in RUN.rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        texts.append(raw)
    combined = "\n".join(texts)
    assert "C:\\Users\\" not in combined
    for phrase in ("api_secret=", "access_token=", "request_token=", "password=", "private_fno_binding"):
        assert phrase not in combined.lower()
