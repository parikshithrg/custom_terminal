from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from market_intel.foundation.current_market import (
    CurrentInstrument, CurrentInstrumentSnapshot, CurrentQuote, CurrentQuoteSnapshot,
)
from market_intel.foundation.current_market_health import (
    DeclaredExchangeCalendar, EntitlementClass, FreshnessClass, MarketSessionClass,
    build_health, claim_refresh, entitlement_status, freshness, inventory_diagnostics,
    market_session, provider_quote_age, sanitized_error_category, sanitized_health_json,
)

NOW = datetime(2026, 8, 26, 6, 0, tzinfo=timezone.utc)


def instrument(token, symbol, kind="EQ", *, exchange="NSE", segment="NSE", expiry=None,
               flags=()):
    return CurrentInstrument(token, token + 100, symbol, exchange, segment, kind, expiry,
                             0.0, 0.05, 1, flags)


def inventory(*items):
    return CurrentInstrumentSnapshot("kite_connect", NOW - timedelta(seconds=4), "2026-08-26",
        "/instruments", "v1", tuple(items))


def quotes(cache="LIVE_PROVIDER_VALUE", provider_time="2026-08-26 11:29:59"):
    return CurrentQuoteSnapshot("kite_connect", NOW - timedelta(seconds=2), "/quote", (
        CurrentQuote("NSE:A", "AVAILABLE", 10.0, None, provider_time),
        CurrentQuote("NSE:B", "MISSING", None, None, None, "Provider returned no value"),
    ), cache)


def test_inventory_aggregation_duplicates_incomplete_and_expired():
    snapshot = inventory(
        instrument(1, "A"), instrument(1, "A"), instrument(2, "NIFTY", "INDICES"),
        instrument(3, "FUT", "FUT", exchange="NFO", segment="NFO-FUT", expiry="2026-08-01"),
        instrument(4, "CALL", "CE", exchange="NFO", segment="NFO-OPT", expiry="2026-09-01"),
        instrument(5, "", flags=("MISSING_TRADINGSYMBOL",)),
    )
    result = inventory_diagnostics(snapshot, as_of=date(2026, 8, 26))
    assert result.total_instruments == 6
    assert (result.equities, result.indices, result.futures, result.options) == (3, 1, 1, 1)
    assert result.counts_by_exchange == {"NFO": 2, "NSE": 4}
    assert result.incomplete_rows == 1
    assert result.expired_derivatives == 1
    assert result.duplicate_provider_keys == 1
    assert result.duplicate_exchange_symbols == 1


def test_freshness_uses_cache_and_provider_time_honestly():
    assert freshness(None) == (FreshnessClass.NO_DATA, False)
    assert freshness(quotes("FRESH_CACHE")) == (FreshnessClass.FRESH_CACHE, True)
    assert freshness(quotes("STALE_CACHE")) == (FreshnessClass.STALE_CACHE, True)
    assert freshness(quotes(provider_time=None)) == (FreshnessClass.UNKNOWN_PROVIDER_TIME, False)
    assert freshness(quotes()) == (FreshnessClass.FRESH_NETWORK, True)
    assert provider_quote_age(quotes(), NOW) == 1.0
    assert provider_quote_age(quotes(provider_time="not-a-time"), NOW) is None


def test_market_session_requires_declared_calendar_and_handles_nontrading_days():
    assert market_session(NOW, None) == MarketSessionClass.UNKNOWN
    calendar = DeclaredExchangeCalendar("test-v1", "Asia/Kolkata",
        frozenset({date(2026, 8, 26)}), frozenset({date(2026, 8, 27)}))
    assert market_session(datetime(2026, 8, 26, 3, 35, tzinfo=timezone.utc), calendar) == MarketSessionClass.PRE_OPEN
    assert market_session(datetime(2026, 8, 26, 6, 0, tzinfo=timezone.utc), calendar) == MarketSessionClass.OPEN
    assert market_session(datetime(2026, 8, 26, 11, 0, tzinfo=timezone.utc), calendar) == MarketSessionClass.POST_CLOSE
    assert market_session(datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc), calendar) == MarketSessionClass.NON_TRADING_DAY


def test_entitlement_classification_does_not_infer_permission_from_missing():
    assert entitlement_status(quotes(), None) == EntitlementClass.PROVIDER_NO_VALUE_UNCERTAIN
    assert entitlement_status(None, "EXPLICIT_PERMISSION_LIMIT") == EntitlementClass.EXPLICIT_PERMISSION_LIMIT
    assert entitlement_status(None, "INVALID_LOCAL_SELECTION") == EntitlementClass.INVALID_LOCAL_SELECTION
    assert entitlement_status(None, "INVALID_SESSION") == EntitlementClass.INVALID_SESSION


def test_refresh_cooldown_is_user_triggered_and_bounded():
    state = {}
    assert claim_refresh(state, "quotes", NOW, seconds=5) == (True, 0.0)
    allowed, remaining = claim_refresh(state, "quotes", NOW + timedelta(seconds=2), seconds=5)
    assert allowed is False and remaining == 3.0
    assert claim_refresh(state, "quotes", NOW + timedelta(seconds=5), seconds=5) == (True, 0.0)


def test_sanitized_health_export_contains_only_aggregate_contract():
    health = build_health(now=NOW, session_state="AUTHENTICATED", validation_state="VALID",
        inventory=inventory(instrument(1, "A")), quotes=quotes(), requested_count=2,
        last_error=None, calendar=None)
    exported = sanitized_health_json(health)
    body = json.loads(exported)
    assert body["scope"] == "CURRENT_TRADABLE_ONLY"
    assert body["market_session"] == "UNKNOWN"
    assert body["requested_instrument_count"] == 2
    assert body["returned_instrument_count"] == 1
    assert body["missing_instrument_count"] == 1
    assert not any(term in exported for term in ("access_token", "api_secret", "authorization_header", "user_id"))
    with pytest.raises(TypeError): health.as_historical_capability()


def test_sanitized_error_categories():
    class KiteEntitlementError(Exception): pass
    class KiteInvalidSessionError(Exception): pass
    class KiteCurrentDataError(Exception): pass
    assert sanitized_error_category(KiteEntitlementError()) == "EXPLICIT_PERMISSION_LIMIT"
    assert sanitized_error_category(KiteInvalidSessionError()) == "INVALID_SESSION"
    assert sanitized_error_category(ValueError()) == "INVALID_LOCAL_SELECTION"
    assert sanitized_error_category(KiteCurrentDataError("request failed")) == "TEMPORARY_PROVIDER_FAILURE"
