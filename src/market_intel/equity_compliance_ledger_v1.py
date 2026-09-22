"""Sanitized in-memory compliance record for synthetic equity request fixtures."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import re

from .equity_cash_session_policy_v1 import CashSessionResolution


SCHEMA_VERSION = "equity_compliance_ledger_v1"
CONSUMER_ID = "dashboard_current_cash_equity_watchlist"
READINESS = "SYNTHETIC_NOT_MARKET_READY"


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
class EquityComplianceRecord:
    schema_version: str
    ledger_version: str
    policy_version: str
    code_version: str
    consumer_id: str
    recorded_at: datetime
    request_started_at: datetime
    request_completed_at: datetime
    duration_milliseconds: int
    endpoint_category: str
    request_count: int
    requested_count: int
    returned_count: int
    missing_count: int
    unavailable_count: int
    response_byte_count: int
    outcome_state: str
    reason_codes: tuple[str, ...]
    session_resolution_hash: str
    cache_policy: str = "TRANSIENT_MEMORY_ONLY"
    raw_payload_retained: bool = False
    contains_credentials: bool = False
    contains_instrument_identities: bool = False
    contains_prices: bool = False
    can_persist: bool = False
    can_authorize_requests: bool = False
    can_authorize_display: bool = False
    research_eligible: bool = False
    production_eligible: bool = False
    readiness_state: str = READINESS

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION or self.consumer_id != CONSUMER_ID:
            raise ValueError("Unexpected compliance contract")
        if not all(_version(value) for value in (
                self.ledger_version, self.policy_version, self.code_version)):
            raise ValueError("Explicit versions required")
        for value in (self.recorded_at, self.request_started_at, self.request_completed_at):
            if not _aware(value):
                raise ValueError("Caller-injected aware clocks required")
        if not self.request_started_at <= self.request_completed_at <= self.recorded_at:
            raise ValueError("Compliance clocks are unordered")
        expected_duration = int((self.request_completed_at-self.request_started_at).total_seconds()*1000)
        if self.duration_milliseconds != expected_duration or self.duration_milliseconds < 0:
            raise ValueError("Exact nonnegative duration required")
        if self.endpoint_category != "SYNTHETIC_CURRENT_EQUITY_QUOTE":
            raise ValueError("Synthetic endpoint category only")
        for value in (self.request_count, self.requested_count, self.returned_count,
                      self.missing_count, self.unavailable_count, self.response_byte_count):
            if type(value) is not int or value < 0:
                raise ValueError("Nonnegative aggregate values required")
        if not 0 <= self.request_count <= 2 or not 0 <= self.requested_count <= 50:
            raise ValueError("Approved offline bounds exceeded")
        if self.returned_count + self.missing_count != self.requested_count:
            raise ValueError("Coverage counts do not reconcile")
        if self.unavailable_count > self.returned_count or self.response_byte_count > 8*1024*1024:
            raise ValueError("Quality or byte bound exceeded")
        if self.outcome_state not in {"SYNTHETIC_SUCCESS", "SYNTHETIC_PARTIAL", "SYNTHETIC_FAILURE"}:
            raise ValueError("Unknown synthetic outcome")
        if type(self.reason_codes) is not tuple or len(self.reason_codes) > 16:
            raise ValueError("Immutable bounded reason codes required")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("Reason codes must be unique and sorted")
        if any(type(code) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code)
               for code in self.reason_codes):
            raise ValueError("Sanitized reason codes required")
        if self.outcome_state == "SYNTHETIC_SUCCESS" and (
                self.missing_count or self.unavailable_count or self.reason_codes):
            raise ValueError("Success cannot hide missing or unavailable results")
        if not _hash(self.session_resolution_hash):
            raise ValueError("Session resolution binding required")
        if (self.cache_policy != "TRANSIENT_MEMORY_ONLY" or
                self.raw_payload_retained is not False or self.contains_credentials is not False or
                self.contains_instrument_identities is not False or self.contains_prices is not False or
                self.can_persist is not False or self.can_authorize_requests is not False or
                self.can_authorize_display is not False or self.research_eligible is not False or
                self.production_eligible is not False or self.readiness_state != READINESS):
            raise ValueError("Compliance record cannot retain facts or grant authority")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def build_compliance_record(*, mode, ledger_version, policy_version, code_version,
                            recorded_at, request_started_at, request_completed_at,
                            request_count, requested_count, returned_count,
                            missing_count, unavailable_count, response_byte_count,
                            outcome_state, reason_codes, session_resolution):
    """Build one sanitized aggregate record without writing or requesting data."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if type(session_resolution) is not CashSessionResolution:
        raise ValueError("CashSessionResolution required")
    session_resolution.__post_init__()
    if session_resolution.session_state in {"UNKNOWN_DATE", "CALENDAR_EXPIRED"}:
        raise ValueError("Unresolved session policy cannot support an event record")
    if type(reason_codes) is not tuple:
        raise ValueError("Immutable reason codes required")
    duration = int((request_completed_at-request_started_at).total_seconds()*1000) \
        if _aware(request_started_at) and _aware(request_completed_at) else -1
    return EquityComplianceRecord(
        SCHEMA_VERSION, ledger_version, policy_version, code_version, CONSUMER_ID,
        recorded_at, request_started_at, request_completed_at, duration,
        "SYNTHETIC_CURRENT_EQUITY_QUOTE", request_count, requested_count,
        returned_count, missing_count, unavailable_count, response_byte_count,
        outcome_state, tuple(sorted(reason_codes)), session_resolution.content_hash,
    )
