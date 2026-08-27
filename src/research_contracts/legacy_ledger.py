"""Dependency-neutral, read-only legacy hypothesis-ledger translation.

The exporter is deliberately conservative. It preserves source strings, never
recomputes performance, and cannot make a legacy row production eligible.
Artifact paths must be assigned by a reviewed mapping; titles are never used
for runtime matching.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .models import map_legacy_lifecycle


LEGACY_EXPORT_VERSION = "legacy_ledger_export_v1"
LEGACY_EVIDENCE_CLASS = "LEGACY_EXPLORATORY_EVIDENCE"
COMPONENT_NAMES = (
    "economic_story",
    "selection_rule",
    "decision_clock",
    "entry_rule",
    "holding_horizon_sessions",
    "exit_overlay",
    "cost_schedule_version",
    "portfolio_construction",
    "research_split",
    "research_status",
    "experiment_family_id",
)
EVIDENCE_STATUSES = {
    "VERIFIED_MANIFEST",
    "PARTIAL_ARTIFACTS_NO_MANIFEST",
    "MISSING_MANIFEST",
    "AMBIGUOUS_ARTIFACT_MATCH",
    "MISSING_ARTIFACTS",
}


class LegacyLedgerError(ValueError):
    """Raised when immutable legacy evidence violates its declared contract."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LegacyLedgerError(f"expected JSON object: {path}")
    return value


