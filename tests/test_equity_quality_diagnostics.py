import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path

import pytest

from market_intel.dashboard_current_equity_fixtures_v1 import AS_OF, fixture_records
from market_intel.equity_quality_diagnostic_fixtures_v1 import (
    DIAGNOSTIC_VERSION,
    EXPECTED_KEYS,
    anomaly_readiness,
    clean_readiness,
    partial_readiness,
    session,
)
from market_intel.equity_quality_diagnostics_v1 import diagnose, SyntheticSessionContext

ROOT = Path(__file__).resolve().parents[1]


def run(readiness=None, **updates):
    args = dict(mode="SYNTHETIC", diagnostic_version=DIAGNOSTIC_VERSION,
                as_of=AS_OF, readiness=readiness or clean_readiness(),
                expected_instrument_keys=EXPECTED_KEYS, session=session())
    args.update(updates)
    return diagnose(**args)


def test_clean_diagnostic_is_deterministic_sanitized_and_read_only():
    result = run()
    assert result.to_bytes() == run().to_bytes()
    assert result.content_hash == run().content_hash
    assert result.quality_state == "CLEAN_SYNTHETIC_FIXTURE"
    assert result.observed_record_count == result.expected_record_count == 2
    assert result.issue_record_count == result.expected_gap_count == 0
    assert result.evidence_class == "SYNTHETIC_FIXTURE"
    assert result.original_facts_preserved
    assert not result.can_repair and not result.can_fill_gaps
    assert not result.can_select_provider and not result.production_eligible
    encoded = result.to_bytes().lower()
    for forbidden in (b"equity_a", b"token_a", b"demo equity", b"125.5",
                      b"api_key", b"access_token", b"c:\\users"):
        assert forbidden not in encoded
    with pytest.raises(FrozenInstanceError):
        result.quality_state = "ISSUES_DETECTED"
    with pytest.raises(ValueError):
        replace(result, can_repair=True)


def test_stronger_anomaly_fixture_reports_without_repair_or_dropping():
    source = anomaly_readiness()
    before = source.to_bytes()
    result = run(source, expected_instrument_keys=EXPECTED_KEYS + (
        "SYNTHETIC:EQUITY_E",))
    assert source.to_bytes() == before
    assert result.observed_record_count == 5
    assert result.issue_record_count == 5
    assert result.duplicate_identity_count == 2
    assert result.expected_gap_count == 1
    assert result.unexpected_identity_count == 2
    assert result.missing_price_count == 1
    assert result.invalid_price_count == result.nonfinite_price_count == 1
    assert result.timestamp_issue_count == 1
    assert result.semantic_issue_count == 1
    assert result.source_failure_count == 1
    assert result.quality_state == "ISSUES_DETECTED"
    codes = {item.code: item.count for item in result.diagnostic_counts}
    assert codes["AMBIGUOUS_IDENTITY"] == 2
    assert codes["EXPECTED_OBSERVATION_GAP"] == 1
    assert codes["NONFINITE_PRICE"] == 1
    assert all(row.display_price is None for row in source.records)


def test_non_trading_day_never_counts_expected_absence_as_gap():
    result = run(partial_readiness(), session=session("NON_TRADING_DAY"))
    assert result.expected_gap_count == 0
    assert result.quality_state == "CLEAN_SYNTHETIC_FIXTURE"
    assert {item.code for item in result.diagnostic_counts} == {
        "GAP_CHECK_NOT_APPLICABLE_NON_TRADING_DAY"
    }


def test_unknown_session_is_indeterminate_not_missing():
    result = run(partial_readiness(), session=session("UNKNOWN"))
    assert result.expected_gap_count == 0
    assert result.quality_state == "INDETERMINATE_SESSION"
    assert {item.code for item in result.diagnostic_counts} == {
        "SESSION_EXPECTATION_UNKNOWN"
    }


def test_trading_session_counts_declared_gap_only():
    result = run(partial_readiness())
    assert result.expected_gap_count == 1
    assert result.quality_state == "ISSUES_DETECTED"


