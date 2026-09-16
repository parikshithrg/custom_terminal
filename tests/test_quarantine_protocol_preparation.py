"""Proposal governance only: no runtime quarantine implementation or row access."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/investigations/post_r10ni_policy/quarantine_protocol_v1"

def load(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))

def test_approval_missing_stops_at_preparation():
    p, c = load("protocol.json"), load("completion.json")
    assert p["status"] == "PROPOSED_PENDING_OWNER_APPROVAL_NOT_EXECUTED"
    for gate in ("experiment_implementation", "consumer_scope", "materiality_thresholds"):
        assert p["authorization"][gate] is False
    assert c["approved_protocol_available"] is False
    assert c["exclusion_results_viewed"] is False
    assert c["normalization_performed"] is False
    assert c["quarantine_created"] is False
    assert "SHA-256" in p["freeze_rule"]
    assert len(c["next_decisions"]) == 3

@pytest.mark.parametrize("gate", ["alternative_source_access", "network", "strategy_research", "waivers", "qualification", "production", "deletion"])
def test_prohibited_authority_not_inferred(gate):
    assert load("protocol.json")["authorization"][gate] is False

def test_scope_metrics_and_consumers_are_specific():
    p = load("protocol.json")
    assert p["exact_dates"] == ["2026-09-09", "2026-09-10", "2025-07-08"]
    assert [x["id"] for x in p["consumers"]] == ["OFFLINE_COVERAGE_AUDIT", "OFFLINE_CONTRACT_DATE_COMPLETENESS"]
    assert all(x["future_test_ids"] for x in p["consumers"])
    assert all(x["formula"] and x["denominators"] for x in p["metrics"])
    assert p["metrics"][0]["proposed_threshold_percent"] == "0"
    assert p["metrics"][1]["proposed_threshold_percentage_points"] == "0"
    assert p["metrics"][2]["proposed_threshold_count"] == 0
    assert "THRESHOLD_CHANGE_AFTER_RESULT_ACCESS" in p["stopping_conditions"]
    assert "NOT_EVALUATED" in p["metrics"][0]["denominators"]

def test_mapping_keeps_date_uncertainty_and_source_values():
    p = load("protocol.json")
    q = p["quarantine"]
    assert q["unit"] == "CONTRACT_DATE"
    assert q["mapping"]["CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS"] == "EXCLUDE_CONTRACT_DATE_FROM_ROW_FILTERED_VIEW"
    assert q["mapping"]["TRADE_STATE_ATTRIBUTION_UNAVAILABLE"] == "DATE_LEVEL_RESTRICTION_PERSISTS_DO_NOT_MAP_TO_THIRD_ROW"
    for code in ("ZERO_VOLUME_PRICE_STATE", "SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS"):
        assert q["mapping"][code] == "VISIBLE_NONBLOCKING_NO_AUTOMATIC_EXCLUSION"
    assert "immutable" in q["storage"].lower() or "append-once" in q["storage"]
    assert "No forward-fill" in p["missing_data"]
    assert "INTEGRITY_MISMATCH" in p["stopping_conditions"]
    assert "PRICE_DIGEST_CHANGE" in p["stopping_conditions"]

def test_corroboration_must_match_all_keys_and_semantics():
    c = load("protocol.json")["corroboration"]
    assert c["status"].startswith("NOT_EVALUATED")
    assert c["matching_keys"] == ["exchange", "instrument_class", "underlying", "expiry", "option_type", "strike", "trading_date", "session", "units", "field_semantics"]
    assert "fails closed" in c["rule"]
    assert "NOT_ESTABLISHED" in c["independence"]

def test_no_new_results_or_changed_acceptance():
    p, c = load("protocol.json"), load("completion.json")
    assert c["diagnostic_reconciliation"]["experimental_counts"] is None
    assert c["diagnostic_reconciliation"]["historical_reference_only"] == {"CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS": 2, "TRADE_STATE_ATTRIBUTION_UNAVAILABLE": 1}
    assert all(x["baseline"] == x["experimental"] == "NOT_EVALUATED" and x["differences"] is None for x in c["consumer_results"])
    assert p["source_result"] == c["source_result"] == "MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED"
    assert p["every_approved_date_must_pass"] and not p["partial_source_qualification"]
    assert not c["source_qualified"] and not c["production_exposed"]
    assert c["network_transactions"] == 0
    assert not c["research"] and not c["fingerprint_refreshed"] and not c["deletion"]
    assert p["retention_deadline"] == "2026-12-31" and not p["retention_amended"]

def test_root_manifest_complete_and_historical_files_intact():
    m = load("root_manifest.json")
    expected = {
        "docs/investigations/post_r10ni_policy/quarantine_protocol_v1/protocol.json",
        "docs/investigations/post_r10ni_policy/quarantine_protocol_v1/completion.json",
        "reports/NSE_FNO_QUARANTINE_PROTOCOL_PREPARATION.md",
        "tests/test_quarantine_protocol_preparation.py",
    }
    assert expected.issubset({e["path"] for e in m["files"]})
    for e in m["files"]:
        assert hashlib.sha256((ROOT / e["path"]).read_bytes()).hexdigest() == e["sha256"]
    for name in ("protocol.json", "completion.json"):
        text = (PACKAGE / name).read_text()
        for forbidden in ("C:", "Cookie:", "Authorization:", "access_token", "password"):
            assert forbidden not in text
