"""Kite authentication primitives with redacted, memory-only session values."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any, MutableMapping, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

LOGIN_URL = "https://kite.zerodha.com/connect/login"
SESSION_URL = "https://api.kite.trade/session/token"
SENSITIVE_STATE_KEYS = ("kite_api_secret", "kite_request_token", "kite_session",
    "kite_client", "kite_inventory", "kite_quote_cache")

class KiteAuthenticationError(RuntimeError): pass
class KiteSessionState(StrEnum):
    UNAUTHENTICATED="UNAUTHENTICATED"; AUTHENTICATING="AUTHENTICATING"
    AUTHENTICATED="AUTHENTICATED"; EXPIRED="EXPIRED"; INVALID="INVALID"; DISCONNECTED="DISCONNECTED"
class HttpClient(Protocol):
    def post(self, url: str, *, data: dict[str, str], headers: dict[str, str],
             timeout: int) -> Any: ...

@dataclass(frozen=True, repr=False)
class KiteSession:
    api_key: str
    access_token: str
    user_id: str | None = None
    def __repr__(self) -> str:
        return f"KiteSession(api_key=<identifier>, access_token=<redacted>, user_id={self.user_id!r})"
    @property
    def authorization_header(self) -> str: return f"token {self.api_key}:{self.access_token}"

def build_login_url(api_key: str) -> str:
    key=api_key.strip()
    if not key: raise ValueError("API key is required")
    return f"{LOGIN_URL}?{urlencode({'v':3,'api_key':key})}"

def extract_request_token(value: str) -> str:
    supplied=value.strip()
    if not supplied: raise ValueError("Request token is required")
    if "://" not in supplied: return supplied
    token=parse_qs(urlparse(supplied).query).get("request_token",[""])[0]
    if not token: raise ValueError("The redirect URL does not contain request_token")
    return token

def exchange_request_token(api_key: str, api_secret: str, request_token_or_url: str,
                           *, http: HttpClient) -> KiteSession:
    key,secret=api_key.strip(),api_secret.strip()
    if not key or not secret or not request_token_or_url.strip():
        raise ValueError("API key, API secret, and request token are required")
    request_token=extract_request_token(request_token_or_url)
    checksum=sha256(f"{key}{request_token}{secret}".encode()).hexdigest()
    try:
        response=http.post(SESSION_URL,data={"api_key":key,"request_token":request_token,"checksum":checksum},
            headers={"X-Kite-Version":"3"},timeout=20)
        try:
            body=response.json()
        except Exception:
            body={}
        if isinstance(body,dict) and body.get("status")=="error":
            error_type=body.get("error_type")
            safe_types={"TokenException","InputException","PermissionException","NetworkException","GeneralException"}
            category=error_type if error_type in safe_types else "PROVIDER_ERROR"
            raise KiteAuthenticationError(f"Kite login failed ({category}). Use a fresh request token and verify your credentials.")
        response.raise_for_status(); data=body.get("data",{}) if isinstance(body,dict) else {}; access_token=data.get("access_token")
        if not access_token: raise KiteAuthenticationError("Kite did not return an access token")
        return KiteSession(key,str(access_token),data.get("user_id"))
    except KiteAuthenticationError: raise
    except Exception as exc:
        error_name=type(exc).__name__
        if error_name in {"ConnectionError","ConnectTimeout","ReadTimeout","TimeoutError"}:
            category="NETWORK_ERROR"
        else:
            category="AUTHENTICATION_ERROR"
        raise KiteAuthenticationError(f"Kite login failed ({category}). Use a fresh request token and verify your credentials.") from exc

def finish_login(state: MutableMapping[str,Any], *, http: HttpClient) -> None:
    state["kite_connection_state"]=KiteSessionState.AUTHENTICATING
    try:
        session=exchange_request_token(str(state.get("kite_api_key","")),str(state.get("kite_api_secret","")),str(state.get("kite_request_token","")),http=http)
        state["kite_session"]=session; state["kite_connection_state"]=KiteSessionState.AUTHENTICATED
        state.pop("kite_ui_error",None)
        state["kite_ui_message"]="Kite session authenticated."
    except (ValueError,KiteAuthenticationError) as exc:
        state.pop("kite_session",None); state["kite_connection_state"]=KiteSessionState.INVALID
        state["kite_ui_error"]=str(exc)
    finally:
        state.pop("kite_api_secret",None); state.pop("kite_request_token",None)

def disconnect(state: MutableMapping[str,Any], *, clear_api_key: bool=True) -> None:
    for key in SENSITIVE_STATE_KEYS: state.pop(key,None)
    if clear_api_key: state.pop("kite_api_key",None)
    state.pop("kite_authenticated_user",None); state.pop("kite_last_request",None)
    state["kite_connection_state"]=KiteSessionState.DISCONNECTED
    state["kite_ui_message"]="Disconnected. Values were removed from application references; Python memory is not claimed to be securely erased."

def invalidate_session(state: MutableMapping[str,Any], *, expired: bool=False) -> None:
    for key in ("kite_session","kite_client","kite_inventory","kite_quote_cache"):
        state.pop(key,None)
    state.pop("kite_authenticated_user",None)
    state["kite_connection_state"]=KiteSessionState.EXPIRED if expired else KiteSessionState.INVALID
    state["kite_ui_error"]="Kite rejected the session. Log in again with a fresh request token."

def current_data_scope() -> dict[str,object]:
    return {"scope":"CURRENT_TRADABLE_ONLY","trade_execution_enabled":False,
        "historical_universe_approved":False,"delisted_instruments_in_live_view":False,
        "warning":"Kite current instruments are not a historical universe and cannot validate historical cross-sectional research."}
