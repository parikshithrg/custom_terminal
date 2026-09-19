import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path

import pytest

from market_intel.daily_equity_data_health_fixtures_v1 import (
    AS_OF, HEALTH_FIXTURE_VERSION, readiness_batches, session_fixture,
)
from market_intel.daily_equity_data_health_v1 import build_health, SessionFixture

ROOT = Path(__file__).resolve().parents[1]


def build(**updates):
    args = dict(mode="SYNTHETIC", fixture_version=HEALTH_FIXTURE_VERSION,
                as_of=AS_OF, batches=readiness_batches(), session=session_fixture(),
                last_successful_refresh_at=AS_OF-timedelta(minutes=1))
    args.update(updates)
    return build_health(**args)


def test_deterministic_sanitized_aggregate_and_never_ready():
    result = build()
    assert result.to_bytes() == build().to_bytes()
    assert result.content_hash == build().content_hash
    assert (result.requested_count, result.returned_count, result.missing_count) == (2, 2, 0)
    assert (result.valid_fixture_count, result.unavailable_count, result.stale_count) == (2, 0, 0)
    assert result.batch_count == 2 and result.session_state == "SYNTHETIC_VALID"
    assert result.earliest_provider_quote_time < result.latest_provider_quote_time
    assert result.earliest_retrieval_completed_at == result.latest_retrieval_completed_at
    assert result.oldest_inventory_as_of == result.newest_inventory_as_of
    assert result.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not result.can_fetch and not result.can_expose_real_data and not result.can_persist
    reasons = {item.code: item.count for item in result.reason_counts}
    assert reasons["PERMISSION_NOT_VERIFIED"] == 2
    assert reasons["MARKET_SESSION_UNKNOWN"] == 2
    encoded = result.to_bytes()
    assert b"EQUITY_A" not in encoded and b"TOKEN_A" not in encoded
    assert b"125.5" not in encoded and b"display_symbol" not in encoded
    assert b"account" not in encoded.lower() and b"credential" not in encoded.lower()
    with pytest.raises(FrozenInstanceError):
        result.requested_count = 3
    with pytest.raises(ValueError):
        replace(result, can_fetch=True)


def test_exact_schema_and_deterministic_hash_bindings():
    payload = json.loads(build().to_bytes())
    assert set(payload) == {
        "schema_version", "consumer_id", "fixture_version", "as_of", "input_hash",
        "batch_count", "requested_count", "returned_count", "missing_count",
        "valid_fixture_count", "unavailable_count", "stale_count",
        "earliest_provider_quote_time", "latest_provider_quote_time",
        "earliest_retrieval_completed_at", "latest_retrieval_completed_at",
        "oldest_inventory_as_of", "newest_inventory_as_of",
        "last_successful_refresh_at", "session_state", "reason_counts",
        "readiness_state", "can_fetch", "can_expose_real_data", "can_persist",
    }
    assert build(last_successful_refresh_at=None).input_hash != build().input_hash
    assert build(session=SessionFixture("UNKNOWN", None, None)).input_hash != build().input_hash


@pytest.mark.parametrize("state", ["UNKNOWN", "EXPIRED", "UNAVAILABLE"])
def test_session_unavailable_states_are_explicit(state):
    expiry = AS_OF-timedelta(seconds=1) if state == "EXPIRED" else None
    checked = AS_OF-timedelta(seconds=2) if state != "UNKNOWN" else None
    result = build(session=SessionFixture(state, checked, expiry))
    reasons = {item.code: item.count for item in result.reason_counts}
    assert reasons[f"SESSION_{state}"] == 1
    assert result.readiness_state == "SYNTHETIC_NOT_MARKET_READY"


