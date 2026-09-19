import ast
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path

import pytest

from market_intel.equity_validation_refresh_ledger_fixtures_v1 import (
    AS_OF,
    CODE_VERSION,
    CONFIGURATION_VERSION,
    LEDGER_VERSION,
    POLICY_VERSION,
    RECORDED_AT,
    health_fixture,
)
from market_intel.equity_validation_refresh_ledger_v1 import build_ledger

ROOT = Path(__file__).resolve().parents[1]


def build(**updates):
    health = updates.pop("health", health_fixture())
    default_hash = getattr(health, "input_hash", health_fixture().input_hash)
    args = dict(
        mode="SYNTHETIC",
        ledger_version=LEDGER_VERSION,
        code_version=CODE_VERSION,
        configuration_version=CONFIGURATION_VERSION,
        policy_version=POLICY_VERSION,
        recorded_at=RECORDED_AT,
        health=health,
        permitted_input_hashes=(default_hash,),
    )
    args.update(updates)
    return build_ledger(**args)


def test_deterministic_sanitized_hash_bound_ledger():
    result = build()
    assert result.to_bytes() == build().to_bytes()
    assert result.content_hash == build().content_hash
    assert result.source_input_hash == health_fixture().input_hash
    assert result.source_content_hash == health_fixture().content_hash
    assert result.validation_state == "VALIDATED_SYNTHETIC_CONTRACT"
    assert result.evidence_class == "SYNTHETIC_FIXTURE"
    assert result.verification_state == "NOT_EXTERNALLY_VERIFIED"
    assert result.refresh_state == "REFRESH_NOT_AUTHORIZED"
    assert not result.rejection_reasons
    assert not result.can_persist and not result.can_activate_source
    assert not result.can_expose_real_data and not result.research_eligible
    assert not result.production_eligible
    encoded = result.to_bytes().lower()
    for forbidden in (b"equity_a", b"token_a", b"demo equity", b"125.5",
                      b"api_key", b"access_token", b"c:\\users"):
        assert forbidden not in encoded


def test_exact_envelope_and_aggregate_counts():
    payload = json.loads(build().to_bytes())
    assert set(payload) == {
        "schema_version", "ledger_version", "consumer_id", "recorded_at",
        "contract_version", "code_version", "configuration_version",
        "policy_version", "evidence_class", "verification_state",
        "source_input_hash", "source_content_hash", "permitted_input_hashes",
        "requested_count", "returned_count", "missing_count",
        "unavailable_count", "stale_count", "validation_state",
        "rejection_reasons", "refresh_state", "can_persist",
        "can_activate_source", "can_expose_real_data", "research_eligible",
        "production_eligible",
    }
    assert (payload["requested_count"], payload["returned_count"],
            payload["missing_count"], payload["unavailable_count"],
            payload["stale_count"]) == (2, 2, 0, 0, 0)


def test_unpermitted_hash_is_recorded_as_rejection():
    result = build(permitted_input_hashes=("0" * 64,))
    assert result.validation_state == "REJECTED"
    assert [(reason.code, reason.count) for reason in result.rejection_reasons] == [
        ("INPUT_HASH_NOT_PERMITTED", 1)
    ]
    assert not result.can_persist and result.refresh_state == "REFRESH_NOT_AUTHORIZED"


def test_contract_mismatch_and_unpermitted_hash_are_both_visible():
    result = build(expected_contract_version="daily_equity_data_health_v2",
                   permitted_input_hashes=("f" * 64,))
    assert [reason.code for reason in result.rejection_reasons] == [
        "CONTRACT_VERSION_MISMATCH", "INPUT_HASH_NOT_PERMITTED"
    ]


@pytest.mark.parametrize("mode", [
    "OWNER_REPORTED", "MANUAL", "VERIFIED", "LIVE", "PROVIDER",
    "HISTORICAL_NSE", "QUARANTINED", "DERIVATIVE",
])
def test_non_synthetic_evidence_classes_fail_closed(mode):
    with pytest.raises(ValueError, match="Synthetic evidence only"):
        build(mode=mode)


@pytest.mark.parametrize("updates", [
    dict(ledger_version=""), dict(code_version="bad path/value"),
    dict(configuration_version=""), dict(policy_version=""),
    dict(recorded_at=AS_OF.replace(tzinfo=None)),
    dict(recorded_at=AS_OF-timedelta(seconds=1)),
    dict(health=object()), dict(permitted_input_hashes=[]),
    dict(permitted_input_hashes=()), dict(permitted_input_hashes=("bad",)),
    dict(permitted_input_hashes=tuple(str(i) * 64 for i in range(17))),
])
def test_malformed_boundaries_fail_closed(updates):
    with pytest.raises(ValueError):
        build(**updates)


def test_duplicate_permitted_hashes_fail_closed_and_order_is_canonical():
    source_hash = health_fixture().input_hash
    with pytest.raises(ValueError, match="Duplicate"):
        build(permitted_input_hashes=(source_hash, source_hash))
    result = build(permitted_input_hashes=("f" * 64, source_hash, "0" * 64))
    assert result.permitted_input_hashes == tuple(sorted(("f" * 64, source_hash, "0" * 64)))


def test_ledger_and_input_are_immutable():
    health = health_fixture()
    result = build(health=health)
    with pytest.raises(FrozenInstanceError):
        result.validation_state = "REJECTED"
    with pytest.raises(FrozenInstanceError):
        health.requested_count = 99
    with pytest.raises(ValueError):
        replace(result, can_persist=True)
    with pytest.raises(ValueError):
        replace(result, evidence_class="VERIFIED_PROVIDER")


def test_version_or_hash_change_changes_content_hash():
    assert build(code_version="equity_health_code_v2").content_hash != build().content_hash
    assert build(configuration_version="equity_health_config_v2").content_hash != build().content_hash
    assert build(policy_version="synthetic_validation_policy_v2").content_hash != build().content_hash
    assert build(permitted_input_hashes=(health_fixture().input_hash, "f" * 64)).content_hash != build().content_hash


def test_no_io_clock_provider_ui_or_persistence_dependency(monkeypatch):
    import builtins
    import socket
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("Ledger must not access or persist external state")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert build().to_bytes()
    monkeypatch.undo()
    for name in ("equity_validation_refresh_ledger_v1.py",
                 "equity_validation_refresh_ledger_fixtures_v1.py"):
        tree = ast.parse((ROOT/"src/market_intel"/name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert getattr(node.func, "id", None) not in {
                    "open", "eval", "exec", "__import__"
                }
                assert getattr(node.func, "attr", None) not in {
                    "now", "today", "connect", "request", "read_text", "write_text"
                }
    assert all("equity_validation_refresh_ledger_v1" not in page.read_text(encoding="utf-8")
               for page in (ROOT/"views").glob("*.py"))
