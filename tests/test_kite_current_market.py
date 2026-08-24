from datetime import datetime, timedelta, timezone

import pytest

from market_intel.foundation.kite_connect import KiteSession
from market_intel.foundation.kite_current_market import (
    MAX_QUOTE_SYMBOLS, KiteCurrentDataError, KiteCurrentMarketClient,
    KiteInvalidSessionError, KiteReadOnlyViolation,
)

CSV = """instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange
1,11,INFY,Infosys,0,,0,0.05,1,EQ,NSE,NSE
2,12,NIFTY 50,Nifty 50,0,,0,0.05,1,INDICES,INDICES,NSE
3,13,NIFTY26AUGFUT,Nifty,0,2026-08-27,0,0.05,65,FUT,NFO-FUT,NFO
4,14,NIFTY26AUG25000CE,Nifty,0,2026-08-27,25000,0.05,65,CE,NFO-OPT,NFO
"""


class Response:
    def __init__(self, *, body=None, text="", status=200, fail=False):
        self._body, self.text, self.status_code, self.fail = body, text, status, fail
    def json(self):
        if isinstance(self._body, Exception): raise self._body
        return self._body
    def raise_for_status(self):
        if self.fail: raise TimeoutError("response contains token-do-not-leak")


class Http:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def client(responses, now=None):
    return KiteCurrentMarketClient(KiteSession("key", "access", "AB123"), http=Http(responses), now=now)


def test_successful_session_validation_is_get_only():
    c = client([Response(body={"data": {"user_id": "AB123"}})])
    assert c.validate_session() == "AB123"
    assert c._http.calls[0][0].endswith("/user/profile")


@pytest.mark.parametrize("status", [401, 403])
def test_expired_or_invalid_token_is_explicit(status):
    with pytest.raises(KiteInvalidSessionError):
        client([Response(status=status)]).validate_session()


def test_token_exception_in_success_status_is_invalid_session():
    with pytest.raises(KiteInvalidSessionError):
        client([Response(body={"status": "error", "error_type": "TokenException"})]).validate_session()


def test_read_only_allowlist_rejects_orders_and_post_before_network():
    c = client([])
    with pytest.raises(KiteReadOnlyViolation): c._request("orders")
    with pytest.raises(KiteReadOnlyViolation): c._request("quote", method="POST")
    assert c._http.calls == []


def test_instrument_normalization_and_current_only_scope():
    snapshot = client([Response(text=CSV)]).discover_current_instruments()
    assert snapshot.scope == "CURRENT_TRADABLE_ONLY"
    assert len(snapshot.instruments) == 4
    assert {i.instrument_type for i in snapshot.instruments} == {"EQ", "INDICES", "FUT", "CE"}
    assert snapshot.instruments[0].provider_key == "NSE:INFY"
    with pytest.raises(TypeError): snapshot.as_historical_universe()


def test_quote_limit_and_inventory_validation():
    c = client([Response(text=CSV)])
    c.discover_current_instruments()
    with pytest.raises(ValueError): c.get_current_quotes([f"NSE:X{i}" for i in range(MAX_QUOTE_SYMBOLS + 1)])
    with pytest.raises(ValueError): c.get_current_quotes(["NSE:UNKNOWN"])
    assert len(c._http.calls) == 1


def test_quote_values_missing_rows_and_short_cache():
    clock = [datetime(2026, 8, 24, tzinfo=timezone.utc)]
    c = client([Response(text=CSV), Response(body={"data": {
        "NSE:INFY": {"last_price": 1500, "ohlc": {"open": 1490, "high": 1510, "low": 1480, "close": 1495}}
    }})], now=lambda: clock[0])
    c.discover_current_instruments()
    first = c.get_current_quotes(["NSE:INFY", "NSE:NIFTY 50"])
    assert first.cache_status == "LIVE_PROVIDER_VALUE"
    assert [q.status for q in first.quotes] == ["AVAILABLE", "MISSING"]
    clock[0] += timedelta(seconds=10)
    cached = c.get_current_quotes(["NSE:INFY", "NSE:NIFTY 50"])
    assert cached.cache_status == "FRESH_CACHE" and len(c._http.calls) == 2


def test_stale_cache_is_labeled_when_refresh_times_out():
    clock = [datetime(2026, 8, 24, tzinfo=timezone.utc)]
    c = client([Response(text=CSV), Response(body={"data": {"NSE:INFY": {"last_price": 1500}}}),
                Response(fail=True)], now=lambda: clock[0])
    c.discover_current_instruments(); c.get_current_quotes(["NSE:INFY"])
    clock[0] += timedelta(seconds=16)
    assert c.get_current_quotes(["NSE:INFY"]).cache_status == "STALE_CACHE"


def test_malformed_and_timeout_errors_are_sanitized():
    with pytest.raises(KiteCurrentDataError, match="unsupported schema"):
        client([Response(text="wrong,columns\n1,2")]).discover_current_instruments()
    with pytest.raises(KiteCurrentDataError) as caught:
        client([Response(fail=True)]).validate_session()
    assert "token-do-not-leak" not in str(caught.value)
    with pytest.raises(KiteCurrentDataError, match="malformed"):
        client([Response(body=ValueError("private"))]).validate_session()
    with pytest.raises(KiteCurrentDataError, match="malformed"):
        client([Response(body={"data": []})]).validate_session()
