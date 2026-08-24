"""Minimal Kite Connect authentication for current-market data access.

This module deliberately does not place orders and does not claim that Kite's
current instrument dump is a point-in-time historical security master.
Credentials and session tokens are memory-only values.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

LOGIN_URL = "https://kite.zerodha.com/connect/login"
SESSION_URL = "https://api.kite.trade/session/token"


class KiteAuthenticationError(RuntimeError):
    """A sanitized authentication failure safe to display in the UI."""


class HttpClient(Protocol):
    def post(self, url: str, *, data: dict[str, str], timeout: int) -> Any: ...


@dataclass(frozen=True)
class KiteSession:
    api_key: str
    access_token: str
    user_id: str | None = None

    @property
    def authorization_header(self) -> str:
        return f"token {self.api_key}:{self.access_token}"


def build_login_url(api_key: str) -> str:
    key = api_key.strip()
    if not key:
        raise ValueError("API key is required")
    return f"{LOGIN_URL}?{urlencode({'v': 3, 'api_key': key})}"


def extract_request_token(value: str) -> str:
    """Accept either a request token or the complete redirect URL."""
    supplied = value.strip()
    if not supplied:
        raise ValueError("Request token is required")
    if "://" not in supplied:
        return supplied
    token = parse_qs(urlparse(supplied).query).get("request_token", [""])[0]
    if not token:
        raise ValueError("The redirect URL does not contain request_token")
    return token


def exchange_request_token(
    api_key: str,
    api_secret: str,
    request_token_or_url: str,
    *,
    http: HttpClient,
) -> KiteSession:
    key = api_key.strip()
    secret = api_secret.strip()
    if not key or not secret:
        raise ValueError("API key and API secret are required")
    request_token = extract_request_token(request_token_or_url)
    checksum = sha256(f"{key}{request_token}{secret}".encode()).hexdigest()
    try:
        response = http.post(
            SESSION_URL,
            data={"api_key": key, "request_token": request_token, "checksum": checksum},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        access_token = data.get("access_token")
        if not access_token:
            raise KiteAuthenticationError("Kite did not return an access token")
        return KiteSession(key, str(access_token), data.get("user_id"))
    except KiteAuthenticationError:
        raise
    except Exception as exc:
        raise KiteAuthenticationError(
            "Kite login failed. Confirm the key, secret, and fresh request token."
        ) from exc


def current_data_scope() -> dict[str, object]:
    return {
        "scope": "CURRENT_TRADABLE_ONLY",
        "trade_execution_enabled": False,
        "historical_universe_approved": False,
        "delisted_instruments_in_live_view": False,
        "warning": (
            "Current instruments may exclude inactive securities and must not be "
            "used to construct historical cross-sectional universes."
        ),
    }
