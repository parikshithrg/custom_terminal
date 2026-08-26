"""Small dependency-neutral evidence contracts for Research Reconciliation R.1.

This package intentionally imports neither ``dtest`` nor ``market_intel``.
Adapters may translate their artifacts into these contracts without making
either research system depend on the other's implementation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Iterable, Mapping, Any


CONTRACT_VERSION = "shared_research_contracts_v1"


class CapabilityStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class PopulationCapability(StrEnum):
    HISTORICALLY_TRADED = "historically_traded_population_reconstructible"
    HISTORICALLY_LISTED = "historically_listed_population_reconstructible"
    INACTIVE_SECURITY = "inactive_security_coverage"
    SUSPENSION_HISTORY = "suspension_history_available"
    TERMINAL_OUTCOMES = "terminal_outcomes_available"
    STABLE_IDENTITY = "stable_security_identity_verified"


@dataclass(frozen=True)
class PopulationCapabilityAssessment:
    capability: PopulationCapability
    status: CapabilityStatus
    scope: str
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.scope.strip() or not self.evidence_refs:
            raise ValueError("population assessments require scope and evidence")


class EvidenceStage(StrEnum):
    OBSERVED_PREV_CLOSE = "EXCHANGE_PREV_CLOSE_OBSERVED"
    DISCONTINUITY_CANDIDATE = "ISOLATED_DISCONTINUITY_CANDIDATE"
    MARKET_WIDE_REJECTED = "MARKET_WIDE_INCONSISTENCY_REJECTED"
    FACTOR_DERIVED = "ADJUSTMENT_FACTOR_DERIVED"
    ACTION_TYPE_VERIFIED = "CORPORATE_ACTION_TYPE_VERIFIED"
    RATIO_VERIFIED = "RATIO_VERIFIED_AUTHORITATIVELY"
    DIVIDEND_INCLUSIVE = "DIVIDEND_INCLUSIVE_RETURN_AVAILABLE"
    AUTHORITATIVE_LINKED = "AUTHORITATIVE_ACTION_RECORD_LINKED"


@dataclass(frozen=True)
class CorporateActionEvidence:
    instrument_reference: str
    event_date: str
    stages: frozenset[EvidenceStage]
    raw_price_series_preserved: bool
    authoritative_evidence_ref: str | None = None
    adjustment_factor: float | None = None
    action_type: str | None = None
    version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.raw_price_series_preserved:
            raise ValueError("raw prices must remain preserved")
        verified = {EvidenceStage.ACTION_TYPE_VERIFIED, EvidenceStage.RATIO_VERIFIED,
                    EvidenceStage.AUTHORITATIVE_LINKED}
        if self.stages & verified and not self.authoritative_evidence_ref:
            raise ValueError("verified corporate-action claims require authoritative evidence")
        if EvidenceStage.FACTOR_DERIVED in self.stages and self.adjustment_factor is None:
            raise ValueError("a derived-factor stage requires the factor")
        if EvidenceStage.ACTION_TYPE_VERIFIED in self.stages and not self.action_type:
            raise ValueError("verified action type must be explicit")


class TerminalClassification(StrEnum):
    ORDINARY_MISSING_OBSERVATION = "ORDINARY_MISSING_OBSERVATION"
    TEMPORARY_SUSPENSION = "TEMPORARY_SUSPENSION"
    PERMANENT_DELISTING = "PERMANENT_DELISTING"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    DEMERGER = "DEMERGER"
    SYMBOL_OR_ISIN_TRANSITION = "SYMBOL_OR_ISIN_TRANSITION"
    SOURCE_FAILURE = "SOURCE_FAILURE"
    UNRESOLVED_DISAPPEARANCE = "UNRESOLVED_DISAPPEARANCE"


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class TerminalOutcome:
    instrument_reference: str
    classification: TerminalClassification
    status: ResolutionStatus
    event_date: str | None = None
    final_tradable_price: float | None = None
    cash_consideration: float | None = None
    successor_instrument_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        unresolved_classes = {
            TerminalClassification.ORDINARY_MISSING_OBSERVATION,
            TerminalClassification.SOURCE_FAILURE,
            TerminalClassification.UNRESOLVED_DISAPPEARANCE,
        }
        if self.classification in unresolved_classes and self.status is ResolutionStatus.RESOLVED:
            raise ValueError("missing/source-failure observations cannot be resolved as terminal economics")
        if self.status is ResolutionStatus.RESOLVED and not self.evidence_refs:
            raise ValueError("resolved terminal economics require authoritative evidence")
        if self.status is ResolutionStatus.UNRESOLVED and (
            self.cash_consideration is not None or self.successor_instrument_id is not None
        ):
            raise ValueError("unresolved terminal outcomes cannot assert consideration or successor")


class LegacyLifecycle(StrEnum):
    PROPOSED = "PROPOSED"
    PREREGISTERED = "PREREGISTERED"
    TRAIN_REJECTED = "TRAIN_REJECTED"
    TRAIN_PROMOTED = "TRAIN_PROMOTED"
    VALIDATION_REJECTED = "VALIDATION_REJECTED"
    VALIDATION_CONFIRMED = "VALIDATION_CONFIRMED"
    TEST_REJECTED = "TEST_REJECTED"
    TEST_CONFIRMED = "TEST_CONFIRMED"
    REPLICATION_FAILED = "REPLICATION_FAILED"
    REPLICATION_CONFIRMED = "REPLICATION_CONFIRMED"
    PRODUCTION_INELIGIBLE = "PRODUCTION_INELIGIBLE"
    UNRESOLVED_LEGACY_STATE = "UNRESOLVED_LEGACY_STATE"


def map_legacy_lifecycle(window: str, decision: str) -> LegacyLifecycle:
    """Map one old log row without claiming more than that row proves."""
    mapping = {
        ("train", "accepted"): LegacyLifecycle.TRAIN_PROMOTED,
        ("train", "rejected"): LegacyLifecycle.TRAIN_REJECTED,
        ("val", "accepted"): LegacyLifecycle.VALIDATION_CONFIRMED,
        ("val", "rejected"): LegacyLifecycle.VALIDATION_REJECTED,
        ("test", "accepted"): LegacyLifecycle.TEST_CONFIRMED,
        ("test", "rejected"): LegacyLifecycle.TEST_REJECTED,
    }
    return mapping.get((str(window).lower(), str(decision).lower()),
                       LegacyLifecycle.UNRESOLVED_LEGACY_STATE)


def reconcile_legacy_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Return a non-mutating reconciliation view over append-only legacy rows."""
    reconciled = []
    for row in rows:
        reconciled.append({
            "hypothesis_id": row.get("hypothesis_id"),
            "title": row.get("title"),
            "split": row.get("split"),
            "window": row.get("window"),
            "legacy_decision": row.get("decision"),
            "lifecycle": map_legacy_lifecycle(
                str(row.get("window", "")), str(row.get("decision", ""))
            ).value,
            "mapping_version": CONTRACT_VERSION,
            "production_eligible": False,
        })
    return tuple(reconciled)


@dataclass(frozen=True)
class HypothesisContract:
    hypothesis_id: str
    version: str
    economic_story: str
    selection_rule: str
    decision_clock: str
    entry_rule: str
    holding_horizon_sessions: int
    exit_overlay: str
    cost_schedule_version: str
    portfolio_construction: str
    research_split: str
    research_status: str
    experiment_family_id: str

    def __post_init__(self) -> None:
        required = asdict(self)
        if any(not str(value).strip() for key, value in required.items()
               if key != "holding_horizon_sessions"):
            raise ValueError("hypothesis contract fields cannot be blank")
        if self.holding_horizon_sessions < 1:
            raise ValueError("holding horizon must be positive")
        if self.research_status not in {"EXPLORATORY", "DIAGNOSTIC", "CONFIRMATORY"}:
            raise ValueError("research status must distinguish exploratory/diagnostic/confirmatory")
