import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import pytest

from market_intel.foundation.current_market import CurrentInstrument, CurrentInstrumentSnapshot
from market_intel.foundation.kite_connect import KiteSession
from market_intel.foundation.kite_exact_transport_v1 import (
    API_URL,
    BATCH_SIZE,
    MAX_RESPONSE_BYTES,
    ExactTransportError,
    LocalExecutionApproval,
    build_target_binding,
    execute_two_batch_test,
)


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
CREATED = datetime(2026, 9, 22, 5, 0, tzinfo=UTC)


def inventory_fixture(*, items=None, session_date="2026-09-22"):
    if items is None:
        items = tuple(CurrentInstrument(
            index+1, index+101, f"DEMO{index:02d}", "NSE", "NSE", "EQ",
            None, None, 0.05, 1,
        ) for index in range(50))
    return CurrentInstrumentSnapshot(
        "kite_connect", CREATED-timedelta(minutes=1), session_date,
        "/instruments", "synthetic_inventory_v1", items,
    )


def binding_fixture(**updates):
    inventory = updates.pop("inventory", inventory_fixture())
    keys = updates.pop("selected_keys", tuple(
        f"NSE:DEMO{index:02d}" for index in reversed(range(50))))
    args = dict(
        binding_version="synthetic_exact_binding_v1", created_at=CREATED,
        inventory=inventory, selected_keys=keys,
        constituent_csv_hash="a"*64, inventory_snapshot_hash="b"*64,
    )
    args.update(updates)
    return build_target_binding(**args)


def approval_fixture(binding=None, **updates):
    binding = binding or binding_fixture()
    args = dict(binding_hash=binding.binding_hash,
                approved_at=CREATED,
                expires_at=CREATED+timedelta(minutes=9),
                authorization_state="OWNER_CONFIRMED_LOCAL_BINDING")
    args.update(updates)
    return LocalExecutionApproval(**args)


class Clock:
    def __init__(self):
        self.tick = 0.0
        self.times = iter((
            CREATED+timedelta(seconds=1),
            CREATED+timedelta(seconds=2),
            CREATED+timedelta(seconds=3),
            CREATED+timedelta(seconds=4),
        ))

    def now(self):
        return next(self.times)

    def monotonic(self):
        return self.tick


