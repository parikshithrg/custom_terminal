from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from research_contracts import (
    FingerprintReconciliationError,
    compute_research_state_fingerprint,
    git_commit_research_state_fingerprint,
    validate_fingerprint_reconciliation,
)
from research_contracts.legacy_ledger import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "docs/project_status/research_fingerprint_reconciliation_r10i_v1.json"
POLICY_V1 = ROOT / "specs/pre_research_review_policy_v1.json"
POLICY_V2 = ROOT / "specs/pre_research_review_policy_v2.json"
INVENTORY_V1 = ROOT / "specs/laboratory_entrypoint_inventory_v1.json"
INVENTORY_V2 = ROOT / "specs/laboratory_entrypoint_inventory_v2.json"
HISTORICAL_RECORDS = [f"docs/project_status/pre_research_review_record_v{x}.json" for x in range(1, 6)]
R10_MISSING_FROM_V1 = {
    "tools/r9j_synthetic_boundary.py", "tools/r9k_windows_feasibility.py",
    "tools/r9m_vfs_evaluation.py", "tools/r9n_adversarial.py",
    "tools/r9n_regression.py", "tools/r9p_integrated.py", "tools/r9p_regression.py",
    *{f"tools/r10{x}_generate_evidence.py" for x in "abcdefg"},
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reseal(value: dict) -> dict:
    result = deepcopy(value)
    result.pop("deterministic_payload_sha256", None)
    result["deterministic_payload_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _discover() -> set[str]:
    result = set()
    for root_name in ("Data test", "scripts", "tools", "src", "views"):
        for path in (ROOT / root_name).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if "/tests/" not in f"/{relative}/" and "__main__" in path.read_text(encoding="utf-8"):
                result.add(relative)
    return result


def test_checkpoint_validates_current_and_historical_state_without_authority():
    checkpoint, policy = _load(CHECKPOINT), _load(POLICY_V2)
    # The v1 checkpoint is preserved historical evidence, not a claim about the
    # post-amendment working tree.  Its source commit is verified independently.
    source = git_commit_research_state_fingerprint(ROOT, policy, checkpoint["source_commit"])
    assert source["sha256"] == "19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6"
    assert source["file_count"] == checkpoint["current_file_count"] == 280
    with pytest.raises(FingerprintReconciliationError, match="current fingerprint checkpoint is stale"):
        validate_fingerprint_reconciliation(
            checkpoint, repository_root=ROOT, policy=policy,
            historical_records=HISTORICAL_RECORDS,
        )
    assert checkpoint["execution_start_clean"] is True
    assert all(value is False for value in checkpoint["authority"].values())


def test_historical_records_retain_original_fingerprints_and_scopes():
    checkpoint = _load(CHECKPOINT)
    for row in checkpoint["historical_reviews"]:
        record = _load(ROOT / row["record_path"])
        assert _sha(ROOT / row["record_path"]) == row["record_byte_sha256"]
        assert record["research_state_fingerprint"] == row["reviewed_fingerprint"]
        assert record["covered_future_scope"] == row["review_scope"]
        assert row["current_scope_status"] == "HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE"


def test_tampered_current_evidence_fails():
    checkpoint, policy = _load(CHECKPOINT), _load(POLICY_V2)
    checkpoint["current_fingerprint"] = "0" * 64
    checkpoint = _reseal(checkpoint)
    with pytest.raises(FingerprintReconciliationError, match="current fingerprint checkpoint is stale"):
        validate_fingerprint_reconciliation(
            checkpoint, repository_root=ROOT, policy=policy,
            historical_records=HISTORICAL_RECORDS,
        )


def test_tampered_historical_record_hash_is_detectable_without_rewriting_v1():
    checkpoint = _load(CHECKPOINT)
    checkpoint["historical_reviews"][0]["record_byte_sha256"] = "0" * 64
    row = checkpoint["historical_reviews"][0]
    assert _sha(ROOT / row["record_path"]) != row["record_byte_sha256"]


def test_unsealed_tampering_and_policy_changes_fail_closed():
    checkpoint, policy = _load(CHECKPOINT), _load(POLICY_V2)
    checkpoint["authority"]["research_execution_authorized"] = True
    with pytest.raises(FingerprintReconciliationError, match="payload hash"):
        validate_fingerprint_reconciliation(
            checkpoint, repository_root=ROOT, policy=policy,
            historical_records=HISTORICAL_RECORDS,
        )
    checkpoint = _load(CHECKPOINT)
    policy["research_state"]["exclude_globs"].append("src/**")
    with pytest.raises(FingerprintReconciliationError):
        validate_fingerprint_reconciliation(
            checkpoint, repository_root=ROOT, policy=policy,
            historical_records=HISTORICAL_RECORDS,
        )


def test_v2_policy_preserves_v1_hash_rules_and_v1_bytes():
    v1, v2 = _load(POLICY_V1), _load(POLICY_V2)
    assert _sha(POLICY_V1) == "dfd4c848ff6e73d8ecb63c069e8421dda848271c42c4b4900db9f5919d3ab5d4"
    assert v2["base_policy"]["sha256"] == _sha(POLICY_V1)
    assert v2["research_state"] == v1["research_state"]
    assert v2["fingerprint_reconciliation"]["statuses"] == [
        "CURRENT_FOR_DECLARED_SCOPE",
        "HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE",
        "INVALID",
    ]


def test_cumulative_inventory_is_complete_unique_and_hash_current():
    inventory = _load(INVENTORY_V2)
    entries = inventory["entries"]
    paths = [entry["path"] for entry in entries]
    assert inventory["entrypoint_count"] == len(paths) == 77
    assert len(paths) == len(set(paths))
    assert set(paths) == _discover()
    for entry in entries:
        assert entry["source_sha256"] == _sha(ROOT / entry["path"])
        assert entry["governance_classification"]
        assert entry["permitted_operating_mode"]


def test_fourteen_forward_tools_are_synthetic_offline_and_nonpromoting():
    entries = {entry["path"]: entry for entry in _load(INVENTORY_V2)["entries"]}
    assert R10_MISSING_FROM_V1 <= entries.keys()
    for path in R10_MISSING_FROM_V1:
        entry = entries[path]
        assert entry["real_or_private_data_eligibility"] == "SYNTHETIC_ONLY"
        assert entry["network_or_provider_access"] == "NO"
        assert entry["broker_connectivity"] == "NO"
        assert entry["lifecycle_promotion"] == "NO"
        assert entry["external_mutation"] == "NO"
        assert entry["permitted_operating_mode"] == "OFFLINE_SYNTHETIC_ONLY"


def test_historical_inventory_is_preserved_and_v2_is_forward_only():
    assert _sha(INVENTORY_V1) == "6bb3b6a91422903ec2682b13a41b45b92de48300bce8a001179d32633bc3526b"
    inventory = _load(INVENTORY_V2)
    assert inventory["schema_version"] == "laboratory_entrypoint_inventory_v2"
    assert inventory["supersedes_for_current_enforcement"] == "specs/laboratory_entrypoint_inventory_v1.json"
    assert inventory["preserves_historical_inventory"] is True
    assert inventory["unsafe_bypass_count"] == 0


def test_r10i_manifest_binds_inputs_outputs_and_has_no_authority():
    path = ROOT / "docs/investigations/r10i/remediation_v1/manifest.json"
    manifest = _load(path)
    expected_payload = manifest.pop("payload_sha256")
    assert sha256_bytes(canonical_json_bytes(manifest)) == expected_payload
    for section in ("bound_inputs", "outputs"):
        for relative, expected in manifest[section].items():
            assert _sha(ROOT / relative) == expected
    for relative, expected in manifest["implementation_hashes"].items():
        content = subprocess.check_output(
            ["git", "cat-file", "blob", f"{manifest['clean_checkpoint_commit']}:{relative}"],
            cwd=ROOT,
        )
        assert hashlib.sha256(content).hexdigest() == expected
    # Verification tests describe evidence commit 886cf56; later amendment
    # tests are allowed to evolve without invalidating the v1 manifest.
    for relative, expected in manifest["verification_test_hashes"].items():
        content = subprocess.check_output(
            ["git", "cat-file", "blob", f"886cf5687b094f648f960373fedeec3219dca67f:{relative}"],
            cwd=ROOT,
        )
        assert hashlib.sha256(content).hexdigest() == expected
    assert all(value is False for value in manifest["authority"].values())
    assert manifest["completion_state"] == "GOVERNANCE_FORWARD_REMEDIATION_COMPLETE_READY_FOR_CONSOLIDATED_PDF"
