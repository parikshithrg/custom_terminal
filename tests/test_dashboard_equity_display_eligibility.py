import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "docs/project_status/DASHBOARD_EQUITY_DISPLAY_ELIGIBILITY_V1.json"


def load():
    return json.loads(DECISION.read_text(encoding="utf-8"))


def test_decision_is_blocked_and_cannot_authorize_wiring():
    decision = load()
    assert decision["decision"] == "NOT_ELIGIBLE_FOR_DASHBOARD_WIRING"
    assert decision["completion_state"] == "DISPLAY_ELIGIBILITY_BLOCKED_PENDING_PREREQUISITES"
    assert decision["implementation_authorized"] is False
    assert decision["display_authorized"] is False
    assert decision["provider_requests_authorized"] is False
    assert decision["source_qualified"] is False
    assert decision["unchanged_boundaries"]["dashboard_values"] == "SYNTHETIC"
    assert decision["unchanged_boundaries"]["ui_change"] is False


def test_acceptance_matrix_is_complete_independent_and_fail_closed():
    decision = load()
    gates = decision["gates"]
    assert len(gates) == 12
    assert len({gate["gate_id"] for gate in gates}) == len(gates)
    assert any(gate["blocking"] is True for gate in gates)
    assert all(type(gate["blocking"]) is bool for gate in gates)
    assert all(gate["state"] and gate["required_to_pass"] and gate["evidence_class"] for gate in gates)
    policy = decision["acceptance_policy"]
    assert policy["rule"] == "EVERY_GATE_MUST_PASS_INDEPENDENTLY_BEFORE_SEPARATE_WIRING_APPROVAL"
    assert policy["threshold_revision_after_results"] is False
    assert policy["complete_coverage_overrides_other_gates"] is False
    assert policy["owner_approval_is_authoritative_source_evidence"] is False
    assert policy["synthetic_or_manual_results_can_promote_source"] is False


def test_consumer_fields_do_not_expand_to_change_history_or_trading():
    contract = load()["consumer_contract"]
    assert contract["universe"] == "at_most_25_explicitly_selected_current_NSE_or_BSE_EQ_targets"
    assert contract["change_percentage"] == "UNAVAILABLE_NO_APPROVED_PREVIOUS_CLOSE_SEMANTICS"
    assert contract["missing_value"] is None
    assert contract["fallback_or_repair"] is False
    assert contract["history_research_or_trading"] is False


def test_source_bindings_match_existing_evidence_byte_exact():
    decision = load()
    for binding in decision["source_bindings"]:
        path = ROOT / binding["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]


def test_artifacts_are_sanitized_and_do_not_change_application_paths():
    payload = DECISION.read_text(encoding="utf-8").lower()
    for forbidden in ("c:\\users", "api_secret", "access_token", "authorization_header",
                      "instrument_token", "trading_symbol"):
        assert forbidden not in payload
    assert all("dashboard_equity_display_eligibility" not in path.read_text(encoding="utf-8")
               for path in [ROOT/"app.py", *(ROOT/"views").glob("*.py")])
