"""Canonical validation/import gate for prospectively governed bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from research_contracts.governance import (
    GOVERNED_EVIDENCE_CLASS,
    ROOT_MANIFEST_CONTRACT_VERSION,
    GovernanceCatalog,
    GovernanceError,
    canonical_hash,
    validate_family,
    validate_input_declaration,
    validate_preregistration,
)
from research_contracts.legacy_ledger import canonical_json_bytes, sha256_file


FUTURE_IMPORTER_VERSION = "canonical_future_evidence_importer_v1"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GovernanceError(f"expected JSON object: {path}")
    return value


def validate_governed_bundle(
    *, bundle_path: str | Path, family_path: str | Path,
    preregistration_path: str | Path, catalog: GovernanceCatalog,
) -> dict[str, Any]:
    bundle = Path(bundle_path).resolve()
    manifest_path = bundle / "root_manifest.json"
    if not manifest_path.is_file():
        raise GovernanceError("ungoverned output rejected: mandatory root manifest is missing")
    manifest = _load(manifest_path)
    family = _load(family_path)
    prereg = _load(preregistration_path)
    validate_family(family)
    validate_preregistration(prereg)
    if manifest.get("manifest_contract_version") != ROOT_MANIFEST_CONTRACT_VERSION:
        raise GovernanceError("unknown root-manifest contract")
    if manifest.get("evidence_classification") != GOVERNED_EVIDENCE_CLASS:
        raise GovernanceError("ungoverned output cannot enter canonical evidence")
    if manifest.get("preregistration_sha256") != sha256_file(preregistration_path):
        raise GovernanceError("root manifest preregistration hash mismatch")
    if (manifest.get("family_id"), manifest.get("family_version")) != (
        family["family_id"], family["version"]
    ):
        raise GovernanceError("root manifest family is not registered")
    if (manifest.get("experiment_id"), manifest.get("experiment_version")) != (
        prereg["experiment_id"], prereg["version"]
    ):
        raise GovernanceError("root manifest experiment differs from preregistration")
    declaration = manifest.get("input_declaration", {})
    if declaration.get("sha256") != canonical_hash(declaration.get("value")):
        raise GovernanceError("root manifest input declaration hash mismatch")
    capability_pass = validate_input_declaration(declaration["value"], prereg)
    if bool(manifest.get("dataset_capability_gate_passed")) != capability_pass:
        raise GovernanceError("root manifest dataset-gate result is inconsistent")
    if manifest.get("configuration_hash") != declaration["value"]["configuration_hash"]:
        raise GovernanceError("root manifest configuration hash mismatch")
    if manifest.get("environment_fingerprint") != declaration["value"]["environment_fingerprint"]:
        raise GovernanceError("root manifest environment fingerprint mismatch")

    events = catalog.events()
    catalog.verify(events)
    family_key = f"{family['family_id']}__{family['version']}"
    family_hash = sha256_file(family_path)
    registered = [
        event for event in events
        if event.get("event_type") == "FAMILY_REGISTERED"
        and event.get("object_refs", {}).get("family_key") == family_key
        and event.get("object_hashes", {}).get("family_sha256") == family_hash
    ]
    if len(registered) != 1:
        raise GovernanceError("canonical import requires the exact registered family version")
    locked = [
        event for event in events
        if event.get("event_type") == "PREREGISTRATION_LOCKED"
        and event.get("object_hashes", {}).get("preregistration_sha256")
        == manifest["preregistration_sha256"]
    ]
    if len(locked) != 1:
        raise GovernanceError("canonical import requires a locked preregistration")
    authorization = [
        event for event in events
        if event.get("event_type") == "RUN_AUTHORIZED"
        and event.get("object_refs", {}).get("run_attempt_id") == manifest["run_attempt_id"]
        and event.get("event_sha256") == manifest["authorization_event_sha256"]
        and event.get("object_refs", {}).get("family_key") == family_key
        and event.get("object_hashes", {}).get("family_sha256") == family_hash
        and event.get("object_hashes", {}).get("preregistration_sha256")
        == manifest["preregistration_sha256"]
        and event.get("object_hashes", {}).get("input_declaration_sha256")
        == declaration["sha256"]
        and event.get("object_hashes", {}).get("approval_sha256")
        == manifest.get("run_approval_reference", {}).get("approval_sha256")
    ]
    if len(authorization) != 1:
        raise GovernanceError("canonical import requires the exact authorization event")
    approval_ref = manifest.get("run_approval_reference", {})
    registered_approval = [
        event for event in events
        if event.get("event_type") == "RUN_APPROVAL_REGISTERED"
        and event.get("object_refs", {}).get("approval_id") == approval_ref.get("approval_id")
        and event.get("object_hashes", {}).get("approval_sha256")
        == approval_ref.get("approval_sha256")
        and event.get("object_hashes", {}).get("approval_payload_sha256")
        == approval_ref.get("approval_payload_sha256")
    ]
    consumed_approval = [
        event for event in events
        if event.get("event_type") == "RUN_STARTED"
        and event.get("event_id") == approval_ref.get("consumed_by_event_id")
        and event.get("event_sha256") == approval_ref.get("consumed_by_event_sha256")
        and event.get("object_refs", {}).get("run_attempt_id") == manifest["run_attempt_id"]
        and event.get("object_refs", {}).get("approval_id") == approval_ref.get("approval_id")
        and event.get("object_hashes", {}).get("approval_sha256")
        == approval_ref.get("approval_sha256")
    ]
    if len(registered_approval) != 1 or len(consumed_approval) != 1:
        raise GovernanceError("canonical import requires exact registered and consumed run approval")
    final_ref = manifest.get("catalog_event_reference", {})
    final_events = [
        event for event in events
        if event.get("event_id") == final_ref.get("event_id")
        and event.get("event_type") == final_ref.get("event_type")
        and event.get("object_refs", {}).get("run_attempt_id") == manifest["run_attempt_id"]
        and event.get("object_hashes", {}).get("root_manifest_sha256") == sha256_file(manifest_path)
    ]
    if len(final_events) != 1:
        raise GovernanceError("root manifest lacks its exact final catalog event")
    split = prereg["split_requested"]
    split_ref = manifest.get("split_access_event")
    if split == "train" and split_ref is not None:
        raise GovernanceError("training run has an unexpected split-access event")
    if split in {"validation", "test", "replication"}:
        expected_event_type = {
            "validation": "VALIDATION_ACCESS_GRANTED",
            "test": "TEST_ACCESS_CONSUMED",
            "replication": "REPLICATION_REGISTERED",
        }[split]
        if not split_ref or not any(
            event.get("event_id") == split_ref.get("event_id")
            and event.get("event_sha256") == split_ref.get("event_sha256")
            and event.get("event_type") == expected_event_type
            and event.get("object_refs", {}).get("family_key") == family_key
            and event.get("object_refs", {}).get("experiment_key")
            == f"{prereg['experiment_id']}__{prereg['version']}"
            and event.get("object_refs", {}).get("dataset_split_version")
            == declaration["value"]["dataset_split_version"]
            and event.get("object_hashes", {}).get("preregistration_sha256")
            == manifest["preregistration_sha256"]
            for event in events
        ):
            raise GovernanceError("canonical import requires valid split-access evidence")
    status_to_event = {
        "COMPLETED": "RUN_COMPLETED", "FAILED": "RUN_FAILED", "ABORTED": "RUN_ABORTED"
    }
    if status_to_event.get(manifest.get("completion_status")) != final_ref.get("event_type"):
        raise GovernanceError("manifest completion state conflicts with catalog")
    if manifest.get("completion_status") == "COMPLETED" and manifest.get("missing_required_outputs"):
        raise GovernanceError("completed bundle has unresolved required outputs")

    declared = {str(item["relative_path"]): item for item in manifest["output_artifact_inventory"]}
    expected = {str(item["relative_path"]): item for item in prereg["expected_artifacts"]}
    unknown_canonical = sorted(set(declared) - set(expected))
    missing_required = sorted(
        relative for relative, definition in expected.items()
        if definition.get("required", True) and relative not in declared
    )
    if unknown_canonical:
        raise GovernanceError(f"canonical inventory contains undeclared artifacts: {unknown_canonical}")
    if manifest.get("completion_status") == "COMPLETED" and missing_required:
        raise GovernanceError(f"canonical inventory is missing required artifacts: {missing_required}")
    for relative, item in declared.items():
        path = (bundle / relative).resolve()
        try:
            path.relative_to(bundle)
        except ValueError as exc:
            raise GovernanceError("manifest artifact escapes its bundle") from exc
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise GovernanceError(f"artifact hash verification failed: {relative}")
        if path.stat().st_size != item.get("byte_size"):
            raise GovernanceError(f"artifact size verification failed: {relative}")
    for relative in manifest.get("unexpected_outputs", []):
        if relative in declared:
            raise GovernanceError("unexpected output silently entered canonical inventory")
    if manifest.get("promotion_eligible"):
        approvals = [
            event for event in events
            if event.get("event_type") == "PROMOTION_APPROVED"
            and event.get("object_refs", {}).get("run_attempt_id") == manifest["run_attempt_id"]
        ]
        if not capability_pass or len(approvals) != 1:
            raise GovernanceError("promotion eligibility is incompatible with gates")
    return {
        "validation_result": "PASS",
        "classification": (
            "CANONICAL_COMPLETED_EVIDENCE"
            if manifest["completion_status"] == "COMPLETED"
            else "CANONICAL_GOVERNED_ATTEMPT"
        ),
        "run_attempt_id": manifest["run_attempt_id"],
        "root_manifest_sha256": sha256_file(manifest_path),
        "completion_status": manifest["completion_status"],
        "promotion_eligible": bool(manifest["promotion_eligible"]),
        "legacy_evidence_affected": False,
        "importer_version": FUTURE_IMPORTER_VERSION,
    }


class CanonicalFutureEvidenceCatalog:
    """Append-only catalog isolated from the R.2 legacy evidence catalog."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]

    def register(self, validation: Mapping[str, Any], *, imported_at: str) -> tuple[dict[str, Any], bool]:
        raise GovernanceError(
            "caller-supplied validation cannot be cataloged; use register_bundle for mandatory revalidation"
        )

    def register_bundle(
        self, *, bundle_path: str | Path, family_path: str | Path,
        preregistration_path: str | Path, governance_catalog: GovernanceCatalog,
        imported_at: str,
    ) -> tuple[dict[str, Any], bool]:
        validation = validate_governed_bundle(
            bundle_path=bundle_path, family_path=family_path,
            preregistration_path=preregistration_path, catalog=governance_catalog,
        )
        record = {**dict(validation), "imported_at": imported_at}
        for existing in self.records():
            if existing.get("run_attempt_id") != record["run_attempt_id"]:
                continue
            left, right = dict(existing), dict(record)
            left.pop("imported_at", None); right.pop("imported_at", None)
            if left == right:
                return existing, False
            raise GovernanceError("canonical run-attempt record cannot be overwritten")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json_bytes(record))
        return record, True
