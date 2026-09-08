from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from research_contracts import (
    FingerprintReconciliationError,
    coherence_binding_hash,
    compute_research_state_fingerprint,
    git_commit_research_state_fingerprint,
    validate_fingerprint_coherence_amendment,
    validate_fingerprint_coherence_bundle,
)
from research_contracts.legacy_ledger import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "docs/investigations/r10i/amendment_v2/fingerprint_reconciliation.json"
COMPLETION = ROOT / "docs/investigations/r10i/amendment_v2/completion.json"
MANIFEST = ROOT / "docs/investigations/r10i/amendment_v2/manifest.json"
REPORT = ROOT / "reports/RESEARCH_R10I_FINGERPRINT_COHERENCE_AMENDMENT.md"
POLICY = ROOT / "specs/pre_research_review_policy_v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reseal(value: dict) -> dict:
    result = deepcopy(value)
    result.pop("payload_sha256", None)
    result["payload_sha256"] = sha256_bytes(canonical_json_bytes(result))
    return result


def _git_row(commit: str, path: str) -> dict:
    content = subprocess.check_output(["git", "cat-file", "blob", f"{commit}:{path}"], cwd=ROOT)
    return {"path": path, "sha256": hashlib.sha256(content).hexdigest(), "byte_size": len(content)}


def test_git_commit_fingerprints_are_exact_and_evidence_is_non_recursive():
    policy = _load(POLICY)
    implementation = git_commit_research_state_fingerprint(ROOT, policy, "89ba5b7")
    evidence = git_commit_research_state_fingerprint(ROOT, policy, "886cf56")
    assert implementation["sha256"] == evidence["sha256"] == (
        "19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6"
    )
    assert implementation["file_count"] == evidence["file_count"] == 280
    assert implementation["fingerprint_input_inventory_hash"] == implementation["sha256"]
    paths = {row["path"] for row in evidence["inventory"]}
    assert not any(path.startswith("docs/investigations/r10i/") for path in paths)
    assert "reports/RESEARCH_R10I_GOVERNANCE_REMEDIATION.md" not in paths


def test_both_conflicting_working_tree_values_are_reproduced():
    policy = _load(POLICY)
    current = compute_research_state_fingerprint(ROOT, policy)
    rows = {row["path"]: row for row in current["inventory"]}
    for path in (
        "src/research_contracts/__init__.py",
        "src/research_contracts/fingerprint_reconciliation.py",
    ):
        rows[path] = _git_row("886cf56", path)
    post_refresh = [rows[path] for path in sorted(rows)]
    assert sha256_bytes(canonical_json_bytes(post_refresh)) == (
        "236fddae8660e373eccdc6bb34a67a0dc0baaf7e91ff6203f4d24a43193a172f"
    )
    for path in (
        "specs/laboratory_entrypoint_inventory_v2.json",
        "specs/pre_research_review_policy_v2.json",
    ):
        rows[path] = _git_row("e07b616", path)
    pre_refresh = [rows[path] for path in sorted(rows)]
    assert sha256_bytes(canonical_json_bytes(pre_refresh)) == (
        "e0870bd050c2906f1aa81ead3ffe66871031db106e5ee39c046c5a011184759c"
    )


def test_amendment_validates_commit_claims_and_preserves_v1_bytes():
    amendment, policy = _load(AMENDMENT), _load(POLICY)
    result = validate_fingerprint_coherence_amendment(
        amendment, repository_root=ROOT, policy=policy,
        preserved_v1_hashes=amendment["preserved_v1_artifact_hashes"],
    )
    assert result["status"] == "VALID_STATE_SPECIFIC_COHERENCE_AMENDMENT"
    assert result["authority_extended"] is False
    for path, expected in amendment["preserved_v1_artifact_hashes"].items():
        assert _sha(ROOT / path) == expected


@pytest.mark.parametrize("mutation", ["fingerprint", "count", "policy", "commit", "kind", "authority"])
def test_amendment_fails_closed_on_incoherent_or_expansive_claims(mutation: str):
    amendment, policy = _load(AMENDMENT), _load(POLICY)
    if mutation == "fingerprint":
        amendment["state_references"]["implementation_source"]["sha256"] = "0" * 64
    elif mutation == "count":
        amendment["state_references"]["evidence"]["file_count"] = 279
    elif mutation == "policy":
        amendment["fingerprint_policy_version"] = "wrong"
    elif mutation == "commit":
        amendment["state_references"]["implementation_source"]["commit"] = "e07b616"
    elif mutation == "kind":
        amendment["state_references"]["evidence"]["reference_kind"] = "WORKING_TREE_SNAPSHOT"
    else:
        amendment["authority"]["research_or_backtesting"] = True
    amendment = _reseal(amendment)
    with pytest.raises(FingerprintReconciliationError):
        validate_fingerprint_coherence_amendment(
            amendment, repository_root=ROOT, policy=policy,
            preserved_v1_hashes=_load(AMENDMENT)["preserved_v1_artifact_hashes"],
        )


def test_report_completion_checkpoint_and_manifest_share_one_binding():
    amendment, completion, manifest = _load(AMENDMENT), _load(COMPLETION), _load(MANIFEST)
    assert coherence_binding_hash(amendment) == amendment["coherence_binding_sha256"]
    result = validate_fingerprint_coherence_bundle(
        amendment=amendment, completion=completion, manifest=manifest,
        report_text=REPORT.read_text(encoding="utf-8"), repository_root=ROOT,
    )
    assert result["status"] == "VALID_COHERENT_AMENDMENT_BUNDLE"


def test_bundle_detects_semantic_and_artifact_hash_disagreement():
    amendment, completion, manifest = _load(AMENDMENT), _load(COMPLETION), _load(MANIFEST)
    completion["coherence_binding_sha256"] = "0" * 64
    with pytest.raises(FingerprintReconciliationError, match="completion disagrees"):
        validate_fingerprint_coherence_bundle(
            amendment=amendment, completion=completion, manifest=manifest,
            report_text=REPORT.read_text(encoding="utf-8"), repository_root=ROOT,
        )
    completion = _load(COMPLETION)
    manifest["outputs"]["reports/RESEARCH_R10I_FINGERPRINT_COHERENCE_AMENDMENT.md"] = "0" * 64
    with pytest.raises(FingerprintReconciliationError):
        validate_fingerprint_coherence_bundle(
            amendment=amendment, completion=completion, manifest=manifest,
            report_text=REPORT.read_text(encoding="utf-8"), repository_root=ROOT,
        )


def test_entrypoint_count_and_protected_momentum_are_unchanged():
    inventory = _load(ROOT / "specs/laboratory_entrypoint_inventory_v2.json")
    assert inventory["entrypoint_count"] == 77
    assert _sha(ROOT / "specs/momentum_12_1_v1.json") == (
        "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5"
    )
