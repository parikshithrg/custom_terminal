import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/project_status/KITE_EXACT_PREFLIGHT_UI_V1.json"
VIEW = ROOT / "views/_nifty50_manual_test.py"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_preflight_ui_does_not_authorize_or_implement_live_execution():
    artifact = load()
    assert artifact["state"] == "LOCAL_PREFLIGHT_AND_CONFIRMATION_IMPLEMENTED"
    assert artifact["live_execution_control"] is False
    assert artifact["provider_request_performed_by_preflight"] is False
    assert artifact["persistent_output"] is False
    assert artifact["dashboard_wiring_authorized"] is False
    assert artifact["currency_state"] == "NOT_VERIFIED"


def test_display_contract_is_sanitized_and_exactly_bounded():
    artifact = load()
    binding = artifact["binding"]
    assert binding["target_count"] == 50
    assert binding["batch_sizes"] == [25, 25]
    assert binding["exchange"] == "NSE"
    assert binding["instrument_class"] == "EQ"
    assert binding["maximum_lifetime_seconds"] == 600
    assert artifact["private_fields_displayed"] is False
    assert set(artifact["displayed_fields"]) == {
        "target_count", "batch_sizes", "exchange", "instrument_class",
        "binding_sha256", "confirmation_expiry",
    }


def test_view_contains_preflight_and_confirmation_but_no_execution_call():
    source = VIEW.read_text(encoding="utf-8")
    assert "Prepare exact 50-equity binding · no request" in source
    assert "Confirm exact binding · still no request" in source
    assert "execute_two_batch_test" not in source
    assert 'st.session_state["kite_exact_approval"]' in source
    assert 'st.session_state["kite_exact_binding"]' in source


def test_artifact_contains_no_secrets_private_paths_or_target_inventory():
    payload = ARTIFACT.read_text(encoding="utf-8").lower()
    for forbidden in ("c:\\users", "api_secret", "access_token", "authorization:",
                      "instrument_token", "trading_symbol", "cookie:", "nse:"):
        assert forbidden not in payload
