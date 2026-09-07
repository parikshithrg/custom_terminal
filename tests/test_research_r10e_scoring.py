"""Known-answer and adversarial tests for R.10E score semantics."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from market_intel.application.synthetic_scoring import (
    disposable_holdout, family_ledger, feature_registry, materialized_features,
    scoring_changes, scoring_dependency_graph, scoring_known_answers, synthetic_oracle_rows,
)
from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.foundation.incremental import execute_rebuild, graph_equivalent, plan_rebuild
from market_intel.research.scoring import (
    AssetEvidenceSnapshot, Direction, FeatureDefinition, FeatureRegistry, Lifecycle,
    ScoringError, apply_combination, assert_transform_fit_before_validation,
    assess_confidence, calibrated_outcome, fit_linear_combination,
    fit_outcome_calibration, fit_percentile_calibration, fit_winsor_standardize,
    holm_correction, infer_direction_from_outcomes, materialize_feature,
    percentile_score, reject_score_average, transition_lifecycle,
    validate_attempt_ledger, validate_semantic_assignment,
)


ROOT = Path(__file__).resolve().parents[1]


def test_registry_contains_declared_component_set():
    definitions = feature_registry().definitions()
    assert len(definitions) == 10
    assert {d.feature_id for d in definitions} >= {
        "momentum_12_1", "short_trend", "mean_reversion", "volatility_risk",
        "liquidity", "momentum_redundant", "deterministic_noise", "missing_stale",
        "corrected_input", "fitted_scale"}
    assert next(d for d in definitions if d.feature_id == "momentum_12_1").version == "momentum_12_1_v1"


def test_registry_rejects_silent_meaning_change():
    registry = FeatureRegistry()
    definition = feature_registry().definitions()[0]
    registry.register(definition)
    changed = FeatureDefinition(**{**definition.__dict__, "meaning": "changed"})
    with pytest.raises(ScoringError, match="FEATURE_MEANING_CHANGED_WITHOUT_VERSION"):
        registry.register(changed)


def test_materialization_keeps_raw_transformed_prediction_separate():
    frame, transform = materialized_features()
    assert len(frame) == 800
    assert {"raw_feature_value", "transformed_value", "oriented_prediction",
            "feature_version", "source_input_hash", "value_state"} <= set(frame)
    mean_reversion = frame[frame.feature_id == "mean_reversion"].iloc[0]
    assert mean_reversion.oriented_prediction == -mean_reversion.transformed_value
    assert transform["training_row_count"] == 60
    assert transform["lower"] == -39.0


def test_training_transform_changes_when_training_rows_change_only():
    oracle = synthetic_oracle_rows()
    first = fit_winsor_standardize(oracle.fitted_scale, fitted_through=oracle[oracle.is_training].decision_instant.max(),
                                   training_mask=oracle.is_training, observation_times=oracle.decision_instant)
    changed_validation = oracle.fitted_scale.copy()
    changed_validation.loc[oracle.is_validation] += 10000
    second = fit_winsor_standardize(changed_validation, fitted_through=oracle[oracle.is_training].decision_instant.max(),
                                    training_mask=oracle.is_training, observation_times=oracle.decision_instant)
    assert first == second
    changed_training = oracle.fitted_scale.copy(); changed_training.iloc[0] -= 1000
    third = fit_winsor_standardize(changed_training, fitted_through=oracle[oracle.is_training].decision_instant.max(),
                                   training_mask=oracle.is_training, observation_times=oracle.decision_instant)
    assert third.training_hash != first.training_hash


def test_missing_and_stale_are_explicit_not_imputed():
    frame, _ = materialized_features()
    subset = frame[frame.feature_id == "missing_stale"]
    assert set(subset.value_state) == {"AVAILABLE", "MISSING", "STALE"}
    assert subset[subset.value_state != "AVAILABLE"].transformed_value.isna().all()


def test_future_feature_input_fails_closed():
    definition = feature_registry().definitions()[0]
    raw = pd.DataFrame([{ "instrument_id": "x", "decision_session_id": "s",
        "decision_instant": pd.Timestamp("2020-01-01T10:00:00Z"),
        "knowledge_cutoff": pd.Timestamp("2020-01-01T10:00:00Z"),
        "available_at": pd.Timestamp("2020-01-01T10:00:01Z"), "input_snapshot_id": "i",
        "calendar_version": definition.calendar_version, "stale": False, "raw_feature_value": 1.0}])
    with pytest.raises(ScoringError, match="FEATURE_INPUT_AFTER_KNOWLEDGE_CUTOFF"):
        materialize_feature(raw, definition)


def test_percentile_ties_ranges_and_negative_direction():
    cal = fit_percentile_calibration(pd.Series([1, 2, 2, 4, 5]), population_id="p",
        period_start=pd.Timestamp("2020-01-01T00:00:00Z"), period_end=pd.Timestamp("2020-01-02T00:00:00Z"),
        training_cutoff=pd.Timestamp("2020-01-02T00:00:00Z"), direction=Direction.POSITIVE)
    assert percentile_score(2, cal) == ("AVAILABLE", 40.0)
    assert percentile_score(-100, cal)[1] == 0.0 and percentile_score(100, cal)[1] == 100.0
    negative = fit_percentile_calibration(pd.Series([1, 2, 3, 4, 5]), population_id="n",
        period_start=pd.Timestamp("2020-01-01T00:00:00Z"), period_end=pd.Timestamp("2020-01-02T00:00:00Z"),
        training_cutoff=pd.Timestamp("2020-01-02T00:00:00Z"), direction=Direction.NEGATIVE)
    assert percentile_score(1, negative)[1] > percentile_score(5, negative)[1]


def test_identical_percentile_can_have_different_expected_outcome():
    statuses = pd.Series(["RESOLVED"] * 5)
    a = fit_outcome_calibration(pd.Series([1,2,3,4,5]), pd.Series([1,2,3,4,5]), statuses,
                                population_id="a", training_cutoff=pd.Timestamp("2020-01-01T00:00:00Z"))
    b = fit_outcome_calibration(pd.Series([1,2,3,4,5]), pd.Series([10,20,30,40,50]), statuses,
                                population_id="b", training_cutoff=pd.Timestamp("2020-01-01T00:00:00Z"))
    assert calibrated_outcome(3, a)["expected_outcome"] == 3
    assert calibrated_outcome(3, b)["expected_outcome"] == 30


def test_small_sample_is_unavailable_not_fabricated():
    cal = fit_outcome_calibration(pd.Series([1,2]), pd.Series([1,2]), pd.Series(["RESOLVED"]*2),
                                  population_id="small", training_cutoff=pd.Timestamp("2020-01-01T00:00:00Z"))
    assert calibrated_outcome(1, cal) == {"state": "UNAVAILABLE", "reason": "INSUFFICIENT_EVIDENCE", "sample_size": 0}


def test_unresolved_outcomes_are_counted_in_calibration():
    cal = fit_outcome_calibration(pd.Series(range(6)), pd.Series(range(6)),
        pd.Series(["RESOLVED"]*5 + ["UNRESOLVED_TERMINAL"]), population_id="p",
        training_cutoff=pd.Timestamp("2020-01-01T00:00:00Z"))
    assert cal.unresolved_count == 1 and len(cal.rows) == 5


@pytest.mark.parametrize("field,semantic", [
    ("score_0_100", "POSITIVE_OUTCOME_PROBABILITY"),
    ("score_0_100", "EXPECTED_OUTCOME"),
    ("positive_outcome_probability", "EXPECTED_OUTCOME"),
    ("positive_outcome_probability", "CONFIDENCE_BAND"),
])
def test_semantic_substitution_is_prohibited(field, semantic):
    with pytest.raises(ScoringError, match="SEMANTIC_SUBSTITUTION_PROHIBITED"):
        validate_semantic_assignment(field, semantic)


def test_combination_drops_redundancy_and_beats_naive():
    answers = scoring_known_answers()
    assert answers["dropped_redundant"] == ("momentum_redundant",)
    assert answers["combination_validation_mse"] < 1e-20
    assert answers["naive_validation_mse"] > 10


def test_validation_outcomes_cannot_change_fitted_weights():
    oracle = synthetic_oracle_rows(); mask = oracle.is_training
    x = oracle[["momentum_12_1", "short_trend", "deterministic_noise"]]
    first = fit_linear_combination(x, oracle.synthetic_outcome, training_mask=mask,
                                   training_cutoff=oracle[mask].decision_instant.max(), observation_times=oracle.decision_instant)
    changed = oracle.synthetic_outcome.copy(); changed.loc[~mask] += 1_000_000
    second = fit_linear_combination(x, changed, training_mask=mask,
                                    training_cutoff=oracle[mask].decision_instant.max(), observation_times=oracle.decision_instant)
    assert first == second


def test_display_score_averaging_and_outcome_direction_inference_rejected():
    with pytest.raises(ScoringError, match="AVERAGING_COMPONENT_DISPLAY_SCORES_PROHIBITED"):
        reject_score_average([10, 90])
    with pytest.raises(ScoringError, match="OUTCOME_LEAKAGE_INTO_FEATURE_DIRECTION"):
        infer_direction_from_outcomes([1, 2], [2, 4])


def test_holm_known_answers_and_attempt_ledger():
    result = holm_correction({"strong": .005, "borderline": .02, "null": .5})
    assert result["strong"]["threshold"] == pytest.approx(1/60)
    assert result["strong"]["reject"] and result["borderline"]["reject"] and not result["null"]["reject"]
    ledger = family_ledger()
    assert len(ledger) == 16 and "deterministic_noise" in set(ledger.attempt_id)


def test_omitted_diagnostic_attempt_fails_closed():
    ledger = family_ledger()
    with pytest.raises(ScoringError, match="DIAGNOSTIC_ATTEMPT_OMITTED"):
        validate_attempt_ledger(ledger, [*ledger.attempt_id, "omitted_diagnostic"])


def test_confidence_is_categorical_with_limits_not_weighted_score():
    result = assess_confidence(sample_size=25, interval_width=1.4, fold_stable=True,
        coverage_broad=False, fresh=True, cost_robust=True, parameter_robust=True,
        multiplicity_pass=False, decay_state="STABLE")
    assert result["confidence"] == "LOW"
    assert result["limiting_factors"] == ["SMALL_EFFECTIVE_SAMPLE", "WIDE_UNCERTAINTY_INTERVAL",
                                          "NARROW_SYNTHETIC_COVERAGE", "MULTIPLE_TESTING_BURDEN"]
    assert "confidence_score" not in result


def test_synthetic_lifecycle_can_never_promote_to_real_or_active():
    assert transition_lifecycle(Lifecycle.RESEARCHING, Lifecycle.SYNTHETIC_VALIDATED_NONCANONICAL,
                                synthetic=True) == Lifecycle.SYNTHETIC_VALIDATED_NONCANONICAL
    for forbidden in (Lifecycle.VALIDATED_REAL_DATA, Lifecycle.ACTIVE):
        with pytest.raises(ScoringError, match="SYNTHETIC_LIFECYCLE_PROMOTION_PROHIBITED"):
            transition_lifecycle(Lifecycle.RESEARCHING, forbidden, synthetic=True)


def test_snapshot_is_no_decision_and_semantically_labeled():
    snapshot = scoring_known_answers()["snapshot"]
    assert snapshot["decision"] == "NO_DECISION"
    assert snapshot["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert snapshot["score_0_100"] == 15.0 and snapshot["confidence"] == "LOW"
    with pytest.raises(ScoringError, match="SYNTHETIC_DECISION_PROHIBITED"):
        AssetEvidenceSnapshot(**{**snapshot, "decision": "BUY"})


def test_disposable_holdout_is_declared_logged_and_one_use():
    holdout = disposable_holdout()
    with pytest.raises(ScoringError, match="HOLDOUT_ACCESS_PROHIBITED"):
        holdout.open(purpose="TRAINING")
    assert holdout.open(purpose="DECLARED_SYNTHETIC_TEST_PATH").iloc[0].value == 7.0
    assert len(holdout.access_log) == 1
    with pytest.raises(ScoringError, match="HOLDOUT_REUSE_PROHIBITED"):
        holdout.open(purpose="DECLARED_SYNTHETIC_TEST_PATH")


def test_training_leakage_guards_fail_closed():
    values = pd.Series([1., 2., 3., 4., 5.]); mask = pd.Series([True] * 5)
    times = pd.Series(pd.date_range("2020-01-01", periods=5, tz="UTC"))
    with pytest.raises(ScoringError, match="GLOBAL_WINSORIZATION_BEFORE_FOLD_SPLIT"):
        fit_winsor_standardize(values, fitted_through=times.iloc[2], training_mask=mask, observation_times=times)
    with pytest.raises(ScoringError, match="FULL_SAMPLE_PERCENTILE_CALIBRATION"):
        fit_percentile_calibration(values, population_id="p", period_start=times.iloc[0], period_end=times.iloc[-1],
                                   training_cutoff=times.iloc[2], direction=Direction.POSITIVE, observation_times=times)
    with pytest.raises(ScoringError, match="HOLDOUT_FITTED_CALIBRATION"):
        fit_outcome_calibration(values, values, pd.Series(["RESOLVED"]*5), population_id="p",
                                training_cutoff=times.iloc[2], observation_times=times)


def test_transform_fitted_at_validation_boundary_is_rejected():
    oracle = synthetic_oracle_rows(); mask = oracle.is_training
    artifact = fit_winsor_standardize(oracle.fitted_scale, fitted_through=oracle[mask].decision_instant.max(),
                                      training_mask=mask, observation_times=oracle.decision_instant)
    with pytest.raises(ScoringError, match="VALIDATION_FITTED_TRANSFORMATION"):
        assert_transform_fit_before_validation(artifact, artifact.fitted_through)


def test_incremental_scoring_changes_are_minimal_and_clean_equivalent():
    graph = scoring_dependency_graph("env")
    original_score = graph.nodes["score_snapshot"].output_hash
    for change in scoring_changes().values():
        plan = plan_rebuild(graph, change)
        clean = _clean_candidate(graph, plan, change.change_id)
        incremental, ledger = execute_rebuild(graph, clean, plan)
        assert graph_equivalent(incremental, clean)
        assert any(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger)
    confidence = plan_rebuild(graph, scoring_changes()["confidence_policy"])
    assert confidence["confidence"]["state"] == "REBUILT_INPUT_CHANGED"
    assert confidence["calibration"]["state"] == "UNAFFECTED"
    assert graph.nodes["score_snapshot"].output_hash == original_score


def test_existing_holdout_and_protected_artifacts_remain_unchanged():
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r10d/run_v1/root_manifest.json": "2f9ca92b086625d10904475254f17fe2cae135d7488d99e40738a05b618fca75",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    manifest = __import__("json").loads((ROOT / "docs/investigations/r10a/run_v1/root_run_manifest.json").read_text())
    assert manifest["holdout"]["state"] == "UNCONSUMED_SYNTHETIC_HOLDOUT"
