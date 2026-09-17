"""Two bounded cash-equity batches, official membership and failure isolation."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import pytest
from market_intel.nifty50_manual_test import parse_constituents, plan_batches, run_test, fetch_constituents, OFFICIAL_URL
from market_intel.foundation.current_market import CurrentInstrument, CurrentInstrumentSnapshot, CurrentQuote, CurrentQuoteSnapshot

NOW = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)


def payload(count=50):
    return ("Symbol,Series,ISIN Code\n" + "".join(f"STOCK{i},EQ,IN{i:010d}\n" for i in range(count))).encode()


def inventory():
    return CurrentInstrumentSnapshot("kite_connect", NOW, "2026-09-17", "/instruments", "v1",
        tuple(CurrentInstrument(i+1, None, f"STOCK{i}", "NSE", "NSE", "EQ", None, None, None, None) for i in range(50)))


class Client:
    def __init__(self, fail=None, stale=False):
        self.calls = []
        self.fail, self.stale = fail, stale
    def get_current_quotes(self, keys, *, mode):
        self.calls.append((keys, mode))
        if len(self.calls) == self.fail:
            raise RuntimeError("simulated failure")
        return CurrentQuoteSnapshot("kite_connect", NOW, "/quote",
            tuple(CurrentQuote(key, "AVAILABLE", 123.0, None, None) for key in keys),
            "STALE_CACHE" if self.stale else "LIVE_PROVIDER_VALUE")


def test_exact_two_batches_immutable_and_no_limit_change():
    members, original, client = parse_constituents(payload(), retrieved_at=NOW), inventory(), Client()
    batches = plan_batches(members, original, as_of=NOW)
    assert len(batches) == 2 and all(len(batch) == 25 for batch in batches)
    assert len(set(batches[0]+batches[1])) == 50
    results = run_test(constituents=members, inventory=original, client=client, as_of=NOW)
    assert len(results) == 2 and len(client.calls) == 2
    assert all(mode == "quote" for _, mode in client.calls)
    assert original == inventory()


@pytest.mark.parametrize("count", [0, 49, 51])
def test_membership_count_fail_closed(count):
    with pytest.raises(ValueError):
        parse_constituents(payload(count), retrieved_at=NOW)


def test_invalid_membership_and_crosswalk():
    for data in (payload().replace(b',EQ,', b',FUT,', 1), payload().replace(b'STOCK1,', b'STOCK0,', 1), b'<html>denied</html>'):
        with pytest.raises(ValueError):
            parse_constituents(data, retrieved_at=NOW)
    members, original = parse_constituents(payload(), retrieved_at=NOW), inventory()
    for items in (original.instruments[:-1], original.instruments+(original.instruments[0],),
                  (replace(original.instruments[0], instrument_type="FUT"),)+original.instruments[1:],
                  (replace(original.instruments[0], quality_flags=("BAD",)),)+original.instruments[1:]):
        client = Client()
        with pytest.raises(ValueError):
            run_test(constituents=members, inventory=replace(original, instruments=items), client=client, as_of=NOW)
        assert not client.calls


@pytest.mark.parametrize("fail", [1, 2])
def test_batch_failure_no_returned_partial_package(fail):
    client = Client(fail=fail)
    with pytest.raises(RuntimeError):
        run_test(constituents=parse_constituents(payload(), retrieved_at=NOW), inventory=inventory(), client=client, as_of=NOW)
    assert len(client.calls) == fail


def test_stale_cache_stops_before_second_batch():
    client = Client(stale=True)
    with pytest.raises(ValueError):
        run_test(constituents=parse_constituents(payload(), retrieved_at=NOW), inventory=inventory(), client=client, as_of=NOW)
    assert len(client.calls) == 1


def test_date_bindings_and_missingness():
    members = parse_constituents(payload(), retrieved_at=NOW)
    with pytest.raises(ValueError):
        plan_batches(members, inventory(), as_of=NOW+timedelta(days=1))
    class Missing(Client):
        def get_current_quotes(self, keys, *, mode):
            snapshot = super().get_current_quotes(keys, mode=mode)
            return replace(snapshot, quotes=(replace(snapshot.quotes[0], status="MISSING", last_price=None),)+snapshot.quotes[1:])
    results = run_test(constituents=members, inventory=inventory(), client=Missing(), as_of=NOW)
    assert sum(row.status == "MISSING" for snapshot in results for row in snapshot.quotes) == 2


def test_fixed_official_request_no_redirect_and_exact_response_cleanup():
    class Response:
        status_code, url, headers = 200, OFFICIAL_URL, {"Content-Type": "application/octet-stream"}
        closed = False
        def iter_content(self, **kwargs):
            yield payload()
        def close(self):
            self.closed = True
    response = Response()
    class Http:
        calls = []
        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return response
    http = Http()
    assert len(fetch_constituents(http=http, now=lambda: NOW).symbols) == 50
    assert response.closed and len(http.calls) == 1
    assert http.calls[0][1]["allow_redirects"] is False
    assert http.calls[0][1]["timeout"] == 30
    response.status_code = 302
    with pytest.raises(ValueError):
        fetch_constituents(http=http, now=lambda: NOW)
    assert response.closed


def test_panel_load_has_zero_requests(monkeypatch):
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root/".venv/Lib/site-packages"))
    pytest.importorskip("streamlit")
    import requests
    def denied(*args, **kwargs):
        raise AssertionError("Panel load must not request data")
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string("from views._nifty50_manual_test import render\nrender(now=lambda: None, manual_refresh=lambda action: True, provider_error=lambda exc: None)").run()
    assert not app.exception
    assert next(button for button in app.button if button.label.startswith("Test all 50")).disabled
