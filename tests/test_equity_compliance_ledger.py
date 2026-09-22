import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from market_intel.equity_cash_session_policy_fixtures_v1 import PUBLISHED_AT, policy_fixture
from market_intel.equity_cash_session_policy_v1 import resolve_session
from market_intel.equity_compliance_ledger_fixtures_v1 import (
    CODE_VERSION,
    COMPLETED_AT,
    LEDGER_VERSION,
    POLICY_VERSION,
    RECORDED_AT,
    STARTED_AT,
    compliance_record_fixture,
    session_resolution_fixture,
)
from market_intel.equity_compliance_ledger_v1 import build_compliance_record


ROOT = Path(__file__).resolve().parents[1]


def build(**updates):
    args = dict(
        mode="SYNTHETIC", ledger_version=LEDGER_VERSION,
        policy_version=POLICY_VERSION, code_version=CODE_VERSION,
        recorded_at=RECORDED_AT, request_started_at=STARTED_AT,
        request_completed_at=COMPLETED_AT, request_count=2,
        requested_count=50, returned_count=50, missing_count=0,
        unavailable_count=0, response_byte_count=4096,
        outcome_state="SYNTHETIC_SUCCESS", reason_codes=(),
        session_resolution=session_resolution_fixture(),
    )
    args.update(updates)
    return build_compliance_record(**args)


def test_record_is_deterministic_sanitized_and_hash_bound():
    record = compliance_record_fixture()
    assert record.to_bytes() == compliance_record_fixture().to_bytes()
    assert record.content_hash == compliance_record_fixture().content_hash
    assert record.duration_milliseconds == 250
    assert record.session_resolution_hash == session_resolution_fixture().content_hash
    assert record.cache_policy == "TRANSIENT_MEMORY_ONLY"
    assert record.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not record.raw_payload_retained and not record.contains_credentials
    assert not record.contains_instrument_identities and not record.contains_prices
    assert not record.can_persist and not record.can_authorize_requests
    assert not record.can_authorize_display and not record.research_eligible
    assert not record.production_eligible
    encoded = record.to_bytes().lower()
    for forbidden in (b"api_key", b"access_token", b"authorization", b"instrument_token",
                      b"trading_symbol", b"last_price", b"c:\\users", b"125.50"):
        assert forbidden not in encoded


def test_exact_aggregate_envelope_contains_no_market_facts():
    payload = json.loads(build().to_bytes())
    assert set(payload) == {
        "schema_version", "ledger_version", "policy_version", "code_version",
        "consumer_id", "recorded_at", "request_started_at", "request_completed_at",
        "duration_milliseconds", "endpoint_category", "request_count",
        "requested_count", "returned_count", "missing_count", "unavailable_count",
        "response_byte_count", "outcome_state", "reason_codes",
        "session_resolution_hash", "cache_policy", "raw_payload_retained",
        "contains_credentials", "contains_instrument_identities", "contains_prices",
        "can_persist", "can_authorize_requests", "can_authorize_display",
        "research_eligible", "production_eligible", "readiness_state",
    }
    assert (payload["request_count"], payload["requested_count"],
            payload["returned_count"], payload["missing_count"]) == (2, 50, 50, 0)


def test_partial_and_failure_states_preserve_missingness():
    partial = build(returned_count=49, missing_count=1, unavailable_count=1,
                    outcome_state="SYNTHETIC_PARTIAL",
                    reason_codes=("ONE_RESULT_UNAVAILABLE", "ONE_RESULT_MISSING"))
    assert partial.reason_codes == ("ONE_RESULT_MISSING", "ONE_RESULT_UNAVAILABLE")
    failure = build(returned_count=0, missing_count=50, unavailable_count=0,
                    outcome_state="SYNTHETIC_FAILURE", response_byte_count=0,
                    reason_codes=("SYNTHETIC_TRANSPORT_FAILURE",))
    assert failure.missing_count == 50
    assert failure.outcome_state == "SYNTHETIC_FAILURE"


@pytest.mark.parametrize("updates", [
    {"mode": "LIVE"}, {"mode": "PROVIDER"}, {"ledger_version": ""},
    {"recorded_at": RECORDED_AT.replace(tzinfo=None)},
    {"request_started_at": COMPLETED_AT+timedelta(seconds=1)},
    {"request_count": 3}, {"requested_count": 51},
    {"returned_count": 49}, {"unavailable_count": 51},
    {"response_byte_count": 8*1024*1024+1},
    {"reason_codes": ["NOT_IMMUTABLE"]},
    {"reason_codes": ("DUPLICATE", "DUPLICATE")},
    {"reason_codes": ("private/path",)},
    {"missing_count": 1},
])
def test_malformed_unbounded_or_non_synthetic_inputs_fail_closed(updates):
    with pytest.raises((ValueError, TypeError)):
        build(**updates)


def test_success_cannot_hide_quality_problems():
    with pytest.raises(ValueError, match="Success cannot hide"):
        build(unavailable_count=1)
    with pytest.raises(ValueError, match="Success cannot hide"):
        build(reason_codes=("HIDDEN_PROBLEM",))


def test_unknown_or_expired_session_cannot_support_record():
    unknown = resolve_session(policy=policy_fixture(), session_date=date(2026, 9, 21),
                              evaluated_at=PUBLISHED_AT+timedelta(hours=1))
    with pytest.raises(ValueError, match="Unresolved session"):
        build(session_resolution=unknown)


def test_record_is_immutable_and_cannot_be_promoted():
    record = build()
    with pytest.raises(FrozenInstanceError):
        record.can_persist = True
    with pytest.raises(ValueError):
        replace(record, contains_prices=True)
    with pytest.raises(ValueError):
        replace(record, can_authorize_requests=True)
    with pytest.raises(ValueError):
        replace(record, readiness_state="MARKET_READY")


def test_no_io_clock_provider_ui_or_persistence_dependency(monkeypatch):
    import builtins
    import socket
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("Compliance contract must not access external state")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert build().to_bytes()
    monkeypatch.undo()
    for name in ("equity_compliance_ledger_v1.py",
                 "equity_compliance_ledger_fixtures_v1.py"):
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
    assert all("equity_compliance_ledger_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
