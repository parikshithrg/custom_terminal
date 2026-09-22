"""Offline, explicit-date cash-session policy for synthetic equity fixtures."""
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "equity_cash_session_policy_v1"
RESOLUTION_SCHEMA_VERSION = "equity_cash_session_resolution_v1"
MARKET_TIMEZONE = "Asia/Kolkata"
READINESS = "SYNTHETIC_NOT_MARKET_READY"
_ZONE = ZoneInfo(MARKET_TIMEZONE)


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    return value


def _bytes(value):
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _local_date(value):
    return value.astimezone(_ZONE).date()


@dataclass(frozen=True, slots=True)
class DeclaredCashSession:
    session_date: date
    session_kind: str
    opens_at: datetime | None
    closes_at: datetime | None
    reason_code: str

    def __post_init__(self):
        if type(self.session_date) is not date:
            raise ValueError("Explicit session date required")
        if self.session_kind not in {"NORMAL", "CLOSED", "SPECIAL"}:
            raise ValueError("Unknown session kind")
        if type(self.reason_code) is not str or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{0,63}", self.reason_code):
            raise ValueError("Sanitized reason code required")
        if self.session_kind == "CLOSED":
            if self.opens_at is not None or self.closes_at is not None:
                raise ValueError("Closed sessions cannot carry trading times")
            return
        if not _aware(self.opens_at) or not _aware(self.closes_at):
            raise ValueError("Trading sessions require aware open and close times")
        if _local_date(self.opens_at) != self.session_date or _local_date(
                self.closes_at) != self.session_date:
            raise ValueError("Trading times must resolve to the declared local date")
        if self.opens_at >= self.closes_at:
            raise ValueError("Session open must precede close")


@dataclass(frozen=True, slots=True)
class CashSessionPolicy:
    schema_version: str
    calendar_version: str
    timezone_name: str
    published_at: datetime
    coverage_start: date
    coverage_end: date
    valid_through: datetime
    sessions: tuple[DeclaredCashSession, ...]
    evidence_class: str = "SYNTHETIC_DECLARATION"
    readiness_state: str = READINESS
    can_fetch: bool = False
    can_persist: bool = False
    can_authorize_display: bool = False

    def __post_init__(self):
        if (self.schema_version != SCHEMA_VERSION or self.timezone_name != MARKET_TIMEZONE or
                self.evidence_class != "SYNTHETIC_DECLARATION" or
                self.readiness_state != READINESS or self.can_fetch is not False or
                self.can_persist is not False or self.can_authorize_display is not False):
            raise ValueError("Offline synthetic calendar only")
        if not _version(self.calendar_version):
            raise ValueError("Explicit calendar version required")
        if not _aware(self.published_at) or not _aware(self.valid_through):
            raise ValueError("Aware publication and validity clocks required")
        if type(self.coverage_start) is not date or type(self.coverage_end) is not date:
            raise ValueError("Explicit date coverage required")
        if self.coverage_start > self.coverage_end:
            raise ValueError("Invalid coverage range")
        if self.valid_through < self.published_at:
            raise ValueError("Validity cannot predate publication")
        if type(self.sessions) is not tuple or not 1 <= len(self.sessions) <= 366:
            raise ValueError("One to 366 immutable declarations required")
        for session in self.sessions:
            if type(session) is not DeclaredCashSession:
                raise ValueError("DeclaredCashSession required")
            session.__post_init__()
        dates = tuple(session.session_date for session in self.sessions)
        if dates != tuple(sorted(dates)) or len(set(dates)) != len(dates):
            raise ValueError("Session dates must be unique and sorted")
        expected = tuple(self.coverage_start + timedelta(days=offset)
                         for offset in range((self.coverage_end-self.coverage_start).days + 1))
        if dates != expected:
            raise ValueError("Every covered calendar date must be declared explicitly")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class CashSessionResolution:
    schema_version: str
    calendar_version: str
    calendar_hash: str
    session_date: date
    evaluated_at: datetime
    session_state: str
    opens_at: datetime | None
    closes_at: datetime | None
    reason_code: str
    readiness_state: str = READINESS
    can_fetch: bool = False
    can_authorize_display: bool = False

    def __post_init__(self):
        if (self.schema_version != RESOLUTION_SCHEMA_VERSION or
                self.readiness_state != READINESS or self.can_fetch is not False or
                self.can_authorize_display is not False):
            raise ValueError("Resolution cannot promote synthetic policy")
        if not _version(self.calendar_version) or not re.fullmatch(r"[0-9a-f]{64}", self.calendar_hash):
            raise ValueError("Versioned calendar binding required")
        if type(self.session_date) is not date or not _aware(self.evaluated_at):
            raise ValueError("Caller-supplied date and aware evaluation time required")
        if self.session_state not in {
                "NORMAL", "CLOSED", "SPECIAL", "UNKNOWN_DATE", "CALENDAR_EXPIRED"}:
            raise ValueError("Unknown resolution state")
        if type(self.reason_code) is not str or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{0,63}", self.reason_code):
            raise ValueError("Sanitized resolution reason required")
        if self.session_state in {"NORMAL", "SPECIAL"}:
            if not _aware(self.opens_at) or not _aware(self.closes_at):
                raise ValueError("Trading resolution requires times")
        elif self.opens_at is not None or self.closes_at is not None:
            raise ValueError("Non-trading resolution cannot imply times")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def build_policy(*, mode, calendar_version, published_at, coverage_start,
                 coverage_end, valid_through, sessions):
    """Build an explicit synthetic calendar without consulting external state."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic declarations only")
    return CashSessionPolicy(
        SCHEMA_VERSION, calendar_version, MARKET_TIMEZONE, published_at,
        coverage_start, coverage_end, valid_through, sessions,
    )


def resolve_session(*, policy, session_date, evaluated_at):
    """Resolve only declared dates; unknown or expired coverage fails closed."""
    if type(policy) is not CashSessionPolicy:
        raise ValueError("CashSessionPolicy required")
    policy.__post_init__()
    if type(session_date) is not date or not _aware(evaluated_at):
        raise ValueError("Caller-supplied date and aware evaluation time required")
    if evaluated_at < policy.published_at:
        raise ValueError("Policy cannot be evaluated before publication")
    common = (RESOLUTION_SCHEMA_VERSION, policy.calendar_version, policy.content_hash,
              session_date, evaluated_at)
    if evaluated_at > policy.valid_through:
        return CashSessionResolution(*common, "CALENDAR_EXPIRED", None, None,
                                     "CALENDAR_VALIDITY_EXPIRED")
    if session_date < policy.coverage_start or session_date > policy.coverage_end:
        return CashSessionResolution(*common, "UNKNOWN_DATE", None, None,
                                     "DATE_NOT_EXPLICITLY_DECLARED")
    declaration = policy.sessions[(session_date-policy.coverage_start).days]
    return CashSessionResolution(*common, declaration.session_kind,
                                 declaration.opens_at, declaration.closes_at,
                                 declaration.reason_code)
