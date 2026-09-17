"""Bounded provider-specific quote decoding, not eligibility or activation."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal, DecimalException, localcontext, ROUND_HALF_UP
import hashlib
import json
import re

MAX_BYTES = 65536
IST = timezone(timedelta(hours=5, minutes=30))


def aware(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def price_text(price):
    """Two display decimals, explicit half-up rounding; never mutate source price."""
    if type(price) is not Decimal or not price.is_finite() or price <= 0:
        raise ValueError("Finite positive exact price required")
    if len(price.as_tuple().digits) > 64 or abs(price.as_tuple().exponent) > 64:
        raise ValueError("Price precision limit exceeded")
    with localcontext() as context:
        context.prec = 160
        return format(price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def constant(value):
    raise ValueError("Nonfinite JSON constant")


def bounded_tree(value, depth=0):
    if depth > 8:
        raise ValueError("JSON nesting limit exceeded")
    if isinstance(value, dict):
        for item in value.values():
            bounded_tree(item, depth+1)
    elif isinstance(value, list):
        for item in value:
            bounded_tree(item, depth+1)


def clock(item, field, label, reasons):
    value = item.get(field)
    if value is None:
        reasons.append(label+"_TIME_MISSING")
        return None
    if type(value) is not str or len(value) > 64:
        raise ValueError("Invalid clock shape")
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        reasons.append(label+"_TIME_MALFORMED")
        return None
    # Existing recorded Kite REST semantics specify IST for naive timestamps.
    return result if aware(result) else result.replace(tzinfo=IST)


@dataclass(frozen=True, slots=True)
class ExactEquityQuote:
    instrument_key: str
    instrument_token: int
    original_price: Decimal | None
    original_quote_time: str | None
    original_trade_time: str | None
    provider_quote_time: datetime | None
    last_trade_time: datetime | None
    display_price: str | None
    value_state: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExactEquityEnvelope:
    payload_hash: str
    retrieval_completed_at: datetime
    as_of: datetime
    records: tuple[ExactEquityQuote, ...]
    schema_version: str = "kite_equity_quote_v1"
    readiness_state: str = "PARSED_NOT_MARKET_READY"
    permission_state: str = "NOT_VERIFIED"
    currency_state: str = "NOT_VERIFIED"
    adjustment_state: str = "NOT_VERIFIED"
    freshness_state: str = "NOT_EVALUATED"
    can_fetch: bool = False
    can_expose_real_data: bool = False

    def to_bytes(self):
        if (self.schema_version != "kite_equity_quote_v1" or
                self.readiness_state != "PARSED_NOT_MARKET_READY" or
                any(getattr(self, field) != "NOT_VERIFIED" for field in
                    ("permission_state", "currency_state", "adjustment_state")) or
                self.freshness_state != "NOT_EVALUATED" or
                self.can_fetch is not False or self.can_expose_real_data is not False):
            raise ValueError("Source activation is not implemented")
        def encode(value):
            if type(value) is Decimal:
                return str(value)
            if type(value) is datetime:
                return value.astimezone(timezone.utc).isoformat()
            raise TypeError("Unsupported contract value")
        return json.dumps(asdict(self), default=encode, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode()

    @property
    def content_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()


def decode(*, payload, targets, retrieval_completed_at, as_of):
    """Targets are exact inventory-validated (provider key, numeric token) pairs."""
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_BYTES:
        raise ValueError("Bounded UTF-8 bytes required")
    if not aware(retrieval_completed_at) or not aware(as_of) or retrieval_completed_at > as_of:
        raise ValueError("Aware completion <= as-of required")
    if type(targets) is not tuple or not 1 <= len(targets) <= 25:
        raise ValueError("One to 25 immutable cash targets required")
    for target in targets:
        if (type(target) is not tuple or len(target) != 2 or type(target[0]) is not str or
                not re.fullmatch(r"(?:NSE|BSE):[A-Z0-9&_.-]{1,32}", target[0]) or
                type(target[1]) is not int or not 0 < target[1] < 2**32):
            raise ValueError("Explicit cash identity/token required")
    if len({key for key, _ in targets}) != len(targets) or len({token for _, token in targets}) != len(targets):
        raise ValueError("Ambiguous target binding")
    try:
        body = json.loads(payload.decode("utf-8"), parse_float=Decimal,
                          parse_constant=constant, object_pairs_hook=pairs)
        bounded_tree(body)
    except (ValueError, DecimalException, RecursionError):
        raise ValueError("Invalid bounded quote JSON") from None
    if (type(body) is not dict or set(body) != {"status", "data"} or body["status"] != "success" or
            type(body["data"]) is not dict or set(body["data"]) - {key for key, _ in targets}):
        raise ValueError("Unsupported or unselected quote response")
    records = []
    for key, token in targets:
        if key not in body["data"]:
            records.append(ExactEquityQuote(key, token, None, None, None, None, None,
                                           None, "UNAVAILABLE", ("MISSING_ROW",)))
            continue
        item = body["data"][key]
        if type(item) is not dict or not {"instrument_token", "last_price"} <= set(item):
            raise ValueError("Missing quote binding or price field")
        if type(item["instrument_token"]) is not int or item["instrument_token"] != token:
            raise ValueError("Provider token mismatch")
        price = item["last_price"]
        if type(price) is int:
            price = Decimal(price)
        display = None if price is None else price_text(price)
        reasons = ["MISSING_PRICE"] if price is None else []
        quote = clock(item, "timestamp", "QUOTE", reasons)
        trade = clock(item, "last_trade_time", "TRADE", reasons)
        if quote is not None and quote > retrieval_completed_at:
            reasons.append("QUOTE_AFTER_RETRIEVAL")
        if trade is not None and trade > retrieval_completed_at:
            reasons.append("TRADE_AFTER_RETRIEVAL")
        if quote is not None and trade is not None and trade > quote:
            reasons.append("TRADE_AFTER_QUOTE")
        records.append(ExactEquityQuote(key, token, price, item.get("timestamp"),
            item.get("last_trade_time"), quote, trade, None if reasons else display,
            "UNAVAILABLE" if reasons else "PARSED_UNQUALIFIED", tuple(reasons)))
    return ExactEquityEnvelope(hashlib.sha256(payload).hexdigest(), retrieval_completed_at,
                               as_of, tuple(records))
