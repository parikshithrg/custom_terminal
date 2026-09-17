"""Offline synthetic contract and no-side-effect governance checks."""
import ast
import builtins
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import socket

import pytest
from market_intel import dashboard_watchlist_read_model_v1 as contract
from market_intel.dashboard_watchlist_fixtures_v1 import equity_records, FIXTURE_VERSION

AS_OF = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def build(records=None, **kwargs):
    return contract.build_watchlist(mode="SYNTHETIC", as_of=AS_OF,
        fixture_version=FIXTURE_VERSION, records=equity_records() if records is None else records, **kwargs)


def test_exact_fields_and_deterministic_binding():
    assert tuple(f.name for f in fields(contract.WatchlistRecord)) == contract.RECORD_FIELDS
    assert tuple(f.name for f in fields(contract.WatchlistEnvelope)) == contract.ENVELOPE_FIELDS
    first, second = build(), build()
    assert first.to_bytes() == second.to_bytes() and first.fixture_hash == second.fixture_hash
    payload = json.loads(first.to_bytes())
    assert set(payload) == set(contract.ENVELOPE_FIELDS)
    assert set(payload["records"][0]) == set(contract.RECORD_FIELDS)
    binding = payload.pop("fixture_hash")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == binding
    assert payload["records"][0]["last_price"] == "125.500000000000000001"
    assert payload["records"][2]["last_price"] is None
    assert payload["readiness_state"] == "SYNTHETIC_NOT_MARKET_READY"


def test_inputs_and_model_are_immutable_and_context_independent():
    records = equity_records()
    before = repr(records)
    model = build(records)
    with localcontext() as context:
        context.prec = 2
        assert model.to_bytes() == build(records).to_bytes()
    assert repr(records) == before and model.records is records
    with pytest.raises(FrozenInstanceError):
        records[0].last_price = Decimal("1")
    with pytest.raises(FrozenInstanceError):
        model.readiness_state = "MARKET_READY"
    with pytest.raises(ValueError):
        replace(model, readiness_state="MARKET_READY")
    with pytest.raises(ValueError):
        replace(model, fixture_hash="0" * 64)


@pytest.mark.parametrize("field,value", [
    ("instrument_id","SYNTHETIC:OTHER"), ("last_price",Decimal("3.141592653589793238462643383279")),
    ("event_time",datetime(2026,1,1,8,tzinfo=timezone.utc)),
    ("published_at",datetime(2026,1,1,9,0,30,tzinfo=timezone.utc)),
    ("retrieved_at",datetime(2026,1,1,9,3,tzinfo=timezone.utc)),
])
def test_changes_alter_content_binding(field,value):
    rows=equity_records()
    assert build((replace(rows[0],**{field:value}),*rows[1:])).fixture_hash != build(rows).fixture_hash


@pytest.mark.parametrize("mode", [None,"","REAL","CURRENT_PROVIDER","HISTORICAL_NSE","QUARANTINED","DEMO_FUTURE","UNCLASSIFIED", "synthetic"])
def test_mode_rejected_before_any_record_evaluation(mode):
    class Bomb:
        def __iter__(self):
            raise AssertionError("Records were evaluated")
    with pytest.raises(ValueError, match="Non-synthetic"):
        contract.build_watchlist(mode=mode, as_of=None, fixture_version=None, records=Bomb())


@pytest.mark.parametrize("field,value", [
    ("instrument_id","NSE:A"),("instrument_id","SYNTHETIC:"),("instrument_id","SYNTHETIC:../A"),
    ("instrument_id",123),("exchange","NSE"),("exchange","NFO"),
    ("instrument_class","DEMO_FUTURE"),("instrument_class","UNCLASSIFIED"),
    ("source_id","kite_connect"),("source_id","historical_nse"),
    ("source_record_id",""),("display_symbol","REAL SYMBOL"),("currency",""),
    ("provider_timestamp",AS_OF),("quality_flags",["MISSING_PRICE"]),
    ("quality_flags",("QUARANTINED",)), ("quality_flags",("unsafe/path",)),
    ("quality_flags",("UNCLASSIFIED",)), ("quality_flags",("DERIVATIVE_INPUT",)),
])
def test_ineligible_or_malformed_records_fail_closed(field,value):
    with pytest.raises(ValueError):
        replace(equity_records()[0],**{field:value})


