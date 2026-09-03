from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

from research_contracts.legacy_ledger import canonical_json_bytes, sha256_file
from research_contracts.pre_research_review import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "quarantined_proposals" / "local_fno_audit_stage_1_3"


def _load(name: str) -> dict:
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def _objects() -> list[dict]:
    return [_load(path.name) for path in sorted(PACKAGE.glob("*.json"))]


def test_proposal_inspection_never_connects_or_executes_sql(monkeypatch):
    calls = []

    def forbidden_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("R.9A proposal validation must not connect to SQLite")

    monkeypatch.setattr(sqlite3, "connect", forbidden_connect)
    assert len(_objects()) == 8
    assert calls == []
    assert not any(path.suffix == ".py" for path in PACKAGE.rglob("*"))
    assert (ROOT / "src" / "market_intel" / "foundation" / "local_fno_audit.py").is_file()


def test_every_proposal_object_is_explicitly_non_authorizing():
    for value in _objects():
        assert value["proposal_only"] is True
        assert value["audit_execution_authorized"] is False
        assert value["market_research_authorized"] is False
        assert value["backtesting_authorized"] is False
        assert value["trading_authorized"] is False


def test_resolved_personal_database_path_is_not_committed_in_package_or_reports():
    inspected = list(PACKAGE.glob("*")) + [
        ROOT / "reports" / "RESEARCH_R9A_REPORT.md",
        ROOT / "reports" / "FNO_STAGE_1_3_AUTHORIZATION_PROPOSAL.md",
        ROOT / "reports" / "FNO_AUDIT_SAFETY_REVIEW.md",
        ROOT / "reports" / "FNO_AUDIT_EXPECTED_OUTPUTS.md",
    ]
    drive_path = re.compile(r"[A-Za-z]:[\\/](?:Users|Documents|Data)[\\/]")
    assert all(not drive_path.search(path.read_text(encoding="utf-8")) for path in inspected)
    assert _load("audit_scope_v1.json")["database_locator"][
        "configuration_file_sha256"
    ] == "cb68999f6e0dd16796d017f1104cc630483ada44ed1959143b99c9e9d11d29a2"


def test_approval_template_is_distinct_exact_empty_and_unusable():
    approval = _load("approval_template_v1.json")
    assert approval["schema_version"] == "local_data_audit_stage_1_3_approval_v1"
    assert approval["required_approval_type"] == "LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1"
    assert approval["market_research_run_approval_substitution_permitted"] is False
    assert approval["approved_stages"] == []
    assert approval["usable"] is False
    assert approval["approval_state"] == "TEMPLATE_NOT_APPROVED_NOT_USABLE"
    for field in (
        "approval_id", "proposal_manifest_sha256", "audit_scope_sha256",
        "resource_envelope_sha256", "expected_outputs_sha256", "approved_at",
        "expires_at", "approved_by", "approval_statement", "consumed_at",
        "consumed_by_attempt_id",
    ):
        assert approval[field] is None


def test_scope_excludes_stages_4_to_6_network_brokers_and_empirical_work():
    scope = _load("audit_scope_v1.json")
    assert [stage["stage"] for stage in scope["requested_stages"]] == [1, 2, 3]
    assert scope["explicitly_excluded_stages"] == [4, 5, 6]
    prohibited = " ".join(scope["prohibited_operations"]).lower()
    for phrase in (
        "database writes", "full-table scan", "external network", "market outcomes",
        "returns", "signals", "ranks", "scores", "strategy", "recommendations",
        "broker actions", "trading",
    ):
        assert phrase in prohibited
    stage2 = scope["requested_stages"][1]
    assert stage2["quick_check_authorized"] is False
    assert stage2["full_integrity_check_authorized"] is False


def test_write_and_unsafe_sql_operations_are_forbidden():
    proposal = _load("implementation_proposal_v1.json")
    deny = {item.upper() for item in proposal["statement_denylist"]}
    assert {"ATTACH", "DETACH", "CREATE", "DROP", "ALTER", "INSERT", "UPDATE",
            "DELETE", "REPLACE", "VACUUM", "REINDEX", "ANALYZE",
            "LOAD_EXTENSION"} <= deny
    assert proposal["future_entry_point"]["implementation_status"] == "NOT_IMPLEMENTED"
    assert proposal["future_entry_point"]["default_mode"] == "PROPOSAL_DRY_RUN"
    assert proposal["future_entry_point"]["direct_cli_execution_permitted"] is False


