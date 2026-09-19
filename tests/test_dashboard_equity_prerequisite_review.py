import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/project_status/DASHBOARD_EQUITY_PREREQUISITE_REVIEW_V1.json"
DECISION = ROOT / "docs/project_status/DASHBOARD_EQUITY_DISPLAY_ELIGIBILITY_V1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_owner_authorization_is_recorded_without_promotion():
    review = load(REVIEW)
    auth = review["owner_authorization"]
    assert auth["account_permission_confirmation_recorded"] is True
    assert auth["private_local_cash_equity_display"] is True
    assert auth["transient_in_memory_processing"] is True
    assert auth["market_data_requests_authorized"] is False
    assert auth["ui_wiring_authorized"] is False
    assert auth["research_authorized"] is False
    assert auth["trading_authorized"] is False
    assert auth["classification"] == "OWNER_PREREQUISITE_DECLARATION_NOT_PUBLISHER_EVIDENCE"


def test_only_fixed_official_documentation_sources_are_recorded():
    sources = load(REVIEW)["sources"]
    assert len(sources) == 5
    assert {source["url"] for source in sources} == {
        "https://kite.trade/docs/connect/v3/market-quotes/",
        "https://kite.trade/docs/connect/v3/websocket/",
        "https://kite.trade/terms/",
        "https://kite.trade/docs/connect/v3/exceptions/",
        "https://www.nseindia.com/resources/exchange-communication-holidays",
    }
    assert all(source["document_hash"] is None and source["copy_retained"] is False
               for source in sources)


def test_questions_separate_authority_policy_and_unresolved_limits():
    rows = load(REVIEW)["question_matrix"]
    assert len(rows) == 5
    assert all(set(row) == {"question", "result", "authoritative_statement",
                            "project_policy", "unresolved"} for row in rows)
    by_question = {row["question"]: row for row in rows}
    assert by_question["What does the selected REST quote price represent?"]["result"] == "ANSWERED_CURRENT_LTP_ONLY"
    assert by_question["What currency and unit apply to NSE cash-equity REST last_price?"]["result"] == "PARTIALLY_ANSWERED_REST_CURRENCY_LABEL_ABSENT"
    assert by_question["How can trading and non-trading sessions be classified?"]["result"] == "AUTHORITATIVE_SOURCE_IDENTIFIED_IMPLEMENTATION_ABSENT"


def test_proposed_policies_are_not_implemented_or_activation_authority():
    review = load(REVIEW)
    assert review["proposed_session_policy"]["status"] == "PROPOSED_NOT_IMPLEMENTED"
    assert review["proposed_compliance_record_policy"]["status"] == "PROPOSED_NOT_IMPLEMENTED_NOT_LEGAL_CONCLUSION"
    assert review["current_gate_updates"]["dashboard_wiring"] == "NOT_AUTHORIZED"
    assert review["current_gate_updates"]["operational_validation"] == "NOT_IMPLEMENTED_NOT_EXECUTED"
    assert review["network_activity"] == {
        "official_documentation_pages_reviewed": True,
        "authenticated_requests": 0,
        "market_data_requests": 0,
        "quote_payloads_retained": 0,
        "document_copies_retained": 0,
    }


def test_overall_display_decision_remains_blocked_with_unresolved_gates():
    decision = load(DECISION)
    gates = {gate["gate_id"]: gate for gate in decision["gates"]}
    assert decision["decision"] == "NOT_ELIGIBLE_FOR_DASHBOARD_WIRING"
    assert gates["OWNER_ACCOUNT_ENTITLEMENT_AND_PERMISSION"]["blocking"] is False
    assert gates["ADJUSTMENT_BASIS"]["blocking"] is False
    assert gates["CURRENCY_UNITS"]["blocking"] is True
    assert gates["EXCHANGE_SESSION_POLICY"]["blocking"] is True
    assert gates["CACHE_RETENTION_AND_COMPLIANCE_RECORDS"]["blocking"] is True
    assert gates["BOUNDED_OPERATIONAL_VALIDATION"]["blocking"] is True
    assert any(gate["blocking"] for gate in gates.values())


def test_review_is_sanitized_and_no_ui_or_provider_imports_it():
    payload = REVIEW.read_text(encoding="utf-8").lower()
    for forbidden in ("c:\\users", "bearer ", "token ", "nse:", "bse:"):
        assert forbidden not in payload
    prohibited = set(load(REVIEW)["proposed_compliance_record_policy"]["prohibited_fields"])
    assert {"credentials", "authorization_headers", "cookies", "account_identifiers",
            "instrument_identifiers", "prices", "response_bodies", "sensitive_headers",
            "private_paths"} == prohibited
    application_paths = [ROOT/"app.py", *(ROOT/"views").glob("*.py"),
                         *(ROOT/"src/market_intel/foundation").glob("kite*.py")]
    assert all("dashboard_equity_prerequisite_review" not in path.read_text(encoding="utf-8")
               for path in application_paths)
