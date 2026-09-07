"""Versioned immutable contracts for fictional portfolio-policy engineering."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from typing import Mapping

import pandas as pd


PORTFOLIO_SCHEMA_VERSION = "synthetic_portfolio_snapshot_r10g_v1"
MANDATE_SCHEMA_VERSION = "synthetic_mandate_r10g_v1"
FILL_SCHEMA_VERSION = "synthetic_simulation_fill_r10g_v1"
ACCOUNTING_VERSION = "decimal_weighted_average_r10g_v1"
POLICY_VERSION = "deterministic_mandate_policy_r10g_v1"
CLASSIFICATION = "SYNTHETIC_ONLY_NONCANONICAL"


class AccountingError(ValueError):
    """Named, fail-closed portfolio or mandate error."""


def aware(value: object, field: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise AccountingError(f"NAIVE_TIMESTAMP:{field}")
    return stamp.tz_convert("UTC")


def implementation_hash(value: Mapping[str, object]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


class ConstraintStatus(StrEnum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    BINDING = "BINDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CashBalance:
    currency: str
    settled: Decimal
    unsettled_receivable: Decimal = Decimal("0")
    unsettled_payable: Decimal = Decimal("0")


@dataclass(frozen=True)
class Holding:
    instrument_id: str
    listing_id: str
    quantity: Decimal
    cost_basis_total: Decimal
    sector: str
    lifecycle: str = "ACTIVE"
    market_price: Decimal | None = None
    price_instant: pd.Timestamp | None = None
    price_artifact_hash: str | None = None
    acquired_at: pd.Timestamp | None = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise AccountingError("NEGATIVE_QUANTITY_SHORTING_PROHIBITED")
        if self.cost_basis_total < 0:
            raise AccountingError("NEGATIVE_COST_BASIS")
        if self.price_instant is not None:
            aware(self.price_instant, "price_instant")
        if self.acquired_at is not None:
            aware(self.acquired_at, "holding_acquired_at")


@dataclass(frozen=True)
class PendingSyntheticTransaction:
    transaction_id: str
    instrument_id: str
    side: str
    quantity: Decimal
    execution_at: pd.Timestamp
    settlement_at: pd.Timestamp
    cash_amount: Decimal
    state: str = "PENDING_SETTLEMENT"

    def __post_init__(self) -> None:
        execution = aware(self.execution_at, "execution_at")
        settlement = aware(self.settlement_at, "settlement_at")
        if settlement <= execution:
            raise AccountingError("TRADE_SETTLEMENT_BEFORE_EXECUTION")
        if self.side not in {"BUY", "SELL"}:
            raise AccountingError("INVALID_SYNTHETIC_FILL_SIDE")


@dataclass(frozen=True)
class Entitlement:
    entitlement_id: str
    event_type: str
    instrument_id: str
    effective_at: pd.Timestamp
    quantity: Decimal | None = None
    cash_amount: Decimal | None = None
    successor_instrument_id: str | None = None
    evidence_hash: str = ""

    def __post_init__(self) -> None:
        aware(self.effective_at, "entitlement_effective_at")
        if not self.evidence_hash:
            raise AccountingError("CORPORATE_ACTION_EVIDENCE_MISSING")


@dataclass(frozen=True)
class PortfolioSnapshot:
    schema_version: str
    portfolio_id: str
    mandate_id: str
    base_currency: str
    valuation_instant: pd.Timestamp
    knowledge_cutoff: pd.Timestamp
    cash: CashBalance
    holdings: tuple[Holding, ...]
    pending_transactions: tuple[PendingSyntheticTransaction, ...]
    entitlements: tuple[Entitlement, ...]
    price_snapshot_references: tuple[str, ...]
    evidence_snapshot_references: tuple[str, ...]
    provenance_hashes: tuple[str, ...]
    classification: str = CLASSIFICATION
    accounting_version: str = ACCOUNTING_VERSION

    def __post_init__(self) -> None:
        valuation = aware(self.valuation_instant, "valuation_instant")
        cutoff = aware(self.knowledge_cutoff, "knowledge_cutoff")
        if cutoff > valuation:
            raise AccountingError("KNOWLEDGE_CUTOFF_AFTER_VALUATION")
        if self.schema_version != PORTFOLIO_SCHEMA_VERSION:
            raise AccountingError("UNKNOWN_PORTFOLIO_SCHEMA_VERSION")
        if self.classification != CLASSIFICATION:
            raise AccountingError("NON_SYNTHETIC_PORTFOLIO_PROHIBITED")
        if self.base_currency != self.cash.currency:
            raise AccountingError("UNSUPPORTED_CURRENCY_OR_MISSING_FX")
        ids = [item.transaction_id for item in self.pending_transactions]
        if len(ids) != len(set(ids)):
            raise AccountingError("DUPLICATE_TRANSACTION_ID")
        if any(aware(item.execution_at, "execution_at") > valuation
               for item in self.pending_transactions):
            raise AccountingError("FUTURE_TRANSACTION_IN_EARLIER_SNAPSHOT")
        if len({item.instrument_id for item in self.holdings}) != len(self.holdings):
            raise AccountingError("DUPLICATE_HOLDING_IDENTITY")
        if any(item.acquired_at is not None and aware(item.acquired_at, "holding_acquired_at") > valuation
               for item in self.holdings):
            raise AccountingError("CURRENT_HOLDINGS_HISTORICAL_SUBSTITUTION")
        if not self.provenance_hashes or any(len(value) != 64 or
                any(char not in "0123456789abcdef" for char in value.lower())
                for value in self.provenance_hashes):
            raise AccountingError("ARTIFACT_HASH_MISMATCH")


@dataclass(frozen=True)
class Mandate:
    mandate_id: str
    version: str
    objective: str
    eligible_instruments: frozenset[str]
    decision_horizon_sessions: int
    permitted_evidence_horizons: frozenset[int]
    rebalance_cadence_sessions: int
    base_currency: str
    maximum_gross_exposure: Decimal
    maximum_net_exposure: Decimal
    maximum_position_weight: Decimal
    maximum_names: int
    sector_limits: Mapping[str, Decimal]
    minimum_cash_buffer: Decimal
    turnover_limit: Decimal
    minimum_liquidity: Decimal
    permitted_lifecycle_states: frozenset[str]
    minimum_confidence: str
    stale_evidence_policy: str
    unresolved_terminal_policy: str
    transaction_cost_version: str
    fractional_share_policy: str
    shorting_allowed: bool
    leverage_allowed: bool
    tax_treatment: str
    risk_overrides: tuple[str, ...]
    implementation_hash: str
    schema_version: str = MANDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MANDATE_SCHEMA_VERSION:
            raise AccountingError("UNKNOWN_MANDATE_SCHEMA_VERSION")
        if self.decision_horizon_sessions not in self.permitted_evidence_horizons:
            raise AccountingError("MANDATE_HORIZON_CONTRACT_INCONSISTENT")
        if self.maximum_names < 1 or self.rebalance_cadence_sessions < 1:
            raise AccountingError("INVALID_MANDATE_LIMIT")
        if not self.implementation_hash:
            raise AccountingError("MANDATE_IMPLEMENTATION_HASH_MISSING")


@dataclass(frozen=True)
class SyntheticFillProposal:
    proposal_id: str
    instrument_id: str
    listing_id: str
    side: str
    intended_quantity: Decimal
    execution_session_id: str
    execution_at: pd.Timestamp
    reference_price_source: str
    reference_price: Decimal | None
    limit_price: Decimal | None
    classification: str = CLASSIFICATION
    schema_version: str = FILL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        aware(self.execution_at, "execution_at")
        if self.classification != CLASSIFICATION:
            raise AccountingError("BROKER_OR_ORDER_PAYLOAD_PROHIBITED")
        if self.side not in {"BUY", "SELL"} or self.intended_quantity <= 0:
            raise AccountingError("INVALID_SYNTHETIC_FILL_PROPOSAL")


@dataclass(frozen=True)
class SyntheticFill:
    proposal_id: str
    instrument_id: str
    side: str
    intended_quantity: Decimal
    filled_quantity: Decimal
    unfilled_quantity: Decimal
    simulated_fill_price: Decimal | None
    fee: Decimal
    fill_state: str
    reason: str
    cost_version: str
    settlement_session_id: str | None
    settlement_at: pd.Timestamp | None
    classification: str = CLASSIFICATION

    def __post_init__(self) -> None:
        if self.filled_quantity + self.unfilled_quantity != self.intended_quantity:
            raise AccountingError("FILL_QUANTITY_DOES_NOT_RECONCILE")
        if self.classification != CLASSIFICATION:
            raise AccountingError("BROKER_OR_ORDER_PAYLOAD_PROHIBITED")
        if self.settlement_at is not None:
            aware(self.settlement_at, "settlement_at")


@dataclass(frozen=True)
class ConstraintResult:
    constraint_id: str
    status: ConstraintStatus
    observed: str | None
    limit: str | None
    reason: str
    required: bool = True


@dataclass(frozen=True)
class ExternalDecision:
    decision: str = "NO_DECISION"
    reason: str = "SYNTHETIC_NONCANONICAL_EVIDENCE"


@dataclass(frozen=True)
class PolicyEvaluation:
    policy_version: str
    portfolio_id: str
    mandate_id: str
    evidence_snapshot_id: str
    eligible: bool
    internal_synthetic_intent: str
    target_exposure: Decimal | None
    binding_constraints: tuple[str, ...]
    rejected_alternatives: tuple[str, ...]
    explanation_codes: tuple[str, ...]
    constraints: tuple[ConstraintResult, ...]
    external_decision: ExternalDecision
    classification: str = CLASSIFICATION
