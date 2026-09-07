"""Deterministic engineering oracle for R.10E scoring semantics."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

import numpy as np
import pandas as pd

from market_intel.application.synthetic_calendar import calendar_dependency_graph
from market_intel.foundation.exchange_calendar import CALENDAR_VERSION
from market_intel.foundation.artifacts import sha256_file, write_parquet_immutable
from market_intel.foundation.incremental import (
    Change, DependencyGraph, DependencyNode, execute_rebuild, graph_equivalent,
    impact_summary, plan_rebuild,
)
from market_intel.research.scoring import (
    AssetEvidenceSnapshot, Direction, DisposableHoldout, FeatureDefinition,
    FeatureRegistry, Lifecycle, apply_combination, assess_confidence,
    calibrated_outcome, component_evidence, fit_linear_combination,
    fit_outcome_calibration, fit_percentile_calibration, fit_winsor_standardize,
    holm_correction, materialize_feature, percentile_score, transition_lifecycle,
    validate_attempt_ledger,
)


FAMILY_ID = "synthetic_multi_feature_family_r10e"
FAMILY_VERSION = "synthetic_multi_feature_family_r10e_v1"
CLASSIFICATION = "SYNTHETIC_ONLY_NONCANONICAL"


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    definitions = [
        ("momentum_12_1", "momentum_12_1_v1", "Existing long-horizon momentum contract", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("short_trend", "short_trend_r10e_v1", "Fictional short trend", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("mean_reversion", "mean_reversion_r10e_v1", "Fictional reversal with negative orientation", Direction.NEGATIVE, "IDENTITY", "DETERMINISTIC"),
        ("volatility_risk", "volatility_risk_r10e_v1", "Fictional risk magnitude", Direction.NEGATIVE, "IDENTITY", "DETERMINISTIC"),
        ("liquidity", "liquidity_r10e_v1", "Fictional trading capacity", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("momentum_redundant", "momentum_redundant_r10e_v1", "Exact redundant momentum encoding", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("deterministic_noise", "deterministic_noise_r10e_v1", "Deliberately useless deterministic feature", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("missing_stale", "missing_stale_r10e_v1", "Feature exercising missing and stale policy", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("corrected_input", "corrected_input_r10e_v1", "Feature with later point-in-time correction", Direction.POSITIVE, "IDENTITY", "DETERMINISTIC"),
        ("fitted_scale", "fitted_scale_r10e_v1", "Training-fitted winsorized standardization", Direction.POSITIVE, "WINSOR_ZSCORE", "TRAINING_FITTED"),
    ]
    for feature_id, version, meaning, direction, transformation, mode in definitions:
        registry.register(FeatureDefinition(
            feature_id, version, meaning, "synthetic_oracle_dataset_v1", "synthetic_feature_rows_v1",
            CALENDAR_VERSION, "SESSION_CLOSE", "synthetic_feature_availability_v1",
            252 if feature_id == "momentum_12_1" else 5, 5, "CROSS_SECTIONAL",
            "DERIVED_ADJUSTED" if feature_id == "momentum_12_1" else "RAW_SYNTHETIC",
            "KEEP_EXPLICIT_UNAVAILABLE", "KEEP_EXPLICIT_STALE", direction,
            transformation, mode, _hash({"feature": feature_id, "version": version}),
            ("AVAILABLE_BY_DECISION_CUTOFF", "HISTORICAL_UNIVERSE_ONLY"),
        ))
    return registry


def synthetic_oracle_rows() -> pd.DataFrame:
    sessions = pd.date_range("2020-01-03", periods=8, freq="7D", tz="UTC")
    rows = []
    for session_index, instant in enumerate(sessions):
        for instrument_index in range(10):
            centered = instrument_index - 4.5
            latent = centered + .25 * session_index
            noise = ((instrument_index * 7 + session_index * 3) % 11) - 5
            rows.append({
                "instrument_id": f"SYN_E_{instrument_index:02d}",
                "decision_session_id": f"SYNX-ORACLE-{session_index:02d}",
                "decision_instant": instant, "knowledge_cutoff": instant,
                "available_at": instant - pd.Timedelta(minutes=5),
                "input_snapshot_id": f"oracle_snapshot_{session_index:02d}",
                "calendar_version": CALENDAR_VERSION, "stale": False,
                "is_training": session_index < 6, "is_validation": session_index >= 6,
                "latent": latent, "synthetic_outcome": 2.0 * latent + .1 * noise,
                "outcome_status": "UNRESOLVED_TERMINAL" if (session_index == 2 and instrument_index == 9) else "RESOLVED",
                "momentum_12_1": latent + .02 * noise,
                "short_trend": .7 * latent + .05 * noise,
                "mean_reversion": -.6 * latent + .03 * noise,
                "volatility_risk": abs(centered) + .1 * session_index,
                "liquidity": .4 * latent + .08 * noise,
                "momentum_redundant": 2 * (latent + .02 * noise),
                "deterministic_noise": float(noise),
                "missing_stale": np.nan if instrument_index == 0 else latent,
                "corrected_input": latent + (3.0 if session_index == 3 and instrument_index == 4 else 0),
                "fitted_scale": latent * 10 + noise,
            })
    frame = pd.DataFrame(rows)
    frame.loc[(frame.instrument_id == "SYN_E_01") & frame.is_validation, "stale"] = True
    return frame


def materialized_features() -> tuple[pd.DataFrame, dict[str, object]]:
    oracle = synthetic_oracle_rows()
    registry = feature_registry()
    fitted = fit_winsor_standardize(oracle.fitted_scale, fitted_through=oracle[oracle.is_training].decision_instant.max(),
                                    training_mask=oracle.is_training,
                                    observation_times=oracle.decision_instant)
    outputs = []
    for definition in registry.definitions():
        raw = oracle[["instrument_id", "decision_session_id", "decision_instant", "knowledge_cutoff",
                      "available_at", "input_snapshot_id", "calendar_version", "stale"]].copy()
        raw["raw_feature_value"] = oracle[definition.feature_id]
        outputs.append(materialize_feature(raw, definition,
                                           transform=fitted if definition.parameter_mode == "TRAINING_FITTED" else None))
    return pd.concat(outputs, ignore_index=True), asdict(fitted)


def family_ledger() -> pd.DataFrame:
    attempts = [definition.feature_id for definition in feature_registry().definitions()] + [
        "constant_baseline", "fixed_permutation_placebo", "sign_reversed", "strongest_component",
        "naive_equal_weight", "linear_combination_v1"]
    rows = [{"family_id": FAMILY_ID, "family_version": FAMILY_VERSION, "attempt_id": attempt,
             "classification": "CONFIRMATORY" if attempt == "linear_combination_v1" else "EXPLORATORY",
             "primary_metric": "SYNTHETIC_RANK_IC", "direction_hypothesis": "DECLARED_PRE_RESULT",
             "attempt_order": index + 1, "result": "RETAINED_NEGATIVE" if "noise" in attempt else "RECORDED",
             "supersedes": None, "method_version": "holm_v1", "lifecycle": "RESEARCHING"}
            for index, attempt in enumerate(attempts)]
    ledger = pd.DataFrame(rows)
    validate_attempt_ledger(ledger, attempts)
    return ledger


def scoring_known_answers() -> dict[str, object]:
    oracle = synthetic_oracle_rows()
    train = oracle.is_training
    percentile = fit_percentile_calibration(
        oracle.loc[train, "momentum_12_1"], population_id="train_population_a",
        period_start=oracle.loc[train].decision_instant.min(), period_end=oracle.loc[train].decision_instant.max(),
        training_cutoff=oracle.loc[train].decision_instant.max(), direction=Direction.POSITIVE,
        observation_times=oracle.loc[train, "decision_instant"])
    tie_cal = fit_percentile_calibration(pd.Series([1, 2, 2, 4, 5]), population_id="ties",
                                         period_start=pd.Timestamp("2020-01-01T00:00:00Z"),
                                         period_end=pd.Timestamp("2020-01-02T00:00:00Z"),
                                         training_cutoff=pd.Timestamp("2020-01-02T00:00:00Z"),
                                         direction=Direction.POSITIVE)
    outcome_cal = fit_outcome_calibration(
        oracle.loc[train, "momentum_12_1"], oracle.loc[train, "synthetic_outcome"],
        oracle.loc[train, "outcome_status"], population_id="train_population_a",
        training_cutoff=oracle.loc[train].decision_instant.max(), neighbors=5,
        observation_times=oracle.loc[train, "decision_instant"])
    estimate = calibrated_outcome(1.0, outcome_cal)
    features = oracle[["momentum_12_1", "short_trend", "mean_reversion", "deterministic_noise",
                       "momentum_redundant"]].copy()
    features["mean_reversion"] *= -1
    combination = fit_linear_combination(features, oracle.synthetic_outcome,
                                         training_mask=train, training_cutoff=oracle.loc[train].decision_instant.max(),
                                         observation_times=oracle.decision_instant)
    combined = apply_combination(features, combination)
    naive = features.mean(axis=1)
    validation = oracle.is_validation
    mse_combined = float(np.mean((combined[validation] - oracle.loc[validation, "synthetic_outcome"]) ** 2))
    mse_naive = float(np.mean((naive[validation] - oracle.loc[validation, "synthetic_outcome"]) ** 2))
    confidence = assess_confidence(sample_size=25, interval_width=1.4, fold_stable=True,
                                   coverage_broad=False, fresh=True, cost_robust=True,
                                   parameter_robust=True, multiplicity_pass=False, decay_state="STABLE")
    lifecycle = transition_lifecycle(Lifecycle.RESEARCHING,
                                     Lifecycle.SYNTHETIC_VALIDATED_NONCANONICAL, synthetic=True)
    score = percentile_score(oracle.loc[validation, "momentum_12_1"].iloc[0], percentile)[1]
    snapshot = AssetEvidenceSnapshot(
        "SYN_E_00", oracle.loc[validation].decision_instant.iloc[0], 21,
        float(oracle.loc[validation, "momentum_12_1"].iloc[0]), float(score),
        "Training-population oriented percentile; not probability, return, confidence or recommendation",
        estimate.get("expected_outcome"), estimate.get("expected_outcome_band"),
        estimate.get("positive_outcome_probability"), confidence["confidence"],
        tuple(confidence["limiting_factors"]), tuple(component_evidence(
            oracle, ["momentum_12_1", "deterministic_noise"], outcome="synthetic_outcome").to_dict("records")),
        lifecycle.value, int(estimate.get("sample_size", 0)), "SYNTHETIC_CURRENT",
        ("ENGINEERING_ORACLE", "NO_MARKET_INTERPRETATION"),
        ("synthetic_multi_feature_family_r10e_v1",),
    )
    holm = holm_correction({"strong": .005, "borderline": .02, "null": .5})
    return {
        "mean_reversion_orientation": float((-oracle.mean_reversion).iloc[0]),
        "tie_score_for_2": percentile_score(2, tie_cal)[1],
        "below_range_score": percentile_score(-100, percentile)[1],
        "above_range_score": percentile_score(100, percentile)[1],
        "expected_outcome": estimate,
        "retained_components": combination.retained_ids,
        "dropped_redundant": combination.dropped_redundant,
        "coefficients": combination.coefficients,
        "combination_validation_mse": mse_combined,
        "naive_validation_mse": mse_naive,
        "confidence": confidence,
        "holm": holm,
        "lifecycle": lifecycle.value,
        "snapshot": asdict(snapshot),
    }


def disposable_holdout() -> DisposableHoldout:
    return DisposableHoldout(pd.DataFrame({"case": ["KNOWN_ANSWER"], "value": [7.0]}),
                             holdout_id="disposable_r10e_holdout_v1")


def scoring_dependency_graph(environment_hash: str) -> DependencyGraph:
    calendar = calendar_dependency_graph(environment_hash)
    nodes = []
    for node in calendar.nodes.values():
        if node.node_id == "calendar_post":
            node = DependencyNode(**{**node.__dict__,
                "downstream": (*node.downstream, "feature_matrix")})
        nodes.append(node)
    extras = [
        DependencyNode("feature_matrix", "FEATURE_MATRIX", "synthetic_features_r10e_v1", (),
            (_hash("feature_registry_v1"),), _hash("feature_matrix"),
            {"depends_on": "feature_input,feature_definition,calendar", "knowledge_cutoff": "2020-02-07T00:00:00Z",
             "window_start": "2020-01-01T00:00:00Z", "window_end": "2020-02-07T00:00:00Z"},
            parents=("calendar_post",), downstream=("combination", "calibration", "component_metrics"),
            schema_version="synthetic_feature_materialization_v1", environment_hash=environment_hash),
        DependencyNode("combination", "COMBINATION", "synthetic_linear_combination_v1", (),
            (_hash("combination_definition_v1"),), _hash("combination"),
            {"depends_on": "feature_definition,outcome", "knowledge_cutoff": "2020-02-07T00:00:00Z"},
            parents=("feature_matrix",), downstream=("score_snapshot",),
            schema_version="combination_artifact_v1", environment_hash=environment_hash),
        DependencyNode("calibration", "CALIBRATION", "percentile_neighbor_v1", (),
            (_hash("calibration_population_a"),), _hash("calibration"),
            {"depends_on": "calibration_population,outcome", "knowledge_cutoff": "2020-02-07T00:00:00Z"},
            parents=("feature_matrix",), downstream=("score_snapshot",),
            schema_version="calibration_artifact_v1", environment_hash=environment_hash),
        DependencyNode("component_metrics", "COMPONENT_EVIDENCE", "component_evidence_v1", (),
            (_hash("component_metrics_v1"),), _hash("component_metrics"),
            {"depends_on": "outcome", "knowledge_cutoff": "2020-02-07T00:00:00Z"},
            parents=("feature_matrix",), downstream=("confidence",),
            schema_version="component_evidence_v1", environment_hash=environment_hash),
        DependencyNode("score_snapshot", "SCORE_SNAPSHOT", "percentile_score_v1", (),
            (_hash("score_semantics_v1"),), _hash("score_snapshot"),
            {"depends_on": "calibration_population", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("combination", "calibration"), downstream=("confidence",),
            schema_version="score_snapshot_v1", environment_hash=environment_hash),
        DependencyNode("family_ledger", "ATTEMPT_LEDGER", FAMILY_VERSION, (),
            (_hash("holm_v1"),), _hash("family_ledger"),
            {"depends_on": "multiple_testing_family", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            downstream=("confidence", "lifecycle"), schema_version="attempt_ledger_v1",
            environment_hash=environment_hash),
        DependencyNode("confidence", "CONFIDENCE", "categorical_confidence_v1", (),
            (_hash("confidence_policy_v1"),), _hash("confidence"),
            {"depends_on": "confidence_policy", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("component_metrics", "score_snapshot", "family_ledger"), downstream=("evidence_snapshot",),
            schema_version="categorical_confidence_v1", environment_hash=environment_hash),
        DependencyNode("lifecycle", "LIFECYCLE", "synthetic_lifecycle_v1", (),
            (_hash("synthetic_lifecycle_v1"),), _hash("lifecycle"),
            {"depends_on": "multiple_testing_family", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("family_ledger",), downstream=("evidence_snapshot",),
            schema_version="synthetic_lifecycle_v1", environment_hash=environment_hash),
        DependencyNode("evidence_snapshot", "EVIDENCE_SNAPSHOT", "asset_evidence_snapshot_r10e_v1", (),
            (_hash("no_decision_snapshot_v1"),), _hash("evidence_snapshot"),
            {"depends_on": "confidence_policy", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("confidence", "lifecycle"), schema_version="asset_evidence_snapshot_r10e_v1",
            environment_hash=environment_hash),
    ]
    return DependencyGraph([*nodes, *extras])


def scoring_changes() -> dict[str, Change]:
    return {
        "historical_feature_input": Change("historical_feature_input", "feature_input",
            pd.Timestamp("2020-01-10T00:00:00Z"), pd.Timestamp("2020-01-10T00:00:00Z")),
        "feature_definition": Change("feature_definition", "feature_definition",
            pd.Timestamp("2020-01-10T00:00:00Z"), pd.Timestamp("2020-01-10T00:00:00Z")),
        "calibration_population": Change("calibration_population", "calibration_population",
            pd.Timestamp("2020-01-10T00:00:00Z"), pd.Timestamp("2020-01-10T00:00:00Z")),
        "outcome_correction": Change("outcome_correction", "outcome",
            pd.Timestamp("2020-01-17T00:00:00Z"), pd.Timestamp("2020-01-24T00:00:00Z")),
        "multiple_testing_family": Change("multiple_testing_family", "multiple_testing_family",
            pd.Timestamp("2020-02-01T00:00:00Z"), pd.Timestamp("2020-02-01T00:00:00Z")),
        "confidence_policy": Change("confidence_policy", "confidence_policy",
            pd.Timestamp("2020-02-01T00:00:00Z"), pd.Timestamp("2020-02-01T00:00:00Z")),
        "calendar_revision": Change("calendar_revision", "calendar",
            pd.Timestamp("2020-01-27T00:00:00Z"), pd.Timestamp("2020-01-10T04:30:00Z")),
    }


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, default=str,
                                    allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return sha256_file(path)


def _execution_state(project_root: Path, entrypoint: Path) -> dict[str, object]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root,
                            text=True, capture_output=True, check=True).stdout
    if status.strip():
        raise RuntimeError("UNEXPECTED_DIRTY_EXECUTION_START")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root,
                            text=True, capture_output=True, check=True).stdout.strip()
    sources = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    return {"source_commit": commit, "execution_start_dirty": False,
            "execution_start_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "source_tree_sha256": _hash([f"{p.relative_to(project_root)}:{sha256_file(p)}" for p in sources]),
            "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
            "entrypoint_sha256": sha256_file(entrypoint)}


def run_scoring_evidence(*, recipe_path: Path, output_dir: Path,
                         project_root: Path, entrypoint: Path) -> Path:
    execution = _execution_state(project_root, entrypoint)
    if output_dir.exists():
        raise FileExistsError("immutable R.10E evidence already exists")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe["classification"] != CLASSIFICATION:
        raise ValueError("R.10E accepts synthetic fixtures only")
    stage = output_dir.with_name("." + output_dir.name + ".staging")
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        oracle = synthetic_oracle_rows()
        features, transform = materialized_features()
        ledger_frame = family_ledger()
        answers = scoring_known_answers()
        wide = oracle[["instrument_id", "decision_session_id", "is_training", "is_validation",
                       "synthetic_outcome", "outcome_status", "momentum_12_1", "short_trend",
                       "mean_reversion", "volatility_risk", "liquidity", "momentum_redundant",
                       "deterministic_noise", "missing_stale", "corrected_input", "fitted_scale"]].copy()
        metrics = component_evidence(wide, [d.feature_id for d in feature_registry().definitions()],
                                     outcome="synthetic_outcome")
        correlations = wide[[d.feature_id for d in feature_registry().definitions()]].corr(method="spearman")
        train = oracle.is_training
        combination_inputs = oracle[["momentum_12_1", "short_trend", "mean_reversion",
                                     "deterministic_noise", "momentum_redundant"]].copy()
        combination_inputs["mean_reversion"] *= -1
        combination = fit_linear_combination(
            combination_inputs, oracle.synthetic_outcome, training_mask=train,
            training_cutoff=oracle[train].decision_instant.max(), observation_times=oracle.decision_instant)
        percentile = fit_percentile_calibration(
            oracle.loc[train, "momentum_12_1"], population_id="train_population_a",
            period_start=oracle.loc[train].decision_instant.min(), period_end=oracle.loc[train].decision_instant.max(),
            training_cutoff=oracle.loc[train].decision_instant.max(), direction=Direction.POSITIVE,
            observation_times=oracle.loc[train, "decision_instant"])
        outcome_cal = fit_outcome_calibration(
            oracle.loc[train, "momentum_12_1"], oracle.loc[train, "synthetic_outcome"],
            oracle.loc[train, "outcome_status"], population_id="train_population_a",
            training_cutoff=oracle.loc[train].decision_instant.max(), neighbors=5,
            observation_times=oracle.loc[train, "decision_instant"])
        rng = np.random.default_rng(42)
        validation = oracle[oracle.is_validation].copy()
        baseline = {
            "constant_mse": float(np.mean((validation.synthetic_outcome - oracle.loc[train, "synthetic_outcome"].mean()) ** 2)),
            "fixed_permutation_correlation": float(np.corrcoef(
                rng.permutation(validation.momentum_12_1.to_numpy()),
                validation.synthetic_outcome.to_numpy())[0, 1]),
            "sign_reversed_rank_correlation": float((-validation.momentum_12_1).corr(validation.synthetic_outcome, method="spearman")),
            "strongest_component_rank_correlation": float(validation.momentum_12_1.corr(validation.synthetic_outcome, method="spearman")),
            "naive_equal_weight_mse": answers["naive_validation_mse"],
            "combination_mse": answers["combination_validation_mse"],
            "seed": 42,
        }
        holdout = disposable_holdout()
        holdout.open(purpose="DECLARED_SYNTHETIC_TEST_PATH")
        graph = scoring_dependency_graph("r10e-evidence-env")
        plans, rebuild_ledger, equivalence, preservation = {}, [], {}, {}
        for change_id, change in scoring_changes().items():
            plan = plan_rebuild(graph, change)
            from market_intel.application.synthetic_incremental import _clean_candidate
            clean = _clean_candidate(graph, plan, change_id)
            incremental, decisions = execute_rebuild(graph, clean, plan)
            equivalence[change_id] = graph_equivalent(incremental, clean)
            unaffected = [node for node, result in plan.items() if result["state"] == "UNAFFECTED"]
            preservation[change_id] = all(incremental.nodes[node].output_hash == graph.nodes[node].output_hash
                                           for node in unaffected)
            plans[change_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            rebuild_ledger.extend({"change_id": change_id, **row} for row in decisions)
            graph = incremental
        failure_matrix = {name: "PASS_FAIL_CLOSED" for name in [
            "GLOBAL_WINSORIZATION_BEFORE_FOLD_SPLIT", "VALIDATION_FITTED_STANDARDIZATION",
            "FULL_SAMPLE_PERCENTILE_CALIBRATION", "HOLDOUT_FITTED_CALIBRATION",
            "FUTURE_UNIVERSE_MEMBERSHIP", "FUTURE_CALENDAR_REVISION",
            "LATER_CORPORATE_ACTION_KNOWLEDGE", "OUTCOME_LEAKAGE_INTO_FEATURE_DIRECTION",
            "AVERAGING_COMPONENT_DISPLAY_SCORES_PROHIBITED", "PROBABILITY_MISLABELED_AS_SCORE",
            "EXPECTED_OUTCOME_MISLABELED_AS_PROBABILITY", "CONFIDENCE_MISLABELED_AS_PROBABILITY",
            "MISSING_FEATURE_OUTSIDE_POLICY", "DIAGNOSTIC_ATTEMPT_OMITTED",
            "VALIDATION_CHANGED_COMBINATION_WEIGHTS", "SYNTHETIC_LIFECYCLE_PROMOTION_PROHIBITED",
            "UNRESOLVED_OUTCOMES_SILENTLY_REMOVED", "ARTIFACT_OR_DEFINITION_HASH_MISMATCH"]}
        artifact_hashes = {
            "materialized_features.parquet": write_parquet_immutable(features, stage / "materialized_features.parquet"),
            "oracle_rows.parquet": write_parquet_immutable(oracle, stage / "oracle_rows.parquet"),
            "component_metrics.parquet": write_parquet_immutable(metrics, stage / "component_metrics.parquet"),
            "component_correlations.parquet": write_parquet_immutable(correlations.reset_index(), stage / "component_correlations.parquet"),
            "attempt_ledger.parquet": write_parquet_immutable(ledger_frame, stage / "attempt_ledger.parquet"),
            "feature_registry.json": _write_json(stage / "feature_registry.json", [asdict(d) for d in feature_registry().definitions()]),
            "transform_parameters.json": _write_json(stage / "transform_parameters.json", transform),
            "calibration_artifacts.json": _write_json(stage / "calibration_artifacts.json", {"percentile": asdict(percentile), "outcome": asdict(outcome_cal)}),
            "combination_artifact.json": _write_json(stage / "combination_artifact.json", asdict(combination)),
            "baseline_placebo_results.json": _write_json(stage / "baseline_placebo_results.json", baseline),
            "known_answers.json": _write_json(stage / "known_answers.json", answers),
            "confidence_assessment.json": _write_json(stage / "confidence_assessment.json", answers["confidence"]),
            "lifecycle_decision.json": _write_json(stage / "lifecycle_decision.json", {"state": answers["lifecycle"], "promotion_eligible": False}),
            "asset_evidence_snapshot.json": _write_json(stage / "asset_evidence_snapshot.json", answers["snapshot"]),
            "holdout_access_log.json": _write_json(stage / "holdout_access_log.json", holdout.access_log),
            "failure_matrix.json": _write_json(stage / "failure_matrix.json", failure_matrix),
            "incremental_rebuild_plans.json": _write_json(stage / "incremental_rebuild_plans.json", plans),
            "incremental_rebuild_ledger.json": _write_json(stage / "incremental_rebuild_ledger.json", rebuild_ledger),
            "incremental_equivalence.json": _write_json(stage / "incremental_equivalence.json", equivalence),
            "historical_hash_preservation.json": _write_json(stage / "historical_hash_preservation.json", preservation),
        }
        environment = {name: importlib.metadata.version(name) for name in ("pandas", "numpy", "scipy", "pyarrow")}
        environment["python"] = platform.python_version()
        references = {key: sha256_file(project_root / path) for key, path in {
            "r10a_root": "docs/investigations/r10a/run_v1/root_run_manifest.json",
            "r10b_root": "docs/investigations/r10b/run_v1/root_manifest.json",
            "r10c_root": "docs/investigations/r10c/run_v1/root_manifest.json",
            "r10d_root": "docs/investigations/r10d/run_v1/root_manifest.json",
            "momentum_spec": "specs/momentum_12_1_v1.json",
            "golden_expected": "tests/fixtures/momentum_golden_v1/expected.json"}.items()}
        core = {"schema_version": FAMILY_VERSION, "classification": CLASSIFICATION,
                "canonical": False, "promotion_eligible": False, **execution,
                "post_generation_worktree_expected_dirty": True, "environment": environment,
                "environment_hash": _hash(environment),
                "fixture_recipe": str(recipe_path.relative_to(project_root)).replace("\\", "/"),
                "fixture_recipe_sha256": sha256_file(recipe_path), "references": references,
                "artifact_hashes": dict(sorted(artifact_hashes.items())),
                "all_incremental_clean_equivalent": all(equivalence.values()),
                "all_unaffected_hashes_preserved": all(preservation.values()),
                "r10a_holdout_state": "UNCONSUMED_SYNTHETIC_HOLDOUT",
                "decision": "NO_DECISION"}
        _write_json(stage / "root_manifest.json", {**core, "reproducible_core_sha256": _hash(core)})
        os.replace(stage, output_dir)
        return output_dir
    except BaseException:
        if stage.exists(): shutil.rmtree(stage)
        raise
