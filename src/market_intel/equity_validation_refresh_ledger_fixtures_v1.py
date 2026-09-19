"""Invented inputs for the offline validation/refresh ledger contract."""
from datetime import timedelta

from .daily_equity_data_health_fixtures_v1 import (
    AS_OF,
    HEALTH_FIXTURE_VERSION,
    readiness_batches,
    session_fixture,
)
from .daily_equity_data_health_v1 import build_health

LEDGER_VERSION = "equity_validation_refresh_fixture_v1"
CODE_VERSION = "equity_health_code_v1"
CONFIGURATION_VERSION = "equity_health_config_v1"
POLICY_VERSION = "synthetic_validation_policy_v1"
RECORDED_AT = AS_OF + timedelta(seconds=1)


def health_fixture():
    return build_health(
        mode="SYNTHETIC",
        fixture_version=HEALTH_FIXTURE_VERSION,
        as_of=AS_OF,
        batches=readiness_batches(),
        session=session_fixture(),
        last_successful_refresh_at=AS_OF-timedelta(minutes=1),
    )