class Response:
    def __init__(self, payload, *, status=200, url=API_URL, headers=None,
                 history=(), advance=None):
        self.payload = payload
        self.status_code = status
        self.url = url
        self.history = history
        self.headers = headers or {
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
            "Content-Encoding": "identity",
        }
        self.advance = advance
        self.closed = False

    def iter_content(self, *, chunk_size):
        assert chunk_size == 4096
        midpoint = max(1, len(self.payload)//2)
        yield self.payload[:midpoint]
        if self.advance:
            self.advance()
        yield self.payload[midpoint:]

    def close(self):
        self.closed = True


class Http:
    def __init__(self, token_by_key, *, response_factory=None, fail_on=None):
        self.token_by_key = token_by_key
        self.response_factory = response_factory
        self.fail_on = fail_on
        self.calls = []
        self.responses = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        call_number = len(self.calls)
        if self.fail_on == call_number:
            raise TimeoutError("secret transport detail")
        keys = tuple(value for name, value in kwargs["params"] if name == "i")
        data = {}
        for key in keys:
            data[key] = {
                "instrument_token": self.token_by_key[key],
                "last_price": 100 + call_number,
                "timestamp": "2026-09-22 10:29:58",
                "last_trade_time": "2026-09-22 10:29:57",
            }
        payload = json.dumps({"status": "success", "data": data},
                             separators=(",", ":")).encode()
        response = (self.response_factory(payload, call_number)
                    if self.response_factory else Response(payload))
        self.responses.append(response)
        return response


def run(*, binding=None, approval=None, http=None, clock=None):
    binding = binding or binding_fixture()
    approval = approval or approval_fixture(binding)
    clock = clock or Clock()
    http = http or Http(dict(binding.targets))
    result = execute_two_batch_test(
        session=KiteSession("fixture-key", "fixture-access"),
        http=http, binding=binding, approval=approval,
        now=clock.now, monotonic=clock.monotonic,
    )
    return result, http


def test_exact_two_batch_transaction_and_transient_result():
    binding = binding_fixture()
    result, http = run(binding=binding)
    assert len(http.calls) == 2
    assert [len(call[1]["params"]) for call in http.calls] == [BATCH_SIZE, BATCH_SIZE]
    assert all(call[0] == API_URL for call in http.calls)
    assert all(call[1]["allow_redirects"] is False for call in http.calls)
    assert all(call[1]["stream"] is True and call[1]["timeout"] == 20
               for call in http.calls)
    assert all(call[1]["headers"]["Accept-Encoding"] == "identity"
               for call in http.calls)
    assert all(response.closed for response in http.responses)
    assert len(result.envelopes) == 2
    assert result.requested_count == result.returned_count == 50
    assert result.missing_count == result.unavailable_count == 0
    assert result.binding_hash == binding.binding_hash
    assert result.currency_state == "NOT_VERIFIED"
    assert result.retention_state == "TRANSIENT_MEMORY_ONLY"
    assert not result.can_persist and not result.can_expose_real_data
    assert not result.can_authorize_dashboard


def test_actual_encoded_final_query_is_validated_for_each_batch():
    binding = binding_fixture()
    http = Http(dict(binding.targets), response_factory=lambda body, number: Response(
        body, url=API_URL+"?"+urlencode([
            ("i", key) for key, _ in binding.batches[number-1]
        ])))
    result, _ = run(binding=binding, http=http)
    assert result.returned_count == 50


def test_binding_is_private_hash_bound_sorted_and_sanitized_summary_only():
    binding = binding_fixture()
    assert binding.targets == tuple(sorted(binding.targets))
    assert [len(batch) for batch in binding.batches] == [25, 25]
    assert "DEMO" not in repr(binding)
    summary = binding.sanitized_summary()
    assert summary["target_count"] == 50
    assert summary["contains_private_targets"] is False
    assert "targets" not in summary
    with pytest.raises(ValueError):
        replace(binding, binding_hash="0"*64)


def test_result_summary_excludes_identities_prices_and_credentials():
    result, _ = run()
    encoded = json.dumps(result.sanitized_summary(), sort_keys=True).lower()
    for forbidden in ("demo", "last_price", "instrument_token", "fixture-key",
                      "fixture-access", "authorization", "c:\\users"):
        assert forbidden not in encoded
    assert "private transient quotes" in repr(result).lower()
    with pytest.raises(FrozenInstanceError):
        result.can_persist = True
    with pytest.raises(ValueError):
        replace(result, can_expose_real_data=True)


@pytest.mark.parametrize("fail_on", [1, 2])
def test_first_or_second_transaction_failure_publishes_no_partial_result(fail_on):
    binding = binding_fixture()
    http = Http(dict(binding.targets), fail_on=fail_on)
    with pytest.raises(ExactTransportError, match="frozen scope") as caught:
        run(binding=binding, http=http)
    assert "secret" not in str(caught.value)
    assert len(http.calls) == fail_on
    assert all(response.closed for response in http.responses)


@pytest.mark.parametrize(("factory", "message"), [
    (lambda body, _: Response(body, status=403), "frozen scope"),
    (lambda body, _: Response(body, url="http://api.kite.trade/quote"), "frozen scope"),
    (lambda body, _: Response(body, url="https://other.invalid/quote"), "frozen scope"),
    (lambda body, _: Response(body, url=API_URL+"?i=NSE%3AWRONG"), "frozen scope"),
    (lambda body, _: Response(body, history=(object(),)), "frozen scope"),
    (lambda body, _: Response(body, headers={"Content-Type": "text/html"}), "frozen scope"),
    (lambda body, _: Response(body, headers={"Content-Type": "application/json",
                                              "Content-Encoding": "gzip"}), "frozen scope"),
    (lambda body, _: Response(body, headers={"Content-Type": "application/json",
                                              "Content-Length": str(len(body)+1)}), "frozen scope"),
])
def test_status_redirect_domain_representation_and_truncation_fail_closed(factory, message):
    binding = binding_fixture()
    http = Http(dict(binding.targets), response_factory=factory)
    with pytest.raises(ExactTransportError, match=message):
        run(binding=binding, http=http)
    assert http.responses[0].closed


def test_response_size_and_total_deadline_are_enforced_while_streaming():
    binding = binding_fixture()
    oversized = Http(dict(binding.targets), response_factory=lambda body, _: Response(
        b"{" + b" "*MAX_RESPONSE_BYTES))
    with pytest.raises(ExactTransportError):
        run(binding=binding, http=oversized)
    assert oversized.responses[0].closed

    clock = Clock()
    delayed = Http(dict(binding.targets), response_factory=lambda body, _: Response(
        body, advance=lambda: setattr(clock, "tick", 61.0)))
    with pytest.raises(ExactTransportError):
        run(binding=binding, http=delayed, clock=clock)
    assert delayed.responses[0].closed


@pytest.mark.parametrize("approval", [
    None,
    "not-an-approval",
])
def test_missing_or_wrong_approval_type_stops_before_request(approval):
    binding = binding_fixture()
    http = Http(dict(binding.targets))
    with pytest.raises(ValueError):
        execute_two_batch_test(
            session=KiteSession("fixture-key", "fixture-access"), http=http,
            binding=binding, approval=approval, now=Clock().now,
            monotonic=Clock().monotonic,
        )
    assert not http.calls


def test_mismatched_or_expired_approval_stops_before_request():
    binding = binding_fixture()
    http = Http(dict(binding.targets))
    for approval in (
        approval_fixture(binding, binding_hash="0"*64),
        approval_fixture(binding, approved_at=CREATED-timedelta(minutes=8),
                         expires_at=CREATED-timedelta(seconds=1)),
    ):
        with pytest.raises(ValueError, match="missing, mismatched or expired"):
            run(binding=binding, approval=approval, http=http)
    assert not http.calls


@pytest.mark.parametrize("updates", [
    {"selected_keys": tuple(f"NSE:DEMO{i:02d}" for i in range(49))},
    {"selected_keys": tuple("NSE:DEMO00" for _ in range(50))},
    {"constituent_csv_hash": "bad"},
    {"inventory_snapshot_hash": "bad"},
    {"created_at": CREATED.replace(tzinfo=None)},
    {"inventory": inventory_fixture(session_date="2026-09-21")},
])
def test_target_binding_scope_failures(updates):
    with pytest.raises(ValueError):
        binding_fixture(**updates)


@pytest.mark.parametrize("replacement", [
    {"segment": "NSE", "instrument_type": "FUT"},
    {"quality_flags": ("INVALID",)},
    {"expiry": "2026-10-29"},
])
def test_derivative_flagged_or_expiring_targets_are_rejected(replacement):
    items = list(inventory_fixture().instruments)
    items[0] = replace(items[0], **replacement)
    with pytest.raises(ValueError, match="Eligible unflagged NSE EQ"):
        binding_fixture(inventory=inventory_fixture(items=tuple(items)))


def test_fake_execution_uses_no_real_network_file_database_or_ui(monkeypatch):
    import builtins
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("No external or persistent access is permitted")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    result, _ = run()
    assert result.sanitized_summary()
    monkeypatch.undo()

    path = ROOT/"src/market_intel/foundation/kite_exact_transport_v1.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all("streamlit" not in alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert "streamlit" not in (node.module or "")
        if isinstance(node, ast.Call):
            assert getattr(node.func, "id", None) not in {"open", "eval", "exec"}
            assert getattr(node.func, "attr", None) not in {
                "read_text", "write_text", "connect", "post", "put", "delete"
            }
    assert all("kite_exact_transport_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
