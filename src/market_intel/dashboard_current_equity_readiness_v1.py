"""Offline, invented current-equity readiness evaluation; never source activation."""
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re

SCHEMA_VERSION = "dashboard_current_equity_readiness_v1"
READINESS = "SYNTHETIC_NOT_MARKET_READY"


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _identity(value):
    return type(value) is str and re.fullmatch(r"SYNTHETIC:[A-Z0-9][A-Z0-9_.-]{0,63}", value)


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


@dataclass(frozen=True, slots=True)
class EquityPolicy:
    version: str
    identity_version: str
    semantics_version: str
    max_quote_age_seconds: int
    max_retrieval_age_seconds: int
    max_inventory_age_seconds: int
    permission_metadata_hash: str | None = None

    def __post_init__(self):
        if not all(_version(value) for value in
                   (self.version, self.identity_version, self.semantics_version)):
            raise ValueError("Explicit versioned policies required")
        for value in (self.max_quote_age_seconds, self.max_retrieval_age_seconds,
                      self.max_inventory_age_seconds):
            if type(value) is not int or not 0 <= value <= 86400:
                raise ValueError("Explicit bounded fixture age policy required")
        if self.permission_metadata_hash is not None and (
                type(self.permission_metadata_hash) is not str or
                not re.fullmatch(r"[0-9a-f]{64}", self.permission_metadata_hash)):
            raise ValueError("Invalid permission metadata binding")


