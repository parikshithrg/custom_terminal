"""Offline R10N-E preflight and R10N-D amendment governance checks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from research_contracts import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "docs/investigations/r10n_d/amendment_v1"
PREFLIGHT = ROOT / "docs/investigations/r10n_e/preflight_v1"


def _load(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text(encoding="utf-8"))


def test_original_budget_cannot_fund_prior_pair_confirmation() -> None:
    audit = _load(AMENDMENT, "inconsistency_audit.json")
    requirements = audit["requirements"]
    assert requirements["payload_gets"] == requirements["original_total_request_ceiling"] == 4
    assert requirements["original_confirmation_request_budget"] == 0
    assert requirements["confirm_complete_pair_before_acquiring_either_file"] is True
    assert audit["finding"] == "INTERNALLY_INCONSISTENT_REQUEST_BUDGET"
    assert audit["network_access_during_audit"] == 0


def test_amendment_is_exactly_four_heads_then_four_gets() -> None:
    budget = _load(AMENDMENT, "amended_request_budget.json")
    protocol = _load(AMENDMENT, "amended_acquisition_protocol.json")
    assert budget["direct_head_confirmation_requests_maximum"] == 4
    assert budget["direct_get_acquisition_requests_maximum"] == 4
    assert budget["total_http_requests_maximum"] == 8
    assert budget["accepted_direct_http_200_responses_maximum"] == 8
    assert budget["ordering"].startswith("ALL_FOUR_EXACT_HEAD_CONFIRMATIONS")
    assert protocol["all_pairs_confirmed_before_any_acquisition"] is True
    assert protocol["confirmation_is_payload_validation"] is False


def test_amendment_preserves_zero_redirect_retry_fallback_and_enumeration() -> None:
    budget = _load(AMENDMENT, "amended_request_budget.json")
    protocol = _load(AMENDMENT, "amended_acquisition_protocol.json")
    for key in ("redirect_hops", "retries", "landing_page_requests",
                "enumeration_requests", "fallback_requests", "anchor_requests"):
        assert budget[key] == 0
    for key in ("automatic_retry", "redirect_following", "alternative_date_or_url",
                "archive_enumeration", "partial_pair_publication"):
        assert protocol[key] is False


def test_owner_amendment_is_blank_and_authorizes_zero_requests() -> None:
    decision = _load(AMENDMENT, "owner_amendment_decision_schema.json")
    state = _load(PREFLIGHT, "owner_authorization_state.json")
    assert decision["decision_state"] == "OWNER_REVIEW_REQUIRED"
    assert all(value is None for value in decision["owner_must_explicitly_confirm"].values())
    assert decision["partial_blank_assumed_or_indirect_approval_authorizes_requests"] is False
    assert state["requests_authorized"] == 0
    assert state["acknowledgement_flag_authorized"] is False


def test_zero_redirect_preflight_matches_implementation() -> None:
    evidence = _load(PREFLIGHT, "zero_redirect_preflight.json")
    source = (ROOT / evidence["implementation"]).read_text(encoding="utf-8")
    source_bytes = (ROOT / evidence["implementation"]).read_bytes()
    assert len(source_bytes) == evidence["implementation_byte_length"]
    assert hashlib.sha256(source_bytes).hexdigest() == evidence["implementation_sha256"]
    assert evidence["strict_mode_api"] in source
    assert 'kwargs["allow_redirects"] = False' in source
    assert "300 <= status <= 399" in source
    assert evidence["maximum_files_per_invocation"] == 2
    assert evidence["automatic_retry"] is False
    assert evidence["legacy_allowlisted_redirect_mode_preserved"] is True
    original = ROOT / "tools/download_nse_fno_reports.py"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == (
        "6d5132aedea3640310852e31290b899aaa6226f7c6d7415f380363c6c9de1073"
    )


def test_stop_is_offline_before_owner_gate_and_execution() -> None:
    ledger = _load(PREFLIGHT, "request_budget_ledger.json")
    stop = _load(PREFLIGHT, "stop_ledger.json")
    assert sum(value for key, value in ledger.items() if key.endswith("requests")) == 0
    assert ledger["payloads_retained"] == 0
    assert stop["external_access_attempted"] is False
    assert stop["phase_2_entered"] is False and stop["phase_3_entered"] is False
    assert stop["partial_acceptance"] is False


def test_original_r10nd_plan_remains_hash_bound_and_unmodified() -> None:
    audit = _load(AMENDMENT, "inconsistency_audit.json")
    plan = ROOT / "docs/investigations/r10n_d/plan_v1"
    root = json.loads((plan / "root_manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((plan / "root_manifest.json").read_bytes()).hexdigest() == audit["governing_root_manifest_sha256"]
    for item in root["artifacts"]:
        payload = (plan / item["path"]).read_bytes()
        assert len(payload) == item["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_lifecycle_and_stale_research_gate_are_unchanged() -> None:
    lifecycle = _load(PREFLIGHT, "lifecycle_state.json")
    impact = json.loads((ROOT / "docs/investigations/r10n_c/adapter_v1/research_state_impact.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "specs/pre_research_review_policy_v2.json").read_text(encoding="utf-8"))
    current = compute_research_state_fingerprint(ROOT, policy)
    assert lifecycle["adapter_state"] == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert lifecycle["production_or_research_authorized"] is False
    assert lifecycle["research_fingerprint"] == "STALE_FAIL_CLOSED_UNCHANGED"
    assert current["file_count"] == impact["candidate_working_tree"]["file_count"]
    assert current["sha256"] == impact["candidate_working_tree"]["sha256"]


def test_amendment_and_preflight_manifests_bind_sanitized_json() -> None:
    private = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
    secret = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\\s*[:=]")
    for directory in (AMENDMENT, PREFLIGHT):
        for path in directory.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            assert not private.search(text) and not secret.search(text)
        manifest = _load(directory, "root_manifest.json")
        expected = {path.name for path in directory.glob("*.json")} - {"root_manifest.json"}
        assert {item["path"] for item in manifest["artifacts"]} == expected
        for item in manifest["artifacts"]:
            payload = (directory / item["path"]).read_bytes()
            assert len(payload) == item["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        if "report_binding" in manifest:
            binding = manifest["report_binding"]
            payload = (ROOT / binding["path"]).read_bytes()
            assert len(payload) == binding["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
        if "amendment_binding" in manifest:
            binding = manifest["amendment_binding"]
            payload = (ROOT / binding["path"]).read_bytes()
            assert len(payload) == binding["byte_length"]
            assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_completion_requires_amendment_and_no_acquisition() -> None:
    amendment = _load(AMENDMENT, "completion.json")
    preflight = _load(PREFLIGHT, "completion.json")
    assert amendment["completion_decision"] == "EXECUTION_PLAN_AMENDMENT_REQUIRED"
    assert preflight["completion_decision"] == amendment["completion_decision"]
    assert amendment["owner_amendment_approval_received"] is False
    assert preflight["network_requests"] == 0 and preflight["payloads_downloaded"] == 0
