"""Bounded invented full-quote JSON parser; no provider or consumer activation."""
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException
import hashlib
import json
import re

SCHEMA_VERSION = "offline_equity_quote_parser_v1"
MAX_PAYLOAD_BYTES = 65536
MAX_TARGETS = 25


def _id(value):
    return type(value) is str and re.fullmatch(r"SYNTHETIC:[A-Z0-9][A-Z0-9_.-]{0,63}", value)


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True, slots=True)
class SyntheticTarget:
    instrument_key: str
    instrument_token: int

    def __post_init__(self):
        if (not _id(self.instrument_key) or not self.instrument_key.startswith("SYNTHETIC:EQUITY_") or
                type(self.instrument_token) is not int or not 0 < self.instrument_token <= 2**32-1):
            raise ValueError("Bounded synthetic target required")


@dataclass(frozen=True, slots=True)
class FixtureTimezonePolicy:
    version: str
    zone: str
    evidence_hash: str

    def __post_init__(self):
        if (not _version(self.version) or self.zone not in {"UTC", "Asia/Kolkata"} or
                type(self.evidence_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}", self.evidence_hash)):
            raise ValueError("Explicit bounded fixture timezone policy required")


def _canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat() if _aware(value) else value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    return value


@dataclass(frozen=True, slots=True)
class ParsedFixtureQuote:
    target: SyntheticTarget
    original_price: Decimal | None
    original_quote_time: str | None
    original_trade_time: str | None
    provider_quote_time: datetime | None
    last_trade_time: datetime | None
    display_price: Decimal | None
    value_state: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedFixtureEnvelope:
    schema_version: str
    fixture_version: str
    consumer_id: str
    payload_hash: str
    targets: tuple[SyntheticTarget, ...]
    timezone_policy: FixtureTimezonePolicy | None
    retrieval_completed_at: datetime
    as_of: datetime
    records: tuple[ParsedFixtureQuote, ...]
    permission_state: str = "NOT_VERIFIED"
    readiness_state: str = "SYNTHETIC_NOT_MARKET_READY"
    can_fetch: bool = False
    can_expose_real_data: bool = False

    def __post_init__(self):
        if (self.schema_version != SCHEMA_VERSION or self.consumer_id != "dashboard_illustrative_watchlist" or
                self.permission_state != "NOT_VERIFIED" or self.readiness_state != "SYNTHETIC_NOT_MARKET_READY" or
                self.can_fetch is not False or self.can_expose_real_data is not False):
            raise ValueError("Only offline synthetic parsing permitted")

    def to_bytes(self):
        self.__post_init__()
        return json.dumps(_canonical(self), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Nonfinite JSON constant")


def _nesting(text):
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[]":
            raise ValueError("JSON arrays not permitted")
        elif char == "{":
            depth += 1
            if depth > 8:
                raise ValueError("JSON nesting limit exceeded")
        elif char == "}":
            depth -= 1


def _clock(item, field, label, policy, reasons):
    value = item.get(field)
    if value is None:
        reasons.append(f"{label}_TIME_NULL" if field in item else f"{label}_TIME_ABSENT")
        return None
    if type(value) is not str or len(value) > 64:
        raise ValueError("Invalid clock field shape")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        reasons.append(f"{label}_TIME_MALFORMED")
        return None
    if not _aware(parsed):
        if policy is None:
            reasons.append(f"{label}_TIME_NAIVE_UNRESOLVED")
        else:
            zone = timezone.utc if policy.zone == "UTC" else timezone(timedelta(hours=5, minutes=30))
            parsed = parsed.replace(tzinfo=zone)
    return parsed


def parse_fixture_quotes(*, mode, fixture_version, payload, targets,
                         retrieval_completed_at, as_of, timezone_policy=None):
    if mode != "SYNTHETIC":
        raise ValueError("Synthetic fixtures only")
    if not _version(fixture_version) or type(payload) is not bytes or not 0 < len(payload) <= MAX_PAYLOAD_BYTES:
        raise ValueError("Bounded UTF-8 fixture bytes and version required")
    if (not _aware(retrieval_completed_at) or not _aware(as_of) or retrieval_completed_at > as_of):
        raise ValueError("Aware response-completion <= as-of required")
    if type(targets) is not tuple or not 1 <= len(targets) <= MAX_TARGETS:
        raise ValueError("One to 25 immutable targets required")
    for target in targets:
        if type(target) is not SyntheticTarget:
            raise ValueError("Synthetic target crosswalk required")
        target.__post_init__()
    if len({target.instrument_key for target in targets}) != len(targets) or len({target.instrument_token for target in targets}) != len(targets):
        raise ValueError("Ambiguous target crosswalk")
    if timezone_policy is not None:
        if type(timezone_policy) is not FixtureTimezonePolicy:
            raise ValueError("Explicit fixture timezone policy required")
        timezone_policy.__post_init__()
    try:
        text = payload.decode("utf-8")
        _nesting(text)
        body = json.loads(text, parse_float=Decimal, parse_int=Decimal,
                          parse_constant=_constant, object_pairs_hook=_pairs)
    except (ValueError, DecimalException, RecursionError, OverflowError):
        raise ValueError("Invalid or unsafe fixture JSON") from None
    if type(body) is not dict or set(body) != {"status", "data"} or body["status"] != "success" or type(body["data"]) is not dict:
        raise ValueError("Unsupported fixture envelope")
    data = body["data"]
    if set(data) - {target.instrument_key for target in targets}:
        raise ValueError("Unselected response identity")
    records = []
    for target in targets:
        if target.instrument_key not in data:
            records.append(ParsedFixtureQuote(target, None, None, None, None, None,
                                              None, "UNAVAILABLE", ("MISSING_ROW",)))
            continue
        item = data[target.instrument_key]
        if (type(item) is not dict or set(item) - {"instrument_token", "last_price", "timestamp", "last_trade_time"}
                or not {"instrument_token", "last_price"} <= set(item)):
            raise ValueError("Unsupported fixture quote shape")
        token = item["instrument_token"]
        if (type(token) is not Decimal or not token.is_finite() or token.as_tuple().exponent != 0
                or token != target.instrument_token):
            raise ValueError("Fixture token crosswalk mismatch")
        price = item["last_price"]
        if price is not None and (type(price) is not Decimal or not price.is_finite() or price <= 0):
            raise ValueError("Invalid fixture price")
        reasons = ["MISSING_PRICE"] if price is None else []
        quote = _clock(item, "timestamp", "QUOTE", timezone_policy, reasons)
        trade = _clock(item, "last_trade_time", "TRADE", timezone_policy, reasons)
        for label, value in (("QUOTE", quote), ("TRADE", trade)):
            if _aware(value) and value > as_of:
                reasons.append(f"{label}_TIME_FUTURE")
        if _aware(quote) and quote > retrieval_completed_at:
            reasons.append("QUOTE_AFTER_RETRIEVAL")
        if _aware(trade) and trade > retrieval_completed_at:
            reasons.append("TRADE_AFTER_RETRIEVAL")
        if _aware(quote) and _aware(trade) and trade > quote:
            reasons.append("TRADE_AFTER_QUOTE")
        records.append(ParsedFixtureQuote(target, price, item.get("timestamp"), item.get("last_trade_time"),
                       quote, trade, None if reasons else price,
                       "UNAVAILABLE" if reasons else "FIXTURE_PARSED_ONLY", tuple(reasons)))
    return ParsedFixtureEnvelope(SCHEMA_VERSION, fixture_version, "dashboard_illustrative_watchlist",
                                 hashlib.sha256(payload).hexdigest(), targets, timezone_policy,
                                 retrieval_completed_at, as_of, tuple(records))
