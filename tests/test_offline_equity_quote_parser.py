"""Bounded offline quote parsing without provider access or UI promotion."""
import ast
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest
from market_intel.offline_equity_quote_fixtures_v1 import AS_OF, RETRIEVAL, TARGETS, PAYLOAD, FIXTURE_VERSION
from market_intel.offline_equity_quote_parser_v1 import (
    FixtureTimezonePolicy, SyntheticTarget, parse_fixture_quotes,
)

ROOT = Path(__file__).resolve().parents[1]


def parse(payload=PAYLOAD, **kwargs):
    args = dict(mode="SYNTHETIC", fixture_version=FIXTURE_VERSION, payload=payload,
                targets=TARGETS, retrieval_completed_at=RETRIEVAL, as_of=AS_OF)
    args.update(kwargs)
    return parse_fixture_quotes(**args)


def mutate(**updates):
    body = json.loads(PAYLOAD)
    body["data"]["SYNTHETIC:EQUITY_A"].update(updates)
    return json.dumps(body).encode()


def test_exact_precision_binding_and_original_facts():
    result = parse()
    row = result.records[0]
    assert row.original_price == Decimal("125.500000000000000001")
    assert row.display_price is row.original_price
    assert row.provider_quote_time != row.last_trade_time
    assert row.original_quote_time == "2026-01-01T09:59:58+00:00"
    assert row.value_state == "FIXTURE_PARSED_ONLY"
    assert result.payload_hash == hashlib.sha256(PAYLOAD).hexdigest()
    assert result.to_bytes() == parse().to_bytes()
    assert result.content_hash == parse().content_hash
    assert json.loads(result.to_bytes())["records"][0]["original_price"] == "125.500000000000000001"
    assert result.permission_state == "NOT_VERIFIED"
    assert result.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not result.can_fetch and not result.can_expose_real_data
    with pytest.raises(FrozenInstanceError):
        row.display_price = Decimal("1")
    with pytest.raises(ValueError):
        replace(result, can_expose_real_data=True)
    assert result.content_hash != parse(PAYLOAD+b' ').content_hash


@pytest.mark.parametrize("literal", [b'125', b'125.5000', b'1.255e2'])
def test_integer_scale_and_exponent_prices(literal):
    result = parse(PAYLOAD.replace(b'125.500000000000000001', literal))
    assert str(result.records[0].original_price) == str(Decimal(literal.decode()))


@pytest.mark.parametrize("literal", [b'0', b'-1', b'NaN', b'Infinity', b'-Infinity', b'true', b'"125.5"'])
def test_invalid_prices_fail_entire_boundary(literal):
    with pytest.raises(ValueError):
        parse(PAYLOAD.replace(b'125.500000000000000001', literal))


def test_missing_row_and_null_price_do_not_disappear_or_zero_fill():
    row = parse(b'{"status":"success","data":{}}').records[0]
    assert row.reason_codes == ("MISSING_ROW",) and row.display_price is None
    row = parse(mutate(last_price=None)).records[0]
    assert "MISSING_PRICE" in row.reason_codes and row.original_price is None


@pytest.mark.parametrize("field,label", [("timestamp", "QUOTE"), ("last_trade_time", "TRADE")])
def test_null_absent_malformed_and_unresolved_naive_clocks(field, label):
    for value, reason in ((None, "NULL"), ("not-a-clock", "MALFORMED"),
                          ("2026-01-01T09:59:00", "NAIVE_UNRESOLVED")):
        row = parse(mutate(**{field: value})).records[0]
        assert f"{label}_TIME_{reason}" in row.reason_codes and row.display_price is None
        assert row.original_price is not None
    body = json.loads(PAYLOAD)
    del body["data"]["SYNTHETIC:EQUITY_A"][field]
    assert f"{label}_TIME_ABSENT" in parse(json.dumps(body).encode()).records[0].reason_codes


def test_explicit_fixture_timezone_policy_not_authoritative_rights():
    payload = mutate(timestamp="2026-01-01T15:29:58", last_trade_time="2026-01-01T15:29:00")
    policy = FixtureTimezonePolicy("fixture_timezone_v1", "Asia/Kolkata", "a"*64)
    result = parse(payload, timezone_policy=policy)
    assert result.records[0].provider_quote_time == parse().records[0].provider_quote_time
    assert result.records[0].value_state == "FIXTURE_PARSED_ONLY"
    assert result.permission_state == "NOT_VERIFIED" and not result.can_fetch
    assert result.content_hash != parse(payload).content_hash
    with pytest.raises(ValueError):
        FixtureTimezonePolicy("v1", "America/New_York", "a"*64)
    with pytest.raises(ValueError):
        FixtureTimezonePolicy("v1", "UTC", "owner-approved")


