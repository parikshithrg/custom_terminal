import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/project_status/KITE_REST_CURRENCY_BINDING_REVIEW_V1.json"
REPORT = ROOT / "docs/project_status/KITE_REST_CURRENCY_BINDING_REVIEW_V1.md"


def load():
    return json.loads(REVIEW.read_text(encoding="utf-8"))


def test_official_review_remains_fail_closed_without_explicit_rest_binding():
    review = load()
    assert review["result"] == "UNRESOLVED_EXPLICIT_REST_CURRENCY_UNIT_BINDING_ABSENT"
    assert review["currency_state"] == "NOT_VERIFIED"
    assert review["cross_surface_inference_is_authoritative_binding"] is False
    assert review["sample_numeric_agreement_is_authoritative_binding"] is False
    assert review["conversion_authorized"] is False
    assert review["currency_label_authorized"] is False
    assert review["dashboard_wiring_authorized"] is False
    assert review["provider_requests_authorized"] is False


def test_each_evidence_item_states_its_limit_and_no_capability_is_invented():
    review = load()
    assert len(review["evidence"]) == 4
    assert all(item["publisher"] in {"KITE_CONNECT", "NSE"}
               for item in review["evidence"])
    assert all(item["url"].startswith("https://") for item in review["evidence"])
    assert all(item["establishes"] and item["does_not_establish"]
               for item in review["evidence"])
    rest = next(item for item in review["evidence"]
                if item["surface"] == "REST_MARKET_QUOTES")
    assert "REST_FIELD_CURRENCY" in rest["does_not_establish"]
    assert "REST_FIELD_MAJOR_OR_MINOR_UNIT" in rest["does_not_establish"]


def test_review_used_no_authenticated_or_retained_input():
    review = load()
    assert review["scope"] == "PUBLIC_OFFICIAL_DOCUMENTATION_ONLY"
    assert review["provider_request_performed"] is False
    assert review["authenticated_access_performed"] is False
    assert review["review_copy_retained"] is False


def test_artifacts_are_sanitized_and_preserve_decoder_boundary():
    payload = (REVIEW.read_text(encoding="utf-8") +
               REPORT.read_text(encoding="utf-8")).lower()
    for forbidden in ("c:\\users", "api_secret", "access_token", "authorization:",
                      "instrument_token", "trading_symbol", "cookie:"):
        assert forbidden not in payload
    decoder = (ROOT/"src/market_intel/foundation/kite_equity_quote_v1.py").read_text(
        encoding="utf-8")
    assert 'currency_state: str = "NOT_VERIFIED"' in decoder
