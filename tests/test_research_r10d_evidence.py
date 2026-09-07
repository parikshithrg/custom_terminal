"""Static integrity tests for the committed R.10D evidence package."""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10d/run_v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_root_binds_exact_clean_checkpoint_and_noncanonical_scope():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert root["source_commit"] == "447bf403fd4eb19b5d72b1cc2db9a7b1c7aa6698"
    assert root["execution_start_dirty"] is False
    assert root["entrypoint"] == "tools/r10d_generate_evidence.py"
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert root["canonical"] is False and root["promotion_eligible"] is False
    assert root["official_exchange_compatibility"] == "NOT_CLAIMED"


def test_every_declared_artifact_hash_reconciles():
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert len(root["artifact_hashes"]) == 11
    for relative, expected in root["artifact_hashes"].items():
        assert _sha(RUN / relative) == expected
    assert not any(path.name.endswith(".tmp") or ".staging" in path.name for path in RUN.rglob("*"))


def test_calendar_and_outcome_tables_are_typed_and_complete():
    vintages = pd.read_parquet(RUN / "calendar_vintages.parquet")
    final = pd.read_parquet(RUN / "calendar_final.parquet")
    outcomes = pd.read_parquet(RUN / "session_outcomes.parquet")
    assert len(vintages) == 174 and len(final) == 169
    assert final.session_id.nunique() == 169
    assert str(final.scheduled_open.dtype).startswith("datetime64[us, UTC]")
    assert outcomes.set_index("prediction_id").at["SYN_CLOCK_P1", "outcome_status"] == "RESOLVED"
    assert outcomes.set_index("prediction_id").at["SYN_CLOCK_P2", "outcome_status"] == "RIGHT_CENSORED"


def test_known_answers_are_exact():
    answers = json.loads((RUN / "known_answers.json").read_text(encoding="utf-8"))
    assert answers["local_open_to_utc"] == "2020-01-06 03:45:00+00:00"
    assert answers["shortened_close"] == "2019-12-31T07:00:00+00:00"
    assert answers["non_session_month_end_resolves_to"] == "SYNX-2019-11-29"
    assert answers["next_entry_after_holiday"]["session_id"] == "SYNX-2020-01-28"
    assert answers["exit_21"]["session_id"] == "SYNX-2020-02-28"
    assert answers["session_distance"] == 21
    assert answers["t_plus_2"]["session_id"] == "SYNX-2020-02-06"
    assert answers["t_plus_1"]["session_id"] == "SYNX-2020-03-03"
    assert answers["terminal_cash_settlement"]["session_id"] == "SYNX-2020-03-04"
    assert answers["terminal_share_settlement"]["session_id"] == "SYNX-2020-03-05"


def test_fold_uses_session_ordinals_and_declared_22_session_boundary():
    fold = json.loads((RUN / "fold_reconciliation.json").read_text(encoding="utf-8"))
    assert fold["calendar_version"] == "synthetic_exchange_calendar_r10d_v1"
    assert fold["purge_sessions"] == fold["embargo_sessions"] == 22
    assert fold["train_end_session_id"] == "SYNX-2020-01-02"
    assert fold["validation_start_session_id"] == "SYNX-2020-03-10"


def test_incremental_equivalence_and_hash_preservation_are_complete():
    equivalent = json.loads((RUN / "incremental_equivalence.json").read_text(encoding="utf-8"))
    preserved = json.loads((RUN / "historical_hash_preservation.json").read_text(encoding="utf-8"))
    ledger = json.loads((RUN / "incremental_rebuild_ledger.json").read_text(encoding="utf-8"))
    assert len(equivalent) == len(preserved) == 6
    assert all(equivalent.values()) and all(preserved.values())
    assert len(ledger) == 156
    assert sum(row["state"] == "REBUILT_INPUT_CHANGED" for row in ledger) == 14
    assert sum(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger) == 142


def test_failure_matrix_and_prior_evidence_are_bound():
    failure = json.loads((RUN / "failure_matrix.json").read_text(encoding="utf-8"))
    assert len(failure) == 16
    assert failure["CONFLICTING_ACTIVE_REVISIONS"] == "PRESERVED_CONFLICT_AND_BLOCKED"
    root = json.loads((RUN / "root_manifest.json").read_text(encoding="utf-8"))
    assert root["references"] == {
        "r10a_root": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "r10b_root": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
        "r10c_root": "bf5722abab22ca1920186a7ff2572c8095d1cb75fbd442ed00e5f8dbd0893ce6",
        "momentum_spec": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "golden_expected": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }


def test_evidence_has_no_private_paths_or_secret_assignments():
    text = "\n".join(path.read_text(encoding="utf-8") for path in RUN.rglob("*.json"))
    assert "C:\\Users\\" not in text
    for phrase in ("api_secret=", "access_token=", "request_token=", "password=", "private_fno_binding"):
        assert phrase not in text.lower()
