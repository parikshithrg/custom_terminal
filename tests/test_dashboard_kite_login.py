"""Daily login UX and secret cleanup without live provider access."""
import sys
from pathlib import Path
import pytest
from market_intel.dashboard_kite_login import connect
from market_intel.foundation.kite_connect import disconnect

ROOT = Path(__file__).resolve().parents[1]


class Http:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.fail:
            raise TimeoutError("private-secret-do-not-render")
        class Response:
            def json(self):
                return {"status": "success", "data": {"access_token": "fixture-access"}}
            def raise_for_status(self):
                pass
        return Response()
    def get(self, *args, **kwargs):
        raise AssertionError("Login must not fetch or validate data")


def inputs():
    return dict(kite_api_key="fixture-key", kite_api_secret="fixture-secret",
                kite_request_token="fixture-request", kite_access_token_input="fixture-access",
                kite_inventory="old-inventory", kite_last_quote_snapshot="old-quotes",
                kite_client="old-client", kite_session="old-session", unrelated="keep")


@pytest.mark.parametrize("method", ["request_token", "access_token"])
def test_manual_login_cleanup_and_no_data_pull(method):
    state, http = inputs(), Http()
    connect(state, method=method, http=http)
    assert state["kite_session"].access_token == "fixture-access"
    assert state["kite_validation_state"] == "NOT_VALIDATED"
    assert state["unrelated"] == "keep"
    assert len(http.calls) == (1 if method == "request_token" else 0)
    assert "kite_inventory" not in state and "kite_last_quote_snapshot" not in state
    for name in ("kite_api_secret", "kite_request_token", "kite_access_token_input"):
        assert name not in state
    assert "fixture-access" not in repr(state["kite_session"])
    disconnect(state)
    assert not any(key.startswith("kite_") for key in state if key not in {"kite_connection_state", "kite_ui_message"})


def test_failed_exchange_clears_old_session_and_hides_sensitive_error():
    state, http = inputs(), Http(fail=True)
    connect(state, method="request_token", http=http)
    assert len(http.calls) == 1 and "kite_session" not in state and "kite_client" not in state
    assert "private-secret" not in state["kite_ui_error"]
    assert "kite_api_secret" not in state and "kite_access_token_input" not in state


@pytest.mark.parametrize("updates,method", [
    ({"kite_api_key": ""}, "request_token"),
    ({"kite_api_secret": ""}, "request_token"),
    ({"kite_access_token_input": "https://invalid.example/token"}, "access_token"),
    ({"kite_access_token_input": "bad\r\nheader"}, "access_token"),
    ({}, "unknown"),
])
def test_invalid_input_has_no_requests_or_old_session(updates, method):
    state, http = inputs(), Http()
    state.update(updates)
    connect(state, method=method, http=http)
    assert not http.calls and "kite_session" not in state
    assert "kite_api_secret" not in state and "kite_access_token_input" not in state


def test_dashboard_login_interactions_with_zero_requests(monkeypatch):
    site = ROOT/".venv/Lib/site-packages"
    if site.exists() and str(site) not in sys.path:
        sys.path.append(str(site))
    pytest.importorskip("streamlit")
    import requests
    import socket
    def denied(*args, **kwargs):
        raise AssertionError("No network on Dashboard login panel")
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT/"app.py"), default_timeout=15).run()
    assert not app.exception and len(app.text_input) == 0
    app.button(key="dashboard_kite_login_button").click().run()
    assert not app.exception
    assert all(field.proto.type == 1 for field in app.text_input)  # PASSWORD protobuf enum.
    app.text_input(key="kite_api_key").input("fixture-key").run()
    app.text_input(key="kite_access_token_input").input("fixture-access").run()
    next(button for button in app.button if button.label == "Attach access token").click().run()
    assert not app.exception and len(app.text_input) == 0
    assert app.session_state["kite_validation_state"] == "NOT_VALIDATED"
    assert "125.500000000000000001" in " ".join(item.value for item in app.markdown)
    assert "fixture-access" not in " ".join(item.value for item in app.markdown)
    next(button for button in app.button if button.label == "Disconnect Kite and clear values").click().run()
    assert not app.exception
    assert all(not field.value for field in app.text_input)
