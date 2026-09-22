import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from market_intel.equity_cash_session_policy_fixtures_v1 import (
    CALENDAR_VERSION,
    PUBLISHED_AT,
    VALID_THROUGH,
    declared_sessions,
    policy_fixture,
)
from market_intel.equity_cash_session_policy_v1 import (
    DeclaredCashSession,
    build_policy,
    resolve_session,
)


ROOT = Path(__file__).resolve().parents[1]


def test_policy_is_deterministic_hash_bound_and_synthetic_only():
    policy = policy_fixture()
    assert policy.to_bytes() == policy_fixture().to_bytes()
    assert policy.content_hash == policy_fixture().content_hash
    assert policy.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not policy.can_fetch and not policy.can_persist
    assert not policy.can_authorize_display
    payload = json.loads(policy.to_bytes())
    assert payload["timezone_name"] == "Asia/Kolkata"
    assert len(payload["sessions"]) == 7


@pytest.mark.parametrize(("day", "state", "reason"), [
    (date(2026, 9, 14), "NORMAL", "DECLARED_NORMAL_SESSION"),
    (date(2026, 9, 15), "CLOSED", "DECLARED_SYNTHETIC_HOLIDAY"),
    (date(2026, 9, 20), "SPECIAL", "DECLARED_SYNTHETIC_SPECIAL_SESSION"),
])
def test_explicit_normal_closed_and_special_resolutions(day, state, reason):
    result = resolve_session(policy=policy_fixture(), session_date=day,
                             evaluated_at=PUBLISHED_AT+timedelta(hours=1))
    assert result.session_state == state
    assert result.reason_code == reason
    assert result.calendar_hash == policy_fixture().content_hash
    assert result.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not result.can_fetch and not result.can_authorize_display
    if state == "CLOSED":
        assert result.opens_at is None and result.closes_at is None
    else:
        assert result.opens_at < result.closes_at


def test_outside_coverage_and_expired_calendar_fail_closed():
    unknown = resolve_session(policy=policy_fixture(), session_date=date(2026, 9, 21),
                              evaluated_at=PUBLISHED_AT+timedelta(hours=1))
    assert unknown.session_state == "UNKNOWN_DATE"
    assert unknown.reason_code == "DATE_NOT_EXPLICITLY_DECLARED"
    expired = resolve_session(policy=policy_fixture(), session_date=date(2026, 9, 14),
                              evaluated_at=VALID_THROUGH+timedelta(microseconds=1))
    assert expired.session_state == "CALENDAR_EXPIRED"
    assert expired.reason_code == "CALENDAR_VALIDITY_EXPIRED"


def test_every_date_must_be_explicit_unique_sorted_and_contiguous():
    sessions = declared_sessions()
    common = dict(mode="SYNTHETIC", calendar_version=CALENDAR_VERSION,
                  published_at=PUBLISHED_AT, coverage_start=sessions[0].session_date,
                  coverage_end=sessions[-1].session_date, valid_through=VALID_THROUGH)
    with pytest.raises(ValueError, match="Every covered"):
        build_policy(**common, sessions=sessions[:2]+sessions[3:])
    with pytest.raises(ValueError, match="unique and sorted"):
        build_policy(**common, sessions=(sessions[1], sessions[0], *sessions[2:]))
    with pytest.raises(ValueError, match="unique and sorted"):
        build_policy(**common, sessions=(sessions[0], sessions[0], *sessions[2:]))


@pytest.mark.parametrize("updates", [
    {"mode": "LIVE"},
    {"calendar_version": ""},
    {"published_at": PUBLISHED_AT.replace(tzinfo=None)},
    {"valid_through": PUBLISHED_AT-timedelta(seconds=1)},
    {"sessions": []},
    {"sessions": tuple()},
])
def test_policy_boundaries_reject_malformed_or_non_synthetic_inputs(updates):
    sessions = declared_sessions()
    args = dict(mode="SYNTHETIC", calendar_version=CALENDAR_VERSION,
                published_at=PUBLISHED_AT, coverage_start=sessions[0].session_date,
                coverage_end=sessions[-1].session_date, valid_through=VALID_THROUGH,
                sessions=sessions)
    args.update(updates)
    with pytest.raises(ValueError):
        build_policy(**args)


def test_declaration_time_and_kind_validation():
    day = date(2026, 9, 14)
    naive = datetime(2026, 9, 14, 9, 15)
    aware = naive.replace(tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        DeclaredCashSession(day, "NORMAL", naive, aware, "DECLARED_NORMAL_SESSION")
    with pytest.raises(ValueError):
        DeclaredCashSession(day, "CLOSED", aware, aware+timedelta(hours=1),
                            "DECLARED_CLOSURE")
    with pytest.raises(ValueError):
        DeclaredCashSession(day, "UNKNOWN", None, None, "UNKNOWN_SESSION")
    with pytest.raises(ValueError):
        DeclaredCashSession(day, "CLOSED", None, None, "private/path")


def test_policy_and_resolution_are_immutable_and_cannot_be_promoted():
    policy = policy_fixture()
    resolution = resolve_session(policy=policy, session_date=date(2026, 9, 14),
                                 evaluated_at=PUBLISHED_AT+timedelta(hours=1))
    with pytest.raises(FrozenInstanceError):
        policy.can_fetch = True
    with pytest.raises(ValueError):
        replace(policy, can_authorize_display=True)
    with pytest.raises(ValueError):
        replace(resolution, readiness_state="MARKET_READY")


def test_no_io_clock_provider_ui_or_persistence_dependency(monkeypatch):
    import builtins
    import socket
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("Session policy must not access external state")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert resolve_session(policy=policy_fixture(), session_date=date(2026, 9, 14),
                           evaluated_at=PUBLISHED_AT+timedelta(hours=1)).to_bytes()
    monkeypatch.undo()
    for name in ("equity_cash_session_policy_v1.py",
                 "equity_cash_session_policy_fixtures_v1.py"):
        tree = ast.parse((ROOT/"src/market_intel"/name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all("kite" not in alias.name and "streamlit" not in alias.name
                           for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert "kite" not in (node.module or "")
                assert "streamlit" not in (node.module or "")
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {
                    "open", "eval", "exec", "__import__"
                }
                assert getattr(node.func, "attr", None) not in {
                    "now", "today", "connect", "request", "read_text", "write_text"
                }
    assert all("equity_cash_session_policy_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
