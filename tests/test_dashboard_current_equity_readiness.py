"""Offline fixture evaluation, exactness and non-authorization regression checks."""
import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from market_intel.dashboard_current_equity_fixtures_v1 import (
    AS_OF, FIXTURE_VERSION, fixture_policy, fixture_records,
)
from market_intel.dashboard_current_equity_readiness_v1 import evaluate

ROOT = Path(__file__).resolve().parents[1]


def assess(records=None, **kwargs):
    args = dict(mode="SYNTHETIC", fixture_version=FIXTURE_VERSION, as_of=AS_OF,
                policy=fixture_policy(), records=fixture_records() if records is None else records)
    args.update(kwargs)
    return evaluate(**args)


def test_exact_deterministic_immutable_and_never_ready():
    records = fixture_records()
    result = assess(records)
    assert result.to_bytes() == assess(records).to_bytes()
    assert result.content_hash == assess(records).content_hash
    assert b'125.500000000000000001' in result.to_bytes()
    assert result.records[0].value_state == "FIXTURE_VALID_ONLY"
    assert result.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert result.market_session == "UNKNOWN"
    assert not result.can_fetch and not result.can_expose_real_data
    assert records == fixture_records()
    assert result.records[0].fixture is records[0]
    assert result.records[0].fixture.last_trade_time != result.records[0].fixture.provider_quote_time
    assert result.records[0].fixture.event_time is None
    assert result.records[0].fixture.published_at is None
    with pytest.raises(FrozenInstanceError):
        records[0].last_price = Decimal("1")
    with pytest.raises(ValueError):
        replace(result, can_fetch=True)
    with pytest.raises(ValueError):
        replace(result, readiness_state="MARKET_READY")
    changed = assess((replace(records[0], last_price=Decimal("125.50")),))
    assert changed.input_hash != result.input_hash


@pytest.mark.parametrize("price", [Decimal("0"), Decimal("-1"), Decimal("NaN"),
                                  Decimal("Infinity"), Decimal("-Infinity"), Decimal("sNaN")])
def test_invalid_price_unavailable(price):
    row = assess((replace(fixture_records()[0], last_price=price),)).records[0]
    assert row.display_price is None and "INVALID_PRICE" in row.reason_codes


@pytest.mark.parametrize("price", [1.2, 1, "125.5", True])
def test_rejects_inexact_price_types(price):
    with pytest.raises(ValueError):
        replace(fixture_records()[0], last_price=price)


def test_missingness_and_source_errors_remain_distinct():
    record = fixture_records()[0]
    for reason in (None, "PROVIDER_NO_VALUE"):
        row = assess((replace(record, last_price=None, missing_reason=reason),)).records[0]
        assert "MISSING_PRICE" in row.reason_codes and row.display_price is None
        assert (reason or "MISSING_REASON_UNSPECIFIED") in row.reason_codes
    for state in ("MISSING_ROW", "ACCESS_FAILURE", "TRANSPORT_FAILURE"):
        assert state in assess((replace(record, source_state=state),)).records[0].reason_codes
    assert "INCONSISTENT_MISSINGNESS" in assess((replace(record, missing_reason="MISSING_PRICE"),)).records[0].reason_codes


def test_duplicate_keys_and_tokens_block_all_ambiguous_records():
    record = fixture_records()[0]
    for other in (replace(record, provider_token="SYNTHETIC:TOKEN_B"),
                  replace(record, instrument_key="SYNTHETIC:EQUITY_B")):
        assert all("AMBIGUOUS_IDENTITY" in row.reason_codes for row in assess((record, other)).records)


@pytest.mark.parametrize("updates", [dict(instrument_class="FUT"), dict(instrument_class="INDICES"),
                                    dict(instrument_class="UNCLASSIFIED"), dict(exchange="NSE"),
                                    dict(currency="USD")])
def test_ineligible_identity_or_semantics_block(updates):
    row = assess((replace(fixture_records()[0], **updates),)).records[0]
    assert row.value_state == "UNAVAILABLE" and row.display_price is None


@pytest.mark.parametrize("field", ["provider_quote_time", "last_trade_time",
                                   "retrieval_completed_at", "inventory_as_of"])
@pytest.mark.parametrize("kind", ["unknown", "naive", "future"])
def test_unknown_naive_future_clocks_block(field, kind):
    value = None if kind == "unknown" else AS_OF.replace(tzinfo=None) if kind == "naive" else AS_OF + timedelta(seconds=1)
    assert assess((replace(fixture_records()[0], **{field: value}),)).records[0].value_state == "UNAVAILABLE"


