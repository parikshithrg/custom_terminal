"""Strong synthetic anomaly fixtures for read-only equity quality diagnostics."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from .dashboard_current_equity_fixtures_v1 import (
    AS_OF,
    FIXTURE_VERSION,
    fixture_policy,
    fixture_records,
)
from .dashboard_current_equity_readiness_v1 import evaluate
from .equity_quality_diagnostics_v1 import SyntheticSessionContext

DIAGNOSTIC_VERSION = "equity_quality_diagnostic_fixture_v1"
EXPECTED_KEYS = ("SYNTHETIC:EQUITY_A", "SYNTHETIC:EQUITY_B")


def session(state="TRADING_SESSION"):
    return SyntheticSessionContext("synthetic_session_calendar_v1", AS_OF.date(), state)


def _evaluate(records):
    return evaluate(mode="SYNTHETIC", fixture_version=FIXTURE_VERSION,
                    as_of=AS_OF, policy=fixture_policy(), records=records)


def clean_readiness():
    first = fixture_records()[0]
    second = replace(first, instrument_key=EXPECTED_KEYS[1],
                     provider_token="SYNTHETIC:TOKEN_B",
                     display_symbol="DEMO EQUITY B")
    return _evaluate((first, second))


def partial_readiness():
    return _evaluate((fixture_records()[0],))


def anomaly_readiness():
    first = fixture_records()[0]
    duplicate = replace(first, provider_token="SYNTHETIC:TOKEN_DUPLICATE",
                        display_symbol="DEMO EQUITY DUPLICATE")
    missing = replace(first, instrument_key=EXPECTED_KEYS[1],
                      provider_token="SYNTHETIC:TOKEN_B",
                      display_symbol="DEMO EQUITY B", last_price=None,
                      missing_reason="PROVIDER_NO_VALUE", source_state="MISSING_ROW")
    nonfinite = replace(first, instrument_key="SYNTHETIC:EQUITY_C",
                        provider_token="SYNTHETIC:TOKEN_C",
                        display_symbol="DEMO EQUITY C", last_price=Decimal("NaN"))
    stale_semantics = replace(first, instrument_key="SYNTHETIC:EQUITY_D",
                              provider_token="SYNTHETIC:TOKEN_D",
                              display_symbol="DEMO EQUITY D", currency="USD",
                              provider_quote_time=AS_OF-timedelta(seconds=31))
    return _evaluate((first, duplicate, missing, nonfinite, stale_semantics))
