"""Invented inputs for the offline Daily Equity Data Health contract."""
from dataclasses import replace
from datetime import timedelta

from .dashboard_current_equity_fixtures_v1 import (
    AS_OF, FIXTURE_VERSION, fixture_policy, fixture_records,
)
from .dashboard_current_equity_readiness_v1 import evaluate
from .daily_equity_data_health_v1 import SessionFixture

HEALTH_FIXTURE_VERSION = "daily_equity_health_fixture_v1"


def readiness_batches():
    first = fixture_records()[0]
    second = replace(first, instrument_key="SYNTHETIC:EQUITY_B",
                     provider_token="SYNTHETIC:TOKEN_B",
                     display_symbol="DEMO EQUITY B",
                     provider_quote_time=first.provider_quote_time-timedelta(seconds=2))
    common = dict(mode="SYNTHETIC", fixture_version=FIXTURE_VERSION,
                  as_of=AS_OF, policy=fixture_policy())
    return (evaluate(records=(first,), **common), evaluate(records=(second,), **common))


def session_fixture():
    return SessionFixture("SYNTHETIC_VALID", AS_OF-timedelta(seconds=1),
                          AS_OF+timedelta(minutes=10))
