from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import ast
from pathlib import Path
import pytest

from market_intel.offline_equity_quote_fixtures_v1 import PAYLOAD, TARGETS, RETRIEVAL, AS_OF
from market_intel.dashboard_current_equity_fixtures_v1 import fixture_policy, fixture_records
from market_intel.offline_equity_validation_v1 import validate


def metadata():
    return replace(fixture_records()[0], last_price=None, missing_reason="INPUT_NOT_PARSED",
                   provider_quote_time=None, last_trade_time=None, retrieval_completed_at=None)


def run(**changes):
    args = dict(mode="SYNTHETIC", fixture_version="validation_fixture_v1", payload=PAYLOAD,
                bindings=((TARGETS[0], metadata()),), retrieval_completed_at=RETRIEVAL,
                as_of=AS_OF, policy=fixture_policy())
    args.update(changes)
    return validate(**args)


def test_exact_deterministic_immutable_pipeline():
    original = metadata()
    result = run(bindings=((TARGETS[0], original),))
    assert result.readiness.records[0].display_price == Decimal("125.500000000000000001")
    assert original.last_price is None and original.provider_quote_time is None
    assert result.to_bytes() == run().to_bytes()
    assert result.content_hash == run().content_hash
    assert result.content_hash != run(payload=PAYLOAD+b' ').content_hash
    assert result.readiness.readiness_state == "SYNTHETIC_NOT_MARKET_READY"
    assert not result.readiness.can_expose_real_data and not result.readiness.can_fetch
    assert result.readiness.permission_state == "NO_PERMISSION_EVIDENCE"


@pytest.mark.parametrize("mode", ["LIVE", "HISTORICAL_NSE", "QUARANTINED", "UNKNOWN"])
def test_real_modes_refused_before_inputs(mode):
    with pytest.raises(ValueError):
        run(mode=mode, bindings=None)


@pytest.mark.parametrize("record", [replace(metadata(), instrument_key="SYNTHETIC:EQUITY_B"),
    replace(metadata(), instrument_class="FUTURE"), fixture_records()[0],
    replace(metadata(), currency="USD")])
def test_incompatible_or_prepopulated_metadata_refused(record):
    with pytest.raises(ValueError):
        run(bindings=((TARGETS[0], record),))


def test_missing_row_and_missing_price_remain_explicit():
    for payload in [b'{"status":"success","data":{}}',
                    PAYLOAD.replace(b'125.500000000000000001', b'null')]:
        result = run(payload=payload)
        assert result.readiness.records[0].display_price is None
        assert result.readiness.records[0].value_state == "UNAVAILABLE"
        assert result.parsed.records[0].original_price is None


def test_clocks_and_age_do_not_substitute_or_relax():
    result = run(payload=PAYLOAD.replace(b'2026-01-01T09:59:00+00:00', b'bad-clock'))
    assert "TRADE_TIME_MALFORMED" in result.readiness.records[0].reason_codes
    assert result.readiness.records[0].display_price is None
    stale = run(as_of=AS_OF+timedelta(seconds=31))
    assert "QUOTE_STALE" in stale.readiness.records[0].reason_codes
    assert stale.parsed.records[0].original_price is not None


@pytest.mark.parametrize("bindings", [(), [], ((TARGETS[0], metadata()),)*26,
                                     ((TARGETS[0], metadata()),)*2])
def test_bounded_unique_immutable_bindings(bindings):
    with pytest.raises(ValueError):
        run(bindings=bindings)


def test_no_io_or_activation_dependencies(monkeypatch):
    import requests
    import builtins
    def deny(*args, **kwargs):
        raise AssertionError("Offline validation must not perform I/O")
    monkeypatch.setattr(requests.sessions.Session, "request", deny)
    monkeypatch.setattr(builtins, "open", deny)
    assert run().to_bytes()


def test_dependency_scope():
    source = Path(__file__).resolve().parents[1]/"src/market_intel/offline_equity_validation_v1.py"
    tree = ast.parse(source.read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert set(imports) <= {"dataclasses", "offline_equity_quote_parser_v1",
                            "dashboard_current_equity_readiness_v1"}
    names = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    assert set(names) <= {"hashlib", "json"}