def test_future_ordering_and_retrieval_completion():
    row = parse(mutate(timestamp="2026-01-01T10:00:01+00:00")).records[0]
    assert "QUOTE_TIME_FUTURE" in row.reason_codes and "QUOTE_AFTER_RETRIEVAL" in row.reason_codes
    row = parse(mutate(last_trade_time="2026-01-01T10:00:01+00:00")).records[0]
    assert "TRADE_TIME_FUTURE" in row.reason_codes and "TRADE_AFTER_QUOTE" in row.reason_codes
    row = parse(retrieval_completed_at=RETRIEVAL-timedelta(seconds=2)).records[0]
    assert "QUOTE_AFTER_RETRIEVAL" in row.reason_codes
    for updates in (dict(as_of=AS_OF.replace(tzinfo=None)),
                    dict(retrieval_completed_at=RETRIEVAL.replace(tzinfo=None)),
                    dict(retrieval_completed_at=AS_OF+timedelta(seconds=1))):
        with pytest.raises(ValueError):
            parse(**updates)


@pytest.mark.parametrize("payload", [b'', b'\xff', b'{', b'[]', b'null', b'{}',
    b'{"status":"success","status":"success","data":{}}',
    b'{"status":"error","data":{}}', b'{"status":"success","data":[]}',
    b'{"status":"success","data":{},"extra":1}', b'{"x":'*9+b'0'+b'}'*9,
    b' '*65537], ids=["empty", "utf8", "malformed", "array", "null", "empty-object",
                     "duplicate", "error-status", "data-array", "extra-field", "depth", "size"])
def test_unsafe_json_failures_are_sanitized(payload):
    with pytest.raises(ValueError) as error:
        parse(payload)
    assert "SYNTHETIC:EQUITY_A" not in str(error.value)


def test_nested_duplicate_and_unselected_keys_and_bad_shapes():
    invalid = [PAYLOAD.replace(b'"instrument_token":1', b'"instrument_token":1,"instrument_token":1'),
               PAYLOAD.replace(b'SYNTHETIC:EQUITY_A', b'SYNTHETIC:EQUITY_B'),
               mutate(instrument_token=2), mutate(instrument_token=True), mutate(instrument_token=1.0),
               mutate(extra="unapproved"), mutate(timestamp=123), mutate(timestamp="x"*65),
               PAYLOAD.replace(b'125.500000000000000001', b'1e999999999999999999999999999'),
               PAYLOAD.replace(b'"last_price":125.500000000000000001,', b'')]
    for payload in invalid:
        with pytest.raises(ValueError):
            parse(payload)


def test_payload_size_exact_boundary_and_bound_crosswalk():
    assert parse(PAYLOAD+b' '*(65536-len(PAYLOAD))).records[0].display_price is not None
    maximum = tuple(SyntheticTarget(f"SYNTHETIC:EQUITY_{index}", index+1) for index in range(25))
    assert len(parse(b'{"status":"success","data":{}}', targets=maximum).records) == 25
    with pytest.raises(ValueError):
        parse(targets=TARGETS*2)
    with pytest.raises(ValueError):
        parse(targets=TARGETS*26)
    for targets in ([], (), (object(),), (TARGETS[0], SyntheticTarget("SYNTHETIC:EQUITY_B", 1))):
        with pytest.raises(ValueError):
            parse(targets=targets)
    with pytest.raises(ValueError):
        SyntheticTarget("NSE:REAL", 1)
    with pytest.raises(ValueError):
        SyntheticTarget("SYNTHETIC:FUTURE_A", 1)


@pytest.mark.parametrize("mode", ["REAL_PROVIDER", "HISTORICAL_NSE", "QUARANTINED", "DERIVATIVE"])
def test_non_synthetic_mode_refused_before_payload_evaluation(mode):
    with pytest.raises(ValueError, match="Synthetic fixtures only"):
        parse(payload=object(), mode=mode)


def test_no_io_or_provider_imports_and_no_ui_wiring(monkeypatch):
    import builtins
    import socket
    import requests
    def denied(*args, **kwargs):
        raise AssertionError("Parser must be offline")
    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert parse().to_bytes()
    monkeypatch.undo()
    allowed = {"dataclasses", "datetime", "decimal", "hashlib", "json", "re", "offline_equity_quote_parser_v1"}
    for name in ("offline_equity_quote_parser_v1.py", "offline_equity_quote_fixtures_v1.py"):
        tree = ast.parse((ROOT/"src/market_intel"/name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {"open", "eval", "exec", "__import__"}
                assert getattr(node.func, "attr", None) not in {"now", "today", "connect", "request", "write_text", "read_text"}
    assert all("offline_equity_quote_parser_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
