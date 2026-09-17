"""Manual in-memory authentication only; no validation or market-data fetch."""
import re
from .foundation.kite_connect import KiteSession, KiteSessionState, disconnect, finish_login
from .foundation.kite_current_market import KiteCurrentMarketClient


def connect(state, *, method, http):
    # Capture widget values, then clear every prior session/cache before replacement.
    key = state.get("kite_api_key", "")
    secret = state.get("kite_api_secret", "")
    request_token = state.get("kite_request_token", "")
    access = state.get("kite_access_token_input", "")
    disconnect(state)
    state.pop("kite_ui_message", None)
    try:
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", key.strip()):
            raise ValueError("Enter a valid API key.")
        state["kite_api_key"] = key.strip()
        if method == "access_token":
            if type(access) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]{1,4096}", access.strip()):
                raise ValueError("Enter an access token, not a redirect URL or request token field.")
            state["kite_session"] = KiteSession(key.strip(), access.strip())
            state["kite_connection_state"] = KiteSessionState.AUTHENTICATED
            state["kite_ui_message"] = "Daily token attached locally; provider validation is pending."
        elif method == "request_token":
            if (type(secret) is not str or not 0 < len(secret.strip()) <= 1024 or
                    type(request_token) is not str or not 0 < len(request_token.strip()) <= 8192):
                raise ValueError("Enter API secret and the fresh request token or redirect URL.")
            state["kite_api_secret"] = secret
            state["kite_request_token"] = request_token
            finish_login(state, http=http)
        else:
            raise ValueError("Unknown login method.")
        if state.get("kite_session"):
            state["kite_client"] = KiteCurrentMarketClient(state["kite_session"], http=http)
            state["kite_validation_state"] = "NOT_VALIDATED"
    except ValueError as exc:
        state["kite_connection_state"] = KiteSessionState.INVALID
        state["kite_ui_error"] = str(exc)
    finally:
        for name in ("kite_api_secret", "kite_request_token", "kite_access_token_input"):
            state.pop(name, None)
