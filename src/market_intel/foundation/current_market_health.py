"""Ephemeral health diagnostics for current-market data only."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from enum import StrEnum
from typing import Any, MutableMapping
from zoneinfo import ZoneInfo

from .current_market import CURRENT_SCOPE, CurrentInstrumentSnapshot, CurrentQuoteSnapshot

IST = ZoneInfo("Asia/Kolkata")


class FreshnessClass(StrEnum):
    FRESH_NETWORK = "FRESH_NETWORK"
    FRESH_CACHE = "FRESH_CACHE"
    STALE_CACHE = "STALE_CACHE"
    NO_DATA = "NO_DATA"
    UNKNOWN_PROVIDER_TIME = "UNKNOWN_PROVIDER_TIME"


class MarketSessionClass(StrEnum):
    PRE_OPEN = "PRE_OPEN"
    OPEN = "OPEN"
    POST_CLOSE = "POST_CLOSE"
    NON_TRADING_DAY = "NON_TRADING_DAY"
    UNKNOWN = "UNKNOWN"


class EntitlementClass(StrEnum):
    CLEAR = "CLEAR"
    INVALID_LOCAL_SELECTION = "INVALID_LOCAL_SELECTION"
    PROVIDER_NO_VALUE_UNCERTAIN = "PROVIDER_NO_VALUE_UNCERTAIN"
    EXPLICIT_PERMISSION_LIMIT = "EXPLICIT_PERMISSION_LIMIT"
    INVALID_SESSION = "INVALID_SESSION"
    TEMPORARY_PROVIDER_FAILURE = "TEMPORARY_PROVIDER_FAILURE"
    UNKNOWN_SANITIZED_ERROR = "UNKNOWN_SANITIZED_ERROR"


@dataclass(frozen=True)
class DeclaredExchangeCalendar:
    version: str
    timezone: str
    trading_dates: frozenset[date]
    non_trading_dates: frozenset[date]


@dataclass(frozen=True)
class InventoryDiagnostics:
    total_instruments: int
    equities: int
    indices: int
    futures: int
    options: int
    counts_by_exchange: dict[str, int]
    counts_by_segment: dict[str, int]
    counts_by_instrument_type: dict[str, int]
    incomplete_rows: int
    expired_derivatives: int
    duplicate_provider_keys: int
    duplicate_exchange_symbols: int


@dataclass(frozen=True)
class CurrentMarketHealth:
    provider: str
    session_state: str
    validation_state: str
    inventory_retrieval_timestamp: str | None
    inventory_age_seconds: float | None
    quote_retrieval_timestamp: str | None
    quote_age_seconds: float | None
    provider_quote_age_seconds: float | None
    freshness: str
    provider_time_known: bool
    market_session: str
    calendar_version: str
    calendar_timezone: str
    requested_instrument_count: int
    returned_instrument_count: int
    missing_instrument_count: int
    inventory_counts_by_exchange: dict[str, int]
    inventory_counts_by_segment: dict[str, int]
    inventory_counts_by_instrument_type: dict[str, int]
    invalid_or_incomplete_inventory_rows: int
    expired_derivatives: int
    duplicate_provider_keys: int
    duplicate_exchange_symbols: int
    entitlement_status: str
    stale_cache: bool
    last_sanitized_provider_error: str | None
    scope: str = CURRENT_SCOPE

    def as_historical_capability(self) -> None:
        raise TypeError("Current-market health cannot promote historical capabilities")


def inventory_diagnostics(snapshot: CurrentInstrumentSnapshot, *, as_of: date) -> InventoryDiagnostics:
    instruments = snapshot.instruments
    by_exchange = Counter(item.exchange or "<MISSING>" for item in instruments)
    by_segment = Counter(item.segment or "<MISSING>" for item in instruments)
    by_type = Counter(item.instrument_type or "<MISSING>" for item in instruments)
    provider_keys = Counter(item.provider_key for item in instruments)
    exchange_symbols = Counter((item.exchange, item.trading_symbol) for item in instruments)
    incomplete = sum(bool(item.quality_flags) for item in instruments)
    expired = 0
    for item in instruments:
        if item.instrument_type not in {"FUT", "CE", "PE"} or not item.expiry:
            continue
        try:
            expired += date.fromisoformat(item.expiry) < as_of
        except ValueError:
            incomplete += 1
    return InventoryDiagnostics(
        total_instruments=len(instruments),
        equities=by_type.get("EQ", 0),
        indices=by_type.get("INDICES", 0),
        futures=by_type.get("FUT", 0),
        options=by_type.get("CE", 0) + by_type.get("PE", 0),
        counts_by_exchange=dict(sorted(by_exchange.items())),
        counts_by_segment=dict(sorted(by_segment.items())),
        counts_by_instrument_type=dict(sorted(by_type.items())),
        incomplete_rows=incomplete,
        expired_derivatives=expired,
        duplicate_provider_keys=sum(count - 1 for count in provider_keys.values() if count > 1),
        duplicate_exchange_symbols=sum(count - 1 for count in exchange_symbols.values() if count > 1),
    )


def market_session(now: datetime, calendar: DeclaredExchangeCalendar | None) -> MarketSessionClass:
    if calendar is None or calendar.timezone != "Asia/Kolkata":
        return MarketSessionClass.UNKNOWN
    local = now.astimezone(IST)
    if local.date() in calendar.non_trading_dates:
        return MarketSessionClass.NON_TRADING_DAY
    if local.date() not in calendar.trading_dates:
        return MarketSessionClass.UNKNOWN
    current = local.time().replace(tzinfo=None)
    if time(9, 0) <= current < time(9, 15):
        return MarketSessionClass.PRE_OPEN
    if time(9, 15) <= current <= time(15, 30):
        return MarketSessionClass.OPEN
    return MarketSessionClass.POST_CLOSE


def provider_quote_age(snapshot: CurrentQuoteSnapshot | None, now: datetime) -> float | None:
    if snapshot is None:
        return None
    parsed = []
    for quote in snapshot.quotes:
        if not quote.provider_timestamp:
            continue
        try:
            value = datetime.fromisoformat(quote.provider_timestamp)
            if value.tzinfo is None:
                value = value.replace(tzinfo=IST)
            parsed.append(value.astimezone(timezone.utc))
        except ValueError:
            continue
    if not parsed:
        return None
    return max(0.0, (now.astimezone(timezone.utc) - max(parsed)).total_seconds())


def freshness(snapshot: CurrentQuoteSnapshot | None, now: datetime | None = None) -> tuple[FreshnessClass, bool]:
    if snapshot is None or not snapshot.quotes:
        return FreshnessClass.NO_DATA, False
    if snapshot.cache_status == "STALE_CACHE":
        return FreshnessClass.STALE_CACHE, any(q.provider_timestamp for q in snapshot.quotes)
    if snapshot.cache_status == "FRESH_CACHE":
        return FreshnessClass.FRESH_CACHE, any(q.provider_timestamp for q in snapshot.quotes)
    provider_known = (provider_quote_age(snapshot, now) is not None if now else
                      any(q.provider_timestamp for q in snapshot.quotes))
    return (FreshnessClass.FRESH_NETWORK if provider_known else FreshnessClass.UNKNOWN_PROVIDER_TIME,
            provider_known)


def entitlement_status(snapshot: CurrentQuoteSnapshot | None, error_category: str | None) -> EntitlementClass:
    if error_category == "INVALID_LOCAL_SELECTION":
        return EntitlementClass.INVALID_LOCAL_SELECTION
    if error_category == "EXPLICIT_PERMISSION_LIMIT":
        return EntitlementClass.EXPLICIT_PERMISSION_LIMIT
    if error_category == "INVALID_SESSION":
        return EntitlementClass.INVALID_SESSION
    if error_category == "TEMPORARY_PROVIDER_FAILURE":
        return EntitlementClass.TEMPORARY_PROVIDER_FAILURE
    if error_category:
        return EntitlementClass.UNKNOWN_SANITIZED_ERROR
    if snapshot and any(quote.status == "MISSING" for quote in snapshot.quotes):
        return EntitlementClass.PROVIDER_NO_VALUE_UNCERTAIN
    return EntitlementClass.CLEAR


def sanitized_error_category(exc: Exception) -> str:
    name = type(exc).__name__
    if name == "KiteEntitlementError":
        return "EXPLICIT_PERMISSION_LIMIT"
    if name == "KiteInvalidSessionError":
        return "INVALID_SESSION"
    if isinstance(exc, ValueError):
        return "INVALID_LOCAL_SELECTION"
    if name == "KiteCurrentDataError" and "request failed" in str(exc):
        return "TEMPORARY_PROVIDER_FAILURE"
    return "UNKNOWN_SANITIZED_ERROR"


def cooldown_remaining(last_request: datetime | None, now: datetime, *, seconds: int = 5) -> float:
    if last_request is None:
        return 0.0
    return max(0.0, seconds - (now - last_request).total_seconds())


def claim_refresh(state: MutableMapping[str, Any], key: str, now: datetime,
                  *, seconds: int = 5) -> tuple[bool, float]:
    state_key = f"kite_refresh_{key}"
    remaining = cooldown_remaining(state.get(state_key), now, seconds=seconds)
    if remaining > 0:
        return False, remaining
    state[state_key] = now
    return True, 0.0


def build_health(*, now: datetime, session_state: str, validation_state: str,
                 inventory: CurrentInstrumentSnapshot | None,
                 quotes: CurrentQuoteSnapshot | None, requested_count: int,
                 last_error: str | None,
                 calendar: DeclaredExchangeCalendar | None = None) -> CurrentMarketHealth:
    diagnostics = inventory_diagnostics(inventory, as_of=now.astimezone(IST).date()) if inventory else None
    fresh, provider_known = freshness(quotes, now)
    provider_age = provider_quote_age(quotes, now)
    returned = sum(q.status == "AVAILABLE" for q in quotes.quotes) if quotes else 0
    missing = sum(q.status != "AVAILABLE" for q in quotes.quotes) if quotes else 0
    session_label = market_session(now, calendar)
    return CurrentMarketHealth(
        provider="kite_connect", session_state=session_state, validation_state=validation_state,
        inventory_retrieval_timestamp=inventory.retrieved_at.isoformat() if inventory else None,
        inventory_age_seconds=max(0.0, (now - inventory.retrieved_at).total_seconds()) if inventory else None,
        quote_retrieval_timestamp=quotes.retrieved_at.isoformat() if quotes else None,
        quote_age_seconds=max(0.0, (now - quotes.retrieved_at).total_seconds()) if quotes else None,
        provider_quote_age_seconds=provider_age,
        freshness=fresh, provider_time_known=provider_known, market_session=session_label,
        calendar_version=calendar.version if calendar else "UNAVAILABLE",
        calendar_timezone=calendar.timezone if calendar else "Asia/Kolkata",
        requested_instrument_count=requested_count, returned_instrument_count=returned,
        missing_instrument_count=missing,
        inventory_counts_by_exchange=diagnostics.counts_by_exchange if diagnostics else {},
        inventory_counts_by_segment=diagnostics.counts_by_segment if diagnostics else {},
        inventory_counts_by_instrument_type=diagnostics.counts_by_instrument_type if diagnostics else {},
        invalid_or_incomplete_inventory_rows=diagnostics.incomplete_rows if diagnostics else 0,
        expired_derivatives=diagnostics.expired_derivatives if diagnostics else 0,
        duplicate_provider_keys=diagnostics.duplicate_provider_keys if diagnostics else 0,
        duplicate_exchange_symbols=diagnostics.duplicate_exchange_symbols if diagnostics else 0,
        entitlement_status=entitlement_status(quotes, last_error),
        stale_cache=fresh == FreshnessClass.STALE_CACHE,
        last_sanitized_provider_error=last_error, scope=CURRENT_SCOPE,
    )


def sanitized_health_json(health: CurrentMarketHealth) -> str:
    return json.dumps(asdict(health), sort_keys=True, indent=2) + "\n"
