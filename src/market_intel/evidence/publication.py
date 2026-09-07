"""Immutable synthetic evidence publication contracts and storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Mapping

import pandas as pd


SNAPSHOT_SCHEMA_VERSION = "asset_evidence_publication_r10f_v1"
PUBLICATION_POLICY_VERSION = "synthetic_publication_policy_r10f_v1"
FRESHNESS_POLICY_VERSION = "synthetic_freshness_policy_r10f_v1"
PRESENTATION_SCHEMA_VERSION = "synthetic_evidence_read_model_r10f_v1"
SYNTHETIC_CLASSIFICATION = "SYNTHETIC_ONLY_NONCANONICAL"


class PublicationError(ValueError):
    pass


class FreshnessStatus(StrEnum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    DATA_BLOCKED = "DATA_BLOCKED"
    CALENDAR_UNKNOWN = "CALENDAR_UNKNOWN"
    NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"


@dataclass(frozen=True)
class ArtifactReference:
    artifact_id: str
    relative_path: str
    sha256: str
    role: str
    version: str


@dataclass(frozen=True)
class PublishedAssetEvidenceSnapshot:
    schema_version: str
    snapshot_id: str
    snapshot_version: str
    classification: str
    canonical: bool
    promotion_eligible: bool
    instrument_id: str
    listing_id: str
    decision_session_id: str
    decision_instant: pd.Timestamp
    knowledge_cutoff: pd.Timestamp
    horizon_sessions: int
    outcome_version: str
    raw_prediction: float
    score_0_100: float
    score_definition: str
    calibration_version: str
    calibration_population_id: str
    calibration_fitted_through: pd.Timestamp
    expected_outcome: float | None
    expected_outcome_units: str | None
    expected_outcome_interval: tuple[float, float] | None
    expected_outcome_unavailable_reason: str | None
    positive_outcome_probability: float | None
    probability_definition: str | None
    probability_unavailable_reason: str | None
    confidence: str
    confidence_limiting_factors: tuple[str, ...]
    component_evidence: tuple[dict, ...]
    edge_family_version: str
    lifecycle: str
    sample_size: int
    effective_sample_size: int
    freshness_status: str
    data_quality_status: str
    risks: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    decision: str
    artifact_references: tuple[ArtifactReference, ...]
    publication_manifest_reference: str | None
    created_from_run_id: str
    supersedes_snapshot_id: str | None = None


def _stamp(value: object, field: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise PublicationError(f"NAIVE_TIMESTAMP:{field}")
    return stamp.tz_convert("UTC")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), default=str,
                       allow_nan=False) + "\n").encode()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def validate_snapshot(snapshot: PublishedAssetEvidenceSnapshot, *, artifact_root: Path) -> None:
    if snapshot.schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise PublicationError("UNKNOWN_SNAPSHOT_SCHEMA_VERSION")
    if not 0 <= snapshot.score_0_100 <= 100:
        raise PublicationError("SCORE_OUT_OF_BOUNDS")
    if "percentile" not in snapshot.score_definition.lower() or "probability" in snapshot.score_definition.lower().replace("not probability", ""):
        raise PublicationError("AMBIGUOUS_SCORE_DEFINITION")
    if snapshot.positive_outcome_probability is not None and not 0 <= snapshot.positive_outcome_probability <= 1:
        raise PublicationError("PROBABILITY_OUT_OF_BOUNDS")
    if snapshot.expected_outcome is None:
        if not snapshot.expected_outcome_unavailable_reason:
            raise PublicationError("EXPECTED_OUTCOME_MISSING_REASON")
    elif not snapshot.expected_outcome_units or snapshot.expected_outcome_interval is None:
        raise PublicationError("EXPECTED_OUTCOME_SEMANTICS_INCOMPLETE")
    if snapshot.positive_outcome_probability is None:
        if not snapshot.probability_unavailable_reason:
            raise PublicationError("PROBABILITY_MISSING_REASON")
    elif not snapshot.probability_definition:
        raise PublicationError("PROBABILITY_DEFINITION_MISSING")
    if snapshot.confidence not in {"LOW", "MODERATE", "HIGH"}:
        raise PublicationError("INVALID_CONFIDENCE_CATEGORY")
    if not snapshot.confidence_limiting_factors:
        raise PublicationError("CONFIDENCE_LIMITING_FACTORS_MISSING")
    if snapshot.sample_size < 0 or snapshot.effective_sample_size < 0 or snapshot.effective_sample_size > snapshot.sample_size:
        raise PublicationError("INVALID_SAMPLE_SIZE")
    decision = _stamp(snapshot.decision_instant, "decision_instant")
    cutoff = _stamp(snapshot.knowledge_cutoff, "knowledge_cutoff")
    fitted = _stamp(snapshot.calibration_fitted_through, "calibration_fitted_through")
    if decision > cutoff:
        raise PublicationError("DECISION_AFTER_KNOWLEDGE_CUTOFF")
    if fitted > cutoff:
        raise PublicationError("CALIBRATION_AFTER_DECISION_CUTOFF")
    if snapshot.classification == SYNTHETIC_CLASSIFICATION:
        if snapshot.canonical:
            raise PublicationError("SYNTHETIC_MARKED_CANONICAL")
        if snapshot.promotion_eligible:
            raise PublicationError("NONCANONICAL_MARKED_PROMOTION_ELIGIBLE")
        if snapshot.decision != "NO_DECISION":
            raise PublicationError("SYNTHETIC_NON_NO_DECISION")
        if snapshot.lifecycle in {"VALIDATED_REAL_DATA", "ACTIVE"}:
            raise PublicationError("SYNTHETIC_LIFECYCLE_ACTIVE")
    if not snapshot.component_evidence:
        raise PublicationError("COMPONENT_EVIDENCE_MISSING")
    component_versions = {str(item.get("edge_family_version")) for item in snapshot.component_evidence}
    if component_versions != {snapshot.edge_family_version}:
        raise PublicationError("COMPONENT_VERSION_MISMATCH")
    root = Path(artifact_root).resolve()
    for reference in snapshot.artifact_references:
        candidate = (root / reference.relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise PublicationError("PATH_TRAVERSAL_REJECTED") from exc
        if not candidate.is_file():
            raise PublicationError("MISSING_COMPONENT_ARTIFACT")
        if _sha_file(candidate) != reference.sha256:
            raise PublicationError("ARTIFACT_HASH_MISMATCH")


@dataclass(frozen=True)
class FreshnessPolicy:
    version: str = FRESHNESS_POLICY_VERSION
    current_minutes: int = 60
    aging_minutes: int = 180


def assess_freshness(snapshot: PublishedAssetEvidenceSnapshot, *, evaluation_instant: pd.Timestamp,
                     policy: FreshnessPolicy, superseded: bool = False,
                     data_blocked: bool = False, calendar_known: bool = True,
                     available_at: pd.Timestamp | None = None,
                     correction_available_at: pd.Timestamp | None = None) -> dict[str, str]:
    now = _stamp(evaluation_instant, "evaluation_instant")
    cutoff = _stamp(snapshot.knowledge_cutoff, "knowledge_cutoff")
    if superseded:
        status, reason = FreshnessStatus.SUPERSEDED, "EXPLICIT_SUPERSESSION"
    elif data_blocked:
        status, reason = FreshnessStatus.DATA_BLOCKED, "DATA_QUALITY_BLOCKED"
    elif not calendar_known:
        status, reason = FreshnessStatus.CALENDAR_UNKNOWN, "CALENDAR_VERSION_UNAVAILABLE"
    elif available_at is not None and now < _stamp(available_at, "available_at"):
        status, reason = FreshnessStatus.NOT_YET_AVAILABLE, "EVALUATION_BEFORE_PUBLICATION"
    elif correction_available_at is not None and now >= _stamp(correction_available_at, "correction_available_at"):
        status, reason = FreshnessStatus.STALE, "LATER_CORRECTION_AVAILABLE"
    else:
        age = (now - cutoff).total_seconds() / 60
        if age < 0:
            status, reason = FreshnessStatus.NOT_YET_AVAILABLE, "EVALUATION_BEFORE_KNOWLEDGE_CUTOFF"
        elif age <= policy.current_minutes:
            status, reason = FreshnessStatus.CURRENT, "WITHIN_CURRENT_BOUNDARY"
        elif age <= policy.aging_minutes:
            status, reason = FreshnessStatus.AGING, "BEYOND_CURRENT_BOUNDARY"
        else:
            status, reason = FreshnessStatus.STALE, "BEYOND_STALE_BOUNDARY"
    if snapshot.lifecycle in {"RETIRED", "SUSPENDED"} and status == FreshnessStatus.CURRENT:
        status, reason = FreshnessStatus.STALE, "EDGE_NOT_CURRENT"
    return {"policy_version": policy.version, "status": status.value, "reason": reason,
            "evaluation_instant": now.isoformat()}


def decision_gate(snapshot: PublishedAssetEvidenceSnapshot, *, provenance_valid: bool = True,
                  multiple_testing_pass: bool = True, calibration_available: bool = True,
                  unresolved_terminal: bool = False, confidence_allowed: bool = True) -> dict[str, str]:
    if snapshot.classification == SYNTHETIC_CLASSIFICATION:
        return {"decision": "NO_DECISION", "reason": "SYNTHETIC_NONCANONICAL_EVIDENCE"}
    conditions = [
        (not provenance_valid, "PROVENANCE_MISMATCH"),
        (snapshot.freshness_status not in {"CURRENT", "AGING"}, "STALE_EVIDENCE"),
        (snapshot.data_quality_status != "PASS", "DATA_QUALITY_BLOCKED"),
        (snapshot.lifecycle != "ACTIVE", "EDGE_NOT_ACTIVE"),
        (not confidence_allowed, "CONFIDENCE_BELOW_POLICY"),
        (unresolved_terminal, "UNRESOLVED_TERMINAL_ECONOMICS"),
        (not calibration_available, "CALIBRATION_UNAVAILABLE"),
        (not multiple_testing_pass, "MULTIPLE_TESTING_GATE_FAILED"),
    ]
    reason = next((name for failed, name in conditions if failed), "DECISION_POLICIES_NOT_IMPLEMENTED")
    return {"decision": "NO_DECISION", "reason": reason}


def publication_policy(snapshot: PublishedAssetEvidenceSnapshot, *, provenance_valid: bool,
                       freshness: Mapping[str, str], source_run_confirmatory: bool = True,
                       terminal_accounting_complete: bool = True) -> dict[str, object]:
    rejected = []
    if not provenance_valid: rejected.append("PROVENANCE_MISMATCH")
    if freshness["status"] in {"STALE", "DATA_BLOCKED", "CALENDAR_UNKNOWN", "NOT_YET_AVAILABLE"}:
        rejected.append("FRESHNESS_OR_DATA_GATE_FAILED")
    if snapshot.data_quality_status != "PASS": rejected.append("DATASET_QUALITY_BLOCKED")
    if not source_run_confirmatory: rejected.append("DIAGNOSTIC_PRESENTED_AS_CONFIRMATORY")
    if not terminal_accounting_complete: rejected.append("TERMINAL_OUTCOMES_OMITTED")
    return {"policy_version": PUBLICATION_POLICY_VERSION,
            "synthetic_engineering_display": not rejected and snapshot.classification == SYNTHETIC_CLASSIFICATION,
            "internal_diagnostic_inspection": provenance_valid,
            "future_canonical_publication": False,
            "decision_support": False,
            "rejected": bool(rejected), "reasons": rejected}


@dataclass(frozen=True)
class PublishedBundle:
    bundle_hash: str
    relative_path: str
    snapshot_id: str
    snapshot_version: str
    manifest_hash: str


class ImmutableBundlePublisher:
    """Atomic, content-addressed publication with an identity conflict ledger."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._identities: dict[tuple[str, str], str] = {}

    def publish(self, snapshot: PublishedAssetEvidenceSnapshot, *, artifact_root: Path,
                freshness: dict[str, str], policy: dict[str, object], fail_at: str | None = None) -> PublishedBundle:
        validate_snapshot(snapshot, artifact_root=artifact_root)
        payloads = {
            "snapshot.json": _canonical(asdict(snapshot)),
            "components.json": _canonical(snapshot.component_evidence),
            "lifecycle.json": _canonical({"lifecycle": snapshot.lifecycle, "promotion_eligible": False}),
            "freshness.json": _canonical(freshness),
            "publication_policy.json": _canonical(policy),
        }
        object_hashes = {name: _sha_bytes(payload) for name, payload in payloads.items()}
        bundle_hash = _sha_bytes(_canonical({"identity": [snapshot.snapshot_id, snapshot.snapshot_version],
                                             "objects": object_hashes}))
        identity = (snapshot.snapshot_id, snapshot.snapshot_version)
        existing = self._identities.get(identity)
        if existing is not None and existing != bundle_hash:
            raise PublicationError("IMMUTABLE_PUBLICATION_IDENTITY_CONFLICT")
        target = self.root / "bundles" / bundle_hash
        if target.exists():
            manifest = target / "root_manifest.json"
            if not manifest.is_file() or _sha_file(manifest) == "":
                raise PublicationError("PARTIAL_PUBLICATION_BUNDLE")
            self._identities[identity] = bundle_hash
            return PublishedBundle(bundle_hash, str(target.relative_to(self.root)).replace("\\", "/"),
                                   *identity, _sha_file(manifest))
        stage = self.root / ".staging" / bundle_hash
        if stage.exists(): shutil.rmtree(stage)
        stage.mkdir(parents=True)
        try:
            for position, (name, payload) in enumerate(sorted(payloads.items())):
                (stage / name).write_bytes(payload)
                if fail_at == f"after_{position}":
                    raise PublicationError("INJECTED_PUBLICATION_INTERRUPTION")
            manifest_value = {"schema_version": "evidence_bundle_manifest_r10f_v1",
                              "bundle_hash": bundle_hash, "snapshot_id": snapshot.snapshot_id,
                              "snapshot_version": snapshot.snapshot_version,
                              "objects": object_hashes, "source_run": snapshot.created_from_run_id}
            (stage / "root_manifest.json").write_bytes(_canonical(manifest_value))
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, target)
            self._identities[identity] = bundle_hash
            return PublishedBundle(bundle_hash, str(target.relative_to(self.root)).replace("\\", "/"),
                                   *identity, _sha_file(target / "root_manifest.json"))
        except BaseException:
            if stage.exists(): shutil.rmtree(stage)
            raise

    def verify(self, bundle: PublishedBundle) -> bool:
        target = (self.root / bundle.relative_path).resolve()
        try: target.relative_to(self.root.resolve())
        except ValueError: raise PublicationError("PATH_TRAVERSAL_REJECTED")
        manifest_path = target / "root_manifest.json"
        if not manifest_path.is_file() or _sha_file(manifest_path) != bundle.manifest_hash:
            raise PublicationError("PUBLICATION_MANIFEST_MISMATCH")
        manifest = json.loads(manifest_path.read_text())
        for name, digest in manifest["objects"].items():
            if not (target / name).is_file() or _sha_file(target / name) != digest:
                raise PublicationError("PUBLISHED_OBJECT_HASH_MISMATCH")
        return True


