"""Invented aggregate inputs for the offline equity compliance record."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .equity_cash_session_policy_fixtures_v1 import policy_fixture
from .equity_cash_session_policy_v1 import resolve_session
from .equity_compliance_ledger_v1 import build_compliance_record


ZONE = ZoneInfo("Asia/Kolkata")
LEDGER_VERSION = "synthetic_equity_compliance_fixture_v1"
POLICY_VERSION = "private_transient_equity_policy_v1"
CODE_VERSION = "equity_compliance_contract_v1"
STARTED_AT = datetime(2026, 9, 14, 10, 0, tzinfo=ZONE)
COMPLETED_AT = STARTED_AT + timedelta(milliseconds=250)
RECORDED_AT = COMPLETED_AT + timedelta(milliseconds=10)


def session_resolution_fixture():
    return resolve_session(policy=policy_fixture(), session_date=date(2026, 9, 14),
                           evaluated_at=STARTED_AT)


def compliance_record_fixture():
    return build_compliance_record(
        mode="SYNTHETIC",
        ledger_version=LEDGER_VERSION,
        policy_version=POLICY_VERSION,
        code_version=CODE_VERSION,
        recorded_at=RECORDED_AT,
        request_started_at=STARTED_AT,
        request_completed_at=COMPLETED_AT,
        request_count=2,
        requested_count=50,
        returned_count=50,
        missing_count=0,
        unavailable_count=0,
        response_byte_count=4096,
        outcome_state="SYNTHETIC_SUCCESS",
        reason_codes=(),
        session_resolution=session_resolution_fixture(),
    )