def test_missing_stale_and_unavailable_counts_reconcile():
    first, second = readiness_batches()
    broken_fixture = replace(second.records[0].fixture, last_price=None,
                             missing_reason="PROVIDER_NO_VALUE",
                             provider_quote_time=AS_OF-timedelta(seconds=31))
    broken_row = replace(second.records[0], fixture=broken_fixture,
                         value_state="UNAVAILABLE", display_price=None,
                         reason_codes=("MISSING_PRICE", "PROVIDER_NO_VALUE", "QUOTE_STALE"))
    result = build(batches=(first, replace(second, records=(broken_row,))))
    assert (result.requested_count, result.returned_count, result.missing_count) == (2, 2, 1)
    assert (result.valid_fixture_count, result.unavailable_count, result.stale_count) == (1, 1, 1)
    reasons = {item.code: item.count for item in result.reason_counts}
    assert reasons["MISSING_PRICE"] == 1 and reasons["QUOTE_STALE"] == 1


def test_missing_all_clocks_stay_explicitly_null():
    batch = readiness_batches()[0]
    fixture = replace(batch.records[0].fixture, provider_quote_time=None,
                      retrieval_completed_at=None, inventory_as_of=None)
    row = replace(batch.records[0], fixture=fixture, value_state="UNAVAILABLE",
                  display_price=None, reason_codes=("QUOTE_TIME_UNKNOWN_OR_NAIVE",))
    result = build(batches=(replace(batch, records=(row,)),))
    assert result.earliest_provider_quote_time is None
    assert result.latest_retrieval_completed_at is None
    assert result.oldest_inventory_as_of is None


@pytest.mark.parametrize("updates", [
    dict(mode="LIVE", batches=object()), dict(mode="HISTORICAL_NSE"),
    dict(mode="QUARANTINED"), dict(mode="DERIVATIVE"),
    dict(batches=[]), dict(batches=()), dict(batches=(object(),)),
    dict(batches=readiness_batches()*2), dict(session=object()),
    dict(as_of=AS_OF.replace(tzinfo=None)), dict(fixture_version=""),
    dict(last_successful_refresh_at=AS_OF+timedelta(seconds=1)),
])
def test_malformed_or_non_synthetic_inputs_fail_closed(updates):
    with pytest.raises(ValueError):
        build(**updates)


def test_cross_batch_duplicates_and_clock_mismatch_fail_closed():
    first = readiness_batches()[0]
    with pytest.raises(ValueError, match="Duplicate"):
        build(batches=(first, first))
    with pytest.raises(ValueError, match="as-of"):
        build(batches=(first, replace(readiness_batches()[1], as_of=AS_OF-timedelta(seconds=1))))


@pytest.mark.parametrize("session", [
    SessionFixture("UNKNOWN", None, None),
    SessionFixture("EXPIRED", AS_OF-timedelta(seconds=2), AS_OF-timedelta(seconds=1)),
])
def test_session_fixture_is_immutable(session):
    with pytest.raises(FrozenInstanceError):
        session.state = "SYNTHETIC_VALID"


def test_invalid_session_clock_semantics_refused():
    with pytest.raises(ValueError):
        SessionFixture("UNKNOWN", AS_OF, None)
    with pytest.raises(ValueError):
        SessionFixture("EXPIRED", AS_OF, AS_OF-timedelta(seconds=1))
    with pytest.raises(ValueError):
        build(session=SessionFixture("SYNTHETIC_VALID", AS_OF, AS_OF-timedelta(seconds=1)))
    with pytest.raises(ValueError):
        build(session=SessionFixture("EXPIRED", AS_OF-timedelta(seconds=1), AS_OF+timedelta(seconds=1)))


def test_no_io_wall_clock_provider_or_ui_dependency(monkeypatch):
    import builtins
    import socket
    import requests
    def denied(*args, **kwargs):
        raise AssertionError("Offline health must not access external state")
    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert build().to_bytes()
    monkeypatch.undo()
    for name in ("daily_equity_data_health_v1.py", "daily_equity_data_health_fixtures_v1.py"):
        tree = ast.parse((ROOT/"src/market_intel"/name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {"open", "eval", "exec", "__import__"}
                assert getattr(node.func, "attr", None) not in {
                    "now", "today", "connect", "request", "read_text", "write_text"
                }
    assert all("daily_equity_data_health_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
