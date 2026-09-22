"""Private in-memory target preflight for the exact two-batch Kite test."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

from .foundation.current_market import CurrentInstrumentSnapshot
from .foundation.kite_equity_quote_v1 import aware
from .foundation.kite_exact_transport_v1 import (
    LocalExecutionApproval,
    OWNER_SESSION_SECONDS,
    ExactTargetBinding,
    build_target_binding,
)
from .nifty50_manual_test import Constituents, plan_batches


PREFLIGHT_VERSION = "kite_exact_local_preflight_v1"


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)


def selected_inventory_hash(inventory, selected_keys):
    """Hash selected private crosswalk and provenance without serializing it outward."""
    if type(inventory) is not CurrentInstrumentSnapshot or not aware(inventory.retrieved_at):
        raise ValueError("Aware current inventory required")
    if type(selected_keys) is not tuple or len(selected_keys) != 50 or len(set(selected_keys)) != 50:
        raise ValueError("Exactly 50 unique immutable keys required")
    lookup = {}
    for item in inventory.instruments:
        lookup.setdefault(item.provider_key, []).append(item)
    rows = []
    for key in sorted(selected_keys):
        matches = lookup.get(key, ())
        if len(matches) != 1:
            raise ValueError("Exact selected inventory crosswalk required")
        item = matches[0]
        for value in (item.strike, item.tick_size):
            if value is not None and (type(value) not in {int, float} or not math.isfinite(value)):
                raise ValueError("Finite selected inventory metadata required")
        rows.append({
            "provider_key": item.provider_key,
            "provider_instrument_token": item.provider_instrument_token,
            "exchange_token": item.exchange_token,
            "exchange": item.exchange,
            "segment": item.segment,
            "instrument_type": item.instrument_type,
            "expiry": item.expiry,
            "strike": item.strike,
            "tick_size": item.tick_size,
            "lot_size": item.lot_size,
            "quality_flags": list(item.quality_flags),
        })
    payload = {
        "provider": inventory.provider,
        "retrieved_at": inventory.retrieved_at.astimezone(timezone.utc).isoformat(),
        "session_date": inventory.session_date,
        "source_endpoint": inventory.source_endpoint,
        "parser_version": inventory.parser_version,
        "scope": inventory.scope,
        "selected_rows": rows,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_preflight(*, constituents, inventory, prepared_at):
    """Build an exact private binding without network, files, credentials or prices."""
    if type(constituents) is not Constituents or not aware(prepared_at):
        raise ValueError("Validated constituents and aware preflight clock required")
    batches = plan_batches(constituents, inventory, as_of=prepared_at)
    selected_keys = tuple(key for batch in batches for key in batch)
    snapshot_hash = selected_inventory_hash(inventory, selected_keys)
    return build_target_binding(
        binding_version=PREFLIGHT_VERSION,
        created_at=prepared_at,
        inventory=inventory,
        selected_keys=selected_keys,
        constituent_csv_hash=constituents.payload_hash,
        inventory_snapshot_hash=snapshot_hash,
    )


def preflight_is_current(*, binding, constituents, inventory):
    """Return false, without mutation, when either private source has changed."""
    if type(binding) is not ExactTargetBinding or type(constituents) is not Constituents:
        return False
    try:
        binding.__post_init__()
        return (constituents.payload_hash == binding.constituent_csv_hash and
                selected_inventory_hash(
                    inventory, tuple(key for key, _ in binding.targets)
                ) == binding.inventory_snapshot_hash)
    except (TypeError, ValueError):
        return False


def confirm_preflight(*, binding, constituents, inventory, confirmed_hash,
                      confirmation_checked, confirmed_at):
    """Confirm only the currently recomputed local binding; does not execute it."""
    if type(binding) is not ExactTargetBinding:
        raise ValueError("Prepared exact binding required")
    binding.__post_init__()
    if confirmation_checked is not True or not aware(confirmed_at):
        raise ValueError("Explicit local confirmation and aware clock required")
    if not _hash(confirmed_hash) or confirmed_hash != binding.binding_hash:
        raise ValueError("Displayed binding hash was not confirmed exactly")
    if type(constituents) is not Constituents or constituents.payload_hash != binding.constituent_csv_hash:
        raise ValueError("Constituent input changed after preflight")
    selected_keys = tuple(key for key, _ in binding.targets)
    if selected_inventory_hash(inventory, selected_keys) != binding.inventory_snapshot_hash:
        raise ValueError("Inventory input changed after preflight")
    binding_deadline = binding.created_at + timedelta(seconds=OWNER_SESSION_SECONDS)
    if confirmed_at < binding.created_at or confirmed_at >= binding_deadline:
        raise ValueError("Preflight expired; prepare and review a new binding")
    return LocalExecutionApproval(
        binding_hash=binding.binding_hash,
        approved_at=confirmed_at,
        expires_at=binding_deadline,
        authorization_state="OWNER_CONFIRMED_LOCAL_BINDING",
    )
