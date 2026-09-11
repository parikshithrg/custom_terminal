"""Offline governance checks for the bounded R10N-D owner decision packet."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from research_contracts import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10n_d/plan_v1"


def _load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_plan_reuses_anchor_and_caps_two_dates_four_payloads() -> None:
    sample = _load("proposed_sample_design.json")
    budget = _load("request_payload_budget.json")
    assert sample["existing_anchor"] == {
        "trading_date": "2026-09-09",
        "disposition": "REUSE_ALREADY_QUALIFIED_PACKAGE_WITHOUT_REACQUISITION",
        "payloads": 2,
    }
    assert len(sample["proposed_new_dates"]) <= 2
    assert sum(len(item["files"]) for item in sample["proposed_new_dates"]) <= 4
    assert budget["new_dates_maximum"] == 2
    assert budget["new_payloads_maximum"] == 4
    assert budget["existing_anchor_retrieval_requests"] == 0


def test_candidates_are_proposals_not_availability_claims() -> None:
    sample = _load("proposed_sample_design.json")
    policy = _load("date_selection_policy.json")
    assert sample["availability_claimed"] is False
    assert all(item["availability"] == "UNCONFIRMED_NO_EXTERNAL_CHECK_AUTHORIZED"
               for item in sample["proposed_new_dates"])
    assert policy["candidate_status"] == "PROPOSED_OFFLINE_AVAILABILITY_AND_TRADING_STATUS_UNCONFIRMED"
    assert policy["if_either_pair_is_unavailable"].startswith("STOP_NO_FALLBACK")


def test_every_date_requires_atomic_explicit_owner_approval() -> None:
    approval = _load("owner_approval_schema.json")
    protocol = _load("acquisition_protocol.json")
    assert approval["approval_state"] == "NOT_APPROVED"
    assert approval["approval_is_atomic_per_exact_date_pair"] is True
    assert approval["partial_or_blank_decision_authorizes_requests"] is False
    assert all(value is None for key, value in approval["owner_must_decide"].items()
               if key != "dates")
    assert "OWNER_APPROVES_EXACT_DATE_FILENAME_URL_DESTINATION_PURPOSE_AND_RETENTION_FOR_EACH_DATE" in protocol["prerequisites"]


def test_request_budget_prohibits_retry_redirect_enumeration_and_fallback() -> None:
    budget = _load("request_payload_budget.json")
    failures = _load("failure_stop_matrix.json")
    assert budget["authorized_initial_http_gets_maximum"] == 4
    assert budget["authorized_http_responses_maximum"] == 4
    assert budget["authorized_redirect_hops"] == 0
    assert budget["retries_per_request"] == 0
    assert budget["availability_enumeration_requests"] == 0
    assert budget["fallback_date_requests"] == 0
    for key in ("automatic_retry", "enumeration", "fallback", "access_control_bypass"):
        assert failures[key] is False


def test_legacy_and_udiff_scopes_remain_distinct() -> None:
    failures = _load("failure_stop_matrix.json")
    record = _load("non_authorization_record.json")
    legacy = next(item for item in failures["conditions"] if item["condition"] == "legacy bhavcopy encountered")
    assert legacy["action"] == "STOP_SEPARATE_FUTURE_LEGACY_ADAPTER_APPROVAL"
    assert record["legacy_adapter_authorized"] is False


def test_acceptance_matrix_fails_closed_without_matching_anchor_counts() -> None:
    matrix = _load("schema_stability_acceptance_matrix.json")
    by_question = {item["question"]: item for item in matrix["criteria"]}
    assert matrix["silent_acceptance_of_required_or_identity_change"] is False
    assert by_question["UDiFF to MII join"]["threshold"] == "100_PERCENT_MATCHED"
    assert "STOP_ON_FIRST" in by_question["required type drift"]["failure"]
    assert "WITHOUT_EQUAL_COUNT_REQUIREMENT" in by_question["contract population changes"]["threshold"]
    assert "prior success" not in matrix["threshold_rationale"].lower()


def test_correction_behavior_is_honest_and_not_monitored() -> None:
    correction = _load("correction_behavior_evidence_plan.json")
    assert correction["recurring_monitor"] is False
    assert correction["repeated_retrieval_authorized"] is False
    assert correction["bounded_plan_can_establish_correction_behavior"] is False
    assert "SAME_DATE_SAME_FILENAME" in correction["replacement_evidence_rule"]
    assert "NEVER_TREAT_DIFFERENT_DATE" in correction["cross_date_rule"]


def test_production_and_research_remain_unauthorized_and_fingerprint_unchanged() -> None:
    record = _load("non_authorization_record.json")
    impact = json.loads((ROOT / "docs/investigations/r10n_c/adapter_v1/research_state_impact.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "specs/pre_research_review_policy_v2.json").read_text(encoding="utf-8"))
    current = compute_research_state_fingerprint(ROOT, policy)
    assert record["lifecycle_state"] == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert record["production_activation"] is False
    assert record["research_authorized"] is False
    assert record["research_fingerprint_state"] == "STALE_FAIL_CLOSED_UNCHANGED"
    assert current["file_count"] == impact["candidate_working_tree"]["file_count"]
    assert current["sha256"] == impact["candidate_working_tree"]["sha256"]


def test_r10nb_and_r10nc_evidence_is_byte_identical() -> None:
    bindings = _load("historical_evidence_bindings.json")
    for version, relative in (("r10n_b", "r10n_b/qualification_v1"), ("r10n_c", "r10n_c/adapter_v1")):
        directory = ROOT / "docs/investigations" / relative
        assert set(bindings[version]) == {path.name for path in directory.glob("*.json")}
        for name, expected in bindings[version].items():
            assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    assert bindings["historical_files_modified"] is False


def test_retention_is_bounded_and_raw_payloads_remain_untracked() -> None:
    retention = _load("retention_deletion_policy.json")
    assert retention["new_raw_packages"]["git_status"] == "IGNORED_AND_NEVER_COMMITTED"
    assert retention["new_raw_packages"]["retention_deadline"].startswith("OWNER_MUST_SUPPLY")
    assert retention["indefinite_raw_retention"] is False
    assert not any(path.suffix.lower() in {".zip", ".gz", ".csv", ".parquet"} for path in RUN.iterdir())


def test_evidence_is_strict_sanitized_json_and_manifest_bound() -> None:
    private = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
    secret = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\\s*[:=]")
    for path in RUN.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        assert not private.search(text) and not secret.search(text)
    manifest = _load("root_manifest.json")
    expected = {path.name for path in RUN.glob("*.json")} - {"root_manifest.json"}
    assert {item["path"] for item in manifest["artifacts"]} == expected
    for item in manifest["artifacts"]:
        payload = (RUN / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
    report = manifest["report_binding"]
    payload = (ROOT / report["path"]).read_bytes()
    assert len(payload) == report["byte_length"]
    assert hashlib.sha256(payload).hexdigest() == report["sha256"]


def test_completion_records_zero_access_and_owner_decision_only() -> None:
    completion = _load("completion.json")
    assert completion["completion_decision"] == "READY_FOR_OWNER_MULTI_DATE_DECISION"
    assert completion["network_requests"] == 0
    assert completion["payloads_downloaded"] == 0
    assert completion["external_access_authorized"] is False
    assert completion["recommended_next_milestone"] == "SEPARATELY_OWNER_APPROVED_R10N_E_BOUNDED_EXECUTION"