@dataclass(frozen=True)
class IndexEntry:
    snapshot_id: str
    snapshot_version: str
    instrument_id: str
    horizon_sessions: int
    edge_family_version: str
    bundle: PublishedBundle
    lifecycle: str
    freshness: str
    classification: str
    decision: str
    supersedes_snapshot_id: str | None
    decision_instant: str
    valid: bool = True


class PublicationIndex:
    def __init__(self, publisher: ImmutableBundlePublisher):
        self.publisher = publisher
        self._entries: list[IndexEntry] = []

    def add(self, entry: IndexEntry) -> None:
        if not self.publisher.verify(entry.bundle):
            raise PublicationError("INVALID_BUNDLE_POINTER")
        if any(item.snapshot_id == entry.snapshot_id and item.snapshot_version == entry.snapshot_version
               and item.bundle.bundle_hash != entry.bundle.bundle_hash for item in self._entries):
            raise PublicationError("CONFLICTING_INDEX_IDENTITY")
        self._entries.append(entry)
        try:
            self._assert_acyclic()
        except BaseException:
            self._entries.pop()
            raise

    def _assert_acyclic(self) -> None:
        parents = {item.snapshot_id: item.supersedes_snapshot_id for item in self._entries}
        for start in parents:
            seen, current = set(), start
            while current:
                if current in seen: raise PublicationError("SUPERSESSION_CYCLE")
                seen.add(current); current = parents.get(current)

    def history(self, instrument_id: str, edge_family_version: str) -> tuple[IndexEntry, ...]:
        return tuple(sorted((item for item in self._entries if item.instrument_id == instrument_id
                            and item.edge_family_version == edge_family_version and item.valid),
                            key=lambda item: (item.decision_instant, item.snapshot_version), reverse=True))

    def latest(self, instrument_id: str, horizon_sessions: int,
               edge_family_version: str) -> IndexEntry:
        candidates = [item for item in self.history(instrument_id, edge_family_version)
                      if item.horizon_sessions == horizon_sessions
                      and item.freshness in {"CURRENT", "AGING"}
                      and item.lifecycle not in {"SUSPENDED", "RETIRED", "REJECTED"}]
        if not candidates: raise PublicationError("SNAPSHOT_NOT_FOUND")
        for item in candidates:
            self.publisher.verify(item.bundle)
        return candidates[0]


def validate_identifier(value: str, field: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value):
        raise PublicationError(f"INVALID_TYPED_IDENTIFIER:{field}")
    return value
