from dataclasses import replace, FrozenInstanceError
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import pytest
from market_intel.foundation.current_market import CurrentInstrument, CurrentInstrumentSnapshot
from market_intel.foundation.kite_connect import KiteSession
from market_intel.foundation.kite_current_market import KiteCurrentMarketClient, KiteCurrentDataError
from market_intel.foundation.kite_equity_quote_v1 import decode, price_text

NOW = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
PAYLOAD = (b'{"status":"success","data":{"NSE:DEMO":{'
           b'"instrument_token":1,"last_price":125.505000000000000001,'
           b'"timestamp":"2026-01-01 15:29:58",'
           b'"last_trade_time":"2026-01-01 15:29:00"}}}')
INSTRUMENT = CurrentInstrument(1, 11, "DEMO", "NSE", "NSE", "EQ", None, None, .05, 1)


def parse(payload=PAYLOAD, **changes):
    args=dict(payload=payload, targets=(("NSE:DEMO", 1),),
              retrieval_completed_at=NOW, as_of=NOW)
    args.update(changes)
    return decode(**args)


class Response:
    status_code=200
    url="https://api.kite.trade/quote"
    def __init__(self, payload=PAYLOAD):
        self.payload=payload
        self.headers={"Content-Type":"application/json", "Content-Length":str(len(payload))}
        self.exhausted=False
        self.closed=False
    def json(self):
        raise AssertionError("Float-decoded response.json must never be used")
    def iter_content(self, **kwargs):
        yield self.payload[:30]
        yield self.payload[30:]
        self.exhausted=True
    def close(self):
        self.closed=True


class NoHttp:
    def get(self, *args, **kwargs):
        raise AssertionError("Offline response injection must not request data")


def client(response=None, item=INSTRUMENT):
    def now():
        assert response is None or response.exhausted
        return NOW
    c=KiteCurrentMarketClient(KiteSession("fixture-key","fixture-access"),http=NoHttp(),now=now)
    c.attach_current_inventory(CurrentInstrumentSnapshot("kite_connect",NOW-timedelta(seconds=2),
        "2026-01-01","/instruments","fixture_v1",(item,)))
    return c


def test_source_precision_display_rounding_and_separate_ist_clocks():
    result=parse()
    row=result.records[0]
    assert row.original_price == Decimal("125.505000000000000001")
    assert row.display_price == "125.51"
    assert row.provider_quote_time != row.last_trade_time
    assert row.provider_quote_time.astimezone(timezone.utc) == NOW-timedelta(seconds=2)
    assert row.original_quote_time == "2026-01-01 15:29:58"
    assert result.payload_hash == hashlib.sha256(PAYLOAD).hexdigest()
    assert result.to_bytes() == parse().to_bytes()
    assert result.content_hash == parse().content_hash
    with pytest.raises(FrozenInstanceError):
        row.original_price=Decimal("1")
    with pytest.raises(ValueError):
        replace(result, can_expose_real_data=True).to_bytes()


@pytest.mark.parametrize("value,text", [("1","1.00"),("1.004","1.00"),("1.005","1.01"),
    ("1.999","2.00"),("0.001","0.00"),("1.234e2","123.40")])
def test_explicit_half_up_two_decimal_display(value,text):
    assert price_text(Decimal(value)) == text


@pytest.mark.parametrize("literal", [b'0', b'-1', b'true', b'"1.23"', b'NaN', b'Infinity', b'1e999999'])
def test_invalid_prices_fail_closed(literal):
    with pytest.raises(ValueError):
        parse(PAYLOAD.replace(b'125.505000000000000001',literal))


def test_missing_values_never_zero_or_time_substituted():
    missing=parse(b'{"status":"success","data":{}}')
    assert missing.records[0].reason_codes == ("MISSING_ROW",)
    for payload in [PAYLOAD.replace(b'125.505000000000000001', b'null'),
                    PAYLOAD.replace(b'"2026-01-01 15:29:00"',b'null'),
                    PAYLOAD.replace(b'2026-01-01 15:29:58',b'bad')]:
        row=parse(payload).records[0]
        assert row.display_price is None and row.value_state=="UNAVAILABLE"


