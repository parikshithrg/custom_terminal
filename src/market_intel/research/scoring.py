"""Synthetic-safe feature, calibration, score, confidence and lifecycle contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
from scipy import stats


class ScoringError(ValueError):
    pass


class Direction(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class ConfidenceBand(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class Lifecycle(StrEnum):
    DRAFT = "DRAFT"
    RESEARCHING = "RESEARCHING"
    SYNTHETIC_VALIDATED_NONCANONICAL = "SYNTHETIC_VALIDATED_NONCANONICAL"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"
    VALIDATED_REAL_DATA = "VALIDATED_REAL_DATA"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    version: str
    meaning: str
    input_dataset_version: str
    input_schema_version: str
    calendar_version: str
    decision_clock: str
    availability_policy: str
    lookback_sessions: int
    minimum_history: int
    scope: str
    price_basis: str
    null_policy: str
    staleness_policy: str
    direction: Direction
    transformation: str
    parameter_mode: str
    implementation_hash: str
    quality_requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        missing = [name for name, value in asdict(self).items()
                   if value in (None, "", ()) and name not in {"quality_requirements"}]
        if missing:
            raise ScoringError("INCOMPLETE_FEATURE_DEFINITION:" + ",".join(missing))
        if self.scope not in {"CROSS_SECTIONAL", "TIME_SERIES"}:
            raise ScoringError("UNKNOWN_FEATURE_SCOPE")
        if self.parameter_mode not in {"DETERMINISTIC", "TRAINING_FITTED"}:
            raise ScoringError("AMBIGUOUS_PARAMETER_MODE")


class FeatureRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        key = (definition.feature_id, definition.version)
        if key in self._items and self._items[key] != definition:
            raise ScoringError("FEATURE_MEANING_CHANGED_WITHOUT_VERSION")
        self._items[key] = definition

    def definitions(self) -> tuple[FeatureDefinition, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


@dataclass(frozen=True)
class TransformArtifact:
    transform_version: str
    fitted_through: pd.Timestamp
    lower: float
    upper: float
    mean: float
    scale: float
    training_row_count: int
    training_hash: str


def _hash_records(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def fit_winsor_standardize(values: pd.Series, *, fitted_through: pd.Timestamp,
                           training_mask: pd.Series,
                           observation_times: pd.Series | None = None) -> TransformArtifact:
    if len(values) != len(training_mask):
        raise ScoringError("TRANSFORM_MASK_LENGTH_MISMATCH")
    if observation_times is not None:
        times = pd.to_datetime(observation_times, utc=True)
        if (times[training_mask] > pd.Timestamp(fitted_through)).any():
            raise ScoringError("GLOBAL_WINSORIZATION_BEFORE_FOLD_SPLIT")
    train = pd.to_numeric(values[training_mask], errors="coerce").dropna()
    if len(train) < 4:
        raise ScoringError("INSUFFICIENT_TRANSFORM_TRAINING_ROWS")
    lower, upper = float(train.quantile(.05)), float(train.quantile(.95))
    clipped = train.clip(lower, upper)
    scale = float(clipped.std(ddof=0))
    if scale <= 0:
        raise ScoringError("ZERO_TRANSFORM_SCALE")
    return TransformArtifact("winsor_zscore_training_only_v1", pd.Timestamp(fitted_through),
                             lower, upper, float(clipped.mean()), scale, len(train),
                             _hash_records(train.tolist()))


def apply_transform(values: pd.Series, artifact: TransformArtifact) -> pd.Series:
    return (pd.to_numeric(values, errors="coerce").clip(artifact.lower, artifact.upper)
            - artifact.mean) / artifact.scale


def materialize_feature(raw: pd.DataFrame, definition: FeatureDefinition, *,
                        transform: TransformArtifact | None = None) -> pd.DataFrame:
    required = {"instrument_id", "decision_session_id", "decision_instant", "knowledge_cutoff",
                "input_snapshot_id", "calendar_version", "raw_feature_value", "available_at",
                "stale"}
    missing = required - set(raw)
    if missing:
        raise ScoringError("MISSING_FEATURE_INPUT_FIELDS:" + ",".join(sorted(missing)))
    frame = raw.copy()
    for column in ("decision_instant", "knowledge_cutoff", "available_at"):
        values = pd.to_datetime(frame[column], utc=True, errors="coerce")
        if values.isna().any():
            raise ScoringError("NAIVE_OR_INVALID_FEATURE_TIMESTAMP")
        frame[column] = values
    if (frame.available_at > frame.knowledge_cutoff).any():
        raise ScoringError("FEATURE_INPUT_AFTER_KNOWLEDGE_CUTOFF")
    if set(frame.calendar_version) != {definition.calendar_version}:
        raise ScoringError("FEATURE_CALENDAR_VERSION_MISMATCH")
    frame["value_state"] = np.where(frame.stale, "STALE", np.where(
        frame.raw_feature_value.isna(), "MISSING", "AVAILABLE"))
    if definition.null_policy == "REJECT" and frame.raw_feature_value.isna().any():
        raise ScoringError("MISSING_FEATURE_OUTSIDE_POLICY")
    if definition.staleness_policy == "REJECT" and frame.stale.any():
        raise ScoringError("STALE_FEATURE_OUTSIDE_POLICY")
    if definition.parameter_mode == "TRAINING_FITTED":
        if transform is None:
            raise ScoringError("MISSING_FITTED_TRANSFORM")
        frame["transformed_value"] = apply_transform(frame.raw_feature_value, transform)
        frame["fitted_through"] = transform.fitted_through
        frame["transformation_version"] = transform.transform_version
    else:
        frame["transformed_value"] = pd.to_numeric(frame.raw_feature_value, errors="coerce")
        frame["fitted_through"] = pd.NaT
        frame["transformation_version"] = definition.transformation
    frame.loc[frame.value_state != "AVAILABLE", "transformed_value"] = np.nan
    frame["feature_id"] = definition.feature_id
    frame["feature_version"] = definition.version
    frame["oriented_prediction"] = frame.transformed_value * (1 if definition.direction == Direction.POSITIVE else -1)
    frame["direction"] = definition.direction.value
    frame["implementation_hash"] = definition.implementation_hash
    frame["source_input_hash"] = frame.apply(lambda row: _hash_records({
        "snapshot": row.input_snapshot_id, "instrument": row.instrument_id,
        "session": row.decision_session_id, "raw": row.raw_feature_value}), axis=1)
    frame["quality_flags"] = frame.value_state.map(lambda state: "[]" if state == "AVAILABLE" else f'["{state}"]')
    return frame


def assert_transform_fit_before_validation(artifact: TransformArtifact,
                                           validation_start: pd.Timestamp) -> None:
    if artifact.fitted_through >= pd.Timestamp(validation_start):
        raise ScoringError("VALIDATION_FITTED_TRANSFORMATION")


@dataclass(frozen=True)
class PredictionDefinition:
    prediction_id: str
    version: str
    prediction_type: str
    direction: Direction
    horizon_sessions: int
    outcome_version: str
    training_cutoff: pd.Timestamp
    population_id: str
    units: str
    model_hash: str


@dataclass(frozen=True)
class PercentileCalibration:
    version: str
    population_id: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    horizon_sessions: int
    direction: Direction
    training_cutoff: pd.Timestamp
    tie_policy: str
    out_of_range_policy: str
    minimum_population: int
    oriented_training_values: tuple[float, ...]
    training_hash: str


def fit_percentile_calibration(values: pd.Series, *, population_id: str,
                               period_start: pd.Timestamp, period_end: pd.Timestamp,
                               training_cutoff: pd.Timestamp, direction: Direction,
                               minimum_population: int = 5,
                               observation_times: pd.Series | None = None) -> PercentileCalibration:
    if observation_times is not None and (
            pd.to_datetime(observation_times, utc=True) > pd.Timestamp(training_cutoff)).any():
        raise ScoringError("FULL_SAMPLE_PERCENTILE_CALIBRATION")
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if len(clean) < minimum_population:
        raise ScoringError("INSUFFICIENT_CALIBRATION_POPULATION")
    oriented = clean * (1 if direction == Direction.POSITIVE else -1)
    ordered = tuple(sorted(oriented.tolist()))
    return PercentileCalibration("percentile_score_v1", population_id,
                                 pd.Timestamp(period_start), pd.Timestamp(period_end), 21,
                                 direction, pd.Timestamp(training_cutoff), "AVERAGE_RANK",
                                 "CLIP_TO_0_100", minimum_population, ordered,
                                 _hash_records(ordered))


def percentile_score(raw_prediction: float | None, calibration: PercentileCalibration) -> tuple[str, float | None]:
    if raw_prediction is None or pd.isna(raw_prediction):
        return "UNAVAILABLE", None
    oriented = float(raw_prediction) * (1 if calibration.direction == Direction.POSITIVE else -1)
    train = np.asarray(calibration.oriented_training_values)
    less = int(np.sum(train < oriented))
    equal = int(np.sum(train == oriented))
    score = 100.0 * (less + .5 * equal) / len(train)
    return "AVAILABLE", float(np.clip(score, 0, 100))


@dataclass(frozen=True)
class OutcomeCalibration:
    version: str
    population_id: str
    training_cutoff: pd.Timestamp
    minimum_sample: int
    neighbors: int
    rows: tuple[tuple[float, float], ...]
    training_hash: str
    unresolved_count: int


def fit_outcome_calibration(predictions: pd.Series, outcomes: pd.Series, statuses: pd.Series, *,
                            population_id: str, training_cutoff: pd.Timestamp,
                            minimum_sample: int = 5, neighbors: int = 5,
                            observation_times: pd.Series | None = None) -> OutcomeCalibration:
    frame = pd.DataFrame({"prediction": predictions, "outcome": outcomes, "status": statuses})
    if observation_times is not None:
        frame["time"] = pd.to_datetime(observation_times, utc=True)
        if (frame.time > pd.Timestamp(training_cutoff)).any():
            raise ScoringError("HOLDOUT_FITTED_CALIBRATION")
    unresolved = int((frame.status != "RESOLVED").sum())
    frame = frame[(frame.status == "RESOLVED")].dropna(subset=["prediction", "outcome"])
    if len(frame) < minimum_sample:
        return OutcomeCalibration("neighbor_calibration_v1", population_id,
                                  pd.Timestamp(training_cutoff), minimum_sample, neighbors, (),
                                  _hash_records([]), unresolved)
    rows = tuple((float(row.prediction), float(row.outcome)) for row in
                 frame.sort_values(["prediction", "outcome"], kind="stable").itertuples())
    return OutcomeCalibration("neighbor_calibration_v1", population_id,
                              pd.Timestamp(training_cutoff), minimum_sample, neighbors, rows,
                              _hash_records(rows), unresolved)


def calibrated_outcome(prediction: float, calibration: OutcomeCalibration) -> dict[str, object]:
    if len(calibration.rows) < calibration.minimum_sample:
        return {"state": "UNAVAILABLE", "reason": "INSUFFICIENT_EVIDENCE", "sample_size": len(calibration.rows)}
    ordered = sorted(calibration.rows, key=lambda row: (abs(row[0] - prediction), row[0], row[1]))
    neighbors = np.asarray([row[1] for row in ordered[:calibration.neighbors]], dtype=float)
    n = len(neighbors)
    mean = float(neighbors.mean())
    se = float(neighbors.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    band = (mean - 1.96 * se, mean + 1.96 * se) if n > 1 else (None, None)
    return {"state": "AVAILABLE", "expected_outcome": mean,
            "expected_outcome_units": "SYNTHETIC_OUTCOME_UNITS",
            "expected_outcome_band": band,
            "positive_outcome_probability": float(np.mean(neighbors > 0)),
            "probability_definition": "P(SYNTHETIC_OUTCOME>0)_TRAINING_NEIGHBORS",
            "sample_size": n, "effective_sample_size": n,
            "calibration_method": calibration.version}


def component_evidence(frame: pd.DataFrame, feature_columns: Iterable[str], *, outcome: str) -> pd.DataFrame:
    rows = []
    clean = frame[frame.outcome_status == "RESOLVED"]
    for feature in feature_columns:
        pair = clean[[feature, outcome]].dropna()
        ic = float(stats.spearmanr(pair[feature], pair[outcome]).statistic) if len(pair) >= 3 else np.nan
        rows.append({"feature_id": feature, "sample_size": len(pair), "effective_sample_size": len(pair),
                     "rank_ic": ic, "missing_or_unresolved": len(frame) - len(pair),
                     "mean_synthetic_outcome": float(pair[outcome].mean()) if len(pair) else np.nan})
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class CombinationArtifact:
    version: str
    component_ids: tuple[str, ...]
    retained_ids: tuple[str, ...]
    dropped_redundant: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    training_cutoff: pd.Timestamp
    training_hash: str
    missing_policy: str = "REJECT_ROW"


def fit_linear_combination(features: pd.DataFrame, outcome: pd.Series, *,
                           training_mask: pd.Series, training_cutoff: pd.Timestamp,
                           observation_times: pd.Series | None = None) -> CombinationArtifact:
    if observation_times is not None:
        times = pd.to_datetime(observation_times, utc=True)
        if (times[training_mask] > pd.Timestamp(training_cutoff)).any():
            raise ScoringError("VALIDATION_FITTED_COMBINATION")
    train_x = features.loc[training_mask].copy()
    train_y = outcome.loc[training_mask]
    valid = train_x.notna().all(axis=1) & train_y.notna()
    train_x, train_y = train_x[valid], train_y[valid]
    if len(train_x) < len(train_x.columns) + 2:
        raise ScoringError("INSUFFICIENT_COMBINATION_TRAINING_ROWS")
    retained, redundant = [], []
    for column in train_x.columns:
        if any(abs(train_x[column].corr(train_x[other])) > .999999 for other in retained):
            redundant.append(column)
        else:
            retained.append(column)
    x = train_x[retained].to_numpy(float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients = np.linalg.lstsq(design, train_y.to_numpy(float), rcond=None)[0]
    return CombinationArtifact("synthetic_linear_combination_v1", tuple(features.columns),
                               tuple(retained), tuple(redundant), tuple(coefficients[1:]),
                               float(coefficients[0]), pd.Timestamp(training_cutoff),
                               _hash_records({"x": x.tolist(), "y": train_y.tolist()}))


def apply_combination(features: pd.DataFrame, artifact: CombinationArtifact) -> pd.Series:
    if any(column not in features for column in artifact.retained_ids):
        raise ScoringError("MISSING_COMBINATION_COMPONENT")
    x = features[list(artifact.retained_ids)]
    result = artifact.intercept + x.to_numpy(float) @ np.asarray(artifact.coefficients)
    return pd.Series(result, index=features.index).where(x.notna().all(axis=1))


def reject_score_average(*_: object) -> None:
    raise ScoringError("AVERAGING_COMPONENT_DISPLAY_SCORES_PROHIBITED")


def validate_semantic_assignment(field_name: str, source_semantic: str) -> None:
    expected = {
        "score_0_100": "ORIENTED_CALIBRATION_PERCENTILE",
        "expected_outcome": "EXPECTED_OUTCOME",
        "positive_outcome_probability": "POSITIVE_OUTCOME_PROBABILITY",
        "confidence": "CONFIDENCE_BAND",
    }
    if expected.get(field_name) != source_semantic:
        raise ScoringError("SEMANTIC_SUBSTITUTION_PROHIBITED")


def infer_direction_from_outcomes(*_: object) -> None:
    raise ScoringError("OUTCOME_LEAKAGE_INTO_FEATURE_DIRECTION")


def holm_correction(p_values: Mapping[str, float], alpha: float = .05) -> dict[str, dict[str, object]]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    result: dict[str, dict[str, object]] = {}
    still_rejecting = True
    for position, (name, p_value) in enumerate(ordered):
        threshold = alpha / (len(ordered) - position)
        reject = still_rejecting and p_value <= threshold
        if not reject:
            still_rejecting = False
        result[name] = {"p_value": p_value, "threshold": threshold, "reject": reject,
                        "method": "HOLM_V1"}
    return result


def validate_attempt_ledger(ledger: pd.DataFrame, expected_attempts: Iterable[str]) -> None:
    required = {"family_id", "family_version", "attempt_id", "classification", "primary_metric",
                "direction_hypothesis", "attempt_order", "result", "supersedes", "method_version",
                "lifecycle"}
    if required - set(ledger):
        raise ScoringError("INCOMPLETE_ATTEMPT_LEDGER")
    missing = set(expected_attempts) - set(ledger.attempt_id)
    if missing:
        raise ScoringError("DIAGNOSTIC_ATTEMPT_OMITTED")


def assess_confidence(*, sample_size: int, interval_width: float, fold_stable: bool,
                      coverage_broad: bool, fresh: bool, cost_robust: bool,
                      parameter_robust: bool, multiplicity_pass: bool,
                      decay_state: str) -> dict[str, object]:
    limits = []
    if sample_size < 30: limits.append("SMALL_EFFECTIVE_SAMPLE")
    if interval_width > 1.0: limits.append("WIDE_UNCERTAINTY_INTERVAL")
    if not fold_stable: limits.append("FOLD_INSTABILITY")
    if not coverage_broad: limits.append("NARROW_SYNTHETIC_COVERAGE")
    if not fresh: limits.append("STALE_OR_INCOMPLETE_DATA")
    if not cost_robust: limits.append("COST_SENSITIVITY")
    if not parameter_robust: limits.append("PARAMETER_SENSITIVITY")
    if not multiplicity_pass: limits.append("MULTIPLE_TESTING_BURDEN")
    if decay_state != "STABLE": limits.append("RECENT_DECAY")
    band = ConfidenceBand.HIGH if not limits else (ConfidenceBand.MODERATE if len(limits) <= 2 else ConfidenceBand.LOW)
    return {"confidence": band.value, "limiting_factors": limits,
            "uncertainty_interval_width": interval_width,
            "effective_sample_size": sample_size}


def transition_lifecycle(current: Lifecycle, requested: Lifecycle, *, synthetic: bool) -> Lifecycle:
    if synthetic and requested in {Lifecycle.VALIDATED_REAL_DATA, Lifecycle.ACTIVE}:
        raise ScoringError("SYNTHETIC_LIFECYCLE_PROMOTION_PROHIBITED")
    allowed = {
        Lifecycle.DRAFT: {Lifecycle.RESEARCHING, Lifecycle.REJECTED},
        Lifecycle.RESEARCHING: {Lifecycle.SYNTHETIC_VALIDATED_NONCANONICAL, Lifecycle.REJECTED},
        Lifecycle.SYNTHETIC_VALIDATED_NONCANONICAL: {Lifecycle.RETIRED},
        Lifecycle.REJECTED: {Lifecycle.RETIRED},
    }
    if requested not in allowed.get(current, set()):
        raise ScoringError("INVALID_LIFECYCLE_TRANSITION")
    return requested


@dataclass(frozen=True)
class AssetEvidenceSnapshot:
    instrument_id: str
    decision_instant: pd.Timestamp
    horizon_sessions: int
    raw_prediction: float
    score_0_100: float
    score_definition: str
    expected_outcome: float | None
    expected_outcome_band: tuple[float, float] | None
    positive_outcome_probability: float | None
    confidence: str
    limiting_factors: tuple[str, ...]
    component_evidence: tuple[dict, ...]
    lifecycle: str
    sample_size: int
    freshness: str
    risks: tuple[str, ...]
    provenance: tuple[str, ...]
    decision: str = "NO_DECISION"
    classification: str = "SYNTHETIC_ONLY_NONCANONICAL"

    def __post_init__(self) -> None:
        if self.decision != "NO_DECISION":
            raise ScoringError("SYNTHETIC_DECISION_PROHIBITED")
        if not 0 <= self.score_0_100 <= 100:
            raise ScoringError("SCORE_OUT_OF_BOUNDS")
        if "percentile" not in self.score_definition.lower():
            raise ScoringError("SCORE_SEMANTICS_MISSING")


class DisposableHoldout:
    def __init__(self, rows: pd.DataFrame, *, holdout_id: str, one_use: bool = True):
        self._rows = rows.copy(deep=True)
        self.holdout_id = holdout_id
        self.one_use = one_use
        self.access_log: list[dict[str, str]] = []

    def open(self, *, purpose: str) -> pd.DataFrame:
        if purpose != "DECLARED_SYNTHETIC_TEST_PATH":
            raise ScoringError("HOLDOUT_ACCESS_PROHIBITED")
        if self.one_use and self.access_log:
            raise ScoringError("HOLDOUT_REUSE_PROHIBITED")
        self.access_log.append({"holdout_id": self.holdout_id, "purpose": purpose,
                                "classification": "SYNTHETIC_ONLY_NONCANONICAL"})
        return self._rows.copy(deep=True)
