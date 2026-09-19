"""Sanitized, in-memory validation ledger for synthetic equity health results."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import re

from .daily_equity_data_health_v1 import (
    DailyEquityDataHealth,
    SCHEMA_VERSION as HEALTH_SCHEMA_VERSION,
)

SCHEMA_VERSION = "equity_validation_refresh_ledger_v1"
CONSUMER_ID = "dashboard_daily_equity_health"
EVIDENCE_CLASS = "SYNTHETIC_FIXTURE"
VERIFICATION_STATE = "NOT_EXTERNALLY_VERIFIED"


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    return value


def _bytes(value):
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class RejectionCount:
    code: str
    count: int

    def __post_init__(self):
        if type(self.code) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.code):
            raise ValueError("Sanitized rejection code required")
        if type(self.count) is not int or self.count < 1:
            raise ValueError("Positive rejection count required")


@dataclass(frozen=True, slots=True)
class ValidationRefreshLedger:
    schema_version: str
    ledger_version: str
    consumer_id: str
    recorded_at: datetime
    contract_version: str
    code_version: str
    configuration_version: str
    policy_version: str
    evidence_class: str
    verification_state: str
    source_input_hash: str
    source_content_hash: str
    permitted_input_hashes: tuple[str, ...]
    requested_count: int
    returned_count: int
    missing_count: int
    unavailable_count: int
    stale_count: int
    validation_state: str
    rejection_reasons: tuple[RejectionCount, ...]
    refresh_state: str = "REFRESH_NOT_AUTHORIZED"
    can_persist: bool = False
    can_activate_source: bool = False
    can_expose_real_data: bool = False
    research_eligible: bool = False
    production_eligible: bool = False

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION or self.consumer_id != CONSUMER_ID:
            raise ValueError("Unexpected ledger contract")
        if not all(_version(value) for value in (
                self.ledger_version, self.contract_version, self.code_version,
                self.configuration_version, self.policy_version)):
            raise ValueError("Explicit bounded versions required")
        if not _aware(self.recorded_at):
            raise ValueError("Caller-injected aware recorded-at required")
        if self.evidence_class != EVIDENCE_CLASS or self.verification_state != VERIFICATION_STATE:
            raise ValueError("Synthetic evidence cannot be promoted")
        if not _hash(self.source_input_hash) or not _hash(self.source_content_hash):
            raise ValueError("Source hash bindings required")
        if type(self.permitted_input_hashes) is not tuple or not 1 <= len(self.permitted_input_hashes) <= 16:
            raise ValueError("One to 16 immutable permitted hashes required")
        if any(not _hash(value) for value in self.permitted_input_hashes):
            raise ValueError("Invalid permitted input hash")
        if tuple(sorted(set(self.permitted_input_hashes))) != self.permitted_input_hashes:
            raise ValueError("Permitted hashes must be unique and sorted")
        for value in (self.requested_count, self.returned_count, self.missing_count,
                      self.unavailable_count, self.stale_count):
            if type(value) is not int or value < 0:
                raise ValueError("Nonnegative aggregate count required")
        if self.returned_count > self.requested_count or self.missing_count > self.requested_count:
            raise ValueError("Coverage counts do not reconcile")
        if self.unavailable_count > self.requested_count or self.stale_count > self.requested_count:
            raise ValueError("Quality counts do not reconcile")
        if self.validation_state not in {"VALIDATED_SYNTHETIC_CONTRACT", "REJECTED"}:
            raise ValueError("Unknown validation state")
        if type(self.rejection_reasons) is not tuple:
            raise ValueError("Immutable rejection reasons required")
        for reason in self.rejection_reasons:
            if type(reason) is not RejectionCount:
                raise ValueError("RejectionCount required")
            reason.__post_init__()
        if tuple(sorted(reason.code for reason in self.rejection_reasons)) != tuple(
                reason.code for reason in self.rejection_reasons):
            raise ValueError("Rejection reasons must be deterministically ordered")
        if (self.validation_state == "REJECTED") != bool(self.rejection_reasons):
            raise ValueError("Validation state and rejection reasons disagree")
        if (self.refresh_state != "REFRESH_NOT_AUTHORIZED" or self.can_persist is not False or
                self.can_activate_source is not False or self.can_expose_real_data is not False or
                self.research_eligible is not False or self.production_eligible is not False):
            raise ValueError("Ledger grants no refresh, persistence or activation authority")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def build_ledger(*, mode, ledger_version, code_version, configuration_version,
                 policy_version, recorded_at, health, permitted_input_hashes,
                 expected_contract_version=HEALTH_SCHEMA_VERSION):
    """Bind a synthetic health result without persisting or refreshing anything."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic evidence only")
    if not all(_version(value) for value in (
            ledger_version, code_version, configuration_version,
            policy_version, expected_contract_version)):
        raise ValueError("Explicit bounded versions required")
    if not _aware(recorded_at):
        raise ValueError("Caller-injected aware recorded-at required")
    if type(health) is not DailyEquityDataHealth:
        raise ValueError("DailyEquityDataHealth input required")
    health.__post_init__()
    if recorded_at < health.as_of:
        raise ValueError("Ledger cannot predate its input")
    if type(permitted_input_hashes) is not tuple or not 1 <= len(permitted_input_hashes) <= 16:
        raise ValueError("One to 16 immutable permitted hashes required")
    if any(not _hash(value) for value in permitted_input_hashes):
        raise ValueError("Invalid permitted input hash")
    normalized_hashes = tuple(sorted(set(permitted_input_hashes)))
    if len(normalized_hashes) != len(permitted_input_hashes):
        raise ValueError("Duplicate permitted input hash")

    rejection_codes = []
    if health.schema_version != expected_contract_version:
        rejection_codes.append("CONTRACT_VERSION_MISMATCH")
    if health.input_hash not in normalized_hashes:
        rejection_codes.append("INPUT_HASH_NOT_PERMITTED")
    reasons = tuple(RejectionCount(code, 1) for code in sorted(rejection_codes))
    state = "REJECTED" if reasons else "VALIDATED_SYNTHETIC_CONTRACT"
    return ValidationRefreshLedger(
        SCHEMA_VERSION, ledger_version, CONSUMER_ID, recorded_at,
        expected_contract_version, code_version, configuration_version,
        policy_version, EVIDENCE_CLASS, VERIFICATION_STATE,
        health.input_hash, health.content_hash, normalized_hashes,
        health.requested_count, health.returned_count, health.missing_count,
        health.unavailable_count, health.stale_count, state, reasons,
    )
