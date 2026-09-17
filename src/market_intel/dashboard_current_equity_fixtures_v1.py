"""Invented provider-shaped data; age limits are test values, not live policy."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from .dashboard_current_equity_readiness_v1 import EquityFixtureRecord, EquityPolicy

FIXTURE_VERSION = "current_equity_fixture_v1"
AS_OF = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)


def fixture_policy():
    return EquityPolicy("fixture_policy_v1", "fixture_identity_v1", "fixture_semantics_v1",
                        30, 15, 300)


def fixture_records():
    return (EquityFixtureRecord(
        "SYNTHETIC:EQUITY_A", "SYNTHETIC:TOKEN_A", "SIMULATED", "EQ", "DEMO EQUITY A",
        "INR", Decimal("125.500000000000000001"), None,
        AS_OF - timedelta(seconds=3), AS_OF - timedelta(seconds=60),
        AS_OF - timedelta(seconds=1), AS_OF - timedelta(seconds=120), "NETWORK"),)
