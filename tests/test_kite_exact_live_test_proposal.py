"""Preparation artifacts are constraints, never executable authorization."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SCOPE=ROOT/"docs/project_status/KITE_EXACT_LIVE_TEST_SCOPE_V1.json"
REPORT=ROOT/"docs/project_status/KITE_EXACT_LIVE_TEST_PROPOSAL_V1.md"


def scope():
    return json.loads(SCOPE.read_text(encoding="utf-8"))


def test_preparation_does_not_authorize_execution_or_wiring():
    data=scope()
    assert data["preparation_authorized"] is True
    assert data["status"]=="PROPOSED_NOT_EXECUTION_AUTHORIZED"
    for field in ("implementation_authorized","execution_authorized","dashboard_wiring_authorized"):
        assert data[field] is False
    assert data["targets"]["binding_hash"] is None
    assert "PENDING" in data["targets"]["binding_status"]
    assert "do not yet exist" in REPORT.read_text(encoding="utf-8")


def test_bounded_exact_cash_targets_and_transport():
    data=scope()
    targets=data["targets"]
    assert (targets["count"],targets["exchange"],targets["instrument_class"])==(50,"NSE","EQ")
    assert targets["batch_sizes"]==[25,25]
    transport=data["transport"]
    assert transport["url"]=="https://api.kite.trade/quote"
    assert transport["method"]=="GET"
    assert transport["transactions_max"]==2
    assert transport["redirect_hops_max"]==transport["retries_max"]==0
    assert transport["decoded_bytes_per_response_max"]==65536
    assert transport["decoded_bytes_total_max"]==131072
    assert transport["request_connect_read_timeout_seconds"]==20
    assert transport["total_acquisition_deadline_seconds"]==60
    assert transport["owner_session_deadline_seconds"]==600
    assert not any(transport[field] for field in ("cache_reads","stale_fallback","background_polling"))


def test_quality_and_missing_prerequisites_never_waived():
    data=scope()
    rules=data["readiness_rules"]
    assert [rules[field] for field in ("max_quote_age_seconds","max_retrieval_age_seconds",
                                      "max_inventory_age_seconds")]==[30,15,86400]
    assert rules["preserve_unrounded_source"] and rules["quote_and_trade_clocks_separate"]
    assert rules["display_decimal_places"]==2 and rules["display_rounding"]=="ROUND_HALF_UP"
    assert rules["missing_or_stale_display_price"] is None and not rules["price_repair"]
    assert rules["unknown_session_blocks_current_market_display"]
    assert rules["unverified_currency_adjustment_or_permission_blocks_display"]
    assert "UNVERIFIED" in data["prerequisites"].values()
    assert data["original_NSE_FNO_route"]=="MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"


def test_privacy_retention_and_research_separation():
    data=scope()
    assert data["retention"]["parsed_results_max_seconds"]==60
    assert data["retention"]["NSE_package_deadline_unchanged"]=="2026-12-31"
    assert not data["retention"]["public_display"] and not data["retention"]["shared_cache"]
    assert "network_during_preparation" in data["prohibitions"]
    assert {"research","Dashboard_wiring","deletion","fingerprint_refresh"} <= set(data["prohibitions"])
    for path in (SCOPE,REPORT):
        text=path.read_text(encoding="utf-8")
        assert not re.search(r"C:\\Users|Bearer |Cookie:|access_token|api_secret|NSE:[A-Z]",text)
