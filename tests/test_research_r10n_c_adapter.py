"""Recorded evidence, lifecycle, and architecture checks for R10N-C."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from market_intel.foundation import nse_fno_candidate
from research_contracts import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10n_c/adapter_v1"


def _load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_candidate_lifecycle_is_explicit_and_not_registered() -> None:
    lifecycle = _load("lifecycle_state.json")
    assert nse_fno_candidate.LIFECYCLE_STATE == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert lifecycle["state"] == nse_fno_candidate.LIFECYCLE_STATE
    for key in ("active_provider", "source_registry_entry_added", "ui_exposure",
                "production_runner_exposure", "scheduled_job_exposure",
                "research_pipeline_exposure", "network_access"):
        assert lifecycle[key] is False
    registry = (ROOT / "src/market_intel/foundation/source_registry.py").read_text(encoding="utf-8")
    providers = (ROOT / "src/market_intel/foundation/providers.py").read_text(encoding="utf-8")
    assert "nse_fno_candidate" not in registry + providers


def test_candidate_is_not_imported_by_application_ui_or_research() -> None:
    for directory in ("src/market_intel/application", "src/market_intel/research", "views"):
        for path in (ROOT / directory).rglob("*.py"):
            assert "nse_fno_candidate" not in path.read_text(encoding="utf-8")


def test_contract_documents_explicit_inputs_exact_types_and_no_network() -> None:
    contract = _load("adapter_contract.json")
    fields = _load("field_mapping.json")
    assert contract["inputs"]["implicit_manifest_reading"] is False
    assert contract["inputs"]["implicit_archive_discovery"] is False
    assert contract["network_capability"] is False
    assert fields["numeric_policy"] == "DECIMAL_FOR_PRICES_AND_STRIKES_INTEGER_FOR_COUNTS_NO_BINARY_FLOAT"
    assert fields["identity_join_key"] == ["FinInstrmId"]
    normalized = {item["normalized"] for item in fields["fields"]}
    assert normalized == {
        "trading_date", "financial_instrument_id", "instrument_type", "ticker",
        "underlying_financial_instrument_id", "expiry", "strike", "option_type",
        "lot_size", "open", "high", "low", "close", "settlement_price",
        "volume", "open_interest", "source_family", "source_version", "provenance",
    }


def test_synthetic_coverage_does_not_claim_real_schema_stability() -> None:
    coverage = _load("synthetic_test_coverage.json")
    assert coverage["adapter_test_result"] == "20_PASS"
    assert "TWO_DISTINCT_TRADING_DATES" in coverage["covered"]
    assert coverage["inference_limit"] == (
        "SYNTHETIC_MULTI_DATE_BEHAVIOR_DOES_NOT_ESTABLISH_REAL_NSE_SCHEMA_STABILITY"
    )


def test_r10nb_reconciliation_preserves_every_historical_hash() -> None:
    reconciliation = _load("r10nb_reconciliation.json")
    historical = ROOT / "docs/investigations/r10n_b/qualification_v1"
    assert reconciliation["result"] == "BYTE_IDENTICAL"
    for name, expected in reconciliation["artifacts"].items():
        assert hashlib.sha256((historical / name).read_bytes()).hexdigest() == expected
    assert reconciliation["sealed_r10nb_files_modified"] is False


def test_research_state_change_is_explicitly_fail_closed() -> None:
    impact = _load("research_state_impact.json")
    assert impact["baseline"] == {
        "file_count": 280,
        "sha256": "5dec06efda39c94ef0d933d18b442af0014ecf07d6365f09b773c24b5209c901",
    }
    assert impact["candidate_working_tree"]["file_count"] == 281
    policy = json.loads((ROOT / "specs/pre_research_review_policy_v2.json").read_text(encoding="utf-8"))
    current = compute_research_state_fingerprint(ROOT, policy)
    assert impact["candidate_working_tree"] == {
        "file_count": current["file_count"], "sha256": current["sha256"],
    }
    assert impact["review_state"] == "STALE_FAIL_CLOSED"
    assert impact["research_authorized"] is False


def test_failure_matrix_covers_closed_identity_archive_and_schema_boundaries() -> None:
    codes = {item["code"] for item in _load("failure_matrix.json")["failures"]}
    for fragment in ("DUPLICATE_IDENTITY", "AMBIGUOUS_IDENTITY", "UNRESOLVED_IDENTITY",
                     "LEGACY_SCHEMA_REJECTED", "MALFORMED_VALUE", "ARCHIVE_VALIDATION_FAILURE"):
        assert fragment in codes


def test_root_manifest_hashes_all_non_root_evidence() -> None:
    root = _load("root_manifest.json")
    expected = {path.name for path in RUN.glob("*.json")} - {"root_manifest.json"}
    assert {item["path"] for item in root["artifacts"]} == expected
    for item in root["artifacts"]:
        payload = (RUN / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
    report = root["report_binding"]
    payload = (ROOT / report["path"]).read_bytes()
    assert len(payload) == report["byte_length"]
    assert hashlib.sha256(payload).hexdigest() == report["sha256"]


def test_completion_and_report_keep_unauthorized_actions_closed() -> None:
    completion = _load("completion.json")
    report = (ROOT / "reports/NSE_FNO_DATE_AGNOSTIC_CANDIDATE_ADAPTER.md").read_text(encoding="utf-8")
    assert completion["completion_decision"] == "DATE_AGNOSTIC_CANDIDATE_ADAPTER_SYNTHETICALLY_VALIDATED"
    assert completion["real_multi_date_schema_stability_established"] is False
    flattened = " ".join(report.split())
    assert "does not authorize another download" in flattened
    assert "separately owner-approved" in flattened


def test_evidence_is_strict_sanitized_json_without_payloads() -> None:
    private = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
    secret = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\s*[:=]")
    for path in RUN.iterdir():
        assert path.suffix == ".json"
        text = path.read_text(encoding="utf-8")
        json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        assert not private.search(text) and not secret.search(text)
    assert not any(path.suffix.lower() in {".zip", ".gz", ".csv", ".parquet"} for path in RUN.iterdir())
