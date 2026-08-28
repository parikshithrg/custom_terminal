"""Run-specific user approval contract for governed research execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .legacy_ledger import canonical_json_bytes, sha256_bytes


APPROVAL_SCHEMA_VERSION = "governed_run_approval_v1"
AUTHORIZED_GATEWAY_ACTION = "GovernedExecutionGateway.run"
APPROVAL_REQUIRED = (
    "approval_schema_version", "approval_id", "family_id", "family_version",
    "experiment_id", "experiment_version", "experiment_specification_sha256",
    "preregistration_sha256", "input_declaration_sha256",
    "allowed_dataset_snapshots", "permitted_split_access", "maximum_compute_budget",
    "compute_budget_enforcement",
    "authorized_gateway_action", "issued_at", "expires_at", "one_time_use_status",
    "approving_identity", "approval_reason", "template_only", "approval_payload_sha256",
)


class ApprovalError(ValueError):
    pass


def approval_payload_hash(approval: Mapping[str, Any]) -> str:
    body = dict(approval)
    body.pop("approval_payload_sha256", None)
    return sha256_bytes(canonical_json_bytes(body))


def seal_approval(approval: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(approval)
    value["approval_payload_sha256"] = approval_payload_hash(value)
    return value


def _timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ApprovalError(f"{label} must include a timezone")
    return parsed


def dataset_snapshot_refs(inputs: Mapping[str, Any]) -> list[dict[str, str]]:
    return sorted(
        [{
            "dataset_id": str(item["dataset_id"]),
            "version": str(item["version"]),
            "snapshot_sha256": str(item["snapshot_sha256"]),
        } for item in inputs.get("datasets", [])],
        key=lambda item: (item["dataset_id"], item["version"], item["snapshot_sha256"]),
    )


def validate_run_approval(
    approval: Mapping[str, Any], *, family: Mapping[str, Any],
    preregistration: Mapping[str, Any], inputs: Mapping[str, Any],
    preregistration_sha256: str, input_declaration_sha256: str,
    evaluated_at: str,
) -> None:
    missing = [field for field in APPROVAL_REQUIRED if field not in approval]
    unresolved = [
        field for field in APPROVAL_REQUIRED
        if field in approval and (approval[field] is None or approval[field] == "")
    ]
    if missing or unresolved:
        raise ApprovalError(f"approval incomplete: missing={missing}, unresolved={unresolved}")
    if approval["approval_schema_version"] != APPROVAL_SCHEMA_VERSION:
        raise ApprovalError("unsupported approval schema")
    if approval.get("template_only") is not False:
        raise ApprovalError("approval template is not an execution authorization")
    if approval_payload_hash(approval) != approval["approval_payload_sha256"]:
        raise ApprovalError("approval payload hash mismatch")
    if (approval["family_id"], approval["family_version"]) != (
        family["family_id"], family["version"]
    ):
        raise ApprovalError("approval family binding mismatch")
    if (approval["experiment_id"], approval["experiment_version"]) != (
        preregistration["experiment_id"], preregistration["version"]
    ):
        raise ApprovalError("approval experiment binding mismatch")
    # In R.4 the complete locked preregistration is the executable experiment
    # specification. Both named bindings remain explicit so a later separation
    # of the contracts cannot silently widen an existing approval.
    if approval["experiment_specification_sha256"] != preregistration_sha256:
        raise ApprovalError("approval experiment-specification hash mismatch")
    if approval["preregistration_sha256"] != preregistration_sha256:
        raise ApprovalError("approval preregistration hash mismatch")
    if approval["input_declaration_sha256"] != input_declaration_sha256:
        raise ApprovalError("approval input-declaration hash mismatch")
    if approval["allowed_dataset_snapshots"] != dataset_snapshot_refs(inputs):
        raise ApprovalError("approval dataset snapshot binding mismatch")
    permitted = approval["permitted_split_access"]
    if not isinstance(permitted, list) or preregistration["split_requested"] not in permitted:
        raise ApprovalError("approval does not permit the requested split")
    if preregistration["split_requested"] == "test" and "test" not in permitted:
        raise ApprovalError("test access was not explicitly approved")
    if approval["authorized_gateway_action"] != AUTHORIZED_GATEWAY_ACTION:
        raise ApprovalError("approval action does not authorize the governance gateway")
    if approval["one_time_use_status"] != "UNUSED_AT_ISSUE":
        raise ApprovalError("approval is not in its immutable issued state")
    budget = approval["maximum_compute_budget"]
    if not isinstance(budget, Mapping):
        raise ApprovalError("maximum compute budget must be an object")
    for field in ("wall_time_seconds", "memory_mb", "attempts"):
        if field not in budget or int(budget[field]) < 1:
            raise ApprovalError(f"approval compute budget requires positive {field}")
    if int(budget["attempts"]) != 1:
        raise ApprovalError("run-specific approval must authorize exactly one attempt")
    enforcement = approval["compute_budget_enforcement"]
    expected_enforcement = {
        "attempts": "ENFORCED_BY_ONE_TIME_APPROVAL",
        "wall_time_seconds": "DECLARED_NOT_ENFORCED",
        "memory_mb": "DECLARED_NOT_ENFORCED",
    }
    if enforcement != expected_enforcement:
        raise ApprovalError("compute-budget enforcement classification is inaccurate")
    issued = _timestamp(approval["issued_at"], "issued_at")
    expires = _timestamp(approval["expires_at"], "expires_at")
    evaluated = _timestamp(evaluated_at, "evaluated_at")
    if expires <= issued:
        raise ApprovalError("approval expiry must be after issue time")
    if evaluated < issued or evaluated > expires:
        raise ApprovalError("approval is not currently valid")
