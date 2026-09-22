"""Invented declarations for the offline cash-session policy contract."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .equity_cash_session_policy_v1 import DeclaredCashSession, build_policy


ZONE = ZoneInfo("Asia/Kolkata")
CALENDAR_VERSION = "synthetic_cash_calendar_fixture_v1"
PUBLISHED_AT = datetime(2026, 9, 13, 12, 0, tzinfo=ZONE)
VALID_THROUGH = datetime(2026, 9, 21, 0, 0, tzinfo=ZONE)


def _clock(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZONE)


def declared_sessions():
    days = tuple(date(2026, 9, day) for day in range(14, 21))
    return (
        DeclaredCashSession(days[0], "NORMAL", _clock(days[0], 9, 15),
                            _clock(days[0], 15, 30), "DECLARED_NORMAL_SESSION"),
        DeclaredCashSession(days[1], "CLOSED", None, None, "DECLARED_SYNTHETIC_HOLIDAY"),
        DeclaredCashSession(days[2], "NORMAL", _clock(days[2], 9, 15),
                            _clock(days[2], 15, 30), "DECLARED_NORMAL_SESSION"),
        DeclaredCashSession(days[3], "NORMAL", _clock(days[3], 9, 15),
                            _clock(days[3], 15, 30), "DECLARED_NORMAL_SESSION"),
        DeclaredCashSession(days[4], "NORMAL", _clock(days[4], 9, 15),
                            _clock(days[4], 15, 30), "DECLARED_NORMAL_SESSION"),
        DeclaredCashSession(days[5], "CLOSED", None, None, "DECLARED_WEEKEND_CLOSURE"),
        DeclaredCashSession(days[6], "SPECIAL", _clock(days[6], 10, 0),
                            _clock(days[6], 11, 0), "DECLARED_SYNTHETIC_SPECIAL_SESSION"),
    )


def policy_fixture():
    sessions = declared_sessions()
    return build_policy(
        mode="SYNTHETIC",
        calendar_version=CALENDAR_VERSION,
        published_at=PUBLISHED_AT,
        coverage_start=sessions[0].session_date,
        coverage_end=sessions[-1].session_date,
        valid_through=VALID_THROUGH,
        sessions=sessions,
    )