@pytest.mark.parametrize("price", [0,1,1.5,"10",Decimal("0"),Decimal("-1"),Decimal("NaN"),Decimal("sNaN"),Decimal("Infinity"),Decimal("-Infinity")])
def test_invalid_prices_are_not_filled(price):
    with pytest.raises(ValueError):
        replace(equity_records()[0],last_price=price)


def test_explicit_missingness_and_quality_flags():
    missing = equity_records()[2]
    assert missing.last_price is None and missing.value_state=="MISSING"
    assert missing.quality_flags==("MISSING_PRICE",)
    for kwargs in ({"last_price":None},{"value_state":"MISSING"},
                   {"quality_flags":("MISSING_PRICE",)}, {"value_state":"UNKNOWN"}):
        with pytest.raises(ValueError):
            replace(equity_records()[0],**kwargs)
    with pytest.raises(ValueError):
        replace(missing,quality_flags=())
    flagged=replace(equity_records()[0],quality_flags=("SYNTHETIC_TEST_WARNING",))
    assert "SYNTHETIC_TEST_WARNING" in build((flagged,)).to_bytes().decode()


def test_duplicates_record_bounds_and_unknown_input():
    row=equity_records()[0]
    with pytest.raises(ValueError):
        build((row,row))
    with pytest.raises(ValueError):
        build((row,replace(row,instrument_id="SYNTHETIC:OTHER")))
    rows=tuple(replace(row,instrument_id=f"SYNTHETIC:E{i}",source_record_id=f"SYNTHETIC:R{i}") for i in range(26))
    assert len(build(rows[:25]).records)==25
    with pytest.raises(ValueError):
        build(rows)
    for records in ([row],iter((row,)),({"mode":"UNCLASSIFIED"},)):
        with pytest.raises(ValueError):
            build(records)
    assert build(()).readiness_state==contract.READINESS


@pytest.mark.parametrize("field",["event_time","published_at","retrieved_at"])
@pytest.mark.parametrize("invalid",[None,"2026-01-01",datetime(2026,1,1)])
def test_naive_and_invalid_record_times(field,invalid):
    with pytest.raises(ValueError):
        replace(equity_records()[0],**{field:invalid})


def test_unordered_future_times_and_timezone_normalization():
    row=equity_records()[0]
    for kwargs in ({"event_time":AS_OF},{"published_at":AS_OF},
                   {"retrieved_at":row.event_time}):
        with pytest.raises(ValueError):
            replace(row,**kwargs)
    with pytest.raises(ValueError):
        build((replace(row,retrieved_at=AS_OF+timedelta(seconds=1)),))
    for as_of in (None,"2026-01-01",AS_OF.replace(tzinfo=None),row.event_time):
        with pytest.raises(ValueError):
            contract.build_watchlist(mode="SYNTHETIC",as_of=as_of,fixture_version=FIXTURE_VERSION,records=(row,))
    equivalent=AS_OF.astimezone(timezone(timedelta(hours=5,minutes=30)))
    assert build().to_bytes()==contract.build_watchlist(mode="SYNTHETIC",as_of=equivalent,fixture_version=FIXTURE_VERSION,records=equity_records()).to_bytes()


def test_runtime_has_no_io_or_network(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("I/O prohibited")
    monkeypatch.setattr(builtins,"open",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(Path,"open",forbidden)
    assert build().to_bytes()


def test_no_additional_fields_or_consumer_promotion():
    model = build()
    for kwargs in ({"consumer_id":"research"}, {"mode":"REAL"},
                   {"reason_codes":()}, {"schema_version":"other"}):
        with pytest.raises(ValueError):
            replace(model, **kwargs)
    with pytest.raises(TypeError):
        replace(equity_records()[0],close=Decimal("1"))
    # Even low-level bypass of frozen assignment is checked on serialization.
    object.__setattr__(model, "readiness_state", "MARKET_READY")
    with pytest.raises(ValueError):
        model.to_bytes()


def test_imports_and_calls_are_pure_and_ui_not_wired():
    allowed={"dataclasses","datetime","decimal","hashlib","json","re"}
    for filename in ("dashboard_watchlist_read_model_v1.py","dashboard_watchlist_fixtures_v1.py"):
        tree=ast.parse((ROOT/"src/market_intel"/filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert node.module in allowed|{"dashboard_watchlist_read_model_v1"}
            elif isinstance(node,ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            elif isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
                assert name not in {"open","read_text","write_text","connect","get","post","now","today","utcnow","eval","exec","__import__"}
    for page in (ROOT/"views").glob("*.py"):
        assert "dashboard_watchlist_read_model_v1" not in page.read_text(encoding="utf-8")
