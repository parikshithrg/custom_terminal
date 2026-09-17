"""Pure synthetic-only Dashboard watchlist contract; no acquisition or rendering."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re

SCHEMA_VERSION = "dashboard_watchlist_read_model_v1"
CONSUMER_ID = "dashboard_illustrative_watchlist"
MODE = "SYNTHETIC"
READINESS = "SYNTHETIC_NOT_MARKET_READY"
MAX_RECORDS = 25
ENVELOPE_FIELDS = (
    "schema_version", "consumer_id", "mode", "as_of", "fixture_version",
    "fixture_hash", "records", "readiness_state", "reason_codes",
)
RECORD_FIELDS = (
    "instrument_id", "exchange", "instrument_class", "display_symbol", "currency",
    "last_price", "source_id", "source_record_id", "event_time", "published_at",
    "retrieved_at", "provider_timestamp", "value_state", "quality_flags",
)


def _time(value):
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")
    return value.astimezone(timezone.utc)


def _synthetic_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"SYNTHETIC:[A-Z0-9][A-Z0-9_.-]{0,63}", value):
        raise ValueError("Explicit synthetic identity required")


def _codes(value):
    if type(value) is not tuple or len(value) > 25:
        raise ValueError("Reason codes must be a bounded immutable tuple")
    if any(not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code)
           or any(word in code for word in ("QUARANTIN", "REAL_PROVIDER", "HISTORICAL", "UNCLASSIFIED", "DERIVATIVE"))
           for code in value):
        raise ValueError("Invalid or ineligible reason code")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate reason code")


@dataclass(frozen=True, slots=True)
class WatchlistRecord:
    instrument_id: str
    exchange: str
    instrument_class: str
    display_symbol: str
    currency: str
    last_price: Decimal | None
    source_id: str
    source_record_id: str
    event_time: datetime
    published_at: datetime
    retrieved_at: datetime
    provider_timestamp: None
    value_state: str
    quality_flags: tuple[str, ...]

    def __post_init__(self):
        if self.exchange != "SIMULATED" or self.instrument_class != "DEMO_EQUITY":
            raise ValueError("Only simulated demo equities are eligible")
        for value in (self.instrument_id, self.source_id, self.source_record_id):
            _synthetic_id(value)
        if not isinstance(self.display_symbol, str) or not re.fullmatch(r"DEMO EQUITY [A-Z0-9 _.-]{1,40}", self.display_symbol):
            raise ValueError("Synthetic display label required")
        if not isinstance(self.currency, str) or not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("Three-letter currency required")
        if self.provider_timestamp is not None:
            raise ValueError("Synthetic records cannot claim provider time")
        _codes(self.quality_flags)
        if self.last_price is None:
            if self.value_state != "MISSING" or "MISSING_PRICE" not in self.quality_flags:
                raise ValueError("Null price requires MISSING state and MISSING_PRICE reason")
        elif (type(self.last_price) is not Decimal or not self.last_price.is_finite()
              or self.last_price <= 0 or self.value_state != "AVAILABLE"
              or "MISSING_PRICE" in self.quality_flags):
            raise ValueError("Available price must be a finite positive Decimal")
        if not _time(self.event_time) <= _time(self.published_at) <= _time(self.retrieved_at):
            raise ValueError("Synthetic timestamps must be causally ordered")


def _record_payload(record):
    record.__post_init__()
    return {field: (_time(value).isoformat() if isinstance(value, datetime)
                    else str(value) if isinstance(value, Decimal) else value)
            for field in RECORD_FIELDS for value in (getattr(record, field),)}


def _payload(as_of, fixture_version, records):
    return dict(schema_version=SCHEMA_VERSION, consumer_id=CONSUMER_ID, mode=MODE,
                as_of=_time(as_of).isoformat(), fixture_version=fixture_version,
                records=[_record_payload(record) for record in records],
                readiness_state=READINESS,
                reason_codes=("SYNTHETIC_ONLY", "NOT_MARKET_EVIDENCE"))


def _bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _validate(as_of, fixture_version, records):
    cutoff = _time(as_of)
    if not isinstance(fixture_version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", fixture_version):
        raise ValueError("Fixture version required")
    if type(records) is not tuple or len(records) > MAX_RECORDS:
        raise ValueError("At most 25 immutable in-memory records required")
    identities, sources = set(), set()
    for record in records:
        if type(record) is not WatchlistRecord:
            raise ValueError("Only synthetic WatchlistRecord objects are accepted")
        record.__post_init__()
        if _time(record.retrieved_at) > cutoff:
            raise ValueError("Synthetic record is future-dated relative to as_of")
        if record.instrument_id in identities or record.source_record_id in sources:
            raise ValueError("Duplicate fixture instrument or source-record identity")
        identities.add(record.instrument_id)
        sources.add(record.source_record_id)


@dataclass(frozen=True, slots=True)
class WatchlistEnvelope:
    schema_version: str
    consumer_id: str
    mode: str
    as_of: datetime
    fixture_version: str
    fixture_hash: str
    records: tuple[WatchlistRecord, ...]
    readiness_state: str
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if (self.mode != MODE or self.schema_version != SCHEMA_VERSION
                or self.consumer_id != CONSUMER_ID or self.readiness_state != READINESS
                or self.reason_codes != ("SYNTHETIC_ONLY", "NOT_MARKET_EVIDENCE")):
            raise ValueError("Only the frozen synthetic Dashboard scope is permitted")
        _validate(self.as_of, self.fixture_version, self.records)
        expected = hashlib.sha256(_bytes(_payload(self.as_of, self.fixture_version, self.records))).hexdigest()
        if self.fixture_hash != expected:
            raise ValueError("Fixture content binding mismatch")

    def to_bytes(self):
        """Canonical JSON bytes only; no disk output. Recheck binding at boundary."""
        self.__post_init__()
        payload = _payload(self.as_of, self.fixture_version, self.records)
        payload["fixture_hash"] = self.fixture_hash
        return _bytes(payload)


def build_watchlist(*, mode, as_of, fixture_version, records):
    """Reject mode before touching records; no generator or provider evaluation."""
    if mode != MODE:
        raise ValueError("Non-synthetic input mode is prohibited")
    _validate(as_of, fixture_version, records)
    binding = hashlib.sha256(_bytes(_payload(as_of, fixture_version, records))).hexdigest()
    return WatchlistEnvelope(SCHEMA_VERSION, CONSUMER_ID, MODE, as_of,
                            fixture_version, binding, records, READINESS,
                            ("SYNTHETIC_ONLY", "NOT_MARKET_EVIDENCE"))


assert tuple(field.name for field in fields(WatchlistRecord)) == RECORD_FIELDS
assert tuple(field.name for field in fields(WatchlistEnvelope)) == ENVELOPE_FIELDS
