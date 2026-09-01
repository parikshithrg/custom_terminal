"""Deterministic, side-effect-free preview for a prospective governed run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .approval import ApprovalError, validate_run_approval
from .governance import (
    GovernanceCatalog,
    GovernanceError,
    _matching_split_event,
    canonical_hash,
    validate_family,
    validate_input_declaration,
    validate_preregistration,
)
from .legacy_ledger import sha256_file
from .pre_research_review import is_market_research_family, validate_review_record_path


PREFLIGHT_VERSION = "governed_run_preflight_v1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GovernanceError(f"expected JSON object: {path}")
    return value


def preview_governed_run(
    *, family_path: str | Path, preregistration_path: str | Path,
    input_declaration_path: str | Path, approval_path: str | Path | None,
    catalog: GovernanceCatalog, attempts_root: str | Path,
    canonical_catalog_path: str | Path, registered_runner_entry_points: Iterable[str],
    evaluated_at: str, repository_root: str | Path | None = None,
    review_record_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a preview; never writes an event, artifact, or approval state."""
    issues: list[dict[str, str]] = []
    family = prereg = inputs = approval = None
    family_hash = prereg_hash = input_hash = approval_hash = None
    try:
        family = _load(family_path); validate_family(family); family_hash = sha256_file(family_path)
    except Exception as exc:
        issues.append({"category": "FAMILY_INVALID", "message": str(exc)})
    try:
        prereg = _load(preregistration_path); validate_preregistration(prereg)
        prereg_hash = sha256_file(preregistration_path)
    except Exception as exc:
        issues.append({"category": "PREREGISTRATION_INVALID", "message": str(exc)})
    try:
        inputs = _load(input_declaration_path); input_hash = canonical_hash(inputs)
        if prereg is not None:
            validate_input_declaration(inputs, prereg)
    except Exception as exc:
        issues.append({"category": "INPUT_DECLARATION_INVALID", "message": str(exc)})

    events: list[dict[str, Any]] = []
    try:
        events = catalog.events(); catalog.verify(events)
    except Exception as exc:
        issues.append({"category": "GOVERNANCE_CATALOG_INVALID", "message": str(exc)})

    if family is not None and prereg is not None:
        if is_market_research_family(family):
            try:
                if repository_root is None or review_record_path is None:
                    raise GovernanceError(
                        "market research requires an approved current status PDF"
                    )
                validate_review_record_path(
                    review_record_path,
                    preregistration=prereg,
                    repository_root=repository_root,
                )
            except Exception as exc:
                issues.append({
                    "category": "PRE_RESEARCH_REVIEW_INVALID",
                    "message": str(exc),
                })
        if (prereg["family_id"], prereg["family_version"]) != (
            family["family_id"], family["version"]
        ):
            issues.append({"category": "FAMILY_MISMATCH", "message": "family and preregistration differ"})
        family_key = f"{family['family_id']}__{family['version']}"
        experiment_key = f"{prereg['experiment_id']}__{prereg['version']}"
        if not any(
            event.get("event_type") == "FAMILY_REGISTERED"
            and event.get("object_refs", {}).get("family_key") == family_key
            and event.get("object_hashes", {}).get("family_sha256") == family_hash
            for event in events
        ):
            issues.append({"category": "FAMILY_NOT_REGISTERED", "message": "exact family version is absent"})
        if not any(
            event.get("event_type") == "PREREGISTRATION_LOCKED"
            and event.get("object_refs", {}).get("experiment_key") == experiment_key
            and event.get("object_hashes", {}).get("preregistration_sha256") == prereg_hash
            for event in events
        ):
            issues.append({"category": "PREREGISTRATION_NOT_LOCKED", "message": "exact preregistration is absent"})
        if prereg.get("code_entry_point") not in set(registered_runner_entry_points):
            issues.append({"category": "RUNNER_NOT_REGISTERED", "message": "declared runner is unavailable"})
        if inputs is not None and prereg.get("split_requested") != "train":
            try:
                _matching_split_event(
                    catalog=catalog, family_key=family_key, experiment_key=experiment_key,
                    split=prereg["split_requested"], prereg_hash=str(prereg_hash),
                    dataset_split_version=inputs["dataset_split_version"],
                )
            except Exception as exc:
                issues.append({"category": "SPLIT_ACCESS_INVALID", "message": str(exc)})

    approval_status = "MISSING"
    if approval_path is not None:
        try:
            approval = _load(approval_path); approval_hash = sha256_file(approval_path)
            if family is None or prereg is None or inputs is None:
                raise ApprovalError("approval cannot be checked until family, preregistration and inputs are valid")
            validate_run_approval(
                approval, family=family, preregistration=prereg, inputs=inputs,
                preregistration_sha256=str(prereg_hash), input_declaration_sha256=str(input_hash),
                evaluated_at=evaluated_at,
            )
            registered = [
                event for event in events
                if event.get("event_type") == "RUN_APPROVAL_REGISTERED"
                and event.get("object_refs", {}).get("approval_id") == approval["approval_id"]
                and event.get("object_hashes", {}).get("approval_sha256") == approval_hash
            ]
            if len(registered) != 1:
                raise ApprovalError("exact approval is not registered")
            if any(
                event.get("event_type") == "RUN_STARTED"
                and event.get("object_refs", {}).get("approval_id") == approval["approval_id"]
                for event in events
            ):
                raise ApprovalError("approval has already been consumed")
            approval_status = "VALID_UNUSED"
        except Exception as exc:
            approval_status = "INVALID"
            issues.append({"category": "RUN_APPROVAL_INVALID", "message": str(exc)})
    else:
        issues.append({"category": "RUN_APPROVAL_MISSING", "message": "explicit run approval is required"})

    return {
        "preflight_version": PREFLIGHT_VERSION,
        "evaluated_at": evaluated_at,
        "family": None if family is None else {"id": family["family_id"], "version": family["version"],
                                                "sha256": family_hash},
        "experiment_specification": None if prereg is None else {
            "id": prereg["experiment_id"], "version": prereg["version"], "sha256": prereg_hash,
        },
        "preregistration": None if prereg is None else {
            "id": prereg["experiment_id"], "version": prereg["version"], "sha256": prereg_hash,
        },
        "input_declaration": None if inputs is None else {
            "id": inputs["input_declaration_id"], "version": inputs["version"],
            "sha256": input_hash, "datasets": inputs["datasets"],
        },
        "requested_execution": None if prereg is None else {
            "gateway_action": "GovernedExecutionGateway.run",
            "runner_entry_point": prereg["code_entry_point"],
        },
        "split_access": None if prereg is None else {
            "requested": prereg["split_requested"],
            "approval_permitted": [] if approval is None else approval.get("permitted_split_access", []),
        },
        "source_state": None if inputs is None else {
            "code_commit": inputs["code_commit"], "dirty_worktree": inputs["dirty_worktree"],
            "dirty_worktree_fingerprint": inputs["dirty_worktree_fingerprint"],
            "environment_fingerprint": inputs["environment_fingerprint"],
            "configuration_hash": inputs["configuration_hash"],
        },
        "destinations": {
            "attempts_root": str(Path(attempts_root)),
            "governance_catalog": str(catalog.path),
            "canonical_catalog": str(Path(canonical_catalog_path)),
        },
        "approval": {"status": approval_status, "sha256": approval_hash,
                     "id": None if approval is None else approval.get("approval_id"),
                     "maximum_compute_budget": None if approval is None else approval.get("maximum_compute_budget"),
                     "compute_budget_enforcement": None if approval is None else approval.get("compute_budget_enforcement")},
        "issues": sorted(issues, key=lambda item: (item["category"], item["message"])),
        "execution_permitted": not issues and approval_status == "VALID_UNUSED",
        "side_effects": "NONE",
    }