def test_clock_ordering_and_per_record_freshness():
    record = fixture_records()[0]
    stale = replace(record, instrument_key="SYNTHETIC:EQUITY_B", provider_token="SYNTHETIC:TOKEN_B",
                    provider_quote_time=AS_OF - timedelta(seconds=31))
    result = assess((record, stale))
    assert result.records[0].value_state == "FIXTURE_VALID_ONLY"
    assert "QUOTE_STALE" in result.records[1].reason_codes
    assert "TRADE_AFTER_QUOTE" in assess((replace(record, last_trade_time=AS_OF),)).records[0].reason_codes
    assert "QUOTE_AFTER_RETRIEVAL" in assess((replace(record, provider_quote_time=AS_OF),)).records[0].reason_codes
    assert "INVENTORY_AFTER_RETRIEVAL" in assess((replace(record, inventory_as_of=AS_OF),)).records[0].reason_codes
    assert "RETRIEVAL_STALE" in assess((replace(record, retrieval_completed_at=AS_OF-timedelta(seconds=16)),)).records[0].reason_codes
    assert "INVENTORY_STALE" in assess((replace(record, inventory_as_of=AS_OF-timedelta(seconds=301)),)).records[0].reason_codes
    boundary = replace(record, provider_quote_time=AS_OF-timedelta(seconds=30))
    assert assess((boundary,)).records[0].value_state == "FIXTURE_VALID_ONLY"
    cached = replace(stale, cache_state="FRESH_CACHE")
    assert "QUOTE_STALE" in assess((cached,)).records[0].reason_codes


def test_empty_and_exact_maximum_are_bounded():
    assert assess(()).records == ()
    records = tuple(replace(fixture_records()[0], instrument_key=f"SYNTHETIC:EQUITY_{index}",
                            provider_token=f"SYNTHETIC:TOKEN_{index}") for index in range(25))
    assert len(assess(records).records) == 25


def test_json_schema_and_normalized_cutoff_binding():
    result = assess()
    payload = json.loads(result.to_bytes())
    assert tuple(sorted(payload)) == tuple(sorted((
        "schema_version", "consumer_id", "fixture_version", "as_of", "input_hash", "records",
        "permission_state", "readiness_state", "market_session", "can_fetch", "can_expose_real_data")))
    assert payload["records"][0]["fixture"]["last_price"] == "125.500000000000000001"
    assert payload["records"][0]["fixture"]["event_time"] is None
    assert result.to_bytes() == assess(as_of=AS_OF.astimezone(timezone(timedelta(hours=5, minutes=30)))).to_bytes()
    assert result.input_hash != assess(policy=replace(fixture_policy(), max_quote_age_seconds=31)).input_hash


@pytest.mark.parametrize("cache", ["STALE_CACHE", "UNKNOWN"])
def test_cache_does_not_override_freshness(cache):
    assert cache in assess((replace(fixture_records()[0], cache_state=cache),)).records[0].reason_codes


def test_complete_permission_metadata_never_verifies_rights():
    result = assess(policy=replace(fixture_policy(), permission_metadata_hash="a"*64))
    assert result.permission_state == "METADATA_ONLY_NOT_VERIFIED"
    assert not result.can_fetch and not result.can_expose_real_data


@pytest.mark.parametrize("updates", [dict(policy=None), dict(as_of=AS_OF.replace(tzinfo=None)),
                                    dict(records=[]), dict(records=(object(),)), dict(fixture_version=""),
                                    dict(records=fixture_records()*26)])
def test_missing_or_malformed_envelope_refused(updates):
    with pytest.raises(ValueError):
        assess(**updates)


@pytest.mark.parametrize("updates", [dict(version=""), dict(identity_version=""), dict(semantics_version=""),
                                    dict(max_quote_age_seconds=-1), dict(max_retrieval_age_seconds=True),
                                    dict(max_inventory_age_seconds=86401), dict(permission_metadata_hash="approval")])
def test_invalid_policies_refused(updates):
    with pytest.raises(ValueError):
        replace(fixture_policy(), **updates)


@pytest.mark.parametrize("mode", ["REAL_PROVIDER", "HISTORICAL_NSE", "QUARANTINED", "DERIVATIVE", "UNCLASSIFIED"])
def test_mode_refused_before_input_evaluation(mode):
    with pytest.raises(ValueError, match="Synthetic fixtures only"):
        assess(mode=mode, records=object())


def test_real_provenance_and_invented_event_time_refused():
    for updates in (dict(provider="kite_connect"), dict(instrument_key="NSE:ABC"),
                    dict(source_endpoint="/quote"), dict(event_time=AS_OF), dict(published_at=AS_OF)):
        with pytest.raises(ValueError):
            replace(fixture_records()[0], **updates)


def test_no_io_no_provider_imports_no_ui_wiring(monkeypatch):
    import builtins
    import socket
    import requests
    def denied(*args, **kwargs):
        raise AssertionError("Offline fixture evaluation cannot access external state")
    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert assess().to_bytes()
    monkeypatch.undo()
    allowed = {"dataclasses", "datetime", "decimal", "hashlib", "json", "re",
               "dashboard_current_equity_readiness_v1"}
    for name in ("dashboard_current_equity_readiness_v1.py", "dashboard_current_equity_fixtures_v1.py"):
        tree = ast.parse((ROOT / "src/market_intel" / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {"open", "eval", "exec", "__import__"}
                assert getattr(node.func, "attr", None) not in {"now", "today", "connect", "request", "read_text", "write_text"}
    assert all("dashboard_current_equity_readiness_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT / "views").glob("*.py"))