def test_resource_envelope_states_enforced_and_declared_limits_truthfully():
    resource = _load("resource_envelope_v1.json")
    stage1 = resource["stage_1_identity"]
    assert stage1["chunk_size_bytes"] == 4 * 1024 * 1024
    assert stage1["chunk_count"] == 64
    assert stage1["expected_bytes_read_once"] == 64 * 4 * 1024 * 1024 + 100
    assert stage1["identity_checkpoint_count_maximum"] == 5
    assert resource["stage_2"]["maximum_attempted_statements"] == 50
    assert resource["stage_2"]["per_statement_timeout_seconds"] == 5
    assert resource["stage_2"]["quick_check_included"] is False
    assert resource["stage_3"]["maximum_files_inspected"] == 500
    truth = resource["enforcement_truth"]
    assert truth["total_wall_time"] == "DECLARED_NOT_OS_ENFORCED"
    assert truth["memory_limit"] == "DECLARED_NOT_PROCESS_ENFORCED"
    assert "PROGRESS_HANDLER" in truth["statement_cancellation"]
    assert "MODE_RO" in truth["write_prohibition"]


def test_database_change_protection_has_all_required_checkpoints_and_abort_fields():
    policy = _load("abort_and_identity_policy_v1.json")
    assert policy["identity_checkpoints"] == [
        "IMMEDIATELY_BEFORE_OPEN", "AFTER_STAGE_1", "AFTER_STAGE_2",
        "AFTER_STAGE_3", "IMMEDIATELY_BEFORE_EVIDENCE_FINALIZATION",
    ]
    aborts = " ".join(policy["abort_on_change"]).lower()
    for value in ("file size", "modification time", "header", "sampled chunk",
                  "sidecar", "source mutation", "path"):
        assert value in aborts
    assert "DO_NOT_REPAIR" in policy["on_abort"]


def test_expected_outputs_exclude_market_and_strategy_results():
    outputs = _load("expected_outputs_v1.json")
    assert len(outputs["permitted_outputs"]) == 9
    prohibited = " ".join(outputs["prohibited_output_categories"]).lower()
    for value in ("market observations", "features", "returns", "signals", "ranks",
                  "scores", "strategy", "recommendations", "full-table exports"):
        assert value in prohibited
    assert "historical_completeness_NOT_EVALUATED" in outputs[
        "required_capability_decisions"
    ]
    assert "research_eligibility_NOT_APPROVED" in outputs[
        "required_capability_decisions"
    ]


def test_proposal_manifest_binds_exact_package_bytes():
    manifest = _load("proposal_manifest_v1.json")
    rows = []
    for item in manifest["objects"]:
        path = PACKAGE / item["path"]
        assert path.stat().st_size == item["byte_size"]
        assert sha256_file(path) == item["sha256"]
        rows.append({"path": item["path"], "sha256": item["sha256"],
                     "byte_size": item["byte_size"]})
    assert hashlib.sha256(canonical_json_bytes(rows)).hexdigest() == manifest[
        "package_content_sha256"
    ]
    assert manifest["approval_template_is_usable"] is False
    assert manifest["registered_or_sealed"] is False
    assert manifest["execution_entry_point_exists"] is False


def test_reviewed_pdf_bytes_remain_exact_and_fingerprint_is_stale_after_r9b():
    record = json.loads(
        (ROOT / "docs" / "project_status" / "pre_research_review_record_v1.json")
        .read_text(encoding="utf-8")
    )
    assert sha256_file(ROOT / record["pdf_path"]) == (
        "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c"
    )
    policy = json.loads(
        (ROOT / "specs" / "pre_research_review_policy_v1.json").read_text(encoding="utf-8")
    )
    current = compute_research_state_fingerprint(ROOT, policy)
    assert current["sha256"] != record["research_state_fingerprint"]
    assert record["staleness"]["current_research_state_fingerprint"] == (
        "9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31"
    )
    assert current["sha256"] != record["staleness"]["current_research_state_fingerprint"]
    paths = {item["path"] for item in current["inventory"]}
    assert not any(path.startswith("docs/quarantined_proposals/") for path in paths)
    assert record["research_execution_status"] == (
        "REVIEWED_PDF_STALE_AFTER_AUDITOR_IMPLEMENTATION"
    )


def test_r9a_report_has_exact_terminal_decision():
    report = (ROOT / "reports" / "RESEARCH_R9A_REPORT.md").read_text(encoding="utf-8")
    assert report.rstrip().endswith("FNO_STAGE_1_3_PROPOSAL_READY_FOR_OWNER_APPROVAL")
    assert "No real database path was resolved" in report
    assert "No connection was made" in report
