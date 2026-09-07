"""Predeclared deterministic mandate and portfolio constraint policy."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

import pandas as pd

from market_intel.evidence.publication import PublishedAssetEvidenceSnapshot

from .accounting import PortfolioMetrics, qquantity
from .contracts import (
    CLASSIFICATION, POLICY_VERSION, ConstraintResult, ConstraintStatus, ExternalDecision,
    Mandate, PolicyEvaluation, PortfolioSnapshot,
)


CONFIDENCE_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
CONSTRAINT_ORDER = (
    "IDENTITY", "TIMING", "HORIZON_COMPATIBILITY", "LIFECYCLE", "FRESHNESS", "CONFIDENCE",
    "DATA_QUALITY", "CALIBRATION", "UNIVERSE", "POSITION_LIMIT", "GROSS_EXPOSURE",
    "NET_EXPOSURE", "MAXIMUM_NAMES", "SECTOR_LIMIT", "CASH_BUFFER", "TURNOVER", "LIQUIDITY",
    "SETTLEMENT_AVAILABILITY", "MISSING_VALUATION", "UNRESOLVED_TERMINAL_ECONOMICS",
    "REBALANCE_CADENCE", "PROVENANCE",
)


def _result(name: str, status: ConstraintStatus, observed: object = None,
            limit: object = None, reason: str = "") -> ConstraintResult:
    return ConstraintResult(name, status, None if observed is None else str(observed),
                            None if limit is None else str(limit), reason or status.value)


def evaluate_policy(*, evidence: PublishedAssetEvidenceSnapshot, portfolio: PortfolioSnapshot,
                    mandate: Mandate, metrics: PortfolioMetrics, proposed_turnover: Decimal,
                    proposed_weight: Decimal, liquidity: Decimal | None,
                    last_rebalance_session_ordinal: int, current_session_ordinal: int,
                    provenance_valid: bool = True, terminal_resolved: bool = True,
                    settlement_available: bool = True) -> PolicyEvaluation:
    """Evaluate every constraint in fixed order; never emits an external action."""
    holding = next((x for x in portfolio.holdings if x.instrument_id == evidence.instrument_id), None)
    current_weight = Decimal(0) if holding is None else Decimal(str(metrics.position_weights.get(
        evidence.instrument_id) or 0))
    active_names = sum(x.quantity > 0 for x in portfolio.holdings)
    cash_ratio = (Decimal(0) if metrics.partial_total_value == 0 else
                  portfolio.cash.settled / metrics.partial_total_value)
    checks: dict[str, ConstraintResult] = {}
    checks["IDENTITY"] = _result("IDENTITY", ConstraintStatus.PASS if (
        holding is None or holding.listing_id == evidence.listing_id) else ConstraintStatus.BLOCK,
        evidence.listing_id, None, "IDENTITY_MATCH" if holding is None or holding.listing_id == evidence.listing_id
        else "MISMATCHED_INSTRUMENT_IDENTITY")
    timing_ok = (pd.Timestamp(evidence.decision_instant) <= portfolio.valuation_instant
                 and pd.Timestamp(evidence.knowledge_cutoff) <= portfolio.knowledge_cutoff)
    checks["TIMING"] = _result("TIMING", ConstraintStatus.PASS if timing_ok else ConstraintStatus.BLOCK,
        evidence.decision_instant, portfolio.valuation_instant,
        "POINT_IN_TIME_COMPATIBLE" if timing_ok else "EVIDENCE_AFTER_PORTFOLIO_CUTOFF")
    horizon_ok = evidence.horizon_sessions in mandate.permitted_evidence_horizons
    checks["HORIZON_COMPATIBILITY"] = _result("HORIZON_COMPATIBILITY",
        ConstraintStatus.PASS if horizon_ok else ConstraintStatus.BLOCK,
        evidence.horizon_sessions, sorted(mandate.permitted_evidence_horizons),
        "HORIZON_COMPATIBLE" if horizon_ok else "EVIDENCE_MANDATE_HORIZON_MISMATCH")
    lifecycle_ok = evidence.lifecycle in mandate.permitted_lifecycle_states
    checks["LIFECYCLE"] = _result("LIFECYCLE", ConstraintStatus.PASS if lifecycle_ok else ConstraintStatus.BLOCK,
        evidence.lifecycle, sorted(mandate.permitted_lifecycle_states), "LIFECYCLE_PERMITTED" if lifecycle_ok else "EDGE_NOT_ACTIVE")
    fresh_ok = evidence.freshness_status in {"CURRENT", "AGING"} or mandate.stale_evidence_policy == "ALLOW_DIAGNOSTIC"
    checks["FRESHNESS"] = _result("FRESHNESS", ConstraintStatus.PASS if fresh_ok else ConstraintStatus.BLOCK,
        evidence.freshness_status, mandate.stale_evidence_policy, "FRESHNESS_PERMITTED" if fresh_ok else "STALE_EVIDENCE")
    confidence_ok = CONFIDENCE_ORDER.get(evidence.confidence, -1) >= CONFIDENCE_ORDER[mandate.minimum_confidence]
    checks["CONFIDENCE"] = _result("CONFIDENCE", ConstraintStatus.PASS if confidence_ok else ConstraintStatus.BLOCK,
        evidence.confidence, mandate.minimum_confidence, "CONFIDENCE_MEETS_POLICY" if confidence_ok else "CONFIDENCE_BELOW_POLICY")
    checks["DATA_QUALITY"] = _result("DATA_QUALITY", ConstraintStatus.PASS if evidence.data_quality_status == "PASS" else ConstraintStatus.BLOCK,
        evidence.data_quality_status, "PASS", "DATA_QUALITY_OK" if evidence.data_quality_status == "PASS" else "DATA_QUALITY_BLOCKED")
    calibration_ok = bool(evidence.calibration_version and evidence.calibration_population_id)
    checks["CALIBRATION"] = _result("CALIBRATION", ConstraintStatus.PASS if calibration_ok else ConstraintStatus.BLOCK,
        evidence.calibration_version, None, "CALIBRATION_AVAILABLE" if calibration_ok else "CALIBRATION_UNAVAILABLE")
    universe_ok = evidence.instrument_id in mandate.eligible_instruments
    checks["UNIVERSE"] = _result("UNIVERSE", ConstraintStatus.PASS if universe_ok else ConstraintStatus.BLOCK,
        evidence.instrument_id, None, "UNIVERSE_ELIGIBLE" if universe_ok else "INSTRUMENT_NOT_ELIGIBLE")
    pos_status = ConstraintStatus.BLOCK if current_weight > mandate.maximum_position_weight else (
        ConstraintStatus.BINDING if proposed_weight >= mandate.maximum_position_weight else ConstraintStatus.PASS)
    checks["POSITION_LIMIT"] = _result("POSITION_LIMIT", pos_status, proposed_weight,
        mandate.maximum_position_weight, "POSITION_ALREADY_ABOVE_LIMIT" if current_weight > mandate.maximum_position_weight else "POSITION_LIMIT_EVALUATED")
    for key, value, limit in (("GROSS_EXPOSURE", metrics.gross_exposure, mandate.maximum_gross_exposure),
                              ("NET_EXPOSURE", metrics.net_exposure, mandate.maximum_net_exposure)):
        if value is None: status, reason = ConstraintStatus.UNKNOWN, "VALUATION_REQUIRED_CONSTRAINT_UNKNOWN"
        else: status, reason = (ConstraintStatus.BLOCK, f"{key}_LIMIT_EXCEEDED") if value > metrics.partial_total_value * limit else (ConstraintStatus.PASS, f"{key}_WITHIN_LIMIT")
        checks[key] = _result(key, status, value, limit, reason)
    names_status = ConstraintStatus.BLOCK if active_names > mandate.maximum_names else (
        ConstraintStatus.BINDING if active_names == mandate.maximum_names and holding is None else ConstraintStatus.PASS)
    checks["MAXIMUM_NAMES"] = _result("MAXIMUM_NAMES", names_status, active_names, mandate.maximum_names, "MAXIMUM_NAMES_EVALUATED")
    if holding is None or holding.sector not in mandate.sector_limits:
        checks["SECTOR_LIMIT"] = _result("SECTOR_LIMIT", ConstraintStatus.NOT_APPLICABLE,
            None, None, "SYNTHETIC_SECTOR_NOT_AVAILABLE_OR_UNLIMITED")
    else:
        sector_weight = sum((Decimal(str(metrics.position_weights.get(item.instrument_id) or 0))
                             for item in portfolio.holdings if item.sector == holding.sector), Decimal(0))
        sector_limit = mandate.sector_limits[holding.sector]
        checks["SECTOR_LIMIT"] = _result("SECTOR_LIMIT",
            ConstraintStatus.BLOCK if sector_weight > sector_limit else ConstraintStatus.PASS,
            sector_weight, sector_limit, "SECTOR_LIMIT_EXCEEDED" if sector_weight > sector_limit else "SECTOR_LIMIT_OK")
    checks["CASH_BUFFER"] = _result("CASH_BUFFER",
        ConstraintStatus.BLOCK if cash_ratio < mandate.minimum_cash_buffer else ConstraintStatus.PASS,
        qquantity(cash_ratio), mandate.minimum_cash_buffer, "INSUFFICIENT_CASH_BUFFER" if cash_ratio < mandate.minimum_cash_buffer else "CASH_BUFFER_OK")
    checks["TURNOVER"] = _result("TURNOVER",
        ConstraintStatus.BLOCK if proposed_turnover > mandate.turnover_limit else ConstraintStatus.PASS,
        proposed_turnover, mandate.turnover_limit, "TURNOVER_LIMIT_EXCEEDED" if proposed_turnover > mandate.turnover_limit else "TURNOVER_WITHIN_LIMIT")
    liquidity_status = ConstraintStatus.UNKNOWN if liquidity is None else (
        ConstraintStatus.BLOCK if liquidity < mandate.minimum_liquidity else ConstraintStatus.PASS)
    checks["LIQUIDITY"] = _result("LIQUIDITY", liquidity_status, liquidity, mandate.minimum_liquidity,
        "LIQUIDITY_UNKNOWN" if liquidity is None else "LIQUIDITY_BELOW_REQUIREMENT" if liquidity < mandate.minimum_liquidity else "LIQUIDITY_OK")
    checks["SETTLEMENT_AVAILABILITY"] = _result("SETTLEMENT_AVAILABILITY",
        ConstraintStatus.PASS if settlement_available else ConstraintStatus.BLOCK, settlement_available, True,
        "SETTLEMENT_AVAILABLE" if settlement_available else "SETTLEMENT_UNAVAILABLE")
    checks["MISSING_VALUATION"] = _result("MISSING_VALUATION",
        ConstraintStatus.PASS if metrics.valuation_status == "COMPLETE" else ConstraintStatus.BLOCK,
        metrics.valuation_status, "COMPLETE", "VALUATION_COMPLETE" if metrics.valuation_status == "COMPLETE" else "MISSING_VALUATION_PRICE")
    checks["UNRESOLVED_TERMINAL_ECONOMICS"] = _result("UNRESOLVED_TERMINAL_ECONOMICS",
        ConstraintStatus.PASS if terminal_resolved else ConstraintStatus.BLOCK, terminal_resolved, True,
        "TERMINAL_ECONOMICS_RESOLVED" if terminal_resolved else "UNRESOLVED_TERMINAL_ECONOMICS")
    cadence_ok = current_session_ordinal - last_rebalance_session_ordinal >= mandate.rebalance_cadence_sessions
    checks["REBALANCE_CADENCE"] = _result("REBALANCE_CADENCE", ConstraintStatus.PASS if cadence_ok else ConstraintStatus.BLOCK,
        current_session_ordinal - last_rebalance_session_ordinal, mandate.rebalance_cadence_sessions,
        "REBALANCE_DUE" if cadence_ok else "REBALANCE_NOT_DUE")
    checks["PROVENANCE"] = _result("PROVENANCE", ConstraintStatus.PASS if provenance_valid else ConstraintStatus.BLOCK,
        provenance_valid, True, "PROVENANCE_VALID" if provenance_valid else "ARTIFACT_HASH_MISMATCH")
    ordered = tuple(checks[name] for name in CONSTRAINT_ORDER)
    blockers = tuple(item.constraint_id for item in ordered if item.status in {ConstraintStatus.BLOCK, ConstraintStatus.UNKNOWN})
    if current_weight > mandate.maximum_position_weight:
        intent = "DECREASE_SYNTHETIC_EXPOSURE"
    elif blockers:
        intent = "POLICY_BLOCKED"
    elif evidence.score_0_100 >= 70 and (evidence.expected_outcome or 0) > 0:
        intent = "INCREASE_SYNTHETIC_EXPOSURE"
    elif evidence.score_0_100 <= 30:
        intent = "AVOID_OR_DECREASE_SYNTHETIC_EXPOSURE"
    else:
        intent = "MAINTAIN_SYNTHETIC_EXPOSURE"
    target = None if blockers else min(proposed_weight, mandate.maximum_position_weight)
    return PolicyEvaluation(POLICY_VERSION, portfolio.portfolio_id, mandate.mandate_id,
        evidence.snapshot_id, not blockers, intent, target, blockers,
        ("SCORE_ONLY_ACTION_PROHIBITED",), tuple(item.reason for item in ordered), ordered,
        ExternalDecision())
