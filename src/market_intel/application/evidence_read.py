"""Thin read-only facade over validated synthetic publication bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from types import MappingProxyType

from market_intel.evidence.publication import (
    IndexEntry, PublicationError, PublicationIndex, SYNTHETIC_CLASSIFICATION,
    validate_identifier,
)


@dataclass(frozen=True)
class SnapshotSummary:
    snapshot_id: str
    snapshot_version: str
    instrument_id: str
    horizon_sessions: int
    lifecycle: str
    freshness: str
    classification: str
    decision: str


@dataclass(frozen=True)
class PresentationSafeSnapshot:
    warning_banner: str
    snapshot_id: str
    instrument_id: str
    score_0_100: float
    score_definition: str
    expected_outcome: float | None
    expected_outcome_units: str | None
    expected_outcome_interval: tuple | None
    expected_outcome_unavailable_reason: str | None
    positive_outcome_probability: float | None
    probability_definition: str | None
    probability_unavailable_reason: str | None
    confidence: str
    confidence_limiting_factors: tuple
    lifecycle: str
    freshness: str
    component_evidence: tuple
    decision: str
    decision_reason: str
    provenance_artifact_ids: tuple


class EvidenceReadFacade:
    """No calculation, fitting, lifecycle mutation, provider or write methods."""

    MAX_PAGE_SIZE = 50

    def __init__(self, index: PublicationIndex):
        self._index = index

    def list_snapshots(self, *, instrument_id: str, edge_family_version: str,
                       offset: int = 0, limit: int = 20) -> tuple[SnapshotSummary, ...]:
        validate_identifier(instrument_id, "instrument_id")
        validate_identifier(edge_family_version, "edge_family_version")
        if offset < 0 or limit < 1 or limit > self.MAX_PAGE_SIZE:
            raise PublicationError("INVALID_PAGINATION")
        history = self._index.history(instrument_id, edge_family_version)[offset:offset + limit]
        return tuple(SnapshotSummary(item.snapshot_id, item.snapshot_version, item.instrument_id,
                                     item.horizon_sessions, item.lifecycle, item.freshness,
                                     item.classification, item.decision) for item in history)

    def get_exact(self, *, instrument_id: str, edge_family_version: str,
                  snapshot_id: str, snapshot_version: str) -> PresentationSafeSnapshot:
        for value, field in ((instrument_id, "instrument_id"),
                             (edge_family_version, "edge_family_version"),
                             (snapshot_id, "snapshot_id"), (snapshot_version, "snapshot_version")):
            validate_identifier(value, field)
        matches = [item for item in self._index.history(instrument_id, edge_family_version)
                   if item.snapshot_id == snapshot_id and item.snapshot_version == snapshot_version]
        if len(matches) != 1:
            raise PublicationError("SNAPSHOT_NOT_FOUND")
        return self._read(matches[0])

    def get_latest(self, *, instrument_id: str, horizon_sessions: int,
                   edge_family_version: str) -> PresentationSafeSnapshot:
        validate_identifier(instrument_id, "instrument_id")
        validate_identifier(edge_family_version, "edge_family_version")
        if horizon_sessions < 1 or horizon_sessions > 10_000:
            raise PublicationError("INVALID_HORIZON")
        return self._read(self._index.latest(instrument_id, horizon_sessions, edge_family_version))

    def _read(self, entry: IndexEntry) -> PresentationSafeSnapshot:
        self._index.publisher.verify(entry.bundle)
        bundle_path = self._index.publisher.root / entry.bundle.relative_path
        raw = json.loads((bundle_path / "snapshot.json").read_text(encoding="utf-8"))
        policy = json.loads((bundle_path / "publication_policy.json").read_text(encoding="utf-8"))
        freshness = json.loads((bundle_path / "freshness.json").read_text(encoding="utf-8"))
        if entry.classification != SYNTHETIC_CLASSIFICATION or raw["classification"] != SYNTHETIC_CLASSIFICATION:
            raise PublicationError("READ_MODEL_CLASSIFICATION_MISMATCH")
        if raw["decision"] != "NO_DECISION":
            raise PublicationError("READ_MODEL_DECISION_MISMATCH")
        reason = "SYNTHETIC_NONCANONICAL_EVIDENCE"
        if freshness["status"] not in {"CURRENT", "AGING"}:
            reason = "STALE_EVIDENCE"
        if policy["rejected"]:
            reason = policy["reasons"][0]
        components = tuple(MappingProxyType(dict(item)) for item in raw["component_evidence"])
        return PresentationSafeSnapshot(
            "SYNTHETIC ENGINEERING EVIDENCE — NOT LIVE, NOT A RECOMMENDATION",
            raw["snapshot_id"], raw["instrument_id"], raw["score_0_100"],
            raw["score_definition"], raw["expected_outcome"], raw["expected_outcome_units"],
            None if raw["expected_outcome_interval"] is None else tuple(raw["expected_outcome_interval"]),
            raw["expected_outcome_unavailable_reason"], raw["positive_outcome_probability"],
            raw["probability_definition"], raw["probability_unavailable_reason"],
            raw["confidence"], tuple(raw["confidence_limiting_factors"]), raw["lifecycle"],
            freshness["status"], components, "NO_DECISION", reason,
            tuple(reference["artifact_id"] for reference in raw["artifact_references"]),
        )

    def query_sql(self, *_: object, **__: object) -> None:
        raise PublicationError("ARBITRARY_SQL_PROHIBITED")

    def open_path(self, *_: object, **__: object) -> None:
        raise PublicationError("ARBITRARY_FILESYSTEM_PATH_PROHIBITED")

    def write(self, *_: object, **__: object) -> None:
        raise PublicationError("READ_ONLY_FACADE_WRITE_PROHIBITED")