def test_malformed_identity_is_refused_before_diagnostics():
    with pytest.raises(ValueError):
        replace(fixture_records()[0], instrument_key="NSE:REAL")
    with pytest.raises(ValueError):
        run(expected_instrument_keys=("NSE:REAL",))


def test_exact_aggregate_schema():
    payload = json.loads(run().to_bytes())
    assert set(payload) == {
        "schema_version", "diagnostic_version", "consumer_id", "as_of",
        "source_input_hash", "source_content_hash", "expected_universe_hash",
        "session_version", "session_date", "session_state",
        "observed_record_count", "expected_record_count", "issue_record_count",
        "duplicate_identity_count", "expected_gap_count", "unexpected_identity_count",
        "missing_price_count", "invalid_price_count", "nonfinite_price_count",
        "timestamp_issue_count", "semantic_issue_count", "source_failure_count",
        "diagnostic_counts", "quality_state", "evidence_class",
        "original_facts_preserved", "can_repair", "can_fill_gaps",
        "can_select_provider", "production_eligible",
    }


@pytest.mark.parametrize("mode", [
    "LIVE", "PROVIDER", "OWNER_REPORTED", "HISTORICAL_NSE",
    "QUARANTINED", "DERIVATIVE", "UNCLASSIFIED",
])
def test_non_synthetic_modes_fail_before_evaluation(mode):
    with pytest.raises(ValueError, match="Synthetic fixtures only"):
        run(mode=mode, readiness=object())


@pytest.mark.parametrize("updates", [
    dict(diagnostic_version=""), dict(as_of=AS_OF.replace(tzinfo=None)),
    dict(as_of=AS_OF+timedelta(seconds=1)), dict(readiness=object()),
    dict(expected_instrument_keys=[]), dict(expected_instrument_keys=()),
    dict(expected_instrument_keys=EXPECTED_KEYS*13),
    dict(expected_instrument_keys=(EXPECTED_KEYS[0], EXPECTED_KEYS[0])),
    dict(session=object()),
    dict(session=SyntheticSessionContext("session_v1", AS_OF.date()+timedelta(days=1), "TRADING_SESSION")),
])
def test_malformed_boundaries_fail_closed(updates):
    with pytest.raises(ValueError):
        run(**updates)


def test_session_context_is_strict_and_immutable():
    context = session()
    with pytest.raises(FrozenInstanceError):
        context.state = "UNKNOWN"
    with pytest.raises(ValueError):
        SyntheticSessionContext("session_v1", AS_OF.date(), "HOLIDAY_INFERRED")
    with pytest.raises(ValueError):
        SyntheticSessionContext("session_v1", AS_OF.date(), "TRADING_SESSION", "Asia/Kolkata")


def test_inconsistent_upstream_readiness_rows_fail_closed():
    source = clean_readiness()
    row = source.records[0]
    cases = (
        replace(row, instrument_key="SYNTHETIC:EQUITY_OTHER"),
        replace(row, reason_codes=("INVALID_PRICE",), value_state="FIXTURE_VALID_ONLY"),
        replace(row, reason_codes=("INVALID_PRICE", "INVALID_PRICE")),
        replace(row, display_price=None),
    )
    for changed in cases:
        with pytest.raises(ValueError):
            run(replace(source, records=(changed, source.records[1])))


def test_no_io_wall_clock_provider_ui_or_persistence_dependency(monkeypatch):
    import builtins
    import socket
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("Quality diagnostics must remain offline and read-only")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert run().to_bytes()
    monkeypatch.undo()
    for name in ("equity_quality_diagnostics_v1.py",
                 "equity_quality_diagnostic_fixtures_v1.py"):
        tree = ast.parse((ROOT/"src/market_intel"/name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {
                    "open", "eval", "exec", "__import__"
                }
                assert getattr(node.func, "attr", None) not in {
                    "now", "today", "connect", "request", "read_text", "write_text"
                }
    assert all("equity_quality_diagnostics_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
