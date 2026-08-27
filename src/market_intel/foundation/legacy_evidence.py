"""Validation-only import boundary for immutable exploratory legacy evidence."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from research_contracts import (
    LEGACY_EVIDENCE_CLASS,
    LegacyLedgerError,
    canonical_json_bytes,
    map_legacy_lifecycle,
    read_exact_snapshot,
    sha256_file,
    validate_family_mapping,
)


IMPORTER_VERSION = "market_intel_legacy_importer_v1"
FORBIDDEN_CURRENT_MARKET_TOKENS = ("kite", "current_market", "current_tradable_only")


def _load_object(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LegacyLedgerError(f"expected JSON object: {path}")
    return value


def _contains_current_market_reference(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(token in text for token in FORBIDDEN_CURRENT_MARKET_TOKENS)


def validate_legacy_import(
    *,
    ledger_path: str | Path,
    snapshot_path: str | Path,
    snapshot_manifest_path: str | Path,
    family_mapping_path: str | Path,
) -> dict[str, Any]:
    """Validate without registering rows in the production experiment catalog."""
    ledger = _load_object(ledger_path)
    snapshot_manifest = _load_object(snapshot_manifest_path)
    family_mapping = _load_object(family_mapping_path)
    _, source_rows, source_row_hashes = read_exact_snapshot(
        snapshot_path,
        expected_hash=str(snapshot_manifest["sha256"]),
        expected_rows=int(snapshot_manifest["row_count"]),
    )
    source_ids = [str(row["hypothesis_id"]) for row in source_rows]
    validate_family_mapping(family_mapping, source_ids)

    if ledger.get("evidence_classification") != LEGACY_EVIDENCE_CLASS:
        raise LegacyLedgerError("legacy ledger has an invalid evidence classification")
    if ledger.get("snapshot_sha256") != snapshot_manifest.get("sha256"):
        raise LegacyLedgerError("ledger snapshot hash does not match immutable manifest")
    if ledger.get("family_mapping_version") != family_mapping.get("mapping_version"):
        raise LegacyLedgerError("ledger family-mapping version mismatch")
    if ledger.get("source_row_count") != len(source_rows):
        raise LegacyLedgerError("legacy ledger row count mismatch")
    if ledger.get("production_eligible") is not False:
        raise LegacyLedgerError("legacy evidence cannot be production eligible")

    exported = ledger.get("rows")
    if not isinstance(exported, list) or len(exported) != len(source_rows):
        raise LegacyLedgerError("legacy ledger rows are incomplete")
    exported_ids = [str(row.get("original_row_id", "")) for row in exported]
    if exported_ids != source_ids:
        raise LegacyLedgerError("legacy ledger row order or identity differs from snapshot")
    if len(set(exported_ids)) != len(exported_ids):
        raise LegacyLedgerError("legacy ledger contains duplicate row IDs")

    for index, (exported_row, source_row, source_hash) in enumerate(
        zip(exported, source_rows, source_row_hashes, strict=True), 1
    ):
        if exported_row.get("original_row_number") != index:
            raise LegacyLedgerError(f"legacy row number mismatch at {index}")
        if not exported_row.get("original_row_sha256"):
            raise LegacyLedgerError(f"missing source-row hash: {exported_ids[index - 1]}")
        if exported_row["original_row_sha256"] != source_hash:
            raise LegacyLedgerError(f"source-row hash mismatch: {exported_ids[index - 1]}")
        if exported_row.get("legacy_row") != source_row:
            raise LegacyLedgerError(f"legacy row values mutated: {exported_ids[index - 1]}")
        expected_lifecycle = map_legacy_lifecycle(
            str(source_row.get("window", "")), str(source_row.get("decision", ""))
        ).value
        if exported_row.get("neutral_lifecycle") != expected_lifecycle:
            raise LegacyLedgerError(f"lifecycle escalation: {exported_ids[index - 1]}")
        if exported_row.get("production_eligible") is not False:
            raise LegacyLedgerError(f"row is production eligible: {exported_ids[index - 1]}")
        if exported_row.get("manifest_reference") is None and exported_row.get(
            "provenance_status"
        ) == "VERIFIED_MANIFEST":
            raise LegacyLedgerError(f"verified manifest claim lacks reference: {exported_ids[index - 1]}")
        if not isinstance(exported_row.get("hypothesis_components"), dict):
            raise LegacyLedgerError(f"missing component contract: {exported_ids[index - 1]}")
        if _contains_current_market_reference(exported_row):
            raise LegacyLedgerError(
                f"current-market/Kite evidence is prohibited: {exported_ids[index - 1]}"
            )

    provenance = Counter(row["provenance_status"] for row in exported)
    lifecycle = Counter(row["neutral_lifecycle"] for row in exported)
    return {
        "validation_result": "PASS",
        "registration_classification": LEGACY_EVIDENCE_CLASS,
        "ledger_version": ledger["ledger_version"],
        "ledger_sha256": sha256_file(ledger_path),
        "snapshot_sha256": ledger["snapshot_sha256"],
        "family_mapping_version": ledger["family_mapping_version"],
        "source_row_count": len(exported),
        "manifest_status_counts": dict(sorted(provenance.items())),
        "lifecycle_counts": dict(sorted(lifecycle.items())),
        "promotion_eligible": False,
        "production_catalog_registration_allowed": False,
    }


class LegacyEvidenceCatalog:
    """Append-only JSONL catalog separated from the production run catalog."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise LegacyLedgerError("legacy evidence catalog contains a non-object row")
                records.append(value)
        return records

    def register(
        self, validation: Mapping[str, Any], *, imported_at: str | None = None
    ) -> tuple[dict[str, Any], bool]:
        if validation.get("validation_result") != "PASS":
            raise LegacyLedgerError("only validated legacy evidence can be cataloged")
        if validation.get("registration_classification") != LEGACY_EVIDENCE_CLASS:
            raise LegacyLedgerError("catalog accepts legacy exploratory evidence only")
        if validation.get("promotion_eligible") is not False:
            raise LegacyLedgerError("catalog cannot record promotable legacy evidence")
        record = {
            "ledger_version": validation["ledger_version"],
            "ledger_sha256": validation["ledger_sha256"],
            "snapshot_sha256": validation["snapshot_sha256"],
            "family_mapping_version": validation["family_mapping_version"],
            "importer_version": IMPORTER_VERSION,
            "import_timestamp": imported_at or datetime.now(timezone.utc).isoformat(),
            "source_row_count": validation["source_row_count"],
            "manifest_status_counts": validation["manifest_status_counts"],
            "lifecycle_counts": validation["lifecycle_counts"],
            "validation_result": validation["validation_result"],
            "registration_classification": LEGACY_EVIDENCE_CLASS,
            "promotion_eligible": False,
        }
        existing = self._records()
        for prior in existing:
            if prior.get("ledger_version") != record["ledger_version"]:
                continue
            comparable = dict(prior)
            comparable.pop("import_timestamp", None)
            candidate = dict(record)
            candidate.pop("import_timestamp", None)
            if comparable == candidate:
                return prior, False
            raise LegacyLedgerError(
                "an existing ledger version cannot be overwritten; use a new version"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json_bytes(record))
        return record, True