def test_future_and_unordered_clocks_block_without_repair():
    result=parse(PAYLOAD.replace(b'15:29:00',b'15:30:01'))
    assert "TRADE_AFTER_RETRIEVAL" in result.records[0].reason_codes
    assert "TRADE_AFTER_QUOTE" in result.records[0].reason_codes
    assert result.records[0].original_price is not None


@pytest.mark.parametrize("payload", [b'', b' '*65537, b'\xff', b'{}',
    PAYLOAD.replace(b'"last_price":',b'"last_price":1,"last_price":'),
    PAYLOAD.replace(b'"instrument_token":1',b'"instrument_token":2'),
    PAYLOAD.replace(b'NSE:DEMO',b'NSE:OTHER')],
    ids=["empty","oversized","invalid-utf8","bad-envelope","duplicate-key","wrong-token","unselected-key"])
def test_bad_payload_scope_and_bindings(payload):
    with pytest.raises(ValueError):
        parse(payload)


def test_completion_clock_after_bytes_no_http_and_caller_ownership():
    response=Response()
    c=client(response)
    result=c.decode_exact_equity_response(response,("NSE:DEMO",),as_of=NOW)
    assert result.retrieval_completed_at==NOW and not response.closed
    assert not c._quote_cache
    assert result.readiness_state=="PARSED_NOT_MARKET_READY"
    assert result.permission_state==result.currency_state==result.adjustment_state=="NOT_VERIFIED"
    assert result.freshness_state=="NOT_EVALUATED"
    assert not result.can_fetch and not result.can_expose_real_data


@pytest.mark.parametrize("field,value", [("url","http://api.kite.trade/quote"),
    ("url","https://other.invalid/quote"),("status_code",403),
    ("headers",{"Content-Type":"text/html"}),
    ("headers",{"Content-Type":"application/json","Content-Length":"999"})])
def test_response_failures_sanitized(field,value):
    response=Response()
    setattr(response,field,value)
    with pytest.raises(KiteCurrentDataError,match="Exact cash-equity response validation failed"):
        client().decode_exact_equity_response(response,("NSE:DEMO",),as_of=NOW)
    assert not response.closed


@pytest.mark.parametrize("item", [replace(INSTRUMENT,instrument_type="FUT"),
    replace(INSTRUMENT,exchange="NFO"), replace(INSTRUMENT,quality_flags=("INVALID",)),
    replace(INSTRUMENT,expiry="2026-01-30")])
def test_derivative_flagged_or_expiring_inventory_refused(item):
    with pytest.raises(ValueError):
        client(item=item).decode_exact_equity_response(Response(),("NSE:DEMO",),as_of=NOW)


def test_large_integer_prices_and_nesting_bounded():
    with pytest.raises(ValueError):
        parse(PAYLOAD.replace(b'125.505000000000000001',b'9'*100))
    nested=b'{"status":"success","data":{},"extra":'+b'['*10+b'0'+b']'*10+b'}'
    with pytest.raises(ValueError):
        parse(nested)


@pytest.mark.parametrize("changes", [dict(targets=()),dict(targets=(("NSE:DEMO",1),)*26),
    dict(targets=(("NSE:DEMO",1),)*2),dict(targets=(("NFO:DEMO",1),)),
    dict(as_of=NOW.replace(tzinfo=None)),dict(retrieval_completed_at=NOW+timedelta(seconds=1))])
def test_target_and_time_scope_refusal(changes):
    with pytest.raises(ValueError):
        parse(**changes)


def test_offline_decoder_no_file_or_network_access(monkeypatch):
    import builtins
    import requests
    def deny(*args,**kwargs):
        raise AssertionError("Offline decoder must not perform I/O")
    c=client()
    monkeypatch.setattr(builtins,"open",deny)
    monkeypatch.setattr(requests.sessions.Session,"request",deny)
    assert c.decode_exact_equity_response(Response(),("NSE:DEMO",),as_of=NOW).to_bytes()
