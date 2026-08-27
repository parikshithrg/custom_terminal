from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from market_intel.foundation.legacy_evidence import (
    LEGACY_EVIDENCE_CLASS,
    LegacyEvidenceCatalog,
    LegacyLedgerError,
    validate_legacy_import,
)
from research_contracts import (
    canonical_json_bytes,
    export_legacy_ledger,
    map_legacy_lifecycle,
    read_exact_snapshot,
    sha256_file,
    validate_family_mapping,
    write_neutral_ledger,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "evidence" / "legacy" / "legacy_hypothesis_ledger_v1"
SNAPSHOT = PACKAGE / "hypothesis_log.csv"
SNAPSHOT_MANIFEST = PACKAGE / "snapshot_manifest.json"
MAPPING = ROOT / "specs" / "legacy_family_mapping_v1.json"
LEDGER = PACKAGE / "neutral_ledger.json"
EXPECTED_SNAPSHOT_HASH = "124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _export_with_empty_boundaries(tmp_path: Path, mapping: dict | None = None) -> dict:
    mapping_path = tmp_path / "mapping.json"
    value = copy.deepcopy(mapping or _json(MAPPING))
    for row in value["rows"]:
        row["artifact_candidates"] = []
        row.pop("manifest_reference", None)
    _write_json(mapping_path, value)
    return export_legacy_ledger(
        snapshot_path=SNAPSHOT,
        snapshot_manifest_path=SNAPSHOT_MANIFEST,
        family_mapping_path=mapping_path,
        artifact_boundaries={
            "repository_local_runs": tmp_path,
            "sibling_source_runs": tmp_path,
        },
    )


def test_exact_32_row_snapshot_hash_and_accounting():
    manifest = _json(SNAPSHOT_MANIFEST)
    payload, rows, row_hashes = read_exact_snapshot(
        SNAPSHOT, expected_hash=EXPECTED_SNAPSHOT_HASH, expected_rows=32
    )
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SNAPSHOT_HASH
    assert len(payload) == 32665
    assert len(rows) == len(row_hashes) == 32
    assert [row["hypothesis_id"] for row in rows] == manifest["ordered_row_ids"]
    assert sum(row["decision"] == "accepted" for row in rows) == 6
    assert sum(row["decision"] == "rejected" for row in rows) == 26


def test_source_is_immutable_during_export(tmp_path):
    before = SNAPSHOT.read_bytes()
    _export_with_empty_boundaries(tmp_path)
    assert SNAPSHOT.read_bytes() == before


def test_rejects_31_row_substitute(tmp_path):
    lines = SNAPSHOT.read_bytes().splitlines(keepends=True)
    substitute = tmp_path / "31_rows.csv"
    substitute.write_bytes(b"".join(lines[:-1]))
    with pytest.raises(LegacyLedgerError, match="hash mismatch"):
        read_exact_snapshot(
            substitute, expected_hash=EXPECTED_SNAPSHOT_HASH, expected_rows=32
        )


def test_rejects_changed_byte(tmp_path):
    changed = bytearray(SNAPSHOT.read_bytes())
    changed[100] ^= 1
    path = tmp_path / "changed.csv"
    path.write_bytes(changed)
    with pytest.raises(LegacyLedgerError, match="hash mismatch"):
        read_exact_snapshot(path, expected_hash=EXPECTED_SNAPSHOT_HASH, expected_rows=32)


def test_row_hashes_are_deterministic_and_bind_crlf_record():
    _, _, first = read_exact_snapshot(
        SNAPSHOT, expected_hash=EXPECTED_SNAPSHOT_HASH, expected_rows=32
    )
    _, _, second = read_exact_snapshot(
        SNAPSHOT, expected_hash=EXPECTED_SNAPSHOT_HASH, expected_rows=32
    )
    assert first == second
    lines = SNAPSHOT.read_bytes().splitlines(keepends=True)
    assert first[0] == hashlib.sha256(lines[1]).hexdigest()


def test_reviewed_family_mapping_is_complete_and_has_13_families():
    mapping = _json(MAPPING)
    manifest = _json(SNAPSHOT_MANIFEST)
    by_id = validate_family_mapping(mapping, manifest["ordered_row_ids"])
    assert len(by_id) == 32
    assert len({entry["family_id"] for entry in by_id.values()}) == 13
    assert by_id["7facf033cb36"]["family_id"] == "legacy_mf_accumulation_v1"


@pytest.mark.parametrize("defect", ["duplicate", "missing"])
def test_duplicate_or_missing_family_mapping_is_rejected(defect, tmp_path):
    mapping = _json(MAPPING)
    if defect == "duplicate":
        mapping["rows"].append(copy.deepcopy(mapping["rows"][0]))
    else:
        mapping["rows"].pop()
    with pytest.raises(LegacyLedgerError, match="family mapping"):
        validate_family_mapping(mapping, _json(SNAPSHOT_MANIFEST)["ordered_row_ids"])


def test_lifecycle_mapping_cannot_treat_legacy_acceptance_as_production():
    assert map_legacy_lifecycle("train", "accepted").value == "TRAIN_PROMOTED"
    assert map_legacy_lifecycle("val", "accepted").value == "VALIDATION_CONFIRMED"
    ledger = _json(LEDGER)
    assert ledger["production_eligible"] is False
    assert all(row["production_eligible"] is False for row in ledger["rows"])
    assert not any(row["neutral_lifecycle"].startswith("PRODUCTION") for row in ledger["rows"])


def test_missing_manifests_and_ambiguous_artifacts_are_preserved():
    ledger = _json(LEDGER)
    counts = ledger["diagnostics"]["manifest_status_counts"]
    assert counts == {
        "AMBIGUOUS_ARTIFACT_MATCH": 3,
        "PARTIAL_ARTIFACTS_NO_MANIFEST": 29,
    }
    assert all(row["manifest_reference"] is None for row in ledger["rows"])
    ambiguous = {
        row["original_row_id"] for row in ledger["rows"]
        if row["provenance_status"] == "AMBIGUOUS_ARTIFACT_MATCH"
    }
    assert ambiguous == {"cdd796d6e171", "0b11b017cef9", "7facf033cb36"}


def test_unresolved_components_remain_explicit():
    ledger = _json(LEDGER)
    first = ledger["rows"][0]["hypothesis_components"]
    assert first["economic_story"]["status"] == "PROVED_FROM_SNAPSHOT_ROW"
    assert first["decision_clock"] == {
        "value": None, "status": "UNRESOLVED_NO_RUN_MANIFEST", "evidence_refs": []
    }
    value_row = next(row for row in ledger["rows"] if row["original_row_id"] == "e39e744cc436")
    assert value_row["hypothesis_components"]["holding_horizon_sessions"]["value"] == 126


def test_neutral_export_is_byte_deterministic(tmp_path):
    ledger_a = _export_with_empty_boundaries(tmp_path / "a")
    ledger_b = _export_with_empty_boundaries(tmp_path / "b")
    assert canonical_json_bytes(ledger_a) == canonical_json_bytes(ledger_b)
    hash_a = write_neutral_ledger(
        ledger_a, json_path=tmp_path / "one.json", csv_path=tmp_path / "one.csv"
    )
    hash_b = write_neutral_ledger(
        ledger_b, json_path=tmp_path / "two.json", csv_path=tmp_path / "two.csv"
    )
    assert hash_a == hash_b


def test_generated_adapter_artifacts_can_be_rolled_back(tmp_path):
    ledger = _export_with_empty_boundaries(tmp_path / "inputs")
    output = tmp_path / "generated"
    write_neutral_ledger(ledger, json_path=output / "ledger.json", csv_path=output / "ledger.csv")
    assert output.exists()
    shutil.rmtree(output)
    assert not output.exists()
    assert sha256_file(SNAPSHOT) == EXPECTED_SNAPSHOT_HASH


def test_importer_verifies_hash_order_and_nonproduction_class():
    validation = validate_legacy_import(
        ledger_path=LEDGER,
        snapshot_path=SNAPSHOT,
        snapshot_manifest_path=SNAPSHOT_MANIFEST,
        family_mapping_path=MAPPING,
    )
    assert validation["validation_result"] == "PASS"
    assert validation["registration_classification"] == LEGACY_EVIDENCE_CLASS
    assert validation["source_row_count"] == 32
    assert validation["promotion_eligible"] is False
    assert validation["production_catalog_registration_allowed"] is False


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda value: value.update(snapshot_sha256="0" * 64), "snapshot hash"),
        (lambda value: value["rows"][0].update(original_row_sha256=""), "missing source-row hash"),
        (lambda value: value["rows"][0].update(neutral_lifecycle="TEST_CONFIRMED"), "lifecycle escalation"),
        (lambda value: value["rows"][0].update(production_eligible=True), "production eligible"),
    ],
)
def test_importer_rejects_hash_or_lifecycle_escalation(mutation, match, tmp_path):
    ledger = _json(LEDGER)
    mutation(ledger)
    path = tmp_path / "ledger.json"
    _write_json(path, ledger)
    with pytest.raises(LegacyLedgerError, match=match):
        validate_legacy_import(
            ledger_path=path, snapshot_path=SNAPSHOT,
            snapshot_manifest_path=SNAPSHOT_MANIFEST, family_mapping_path=MAPPING,
        )


