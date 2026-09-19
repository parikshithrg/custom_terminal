"""Offline aggregate health read model for the Dashboard equity consumer."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import re

from .dashboard_current_equity_readiness_v1 import EquityReadiness

SCHEMA_VERSION = "daily_equity_data_health_v1"
CONSUMER_ID = "dashboard_daily_equity_health"
READINESS = "SYNTHETIC_NOT_MARKET_READY"


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    return value


def _bytes(value):
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SessionFixture:
    state: str
    checked_at: datetime | None
    expires_at: datetime | None

    def __post_init__(self):
        if self.state not in {"SYNTHETIC_VALID", "UNKNOWN", "EXPIRED", "UNAVAILABLE"}:
            raise ValueError("Unknown synthetic session state")
        for value in (self.checked_at, self.expires_at):
            if value is not None and not _aware(value):
                raise ValueError("Session clocks must be aware or explicitly unknown")
        if self.state == "UNKNOWN" and (self.checked_at is not None or self.expires_at is not None):
            raise ValueError("Unknown session cannot imply clocks")
        if self.checked_at is not None and self.expires_at is not None and self.expires_at < self.checked_at:
            raise ValueError("Session expiry cannot precede its check")


@dataclass(frozen=True, slots=True)
class ReasonCount:
    code: str
    count: int

    def __post_init__(self):
        if type(self.code) is not str or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.code):
            raise ValueError("Sanitized aggregate reason required")
        if type(self.count) is not int or self.count < 1:
            raise ValueError("Positive reason count required")


@dataclass(frozen=True, slots=True)
class DailyEquityDataHealth:
    schema_version: str
    consumer_id: str
    fixture_version: str
    as_of: datetime
    input_hash: str
    batch_count: int
    requested_count: int
    returned_count: int
    missing_count: int
    valid_fixture_count: int
    unavailable_count: int
    stale_count: int
    earliest_provider_quote_time: datetime | None
    latest_provider_quote_time: datetime | None
    earliest_retrieval_completed_at: datetime | None
    latest_retrieval_completed_at: datetime | None
    oldest_inventory_as_of: datetime | None
    newest_inventory_as_of: datetime | None
    last_successful_refresh_at: datetime | None
    session_state: str
    reason_counts: tuple[ReasonCount, ...]
    readiness_state: str = READINESS
    can_fetch: bool = False
    can_expose_real_data: bool = False
    can_persist: bool = False

    def __post_init__(self):
        if (self.schema_version != SCHEMA_VERSION or self.consumer_id != CONSUMER_ID or
                self.readiness_state != READINESS or self.can_fetch is not False or
                self.can_expose_real_data is not False or self.can_persist is not False):
            raise ValueError("Offline synthetic health only")
        if not _version(self.fixture_version) or not _aware(self.as_of):
            raise ValueError("Version and caller-aware as-of required")
        if type(self.input_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}", self.input_hash):
            raise ValueError("Deterministic input binding required")
        for value in (self.batch_count, self.requested_count, self.returned_count,
                      self.missing_count, self.valid_fixture_count,
                      self.unavailable_count, self.stale_count):
            if type(value) is not int or value < 0:
                raise ValueError("Nonnegative aggregate counts required")
        if self.requested_count != self.valid_fixture_count + self.unavailable_count:
            raise ValueError("Availability reconciliation failed")
        if self.returned_count > self.requested_count or self.missing_count > self.requested_count:
            raise ValueError("Coverage reconciliation failed")
        for value in (self.earliest_provider_quote_time, self.latest_provider_quote_time,
                      self.earliest_retrieval_completed_at, self.latest_retrieval_completed_at,
                      self.oldest_inventory_as_of, self.newest_inventory_as_of,
                      self.last_successful_refresh_at):
            if value is not None and not _aware(value):
                raise ValueError("Health clocks must be aware or explicitly unknown")
        if type(self.reason_counts) is not tuple:
            raise ValueError("Immutable reason counts required")
        for reason in self.reason_counts:
            if type(reason) is not ReasonCount:
                raise ValueError("ReasonCount required")
            reason.__post_init__()

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _clock_bounds(records, attribute):
    values = tuple(getattr(row.fixture, attribute) for row in records
                   if _aware(getattr(row.fixture, attribute)))
    return (min(values), max(values)) if values else (None, None)


def build_health(*, mode, fixture_version, as_of, batches, session,
                 last_successful_refresh_at=None):
    """Aggregate existing fixture readiness without exposing record-level facts."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if not _version(fixture_version) or not _aware(as_of):
        raise ValueError("Fixture version and caller-aware as-of required")
    if type(batches) is not tuple or not 1 <= len(batches) <= 2:
        raise ValueError("One or two immutable batches required")
    if type(session) is not SessionFixture:
        raise ValueError("Synthetic session fixture required")
    session.__post_init__()
    if last_successful_refresh_at is not None and not _aware(last_successful_refresh_at):
        raise ValueError("Last successful refresh must be aware or explicitly unknown")
    if last_successful_refresh_at is not None and last_successful_refresh_at > as_of:
        raise ValueError("Last successful refresh cannot be in the future")
    if session.checked_at is not None and session.checked_at > as_of:
        raise ValueError("Session check cannot be in the future")
    if session.state == "SYNTHETIC_VALID" and (
            session.expires_at is None or session.expires_at < as_of):
        raise ValueError("Synthetic valid session must have an unexpired boundary")
    if session.state == "EXPIRED" and (session.expires_at is None or session.expires_at > as_of):
        raise ValueError("Expired session requires an elapsed expiry boundary")

    records = []
    for batch in batches:
        if type(batch) is not EquityReadiness:
            raise ValueError("Existing equity readiness batches required")
        batch.__post_init__()
        if batch.as_of.astimezone(timezone.utc) != as_of.astimezone(timezone.utc):
            raise ValueError("All batch as-of clocks must match")
        if len(batch.records) > 25:
            raise ValueError("Existing per-batch bound exceeded")
        records.extend(batch.records)
    if not 1 <= len(records) <= 50:
        raise ValueError("One to 50 aggregate records required")
    keys = tuple(row.instrument_key for row in records)
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate identities across batches")

    reason_tally = {}
    for row in records:
        for code in row.reason_codes:
            reason_tally[code] = reason_tally.get(code, 0) + 1
    if session.state != "SYNTHETIC_VALID":
        reason_tally[f"SESSION_{session.state}"] = 1
    reason_tally["SYNTHETIC_ONLY"] = len(records)
    if any(batch.permission_state not in {
            "NO_PERMISSION_EVIDENCE", "METADATA_ONLY_NOT_VERIFIED"} for batch in batches):
        raise ValueError("Unexpected permission promotion")
    reason_tally["PERMISSION_NOT_VERIFIED"] = len(records)
    if any(batch.market_session != "UNKNOWN" for batch in batches):
        raise ValueError("Unexpected market-session promotion")
    reason_tally["MARKET_SESSION_UNKNOWN"] = len(records)

    requested = len(records)
    returned = sum(row.fixture.source_state == "AVAILABLE" for row in records)
    missing = sum(row.fixture.source_state == "MISSING_ROW" or row.fixture.last_price is None
                  for row in records)
    valid = sum(row.value_state == "FIXTURE_VALID_ONLY" for row in records)
    stale = sum(any(code == "STALE_CACHE" or code.endswith("_STALE")
                    for code in row.reason_codes) for row in records)
    quote_min, quote_max = _clock_bounds(records, "provider_quote_time")
    retrieval_min, retrieval_max = _clock_bounds(records, "retrieval_completed_at")
    inventory_min, inventory_max = _clock_bounds(records, "inventory_as_of")
    reasons = tuple(ReasonCount(code, reason_tally[code]) for code in sorted(reason_tally))
    binding = hashlib.sha256(_bytes(dict(schema_version=SCHEMA_VERSION, mode=mode,
        fixture_version=fixture_version, as_of=as_of,
        batch_hashes=tuple(batch.content_hash for batch in batches), session=session,
        last_successful_refresh_at=last_successful_refresh_at))).hexdigest()
    return DailyEquityDataHealth(SCHEMA_VERSION, CONSUMER_ID, fixture_version, as_of,
        binding, len(batches), requested, returned, missing, valid, requested-valid, stale,
        quote_min, quote_max, retrieval_min, retrieval_max, inventory_min, inventory_max,
        last_successful_refresh_at, session.state, reasons)
