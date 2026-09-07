"""Static integrity checks for the committed R.10B evidence package."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs" / "investigations" / "r10b" / "run_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_root_binds_clean_exact_implementation_checkpoint_and_entrypoint():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert root["source_commit"] == "2ccbc4844e4c2156595c5097dde6c80ecb7c42b0"
    assert root["execution_start_dirty"] is False
    assert root["post_generation_worktree_expected_dirty"] is True
    assert root["entrypoint"] == "tools/r10b_generate_evidence.py"
    assert root["entrypoint_sha256"] == _sha(ROOT / root["entrypoint"])
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert root["canonical"] is False and root["promotion_eligible"] is False


def test_every_declared_artifact_hash_reconciles_and_staging_is_absent():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert len(root["artifact_hashes"]) == 61
    for relative, expected in root["artifact_hashes"].items():
        assert _sha(RUN / relative) == expected
    assert not (RUN / ".source-staging").exists()
    assert not list(RUN.rglob("*.tmp"))
    assert not list(RUN.rglob("*.staging"))


def test_raw_objects_are_portable_content_addressed_and_identity_bound():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert len(root["raw_manifests"]) == 14
    for relative in root["raw_manifests"].values():
        assert not Path(relative).is_absolute()
        manifest_path = RUN / relative
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = manifest_path.parent / manifest["stored_payload"]
        assert _sha(payload) == manifest["content_hash"]
        assert payload.stat().st_size == manifest["byte_size"]
        assert manifest["state"] == "SUCCEEDED"
        assert manifest["data_classification"] == "SYNTHETIC_ONLY_NONCANONICAL"


def test_all_supported_stages_match_clean_rebuild_and_preserve_unaffected_hashes():
    equivalence = json.loads((RUN / "canonical_equivalence.json").read_text(encoding="utf-8"))
    preservation = json.loads((RUN / "historical_hash_preservation.json").read_text(encoding="utf-8"))
    assert len(equivalence) == 11 and all(equivalence.values())
    assert len(preservation) == 11
    assert sum(item["unaffected_count"] for item in preservation.values()) == 137
    assert all(item["hashes_preserved"] for item in preservation.values())


def test_decision_ledger_has_exact_rebuild_and_reuse_counts():
    ledger = json.loads((RUN / "rebuild_decision_ledger.json").read_text(encoding="utf-8"))
    states = [item["state"] for item in ledger]
    assert len(ledger) == 231
    assert states.count("REBUILT_INPUT_CHANGED") == 94
    assert states.count("REUSED_HASH_IDENTICAL") == 137
    assert all(item["reason"] for item in ledger)


def test_schema_and_failure_outcomes_are_explicit():
    routed = {item["stage_id"]: item for item in json.loads(
        (RUN / "schema_routing_results.json").read_text(encoding="utf-8"))}
    assert routed["additive_schema"]["output_schema_version"] == "synthetic_incremental_bar_v2"
    assert routed["malformed"]["quarantined"] == 1
    assert routed["breaking_schema"]["error"] == "UNKNOWN_SCHEMA_VERSION"
    failures = {item["scenario"]: item for item in json.loads(
        (RUN / "failure_recovery.json").read_text(encoding="utf-8"))}
    assert failures["duplicate_retrieval"]["result"] == "REUSED_IDENTICAL_BYTES"
    assert failures["identity_conflict"]["result"] == "IMMUTABLE_SOURCE_IDENTITY_CONFLICT"
    assert failures["after_object_publish"]["restart"] == "REUSED_IDENTICAL_BYTES"


def test_r10a_and_other_protected_evidence_remain_unchanged():
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r9p/manifest_v1.json": "f0f7b7e8842783c1df2c6ade2dea2ad8cd0c496958361b1cce134e9de0cd0e56",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "src/market_intel/foundation/fno_production_boundary.py": "dcde3cbf1cd2cb1d5e70527cacb7066daf50e9cf6e48eb6fe44df45af8fc11ea",
    }
    for relative, digest in expected.items():
        assert _sha(ROOT / relative) == digest


def test_package_contains_no_private_path_or_secret_assignment():
    content = "\n".join(path.read_text(encoding="utf-8") for path in RUN.rglob("*.json"))
    assert "C:\\Users\\" not in content
    for phrase in ("api_secret=", "access_token=", "password=", "private_fno_binding"):
        assert phrase not in content.lower()
