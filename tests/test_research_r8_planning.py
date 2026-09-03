from __future__ import annotations

import json
from pathlib import Path

from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
R8 = ROOT / "docs" / "research_r8"


def _load(name: str) -> dict:
    return json.loads((R8 / name).read_text(encoding="utf-8"))


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def test_version2_remains_exact_external_reference_and_unmerged():
    inventory = _load("component_inventory_v1.json")
    reference = inventory["reference_repository"]
    assert reference == {
        "name": "version2.0",
        "url": "https://github.com/parikshithrg/version2.0.git",
        "branch": "master",
        "reviewed_commit": "f9a6eaec2cab1dd9e85d284e48b9863cae0b1298",
        "remote_commit_rechecked_at": "2026-09-02T06:34:44.3686602Z",
        "remote_commit_changed": False,
        "relationship": "EXTERNAL_UNTRUSTED_REFERENCE_ONLY",
    }
    assert not (ROOT / "version2.0").exists()
    assert not (ROOT / ".gitmodules").exists()


def test_component_plans_are_non_executable_and_cannot_run_reference_code():
    inventory = _load("component_inventory_v1.json")
    assert inventory["classification"] == "PLANNING_ONLY_NONEXECUTABLE"
    assert "EXECUTE_VERSION2_CODE" in inventory["prohibited_actions"]
    assert "BACKTEST" in inventory["prohibited_actions"]
    assert "BROKER_ACTION" in inventory["prohibited_actions"]
    assert all(component.get("execution_authorized") is False
               for component in inventory["components"][:]
               if "execution_authorized" in component)
    assert not any(key in {"code_entry_point", "command", "callable", "script_path"}
                   for key, _ in _walk(inventory))
    assert not any(path.suffix == ".py" for path in R8.rglob("*"))


def test_sentiment_and_stock_score_plans_define_no_formula_or_weights():
    inventory = _load("component_inventory_v1.json")
    forbidden_keys = {"weight", "weights", "threshold", "thresholds", "formula"}
    assert not any(key.lower() in forbidden_keys for key, _ in _walk(inventory))
    by_id = {item["component_id"]: item for item in inventory["components"]}
    sentiment = by_id["market_sentiment_component_v0_plan"]
    stock = by_id["stock_score_component_v0_plan"]
    assert sentiment["initial_classification"] == "EXPLORATORY_NONACTIONABLE"
    assert sentiment["score_computation_authorized"] is False
    assert sentiment["recommendations_authorized"] is False
    assert stock["initial_classification"] == "EXPLORATORY_NONACTIONABLE"
    assert stock["ranking_authorized"] is False
    assert stock["score_computation_authorized"] is False
    assert stock["recommendations_authorized"] is False


def test_source_matrix_is_unqualified_and_cannot_authorize_empirical_use():
    matrix = _load("source_capability_matrix_v1.json")
    assert matrix["classification"] == "PLANNING_ONLY_UNQUALIFIED_INPUT_INVENTORY"
    assert matrix["empirical_use_authorized"] is False
    assert len(matrix["inputs"]) >= 9
    required = {
        "source", "free_status", "official_status", "data_owner", "access_method",
        "retention_status", "historical_availability", "publication_timestamp",
        "revision_behavior", "point_in_time_suitability", "missingness",
        "current_trust_state",
    }
    assert all(required <= set(item) for item in matrix["inputs"])


def test_fno_audit_contract_is_read_only_bounded_and_not_executed():
    contract = _load("local_fno_audit_contract_v1.json")
    assert contract["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert contract["database_locator"]["resolved_path_must_not_be_committed"] is True
    assert contract["connection_policy"]["sqlite_uri_mode"] == "ro"
    assert contract["connection_policy"]["pragma_query_only"] is True
    assert contract["connection_policy"]["query_timeout_seconds"] == 30
    assert contract["connection_policy"]["progress_handler_required_for_scans"] is True
    prohibited = set(contract["prohibited_sql_or_operations"])
    assert {"CREATE", "DROP", "ALTER", "INSERT", "UPDATE", "DELETE", "REPLACE",
            "VACUUM", "REINDEX", "ANALYZE", "ATTACH", "LOAD_EXTENSION",
            "FULL_TABLE_EXPORT"} <= prohibited
    assert contract["audit_execution_authorized"] is False
    assert contract["market_research_authorized"] is False
    assert contract["backtesting_authorized"] is False


def test_owner_record_approves_planning_only_and_keeps_empirical_gates():
    decision = _load("owner_decision_record_v1.json")
    assert decision["approved_scope"] == "BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING"
    assert decision["execution_authorized"] is False
    assert decision["separate_preregistration_required"] is True
    assert decision["separate_exact_run_approval_required"] is True
    assert {item["question"] for item in decision["deferred_decisions"]} == {13, 14}
    assert {"BACKTESTING", "SCORE_CALCULATION", "BROKER_ACTIONS", "TRADING",
            "FNO_AUDIT_EXECUTION"} <= set(decision["prohibited_actions"])


def test_reviewed_pdf_remains_exact_but_is_stale_after_r9b():
    record = json.loads(
        (ROOT / "docs" / "project_status" / "pre_research_review_record_v1.json")
        .read_text(encoding="utf-8")
    )
    assert record["pdf_sha256"] == (
        "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c"
    )
    assert sha256_file(ROOT / record["pdf_path"]) == record["pdf_sha256"]
    assert record["review_status"] == "REPORT_STALE"
    assert record["covered_future_scope"] == ["BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING"]
    assert record["research_execution_status"] == (
        "REVIEWED_PDF_STALE_AFTER_AUDITOR_IMPLEMENTATION"
    )
    policy = json.loads(
        (ROOT / "specs" / "pre_research_review_policy_v1.json").read_text(encoding="utf-8")
    )
    state = compute_research_state_fingerprint(ROOT, policy)
    assert state["sha256"] != record["research_state_fingerprint"]
    assert record["staleness"]["current_research_state_fingerprint"] == (
        "9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31"
    )
    assert state["sha256"] != record["staleness"]["current_research_state_fingerprint"]
    paths = {item["path"] for item in state["inventory"]}
    assert not any(path.startswith("docs/research_r8/") for path in paths)
    assert not any("RESEARCH_R8" in path for path in paths)


def test_r8_report_ends_with_review_decision_and_authorizes_nothing():
    report = (ROOT / "reports" / "RESEARCH_R8_PLAN.md").read_text(encoding="utf-8")
    assert report.rstrip().endswith("R8_PLANNING_PACKAGE_READY_FOR_OWNER_REVIEW")
    assert "No connection or query was made" in report
    assert "does not authorize" in report
