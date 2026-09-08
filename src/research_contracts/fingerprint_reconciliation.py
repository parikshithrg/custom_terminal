"""Forward-only reconciliation of historical review and current fingerprints."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from .legacy_ledger import canonical_json_bytes, sha256_bytes, sha256_file
from .pre_research_review import compute_research_state_fingerprint


RECONCILIATION_SCHEMA_VERSION = "research_fingerprint_reconciliation_v1"
CURRENT_FOR_DECLARED_SCOPE = "CURRENT_FOR_DECLARED_SCOPE"
HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE = (
    "HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE"
)
INVALID = "INVALID"
VALID_RELATIONSHIPS = frozenset({
    CURRENT_FOR_DECLARED_SCOPE,
    HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE,
    INVALID,
})


class FingerprintReconciliationError(ValueError):
    """Raised when a checkpoint or historical binding cannot be verified."""


def _payload_hash(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("deterministic_payload_sha256", None)
    return sha256_bytes(canonical_json_bytes(payload))


def create_fingerprint_reconciliation(
    *, repository_root: str | Path, policy: Mapping[str, Any],
    historical_records: Sequence[str], checkpoint_id: str,
    generated_at: str, source_commit: str, clean_start: bool,
    evidence_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Create a deterministic checkpoint without granting review authority."""
    root = Path(repository_root).resolve()
    current = compute_research_state_fingerprint(root, policy)
    reviews = []
    for relative in historical_records:
        path = root / relative
        record = __import__("json").loads(path.read_text(encoding="utf-8"))
        reviewed = str(record["research_state_fingerprint"])
        relationship = (
            CURRENT_FOR_DECLARED_SCOPE if reviewed == current["sha256"]
            else HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE
        )
        reviews.append({
            "review_id": f"{record['report_id']}:{record['report_version']}",
            "record_path": relative,
            "record_byte_sha256": sha256_file(path),
            "reviewed_fingerprint": reviewed,
            "reviewed_file_count": record.get("research_state_file_count"),
            "review_scope": list(record.get("covered_future_scope", [])),
            "review_source_commit": record.get("summarized_source_commit"),
            "current_scope_status": relationship,
            "transition_reason": (
                "Reviewed fingerprint equals the current policy inventory."
                if relationship == CURRENT_FOR_DECLARED_SCOPE else
                "The review remains authentic for its recorded scope, but later repository scope is not authorized by it."
            ),
        })
    result = {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "checkpoint_id": checkpoint_id,
        "generation_timestamp": generated_at,
        "source_commit": source_commit,
        "execution_start_clean": bool(clean_start),
        "fingerprint_policy": {
            "policy_version": policy["policy_version"],
            "algorithm": current["algorithm"],
            "include_globs": list(policy["research_state"]["include_globs"]),
            "exclude_globs": list(policy["research_state"]["exclude_globs"]),
        },
        "current_fingerprint": current["sha256"],
        "current_file_count": current["file_count"],
        "historical_reviews": reviews,
        "referenced_evidence_hashes": dict(sorted(evidence_hashes.items())),
        "authority": {
            "historical_scope_expansion": False,
            "research_execution_authorized": False,
            "real_data_access_authorized": False,
            "trading_authorized": False,
        },
    }
    result["deterministic_payload_sha256"] = _payload_hash(result)
    return result


def validate_fingerprint_reconciliation(
    checkpoint: Mapping[str, Any], *, repository_root: str | Path,
    policy: Mapping[str, Any], historical_records: Sequence[str],
) -> dict[str, Any]:
    """Verify current state and historical records without extending authority."""
    if checkpoint.get("schema_version") != RECONCILIATION_SCHEMA_VERSION:
        raise FingerprintReconciliationError("unsupported reconciliation schema")
    if checkpoint.get("deterministic_payload_sha256") != _payload_hash(checkpoint):
        raise FingerprintReconciliationError("reconciliation payload hash mismatch")
    declared_policy = checkpoint.get("fingerprint_policy")
    expected_policy = {
        "policy_version": policy["policy_version"],
        "algorithm": "sha256_canonical_inventory_v1",
        "include_globs": list(policy["research_state"]["include_globs"]),
        "exclude_globs": list(policy["research_state"]["exclude_globs"]),
    }
    if declared_policy != expected_policy:
        raise FingerprintReconciliationError("fingerprint policy or exclusions changed")
    root = Path(repository_root).resolve()
    current = compute_research_state_fingerprint(root, policy)
    if checkpoint.get("current_fingerprint") != current["sha256"] or checkpoint.get("current_file_count") != current["file_count"]:
        raise FingerprintReconciliationError("current fingerprint checkpoint is stale")
    expected_paths = list(historical_records)
    rows = checkpoint.get("historical_reviews")
    if not isinstance(rows, list) or [row.get("record_path") for row in rows] != expected_paths:
        raise FingerprintReconciliationError("historical review set or order mismatch")
    for row in rows:
        path = root / row["record_path"]
        if not path.is_file() or sha256_file(path) != row.get("record_byte_sha256"):
            raise FingerprintReconciliationError("historical review hash mismatch")
        record = __import__("json").loads(path.read_text(encoding="utf-8"))
        if row.get("reviewed_fingerprint") != record.get("research_state_fingerprint"):
            raise FingerprintReconciliationError("historical reviewed fingerprint mismatch")
        if row.get("review_scope") != record.get("covered_future_scope", []):
            raise FingerprintReconciliationError("historical review scope mismatch")
        expected_status = (
            CURRENT_FOR_DECLARED_SCOPE
            if row["reviewed_fingerprint"] == current["sha256"]
            else HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE
        )
        if row.get("current_scope_status") != expected_status:
            raise FingerprintReconciliationError("invalid historical-to-current relationship")
        if row.get("current_scope_status") not in VALID_RELATIONSHIPS:
            raise FingerprintReconciliationError("unknown scope relationship")
    authority = checkpoint.get("authority", {})
    if any(authority.get(key) is not False for key in (
        "historical_scope_expansion", "research_execution_authorized",
        "real_data_access_authorized", "trading_authorized",
    )):
        raise FingerprintReconciliationError("reconciliation cannot grant authority")
    return {
        "status": "VALID_FORWARD_RECONCILIATION",
        "current_fingerprint": current["sha256"],
        "historical_review_count": len(rows),
        "authority_extended": False,
    }


def tampered_copy(checkpoint: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    """Test helper returning a deep copy without resealing it."""
    result = deepcopy(dict(checkpoint))
    result.update(updates)
    return result
