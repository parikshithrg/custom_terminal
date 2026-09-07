"""Static integrity tests for the R.10F evidence package."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10f/run_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_root_binds_clean_noncanonical_checkpoint():
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert root["source_commit"] == "42a938c50ea013dcb1d3971e4f61162fc5148ac9"
    assert root["execution_start_dirty"] is False
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert root["canonical"] is False and root["promotion_eligible"] is False
    assert root["decision"] == "NO_DECISION"
    assert root["r10a_holdout_state"] == "UNCONSUMED_SYNTHETIC_HOLDOUT"


def test_all_forty_eight_artifact_hashes_reconcile():
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert len(root["artifact_hashes"]) == 48
    for relative, digest in root["artifact_hashes"].items():
        assert _sha(RUN / relative) == digest
        assert "\\" not in relative and ".." not in Path(relative).parts


def test_six_bundles_are_complete_and_manifest_last_contract_is_present():
    manifests = list((RUN / "published/bundles").glob("*/root_manifest.json"))
    assert len(manifests) == 6
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        assert set(manifest["objects"]) == {"snapshot.json", "components.json", "lifecycle.json",
                                               "freshness.json", "publication_policy.json"}
        for name, digest in manifest["objects"].items():
            assert _sha(manifest_path.parent / name) == digest


def test_known_history_hash_freshness_and_decision_answers():
    known = json.loads((RUN / "known_answers.json").read_text())
    assert known["bundle_count"] == 6
    assert known["initial_bundle_hash"] == known["idempotent_hash"]
    assert known["latest_snapshot_id"] == "SYN-PUB-003"
    assert known["history_order"] == ["SYN-PUB-006", "SYN-PUB-005", "SYN-PUB-004",
                                       "SYN-PUB-003", "SYN-PUB-002", "SYN-PUB-001"]
    assert known["freshness"]["at_boundary"]["status"] == "CURRENT"
    assert known["freshness"]["one_beyond"]["status"] == "AGING"
    assert known["freshness"]["superseded"]["status"] == "SUPERSEDED"
    assert known["decision"] == {"decision": "NO_DECISION",
                                  "reason": "SYNTHETIC_NONCANONICAL_EVIDENCE"}


def test_incremental_equivalence_and_preservation_are_complete():
    equivalent = json.loads((RUN / "incremental_equivalence.json").read_text())
    preserved = json.loads((RUN / "historical_hash_preservation.json").read_text())
    ledger = json.loads((RUN / "incremental_rebuild_ledger.json").read_text())
    assert len(equivalent) == len(preserved) == 7
    assert all(equivalent.values()) and all(preserved.values())
    assert len(ledger) == 266
    assert sum(row["state"] == "REBUILT_INPUT_CHANGED" for row in ledger) == 52
    assert sum(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger) == 214


def test_failure_matrix_and_prior_roots_are_bound():
    failure = json.loads((RUN / "failure_matrix.json").read_text())
    assert len(failure) == 19 and set(failure.values()) == {"PASS_FAIL_CLOSED"}
    root = json.loads((RUN / "root_manifest.json").read_text())
    assert root["references"]["r10a"] == "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580"
    assert root["references"]["r10e"] == "a48915801d99c8eca7559079c597d9157e3b3699d5a5cf0759f6a4e01aabd7b3"
    assert root["references"]["momentum"] == "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5"


def test_presentation_artifact_is_explicitly_safe():
    model = json.loads((RUN / "presentation_read_models.json").read_text())
    assert model == {"decision": "NO_DECISION", "latest": "SYN-PUB-003",
                     "warning": "SYNTHETIC ENGINEERING EVIDENCE"}


def test_json_is_strict_and_has_no_private_or_secret_material():
    texts = []
    for path in RUN.rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        texts.append(raw)
    combined = "\n".join(texts)
    assert "C:\\Users\\" not in combined
    for phrase in ("api_secret=", "access_token=", "request_token=", "password=", "private_fno_binding"):
        assert phrase not in combined.lower()
