"""Static integrity and known-answer checks for R.10C evidence."""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs" / "investigations" / "r10c" / "run_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_root_binds_clean_exact_checkpoint_and_noncanonical_scope():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert root["source_commit"] == "9737868493649b9c1484f460ebe32ab32dc6158d"
    assert root["execution_start_dirty"] is False
    assert root["entrypoint"] == "tools/r10c_generate_evidence.py"
    assert root["entrypoint_sha256"] == _sha(ROOT / root["entrypoint"])
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert not root["canonical"] and not root["promotion_eligible"]
    assert root["official_format_status"] == "PENDING_OFFICIAL_FORMAT_EVIDENCE"


def test_all_artifact_hashes_and_raw_manifests_reconcile():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert len(root["artifact_hashes"]) == 27
    for relative, digest in root["artifact_hashes"].items():
        assert _sha(RUN / relative) == digest
    assert len(root["raw_manifests"]) == 4
    for relative in root["raw_manifests"].values():
        manifest_path = RUN / relative
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = manifest_path.parent / manifest["stored_payload"]
        assert _sha(payload) == manifest["content_hash"]
        assert manifest["data_classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert not list(RUN.rglob("*.tmp")) and not list(RUN.rglob("*.staging"))


def test_parquet_contracts_load_and_raw_prices_are_byte_logically_unchanged():
    parquets = sorted(RUN.glob("*.parquet"))
    frames = {path.name: pd.read_parquet(path) for path in parquets}
    assert len(frames) == 8
    assert len(frames["event_vintages.parquet"]) == 22
    assert len(frames["identity_graph.parquet"]) == 21
    known = json.loads((RUN / "known_answers.json").read_text(encoding="utf-8"))
    assert known["raw_price_hash_before"] == known["raw_price_hash_after"]


def test_exact_identity_adjustment_and_terminal_known_answers():
    known = json.loads((RUN / "known_answers.json").read_text(encoding="utf-8"))
    assert known["rename_instrument_before"] == known["rename_instrument_after"] == "SYN_C_I001"
    assert known["ticker_reuse_instrument"] == "SYN_C_I013"
    assert known["split_price_factor"] == 0.5
    assert known["bonus_price_factor"] == 2 / 3
    assert known["share_merger_quantity"] == 40
    assert known["share_merger_proceeds"] == 2000
    assert known["mixed_merger_proceeds"] == 4000
    assert known["demerger_quantity"] == 33
    assert known["demerger_cash"] == 10
    assert known["demerger_proceeds"] == 1990
    assert known["cash_delisting_proceeds"] == 7500
    assert known["disappearance_status"] == "UNRESOLVED_TERMINAL"
    assert known["cancel_before"] == "ACTIVE" and known["cancel_after"] == "CANCELLED"


def test_outcome_counts_preserve_all_predictions_and_unresolved_terminal():
    known = json.loads((RUN / "known_answers.json").read_text(encoding="utf-8"))
    assert known["outcome_counts_before"] == {"MISSING_EXIT": 2, "RIGHT_CENSORED": 1}
    assert known["outcome_counts_after"] == {
        "RESOLVED_TERMINAL": 1, "RIGHT_CENSORED": 1, "UNRESOLVED_TERMINAL": 1}
    assert len(pd.read_parquet(RUN / "outcomes_before.parquet")) == 3
    assert len(pd.read_parquet(RUN / "outcomes_after.parquet")) == 3


def test_incremental_equivalence_and_hash_preservation_are_complete():
    equivalence = json.loads((RUN / "incremental_equivalence.json").read_text(encoding="utf-8"))
    preservation = json.loads((RUN / "historical_hash_preservation.json").read_text(encoding="utf-8"))
    ledger = json.loads((RUN / "incremental_rebuild_ledger.json").read_text(encoding="utf-8"))
    assert len(equivalence) == 8 and all(equivalence.values())
    assert len(preservation) == 8 and all(preservation.values())
    assert len(ledger) == 200
    assert sum(row["state"] == "REBUILT_INPUT_CHANGED" for row in ledger) == 54
    assert sum(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger) == 146


def test_failure_matrix_and_prior_evidence_are_bound():
    failures = json.loads((RUN / "failure_matrix.json").read_text(encoding="utf-8"))
    assert len(failures) == 15
    assert failures["CONFLICTING_TERMINAL_CLASSIFICATION"] == "PRESERVED_CONFLICT"
    assert all(value in {"PASS_FAIL_CLOSED", "PRESERVED_CONFLICT"} for value in failures.values())
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r10b/run_v1/root_manifest.json": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }
    for relative, digest in expected.items():
        assert _sha(ROOT / relative) == digest


def test_no_private_paths_or_secret_assignments_in_evidence():
    text = "\n".join(path.read_text(encoding="utf-8") for path in RUN.rglob("*.json"))
    assert "C:\\Users\\" not in text
    for phrase in ("api_secret=", "access_token=", "password=", "private_fno_binding"):
        assert phrase not in text.lower()