@dataclass(frozen=True, slots=True)
class EquityFixtureRecord:
    instrument_key: str
    provider_token: str
    exchange: str
    instrument_class: str
    display_symbol: str
    currency: str
    last_price: Decimal | None
    missing_reason: str | None
    provider_quote_time: datetime | None
    last_trade_time: datetime | None
    retrieval_completed_at: datetime | None
    inventory_as_of: datetime | None
    cache_state: str
    source_state: str = "AVAILABLE"
    event_time: None = None
    published_at: None = None
    provider: str = "SYNTHETIC:PROVIDER"
    source_endpoint: str = "SYNTHETIC:QUOTE"
    parser_version: str = "fixture_parser_v1"

    def __post_init__(self):
        if not _identity(self.instrument_key) or not _identity(self.provider_token):
            raise ValueError("Invented synthetic identities only")
        if not _identity(self.provider) or not _identity(self.source_endpoint) or not _version(self.parser_version):
            raise ValueError("Synthetic provenance and versioned parser required")
        if not (type(self.display_symbol) is str and
                re.fullmatch(r"DEMO EQUITY [A-Z0-9 _.-]{1,40}", self.display_symbol)):
            raise ValueError("Invented display symbol required")
        if type(self.exchange) is not str or not re.fullmatch(r"[A-Z]{1,16}", self.exchange):
            raise ValueError("Bounded exchange classification required")
        if type(self.instrument_class) is not str or not re.fullmatch(r"[A-Z_]{1,24}", self.instrument_class):
            raise ValueError("Bounded instrument classification required")
        if type(self.currency) is not str or not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("Currency required")
        if self.last_price is not None and type(self.last_price) is not Decimal:
            raise ValueError("Exact Decimal required; floats cannot recover source precision")
        if self.missing_reason is not None and not (
                type(self.missing_reason) is str and
                re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.missing_reason)):
            raise ValueError("Sanitized missing reason required")
        for value in (self.provider_quote_time, self.last_trade_time,
                      self.retrieval_completed_at, self.inventory_as_of):
            if value is not None and type(value) is not datetime:
                raise ValueError("Clock must be datetime or explicitly unknown")
        if self.cache_state not in {"NETWORK", "FRESH_CACHE", "STALE_CACHE", "UNKNOWN"}:
            raise ValueError("Unknown cache classification")
        if self.source_state not in {"AVAILABLE", "MISSING_ROW", "ACCESS_FAILURE", "TRANSPORT_FAILURE"}:
            raise ValueError("Unknown source state")
        if self.event_time is not None or self.published_at is not None:
            raise ValueError("Fixture quote clock is not authoritative event/publication time")


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat() if _aware(value) else value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
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
class RecordReadiness:
    instrument_key: str
    fixture: EquityFixtureRecord
    value_state: str
    display_price: Decimal | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EquityReadiness:
    schema_version: str
    consumer_id: str
    fixture_version: str
    as_of: datetime
    input_hash: str
    records: tuple[RecordReadiness, ...]
    permission_state: str
    readiness_state: str = READINESS
    market_session: str = "UNKNOWN"
    can_fetch: bool = False
    can_expose_real_data: bool = False

    def __post_init__(self):
        if (self.schema_version != SCHEMA_VERSION or
                self.consumer_id != "dashboard_illustrative_watchlist" or
                self.readiness_state != READINESS or self.market_session != "UNKNOWN" or
                self.can_fetch is not False or self.can_expose_real_data is not False):
            raise ValueError("Real source activation is not implemented")

    def to_bytes(self):
        self.__post_init__()
        return _bytes(self)

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def evaluate(*, mode, fixture_version, as_of, policy, records):
    """Assess fixture quality only. No permission claim is treated as verified rights."""
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if not _version(fixture_version) or not _aware(as_of):
        raise ValueError("Fixture version and caller-aware as-of required")
    if type(policy) is not EquityPolicy:
        raise ValueError("Explicit policy required; no production defaults")
    policy.__post_init__()
    if type(records) is not tuple or len(records) > 25:
        raise ValueError("At most 25 immutable in-memory records required")
    for record in records:
        if type(record) is not EquityFixtureRecord:
            raise ValueError("Only invented fixture records accepted")
        record.__post_init__()
    keys = tuple(record.instrument_key for record in records)
    tokens = tuple(record.provider_token for record in records)
    results = []
    for record in records:
        reasons = []
        if keys.count(record.instrument_key) > 1 or tokens.count(record.provider_token) > 1:
            reasons.append("AMBIGUOUS_IDENTITY")
        if record.exchange != "SIMULATED" or record.instrument_class != "EQ":
            reasons.append("INELIGIBLE_IDENTITY")
        if record.currency != "INR":
            reasons.append("INCOMPATIBLE_CURRENCY")
        if record.source_state != "AVAILABLE":
            reasons.append(record.source_state)
        price = record.last_price
        if price is None:
            reasons.append("MISSING_PRICE")
            reasons.append(record.missing_reason or "MISSING_REASON_UNSPECIFIED")
        elif not price.is_finite() or price <= 0:
            reasons.append("INVALID_PRICE")
        elif record.missing_reason is not None:
            reasons.append("INCONSISTENT_MISSINGNESS")
        if record.cache_state in {"STALE_CACHE", "UNKNOWN"}:
            reasons.append(record.cache_state)
        clocks = (("QUOTE", record.provider_quote_time, policy.max_quote_age_seconds),
                  ("RETRIEVAL", record.retrieval_completed_at, policy.max_retrieval_age_seconds),
                  ("INVENTORY", record.inventory_as_of, policy.max_inventory_age_seconds))
        for name, value, limit in clocks:
            if not _aware(value):
                reasons.append(f"{name}_TIME_UNKNOWN_OR_NAIVE")
            elif value > as_of:
                reasons.append(f"{name}_TIME_FUTURE")
            elif (as_of - value).total_seconds() > limit:
                reasons.append(f"{name}_STALE")
        trade = record.last_trade_time
        if not _aware(trade):
            reasons.append("TRADE_TIME_UNKNOWN_OR_NAIVE")
        elif trade > as_of:
            reasons.append("TRADE_TIME_FUTURE")
        quote, retrieval, inventory = (record.provider_quote_time,
                                      record.retrieval_completed_at, record.inventory_as_of)
        if _aware(quote) and _aware(trade) and trade > quote:
            reasons.append("TRADE_AFTER_QUOTE")
        if _aware(quote) and _aware(retrieval) and quote > retrieval:
            reasons.append("QUOTE_AFTER_RETRIEVAL")
        if _aware(inventory) and _aware(retrieval) and inventory > retrieval:
            reasons.append("INVENTORY_AFTER_RETRIEVAL")
        codes = tuple(dict.fromkeys(reasons))
        results.append(RecordReadiness(record.instrument_key, record,
                       "UNAVAILABLE" if codes else "FIXTURE_VALID_ONLY",
                       None if codes else price, codes))
    binding = hashlib.sha256(_bytes(dict(schema_version=SCHEMA_VERSION, mode=mode, fixture_version=fixture_version,
                                        as_of=as_of, policy=policy, records=records))).hexdigest()
    return EquityReadiness(SCHEMA_VERSION, "dashboard_illustrative_watchlist",
                          fixture_version, as_of, binding, tuple(results),
                          "METADATA_ONLY_NOT_VERIFIED" if policy.permission_metadata_hash
                          else "NO_PERMISSION_EVIDENCE")
