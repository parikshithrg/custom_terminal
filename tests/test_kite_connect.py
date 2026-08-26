from hashlib import sha256

import pytest

from market_intel.foundation.kite_connect import (
    SESSION_URL, KiteAuthenticationError, KiteSession, KiteSessionState,
    build_login_url, current_data_scope, disconnect, exchange_request_token,
    extract_request_token, finish_login, invalidate_session,
)


class Response:
    def __init__(self, body, failure=False): self.body, self.failure = body, failure
    def raise_for_status(self):
        if self.failure: raise RuntimeError("provider response containing sensitive material")
    def json(self): return self.body


class Http:
    def __init__(self, response): self.response, self.call = response, None
    def post(self, url, *, data, headers, timeout):
        self.call = (url, data, headers, timeout)
        return self.response


def test_login_url_and_redirect_token_parsing():
    assert build_login_url("abc") == "https://kite.zerodha.com/connect/login?v=3&api_key=abc"
    assert extract_request_token("one-time") == "one-time"
    assert extract_request_token("http://127.0.0.1:8501/?request_token=xyz") == "xyz"


def test_daily_session_exchange_uses_official_checksum():
    http = Http(Response({"data": {"access_token": "access", "user_id": "AB123"}}))
    session = exchange_request_token("key", "secret", "request", http=http)
    assert session.authorization_header == "token key:access"
    url, data, headers, timeout = http.call
    assert url == SESSION_URL
    assert data["checksum"] == sha256(b"keyrequestsecret").hexdigest()
    assert headers == {"X-Kite-Version": "3"}
    assert timeout == 20


def test_authentication_error_does_not_leak_secrets():
    with pytest.raises(KiteAuthenticationError) as caught:
        exchange_request_token("key", "very-secret", "one-time", http=Http(Response({}, True)))
    rendered = str(caught.value)
    assert "very-secret" not in rendered and "one-time" not in rendered
    assert "sensitive material" not in rendered
    assert "AUTHENTICATION_ERROR" in rendered


def test_network_error_is_safely_classified():
    class NetworkHttp:
        def post(self, *args, **kwargs):
            raise ConnectionError("private network detail")
    with pytest.raises(KiteAuthenticationError) as caught:
        exchange_request_token("key", "secret", "request", http=NetworkHttp())
    assert "NETWORK_ERROR" in str(caught.value)
    assert "private network detail" not in str(caught.value)


def test_provider_error_exposes_only_safe_category():
    response = Response({"status": "error", "error_type": "InputException",
                         "message": "secret provider detail"})
    with pytest.raises(KiteAuthenticationError) as caught:
        exchange_request_token("key", "secret", "request", http=Http(response))
    assert "InputException" in str(caught.value)
    assert "secret provider detail" not in str(caught.value)


def test_kite_scope_cannot_approve_historical_universe():
    scope = current_data_scope()
    assert scope["scope"] == "CURRENT_TRADABLE_ONLY"
    assert scope["trade_execution_enabled"] is False
    assert scope["historical_universe_approved"] is False
    assert scope["delisted_instruments_in_live_view"] is False


def test_session_representation_is_redacted():
    rendered = repr(KiteSession("visible-id", "access-secret", "AB123"))
    assert "access-secret" not in rendered
    assert "visible-id" not in rendered
    assert "<redacted>" in rendered


def test_login_cleans_sensitive_inputs_on_success():
    state = {"kite_api_key": "key", "kite_api_secret": "secret", "kite_request_token": "request"}
    finish_login(state, http=Http(Response({"data": {"access_token": "access"}})))
    assert "kite_api_secret" not in state and "kite_request_token" not in state
    assert state["kite_connection_state"] == KiteSessionState.AUTHENTICATED


def test_failed_login_cleans_one_time_and_secret_values():
    state = {"kite_api_key": "key", "kite_api_secret": "secret", "kite_request_token": "request"}
    finish_login(state, http=Http(Response({}, True)))
    assert "kite_api_secret" not in state and "kite_request_token" not in state
    assert "kite_session" not in state
    assert state["kite_connection_state"] == KiteSessionState.INVALID


def test_disconnect_removes_all_session_material():
    state = {"kite_api_key": "key", "kite_api_secret": "secret", "kite_request_token": "request",
             "kite_session": object(), "kite_client": object(), "kite_inventory": object(),
             "kite_quote_cache": object(), "kite_authenticated_user": "AB123", "kite_last_request": "now"}
    disconnect(state)
    assert not any(key in state for key in ("kite_api_key", "kite_api_secret", "kite_request_token",
        "kite_session", "kite_client", "kite_inventory", "kite_quote_cache", "kite_authenticated_user"))
    assert state["kite_connection_state"] == KiteSessionState.DISCONNECTED


def test_provider_rejection_clears_access_material_and_marks_expired():
    state = {"kite_session": object(), "kite_client": object(), "kite_inventory": object()}
    invalidate_session(state, expired=True)
    assert not any(key in state for key in ("kite_session", "kite_client", "kite_inventory"))
    assert state["kite_connection_state"] == KiteSessionState.EXPIRED
