"""Read-only aggregate quality diagnostics for synthetic current-equity fixtures."""
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re

from .dashboard_current_equity_readiness_v1 import EquityReadiness, RecordReadiness

SCHEMA_VERSION = "equity_quality_diagnostics_v1"
CONSUMER_ID = "dashboard_daily_equity_health"


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _identity(value):
    return type(value) is str and re.fullmatch(r"SYNTHETIC:[A-Z0-9][A-Z0-9_.-]{0,63}", value)


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


@dataclass(frozen=True, slots=True)
class SyntheticSessionContext:
    version: str
    session_date: date
    state: str
    timezone_name: str = "UTC"

    def __post_init__(self):
        if not _version(self.version) or type(self.session_date) is not date:
            raise ValueError("Versioned synthetic session date required")
        if self.state not in {"TRADING_SESSION", "NON_TRADING_DAY", "UNKNOWN"}:
            raise ValueError("Unknown synthetic session classification")
        if self.timezone_name != "UTC":
            raise ValueError("Synthetic fixture session timezone must be explicit UTC")


@dataclass(frozen=True, slots=True)
class DiagnosticCount:
    code: str
    count: int

    def __post_init__(self):
        if type(self.code) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.code):
            raise ValueError("Sanitized diagnostic code required")
        if type(self.count) is not int or self.count < 1:
            raise ValueError("Positive diagnostic count required")


@dataclass(frozen=True, slots=True)
class EquityQualityDiagnostics:
    schema_version: str
    diagnostic_version: str
    consumer_id: str
    as_of: datetime
    source_input_hash: str
    source_content_hash: str
    expected_universe_hash: str
    session_version: str
    session_date: date
    session_state: str
    observed_record_count: int
    expected_record_count: int
    issue_record_count: int
    duplicate_identity_count: int
    expected_gap_count: int
    unexpected_identity_count: int
    missing_price_count: int
    invalid_price_count: int
    nonfinite_price_count: int
    timestamp_issue_count: int
    semantic_issue_count: int
    source_failure_count: int
    diagnostic_counts: tuple[DiagnosticCount, ...]
    quality_state: str
    evidence_class: str = "SYNTHETIC_FIXTURE"
    original_facts_preserved: bool = True
    can_repair: bool = False
    can_fill_gaps: bool = False
    can_select_provider: bool = False
    production_eligible: bool = False

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION or self.consumer_id != CONSUMER_ID:
            raise ValueError("Unexpected diagnostic contract")
        if not _version(self.diagnostic_version) or not _aware(self.as_of):
            raise ValueError("Version and caller-aware as-of required")
        for value in (self.source_input_hash, self.source_content_hash,
                      self.expected_universe_hash):
            if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("Deterministic hash binding required")
        if not _version(self.session_version) or type(self.session_date) is not date:
            raise ValueError("Versioned session context required")
        if self.session_state not in {"TRADING_SESSION", "NON_TRADING_DAY", "UNKNOWN"}:
            raise ValueError("Unknown session classification")
        for value in (
            self.observed_record_count, self.expected_record_count, self.issue_record_count,
            self.duplicate_identity_count, self.expected_gap_count,
            self.unexpected_identity_count, self.missing_price_count,
            self.invalid_price_count, self.nonfinite_price_count,
            self.timestamp_issue_count, self.semantic_issue_count,
            self.source_failure_count,
        ):
            if type(value) is not int or value < 0:
                raise ValueError("Nonnegative aggregate count required")
        if self.issue_record_count > self.observed_record_count:
            raise ValueError("Issue record count cannot exceed observations")
        if self.expected_gap_count > self.expected_record_count:
            raise ValueError("Gap count cannot exceed expected observations")
        if type(self.diagnostic_counts) is not tuple:
            raise ValueError("Immutable diagnostic counts required")
        for item in self.diagnostic_counts:
            if type(item) is not DiagnosticCount:
                raise ValueError("DiagnosticCount required")
            item.__post_init__()
        if tuple(sorted(item.code for item in self.diagnostic_counts)) != tuple(
                item.code for item in self.diagnostic_counts):
            raise ValueError("Diagnostics must be deterministically ordered")
        if self.quality_state not in {
                "CLEAN_SYNTHETIC_FIXTURE", "ISSUES_DETECTED", "INDETERMINATE_SESSION"}:
            raise ValueError("Unknown quality state")
        if (self.evidence_class != "SYNTHETIC_FIXTURE" or
                self.original_facts_preserved is not True or self.can_repair is not False or
                self.can_fill_gaps is not False or self.can_select_provider is not False or
                self.production_eligible is not False):
            raise ValueError("Diagnostics cannot mutate or promote source facts")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _has_any(codes, exact=(), prefixes=(), suffixes=()):
    return any(code in exact or any(code.startswith(value) for value in prefixes) or
               any(code.endswith(value) for value in suffixes) for code in codes)


