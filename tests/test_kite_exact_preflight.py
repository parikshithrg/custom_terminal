import ast
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from market_intel.foundation.current_market import CurrentInstrument, CurrentInstrumentSnapshot
from market_intel.kite_exact_preflight_v1 import (
    confirm_preflight, preflight_is_current,
    prepare_preflight,
    selected_inventory_hash,
)
from market_intel.nifty50_manual_test import parse_constituents


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 22, 10, tzinfo=timezone.utc)


def csv_payload():
    return ("Symbol,Series,ISIN Code\n" + "".join(
        f"STOCK{i},EQ,IN{i:010d}\n" for i in range(50))).encode()


def constituents():
    return parse_constituents(csv_payload(), retrieved_at=NOW)


def inventory(*, items=None):
    if items is None:
        items = tuple(CurrentInstrument(
            index+1, index+101, f"STOCK{index}", "NSE", "NSE", "EQ",
            None, None, 0.05, 1,
        ) for index in range(50))
    return CurrentInstrumentSnapshot(
        "kite_connect", NOW-timedelta(minutes=1), "2026-09-22",
        "/instruments", "synthetic_inventory_v1", items,
    )


def test_preflight_is_deterministic_private_and_does_not_execute():
    first = prepare_preflight(constituents=constituents(), inventory=inventory(),
                              prepared_at=NOW)
    second = prepare_preflight(constituents=constituents(), inventory=inventory(),
                               prepared_at=NOW)
    assert first == second
    assert first.binding_hash == second.binding_hash
    assert len(first.targets) == 50
    assert [len(batch) for batch in first.batches] == [25, 25]
    summary = first.sanitized_summary()
    assert summary["contains_private_targets"] is False
    assert "targets" not in summary
    assert "STOCK" not in str(summary)


def test_confirmation_binds_exact_current_inputs_and_expires_at_preflight_deadline():
    members, snapshot = constituents(), inventory()
    binding = prepare_preflight(constituents=members, inventory=snapshot, prepared_at=NOW)
    confirmed_at = NOW+timedelta(seconds=30)
    approval = confirm_preflight(
        binding=binding, constituents=members, inventory=snapshot,
        confirmed_hash=binding.binding_hash, confirmation_checked=True,
        confirmed_at=confirmed_at,
    )
    assert approval.binding_hash == binding.binding_hash
    assert approval.approved_at == confirmed_at
    assert approval.expires_at == NOW+timedelta(minutes=10)
    assert approval.authorization_state == "OWNER_CONFIRMED_LOCAL_BINDING"


@pytest.mark.parametrize("updates", [
    {"confirmation_checked": False},
    {"confirmed_hash": "0"*64},
    {"confirmed_at": NOW-timedelta(seconds=1)},
    {"confirmed_at": NOW+timedelta(minutes=10)},
    {"confirmed_at": NOW.replace(tzinfo=None)},
])
def test_missing_mismatched_or_expired_confirmation_fails_closed(updates):
    members, snapshot = constituents(), inventory()
    binding = prepare_preflight(constituents=members, inventory=snapshot, prepared_at=NOW)
    args = dict(binding=binding, constituents=members, inventory=snapshot,
                confirmed_hash=binding.binding_hash, confirmation_checked=True,
                confirmed_at=NOW+timedelta(seconds=1))
    args.update(updates)
    with pytest.raises(ValueError):
        confirm_preflight(**args)


def test_changed_constituents_or_inventory_invalidates_confirmation():
    members, snapshot = constituents(), inventory()
    binding = prepare_preflight(constituents=members, inventory=snapshot, prepared_at=NOW)
    changed_members = replace(members, payload_hash="f"*64)
    assert not preflight_is_current(
        binding=binding, constituents=changed_members, inventory=snapshot)
    with pytest.raises(ValueError, match="Constituent input changed"):
        confirm_preflight(
            binding=binding, constituents=changed_members, inventory=snapshot,
            confirmed_hash=binding.binding_hash, confirmation_checked=True,
            confirmed_at=NOW+timedelta(seconds=1),
        )
    changed_items = list(snapshot.instruments)
    changed_items[0] = replace(changed_items[0], provider_instrument_token=9999)
    changed_snapshot = replace(snapshot, instruments=tuple(changed_items))
    assert not preflight_is_current(
        binding=binding, constituents=members, inventory=changed_snapshot)
    with pytest.raises(ValueError, match="Inventory input changed"):
        confirm_preflight(
            binding=binding, constituents=members,
            inventory=changed_snapshot,
            confirmed_hash=binding.binding_hash, confirmation_checked=True,
            confirmed_at=NOW+timedelta(seconds=1),
        )


def test_snapshot_hash_changes_with_provenance_or_selected_crosswalk():
    snapshot = inventory()
    keys = tuple(item.provider_key for item in snapshot.instruments)
    original = selected_inventory_hash(snapshot, keys)
    assert original != selected_inventory_hash(
        replace(snapshot, parser_version="synthetic_inventory_v2"), keys)
    items = list(snapshot.instruments)
    items[0] = replace(items[0], tick_size=0.01)
    assert original != selected_inventory_hash(replace(snapshot, instruments=tuple(items)), keys)


def test_preflight_has_no_network_file_database_provider_or_execution_calls(monkeypatch):
    import builtins
    import requests

    def denied(*args, **kwargs):
        raise AssertionError("Preflight must remain local and pure")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    binding = prepare_preflight(constituents=constituents(), inventory=inventory(),
                                prepared_at=NOW)
    assert binding.binding_hash
    monkeypatch.undo()

    path = ROOT/"src/market_intel/kite_exact_preflight_v1.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"open", "connect", "request", "post", "put", "delete",
                 "execute_two_batch_test", "read_text", "write_text"}
    assert not any(isinstance(node, ast.Call) and (
        getattr(node.func, "id", None) in forbidden or
        getattr(node.func, "attr", None) in forbidden
    ) for node in ast.walk(tree))
