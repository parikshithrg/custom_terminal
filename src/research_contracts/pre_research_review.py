"""Permanent owner-review gate for prospective market research.

The gate authorizes only progression to a separate research proposal and run
approval. It never authorizes execution by itself.
"""

from __future__ import annotations

import fnmatch
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .legacy_ledger import canonical_json_bytes, sha256_bytes, sha256_file


PRE_RESEARCH_POLICY_VERSION = "pre_research_review_policy_v1"
PRE_RESEARCH_RECORD_VERSION = "pre_research_review_record_v1"
APPROVED_REVIEW_STATE = "REPORT_REVIEWED_APPROVED"
REPORT_GATE_PASS_STATE = "RESEARCH_EXECUTION_PERMITTED_BY_REPORT_GATE"
NON_MARKET_CATEGORIES = frozenset({"INFRASTRUCTURE_CANARY", "SYNTHETIC_TEST"})


class PreResearchReviewError(ValueError):
    pass


def _load_object(path: str | Path, label: str) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise PreResearchReviewError(f"{label} is missing: {source}")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreResearchReviewError(f"{label} is unreadable or invalid") from exc
    if not isinstance(value, dict):
        raise PreResearchReviewError(f"{label} must be a JSON object")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PreResearchReviewError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PreResearchReviewError(f"{label} must include a timezone")
    return parsed


def _is_sha256(value: Any) -> bool:
    text = str(value)
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text.lower())


def is_market_research_family(family: Mapping[str, Any]) -> bool:
    """Infrastructure-only families are exempt; every market family is gated."""
    return str(family.get("hypothesis_category", "")) not in NON_MARKET_CATEGORIES


def research_state_inventory(
    repository_root: str | Path, policy: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return the deterministic byte inventory covered by the review policy."""
    root = Path(repository_root).resolve()
    state = policy.get("research_state", {})
    include = list(state.get("include_globs", []))
    exclude = list(state.get("exclude_globs", []))
    if not include:
        raise PreResearchReviewError("research-state include patterns are missing")
    paths: dict[str, Path] = {}
    for pattern in include:
        for path in root.glob(str(pattern)):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if any(fnmatch.fnmatch(relative, str(item)) for item in exclude):
                continue
            paths[relative] = path
    if not paths:
        raise PreResearchReviewError("research-state inventory is empty")
    return [
        {"path": relative, "sha256": sha256_file(paths[relative]),
         "byte_size": paths[relative].stat().st_size}
        for relative in sorted(paths)
    ]


def compute_research_state_fingerprint(
    repository_root: str | Path, policy: Mapping[str, Any]
) -> dict[str, Any]:
    inventory = research_state_inventory(repository_root, policy)
    return {
        "algorithm": "sha256_canonical_inventory_v1",
        "sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "file_count": len(inventory),
        "inventory": inventory,
    }


def validate_review_record(
    record: Mapping[str, Any], *, preregistration: Mapping[str, Any],
    repository_root: str | Path, policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the report gate and return a non-execution authorization result."""
    required = tuple(policy.get("review_record_required_fields", ()))
    missing = [field for field in required if field not in record]
    if missing:
        raise PreResearchReviewError(f"review record incomplete: missing={missing}")
    if record.get("schema_version") != PRE_RESEARCH_RECORD_VERSION:
        raise PreResearchReviewError("unsupported review-record schema")
    if record.get("review_status") != APPROVED_REVIEW_STATE:
        raise PreResearchReviewError("status PDF has not been explicitly reviewed and approved")
    if record.get("report_current") is not True or record.get("superseded_by") is not None:
        raise PreResearchReviewError("status PDF is stale or superseded")

    expected_repositories = policy.get("external_repository_bindings")
    actual_repositories = record.get("external_repository_bindings")
    if not isinstance(expected_repositories, list) or not expected_repositories:
        raise PreResearchReviewError("policy lacks external repository bindings")
    if actual_repositories != expected_repositories:
        raise PreResearchReviewError("external repository binding mismatch")

    root = Path(repository_root).resolve()
    pdf_path = root / str(record["pdf_path"])
    source_path = root / str(record["source_path"])
    for path, expected, label in (
        (pdf_path, record["pdf_sha256"], "PDF"),
        (source_path, record["source_sha256"], "PDF source"),
    ):
        if not _is_sha256(expected) or not path.is_file() or sha256_file(path) != expected:
            raise PreResearchReviewError(f"{label} hash mismatch or missing file")

    current = compute_research_state_fingerprint(root, policy)
    if record.get("research_state_fingerprint") != current["sha256"]:
        raise PreResearchReviewError("research-state fingerprint changed; report is stale")

    reference = preregistration.get("pre_research_review")
    if not isinstance(reference, Mapping):
        raise PreResearchReviewError("preregistration lacks a pre-research review reference")
    exact_bindings = {
        "report_id": record["report_id"],
        "report_version": record["report_version"],
        "pdf_sha256": record["pdf_sha256"],
        "research_state_fingerprint": record["research_state_fingerprint"],
        "review_record_path": record["record_path"],
        "external_repository_bindings": record["external_repository_bindings"],
    }
    for field, expected in exact_bindings.items():
        if reference.get(field) != expected:
            raise PreResearchReviewError(f"preregistration review binding mismatch: {field}")

    proposed_scope = preregistration.get("proposed_research_scope")
    if not proposed_scope or proposed_scope != reference.get("covered_scope"):
        raise PreResearchReviewError("preregistration research scope is missing or mismatched")
    if proposed_scope not in record.get("covered_future_scope", []):
        raise PreResearchReviewError("proposed research scope is not covered by the reviewed PDF")

    generated = _timestamp(record["generation_timestamp"], "generation_timestamp")
    approval = record.get("reviewer_approval")
    if not isinstance(approval, Mapping):
        raise PreResearchReviewError("explicit reviewer approval is missing")
    approved = _timestamp(approval.get("approved_at"), "reviewer approval timestamp")
    if approved <= generated:
        raise PreResearchReviewError("review approval must occur after PDF generation")
    if approval.get("approval_kind") != "EXPLICIT_POST_REPORT_REVIEW":
        raise PreResearchReviewError("generic conversational or synthetic approval is invalid")
    if not approval.get("approval_statement") or not approval.get("reviewer_classification"):
        raise PreResearchReviewError("reviewer approval fields are incomplete")

    return {
        "gate_state": REPORT_GATE_PASS_STATE,
        "report_gate_satisfied": True,
        "research_execution_authorized": False,
        "separate_run_approval_required": True,
        "report_id": record["report_id"],
        "report_version": record["report_version"],
        "research_state_fingerprint": current["sha256"],
        "covered_scope": proposed_scope,
    }


def validate_review_record_path(
    review_record_path: str | Path, *, preregistration: Mapping[str, Any],
    repository_root: str | Path, policy_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    resolved_policy = (
        root / "specs" / "pre_research_review_policy_v1.json"
        if policy_path is None else Path(policy_path)
    )
    policy = _load_object(resolved_policy, "pre-research policy")
    if policy.get("policy_version") != PRE_RESEARCH_POLICY_VERSION:
        raise PreResearchReviewError("unsupported pre-research policy")
    record = _load_object(review_record_path, "review record")
    return validate_review_record(
        record, preregistration=preregistration, repository_root=root, policy=policy
    )