def diagnose(*, mode, diagnostic_version, as_of, readiness,
             expected_instrument_keys, session):
    """Summarize fixture anomalies without repairing or discarding observations."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if not _version(diagnostic_version) or not _aware(as_of):
        raise ValueError("Version and caller-aware as-of required")
    if type(readiness) is not EquityReadiness:
        raise ValueError("EquityReadiness input required")
    readiness.__post_init__()
    if readiness.as_of.astimezone(timezone.utc) != as_of.astimezone(timezone.utc):
        raise ValueError("Diagnostic and readiness as-of clocks must match")
    if type(session) is not SyntheticSessionContext:
        raise ValueError("Explicit synthetic session context required")
    session.__post_init__()
    if session.session_date != as_of.astimezone(timezone.utc).date():
        raise ValueError("Session date and as-of date must match")
    if type(expected_instrument_keys) is not tuple or not 1 <= len(expected_instrument_keys) <= 25:
        raise ValueError("One to 25 immutable expected identities required")
    if any(not _identity(value) for value in expected_instrument_keys):
        raise ValueError("Invented synthetic identities only")
    if len(set(expected_instrument_keys)) != len(expected_instrument_keys):
        raise ValueError("Expected identities must be unique")
    for row in readiness.records:
        if type(row) is not RecordReadiness:
            raise ValueError("RecordReadiness required")
        row.fixture.__post_init__()
        if row.instrument_key != row.fixture.instrument_key:
            raise ValueError("Readiness identity and source fact disagree")
        if type(row.reason_codes) is not tuple or any(
                type(code) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code)
                for code in row.reason_codes):
            raise ValueError("Immutable sanitized readiness reasons required")
        if len(set(row.reason_codes)) != len(row.reason_codes):
            raise ValueError("Duplicate readiness reason")
        if row.reason_codes:
            if row.value_state != "UNAVAILABLE" or row.display_price is not None:
                raise ValueError("Blocked readiness rows must remain unavailable")
        elif (row.value_state != "FIXTURE_VALID_ONLY" or
              row.display_price != row.fixture.last_price):
            raise ValueError("Clean readiness row must preserve its exact fixture price")

    actual = tuple(row.instrument_key for row in readiness.records)
    expected = set(expected_instrument_keys)
    actual_set = set(actual)
    gap_count = len(expected-actual_set) if session.state == "TRADING_SESSION" else 0
    unexpected_count = len(actual_set-expected)
    tally = {}
    issue_records = 0
    duplicate = missing = invalid = nonfinite = timestamp = semantics = source_failure = 0
    for row in readiness.records:
        codes = row.reason_codes
        for code in codes:
            tally[code] = tally.get(code, 0) + 1
        issue_records += bool(codes)
        duplicate += "AMBIGUOUS_IDENTITY" in codes
        missing += "MISSING_PRICE" in codes
        invalid += "INVALID_PRICE" in codes
        price = row.fixture.last_price
        nonfinite += type(price) is Decimal and not price.is_finite()
        timestamp += _has_any(codes, exact={
            "TRADE_AFTER_QUOTE", "QUOTE_AFTER_RETRIEVAL", "INVENTORY_AFTER_RETRIEVAL"
        }, suffixes=("_TIME_UNKNOWN_OR_NAIVE", "_TIME_FUTURE", "_STALE"))
        semantics += _has_any(codes, exact={
            "INELIGIBLE_IDENTITY", "INCOMPATIBLE_CURRENCY", "INCONSISTENT_MISSINGNESS"
        })
        source_failure += _has_any(codes, exact={
            "MISSING_ROW", "ACCESS_FAILURE", "TRANSPORT_FAILURE"
        })
    if gap_count:
        tally["EXPECTED_OBSERVATION_GAP"] = gap_count
    if unexpected_count:
        tally["UNEXPECTED_IDENTITY"] = unexpected_count
    if session.state == "UNKNOWN":
        tally["SESSION_EXPECTATION_UNKNOWN"] = 1
    if session.state == "NON_TRADING_DAY":
        tally["GAP_CHECK_NOT_APPLICABLE_NON_TRADING_DAY"] = 1
    if nonfinite:
        tally["NONFINITE_PRICE"] = nonfinite

    hard_issue = bool(issue_records or gap_count or unexpected_count)
    quality_state = ("ISSUES_DETECTED" if hard_issue else
                     "INDETERMINATE_SESSION" if session.state == "UNKNOWN" else
                     "CLEAN_SYNTHETIC_FIXTURE")
    expected_hash = hashlib.sha256(_bytes(tuple(sorted(expected_instrument_keys)))).hexdigest()
    diagnostics = tuple(DiagnosticCount(code, tally[code]) for code in sorted(tally))
    return EquityQualityDiagnostics(
        SCHEMA_VERSION, diagnostic_version, CONSUMER_ID, as_of,
        readiness.input_hash, readiness.content_hash, expected_hash,
        session.version, session.session_date, session.state,
        len(readiness.records), len(expected_instrument_keys), issue_records,
        duplicate, gap_count, unexpected_count, missing, invalid, nonfinite,
        timestamp, semantics, source_failure, diagnostics, quality_state,
    )