def test_importer_rejects_current_kite_reference(tmp_path):
    ledger = _json(LEDGER)
    ledger["rows"][0]["artifact_references"].append({
        "boundary": "kite_current_market", "relative_path": "quote.json", "sha256": "0" * 64
    })
    path = tmp_path / "ledger.json"
    _write_json(path, ledger)
    with pytest.raises(LegacyLedgerError, match="Kite"):
        validate_legacy_import(
            ledger_path=path, snapshot_path=SNAPSHOT,
            snapshot_manifest_path=SNAPSHOT_MANIFEST, family_mapping_path=MAPPING,
        )


def test_importer_rejects_duplicate_row_ids(tmp_path):
    ledger = _json(LEDGER)
    ledger["rows"][1]["original_row_id"] = ledger["rows"][0]["original_row_id"]
    path = tmp_path / "ledger.json"
    _write_json(path, ledger)
    with pytest.raises(LegacyLedgerError, match="order or identity|duplicate"):
        validate_legacy_import(
            ledger_path=path, snapshot_path=SNAPSHOT,
            snapshot_manifest_path=SNAPSHOT_MANIFEST, family_mapping_path=MAPPING,
        )


def test_catalog_is_append_only_and_idempotent(tmp_path):
    validation = validate_legacy_import(
        ledger_path=LEDGER, snapshot_path=SNAPSHOT,
        snapshot_manifest_path=SNAPSHOT_MANIFEST, family_mapping_path=MAPPING,
    )
    catalog = LegacyEvidenceCatalog(tmp_path / "catalog.jsonl")
    first, appended = catalog.register(validation, imported_at="2026-08-27T05:05:00Z")
    assert appended is True
    again, appended = catalog.register(validation, imported_at="2099-01-01T00:00:00Z")
    assert appended is False
    assert again == first
    assert len((tmp_path / "catalog.jsonl").read_text().splitlines()) == 1

    changed = dict(validation)
    changed["ledger_sha256"] = "f" * 64
    with pytest.raises(LegacyLedgerError, match="cannot be overwritten"):
        catalog.register(changed, imported_at="2026-08-27T05:06:00Z")
    versioned = dict(changed)
    versioned["ledger_version"] = "neutral_legacy_hypothesis_ledger_v2"
    _, appended = catalog.register(versioned, imported_at="2026-08-27T05:07:00Z")
    assert appended is True
    assert len((tmp_path / "catalog.jsonl").read_text().splitlines()) == 2


def test_dtest_adapter_has_no_market_intel_dependency():
    source = (ROOT / "Data test" / "dtest" / "evaluate" / "legacy_export.py").read_text()
    assert "from market_intel" not in source
    assert "import market_intel" not in source
    assert "research_contracts" in source