def read_exact_snapshot(
    path: str | Path, *, expected_hash: str, expected_rows: int
) -> tuple[bytes, list[dict[str, str]], list[str]]:
    """Read and hash the snapshot without normalizing or rewriting its bytes."""
    payload = Path(path).read_bytes()
    actual_hash = sha256_bytes(payload)
    if actual_hash != expected_hash:
        raise LegacyLedgerError(
            f"legacy snapshot hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LegacyLedgerError("legacy snapshot is not UTF-8 CSV") from exc
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    if len(rows) != expected_rows:
        raise LegacyLedgerError(
            f"legacy snapshot row count mismatch: expected {expected_rows}, got {len(rows)}"
        )

    # This designated v1 snapshot has one physical CRLF record per row. Keeping
    # the line terminator in each hash binds the exported row to its exact bytes.
    physical = payload.splitlines(keepends=True)
    if len(physical) != expected_rows + 1 or any(not line.endswith(b"\r\n") for line in physical):
        raise LegacyLedgerError("legacy snapshot v1 requires one CRLF physical record per row")
    row_hashes = [sha256_bytes(line) for line in physical[1:]]
    return payload, rows, row_hashes


def validate_family_mapping(mapping: Mapping[str, Any], row_ids: list[str]) -> dict[str, dict[str, Any]]:
    entries = mapping.get("rows")
    if not isinstance(entries, list):
        raise LegacyLedgerError("family mapping rows must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not str(entry.get("row_id", "")).strip():
            raise LegacyLedgerError("every family mapping requires row_id")
        row_id = str(entry["row_id"])
        if row_id in by_id:
            raise LegacyLedgerError(f"duplicate family mapping: {row_id}")
        family_id = str(entry.get("family_id", ""))
        if not family_id and entry.get("family_state") != "UNRESOLVED_FAMILY":
            raise LegacyLedgerError(f"missing family mapping: {row_id}")
        by_id[row_id] = entry
    missing = [row_id for row_id in row_ids if row_id not in by_id]
    extra = [row_id for row_id in by_id if row_id not in set(row_ids)]
    if missing or extra:
        raise LegacyLedgerError(f"family mapping mismatch: missing={missing}, extra={extra}")
    return by_id


def _safe_artifact(
    *, boundary_root: Path, relative_path: str
) -> Path:
    root = boundary_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise LegacyLedgerError(f"artifact escapes declared boundary: {relative_path}") from exc
    return candidate


def _component(value: Any, status: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {"value": value, "status": status, "evidence_refs": evidence_refs or []}


def _components(row: Mapping[str, str], mapping: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result = {
        name: _component(None, "UNRESOLVED_NO_RUN_MANIFEST") for name in COMPONENT_NAMES
    }
    result["economic_story"] = _component(
        row.get("story"), "PROVED_FROM_SNAPSHOT_ROW", [f"legacy_row:{row.get('hypothesis_id')}:story"]
    )
    result["research_split"] = _component(
        f"{row.get('split')}/{row.get('window')}",
        "PROVED_FROM_SNAPSHOT_ROW",
        [f"legacy_row:{row.get('hypothesis_id')}:split_window"],
    )
    result["research_status"] = _component(
        "EXPLORATORY", "ASSIGNED_BY_RETROACTIVE_POLICY", ["research_promotion_policy_v1"]
    )
    result["experiment_family_id"] = _component(
        mapping.get("family_id"), "PROVED_FROM_REVIEWED_MAPPING",
        [str(mapping.get("mapping_evidence", "legacy_family_mapping_v1"))],
    )
    for name, override in mapping.get("component_overrides", {}).items():
        if name not in result or not isinstance(override, dict):
            raise LegacyLedgerError(f"invalid component override {name!r}")
        result[name] = {
            "value": override.get("value"),
            "status": str(override.get("status", "UNRESOLVED_NO_RUN_MANIFEST")),
            "evidence_refs": list(override.get("evidence_refs", [])),
        }
    return result


def _artifact_evidence(
    mapping: Mapping[str, Any], boundaries: Mapping[str, Path]
) -> tuple[str, list[dict[str, Any]], list[str]]:
    declarations = mapping.get("artifact_candidates", [])
    if not declarations:
        return "MISSING_ARTIFACTS", [], []
    references: list[dict[str, Any]] = []
    missing: list[str] = []
    for declaration in declarations:
        label = str(declaration.get("boundary", ""))
        relative = str(declaration.get("path", ""))
        if label not in boundaries:
            raise LegacyLedgerError(f"undeclared artifact boundary: {label}")
        candidate = _safe_artifact(boundary_root=Path(boundaries[label]), relative_path=relative)
        if not candidate.is_file():
            missing.append(f"{label}:{relative}")
            continue
        references.append({
            "boundary": label,
            "relative_path": relative.replace("\\", "/"),
            "sha256": sha256_file(candidate),
            "byte_size": candidate.stat().st_size,
        })
    if missing:
        return "MISSING_ARTIFACTS", references, missing
    if mapping.get("artifact_linkage") == "AMBIGUOUS":
        return "AMBIGUOUS_ARTIFACT_MATCH", references, []
    manifest = mapping.get("manifest_reference")
    if not manifest:
        return "PARTIAL_ARTIFACTS_NO_MANIFEST", references, []
    label = str(manifest.get("boundary", ""))
    relative = str(manifest.get("path", ""))
    if label not in boundaries:
        raise LegacyLedgerError(f"undeclared manifest boundary: {label}")
    path = _safe_artifact(boundary_root=Path(boundaries[label]), relative_path=relative)
    if not path.is_file():
        return "MISSING_MANIFEST", references, [f"{label}:{relative}"]
    manifest_data = _load_json(path)
    if manifest_data.get("hypothesis_id") != mapping.get("row_id"):
        return "AMBIGUOUS_ARTIFACT_MATCH", references, []
    references.append({
        "boundary": label, "relative_path": relative.replace("\\", "/"),
        "sha256": sha256_file(path), "byte_size": path.stat().st_size,
        "kind": "root_manifest",
    })
    return "VERIFIED_MANIFEST", references, []


def export_legacy_ledger(
    *,
    snapshot_path: str | Path,
    snapshot_manifest_path: str | Path,
    family_mapping_path: str | Path,
    artifact_boundaries: Mapping[str, str | Path],
) -> dict[str, Any]:
    """Translate a fixed snapshot into the neutral contract without mutation."""
    snapshot_manifest = _load_json(snapshot_manifest_path)
    mapping = _load_json(family_mapping_path)
    expected_hash = str(snapshot_manifest["sha256"])
    expected_rows = int(snapshot_manifest["row_count"])
    before_hash = sha256_file(snapshot_path)
    _, rows, row_hashes = read_exact_snapshot(
        snapshot_path, expected_hash=expected_hash, expected_rows=expected_rows
    )
    row_ids = [str(row.get("hypothesis_id", "")) for row in rows]
    if row_ids != list(snapshot_manifest.get("ordered_row_ids", [])):
        raise LegacyLedgerError("snapshot row ordering differs from its immutable manifest")
    if len(set(row_ids)) != len(row_ids) or any(not row_id for row_id in row_ids):
        raise LegacyLedgerError("snapshot contains duplicate or missing row IDs")
    mappings = validate_family_mapping(mapping, row_ids)
    boundaries = {name: Path(path) for name, path in artifact_boundaries.items()}

    exported_rows: list[dict[str, Any]] = []
    for index, (row, row_hash) in enumerate(zip(rows, row_hashes, strict=True), 1):
        row_id = row_ids[index - 1]
        reviewed = mappings[row_id]
        evidence_status, artifacts, missing = _artifact_evidence(reviewed, boundaries)
        if evidence_status not in EVIDENCE_STATUSES:
            raise LegacyLedgerError(f"unsupported evidence status: {evidence_status}")
        exported_rows.append({
            "snapshot_version": snapshot_manifest["snapshot_version"],
            "snapshot_sha256": expected_hash,
            "original_row_number": index,
            "original_row_id": row_id,
            "original_row_sha256": row_hash,
            "legacy_row": dict(row),
            "legacy_decision": row.get("decision"),
            "neutral_lifecycle": map_legacy_lifecycle(
                str(row.get("window", "")), str(row.get("decision", ""))
            ).value,
            "experiment_family_id": reviewed.get("family_id"),
            "variant_id": reviewed.get("variant_id"),
            "reviewed_lineage_parent_ids": list(reviewed.get("lineage_parent_ids", [])),
            "supersession_reference": row.get("supersedes") or None,
            "mapping_rationale": reviewed.get("rationale"),
            "hypothesis_components": _components(row, reviewed),
            "artifact_references": artifacts,
            "missing_artifact_references": missing,
            "manifest_reference": None if evidence_status != "VERIFIED_MANIFEST" else artifacts[-1],
            "provenance_status": evidence_status,
            "production_eligible": False,
        })

    if sha256_file(snapshot_path) != before_hash:
        raise LegacyLedgerError("source snapshot mutated during read-only export")
    provenance_counts = Counter(row["provenance_status"] for row in exported_rows)
    lifecycle_counts = Counter(row["neutral_lifecycle"] for row in exported_rows)
    family_counts = Counter(row["experiment_family_id"] for row in exported_rows)
    split_counts = Counter(
        f"{row['legacy_row'].get('split')}/{row['legacy_row'].get('window')}"
        for row in exported_rows
    )
    unresolved_components = Counter()
    for row in exported_rows:
        for name, component in row["hypothesis_components"].items():
            if str(component["status"]).startswith("UNRESOLVED"):
                unresolved_components[name] += 1

    return {
        "ledger_version": "neutral_legacy_hypothesis_ledger_v1",
        "exporter_version": LEGACY_EXPORT_VERSION,
        "evidence_classification": LEGACY_EVIDENCE_CLASS,
        "snapshot_version": snapshot_manifest["snapshot_version"],
        "snapshot_sha256": expected_hash,
        "family_mapping_version": mapping["mapping_version"],
        "source_row_count": len(exported_rows),
        "production_eligible": False,
        "rows": exported_rows,
        "diagnostics": {
            "rows_by_family": dict(sorted(family_counts.items())),
            "rows_by_lifecycle": dict(sorted(lifecycle_counts.items())),
            "rows_by_split_window": dict(sorted(split_counts.items())),
            "manifest_status_counts": dict(sorted(provenance_counts.items())),
            "artifact_status_counts": dict(sorted(provenance_counts.items())),
            "unresolved_components": dict(sorted(unresolved_components.items())),
            "accepted_legacy_rows": sum(
                row["legacy_decision"] == "accepted" for row in exported_rows
            ),
            "validation_confirmed_legacy_rows": sum(
                row["neutral_lifecycle"] == "VALIDATION_CONFIRMED" for row in exported_rows
            ),
            "test_rows": sum(row["legacy_row"].get("window") == "test" for row in exported_rows),
            "replication_rows": 0,
        },
    }


def neutral_ledger_csv_bytes(ledger: Mapping[str, Any]) -> bytes:
    output = io.StringIO(newline="")
    fields = [
        "original_row_number", "original_row_id", "original_row_sha256", "title",
        "split", "window", "metric", "real_value", "legacy_decision",
        "neutral_lifecycle", "experiment_family_id", "variant_id",
        "provenance_status", "manifest_reference", "production_eligible",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in ledger["rows"]:
        legacy = row["legacy_row"]
        writer.writerow({
            "original_row_number": row["original_row_number"],
            "original_row_id": row["original_row_id"],
            "original_row_sha256": row["original_row_sha256"],
            "title": legacy.get("title"), "split": legacy.get("split"),
            "window": legacy.get("window"), "metric": legacy.get("metric"),
            "real_value": legacy.get("real_value"),
            "legacy_decision": row["legacy_decision"],
            "neutral_lifecycle": row["neutral_lifecycle"],
            "experiment_family_id": row["experiment_family_id"],
            "variant_id": row["variant_id"],
            "provenance_status": row["provenance_status"],
            "manifest_reference": "" if row["manifest_reference"] is None else json.dumps(
                row["manifest_reference"], sort_keys=True, separators=(",", ":")
            ),
            "production_eligible": "false",
        })
    return output.getvalue().encode("utf-8")


def write_neutral_ledger(
    ledger: Mapping[str, Any], *, json_path: str | Path, csv_path: str | Path
) -> tuple[str, str]:
    payloads = {
        Path(json_path): canonical_json_bytes(ledger),
        Path(csv_path): neutral_ledger_csv_bytes(ledger),
    }
    hashes: list[str] = []
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != payload:
            raise FileExistsError(f"immutable neutral ledger differs: {path}")
        if not path.exists():
            path.write_bytes(payload)
        hashes.append(sha256_bytes(payload))
    return hashes[0], hashes[1]
