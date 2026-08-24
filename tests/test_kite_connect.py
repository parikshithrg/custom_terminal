from hashlib import sha256

import pytest

from market_intel.foundation.kite_connect import (
    SESSION_URL, KiteAuthenticationError, build_login_url, current_data_scope,
    exchange_request_token, extract_request_token,
)


class Response:
    def __init__(self, body, failure=False): self.body, self.failure = body, failure
    def raise_for_status(self):
        if self.failure: raise RuntimeError("provider response containing sensitive material")
    def json(self): return self.body


class Http:
    def __init__(self, response): self.response, self.call = response, None
    def post(self, url, *, data, timeout):
        self.call = (url, data, timeout)
        return self.response


def test_login_url_and_redirect_token_parsing():
    assert build_login_url("abc") == "https://kite.zerodha.com/connect/login?v=3&api_key=abc"
    assert extract_request_token("one-time") == "one-time"
    assert extract_request_token("http://127.0.0.1:8501/?request_token=xyz") == "xyz"


def test_daily_session_exchange_uses_official_checksum():
    http = Http(Response({"data": {"access_token": "access", "user_id": "AB123"}}))
    session = exchange_request_token("key", "secret", "request", http=http)
    assert session.authorization_header == "token key:access"
    url, data, timeout = http.call
    assert url == SESSION_URL
    assert data["checksum"] == sha256(b"keyrequestsecret").hexdigest()
    assert timeout == 20


def test_authentication_error_does_not_leak_secrets():
    with pytest.raises(KiteAuthenticationError) as caught:
        exchange_request_token("key", "very-secret", "one-time", http=Http(Response({}, True)))
    rendered = str(caught.value)
    assert "very-secret" not in rendered and "one-time" not in rendered
    assert "sensitive material" not in rendered


def test_kite_scope_cannot_approve_historical_universe():
    scope = current_data_scope()
    assert scope["scope"] == "CURRENT_TRADABLE_ONLY"
    assert scope["trade_execution_enabled"] is False
    assert scope["historical_universe_approved"] is False
    assert scope["delisted_instruments_in_live_view"] is False
