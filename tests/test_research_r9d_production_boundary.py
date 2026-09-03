from __future__ import annotations

import ast
import dataclasses
import json
import multiprocessing
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from market_intel.foundation import fno_production_boundary as boundary
from market_intel.foundation import local_fno_audit as audit
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)


def _database(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "synthetic_source"
    source.mkdir()
    (source / ".synthetic_audit_fixture").write_text("synthetic only", encoding="utf-8")
    database = source / "fixture.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        "CREATE TABLE instruments(id INTEGER PRIMARY KEY, symbol TEXT UNIQUE);"
        "CREATE TABLE market_rows(id INTEGER PRIMARY KEY, instrument_id INTEGER,"
        " trade_date TEXT, close REAL, secret_note TEXT,"
        " FOREIGN KEY(instrument_id) REFERENCES instruments(id));"
        "CREATE INDEX idx_market_date ON market_rows(trade_date);"
        "INSERT INTO instruments VALUES(1,'NEVER_EXPORT');"
        "INSERT INTO market_rows VALUES(1,1,'2099-01-01',123.45,'NEVER_READ');"
    )
    connection.close()
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    (provenance / "manifest.json").write_text(
        json.dumps({"source": "synthetic", "retention": "test only"}), encoding="utf-8"
    )
    return source, database, provenance


def _approval(database: Path, source: Path, approval_id: str = "r9d-approval") -> audit.AuditApproval:
    identity = audit.capture_file_identity(database, synthetic_root=source)
    value = audit.AuditApproval(
        schema_version="local_data_audit_stage_1_3_approval_v1",
        approval_type=audit.AUDIT_APPROVAL_TYPE,
        approval_id=approval_id,
        proposal=audit.ProposalIdentity(),
        approved_locator_key="synthetic.fixture.path",
        approved_locator_sha256=audit.synthetic_locator_hash(),
        approved_database_identity_root=identity.sampled_root_sha256,
        approved_stages=(1, 2, 3),
        approved_resources=audit.approved_resource_contract(),
        approved_outputs=audit.PERMITTED_OUTPUTS,
        fixture_classification=audit.SYNTHETIC_FIXTURE_CLASS,
        issued_at=(NOW - timedelta(minutes=2)).isoformat(),
        expires_at=(NOW + timedelta(minutes=20)).isoformat(),
        approved_by="synthetic-owner",
        approval_statement="R.9D temporary synthetic test approval only.",
    )
    return audit.seal_audit_approval(value)


def _registry(tmp_path: Path, source: Path) -> boundary.DurableAuditRegistry:
    return boundary.DurableAuditRegistry.create_synthetic(
        tmp_path / "governance", forbidden_roots=[source]
    )


def _race_worker(database_path: str, approval: audit.AuditApproval,
                 attempt_id: str, queue: multiprocessing.Queue) -> None:
    try:
        boundary.DurableAuditRegistry(database_path).consume(approval, attempt_id)
        queue.put((attempt_id, "CONSUMED"))
    except Exception as exc:
        queue.put((attempt_id, type(exc).__name__))


def _consume_then_crash(database_path: str, approval: audit.AuditApproval) -> None:
    boundary.DurableAuditRegistry(database_path).consume(approval, "crash-after-consume")
    os._exit(17)


def _crash_before_consume() -> None:
    os._exit(19)


def test_durable_registration_is_immutable_exact_and_hash_chained(tmp_path):
    source, database, _ = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source)
    registration = registry.register(approval)
    assert registration.approval_payload_sha256 == approval.approval_payload_sha256
    result = registry.verify()
    assert result["approval_count"] == 1
    assert result["event_count"] == 1
    assert result["tamper_check"] == "PASS"
    connection = sqlite3.connect(registry.database_path)
    with pytest.raises(sqlite3.DatabaseError, match="immutable approvals"):
        connection.execute("UPDATE approvals SET approval_json='changed'")
    connection.close()


def test_duplicate_expired_altered_and_market_research_approvals_fail(tmp_path):
    source, database, _ = _database(tmp_path)
    registry = _registry(tmp_path, source)
    approval = _approval(database, source)
    registry.register(approval)
    with pytest.raises(boundary.DurableRegistryError, match="duplicate"):
        registry.register(approval)
    altered = dataclasses.replace(approval, approval_statement="changed")
    with pytest.raises(audit.LocalFnoAuditError, match="payload hash mismatch"):
        registry.consume(altered, "altered")
    expired = audit.seal_audit_approval(dataclasses.replace(
        approval, approval_id="expired", issued_at=(NOW - timedelta(hours=2)).isoformat(),
        expires_at=(NOW - timedelta(hours=1)).isoformat()))
    with pytest.raises(audit.LocalFnoAuditError, match="expired"):
        registry.register(expired)
    with pytest.raises(audit.LocalFnoAuditError, match="market-research"):
        registry.register({"approval_id": "research"})  # type: ignore[arg-type]


def test_private_paths_and_secret_like_values_are_rejected_from_registry(tmp_path):
    source, database, _ = _database(tmp_path)
    registry = _registry(tmp_path, source)
    approval = _approval(database, source)
    for statement, match in (
        ("private target C:\\Users\\person\\database.sqlite", "private absolute path"),
        ("api_secret=must-not-persist", "secret-like"),
    ):
        unsafe = audit.seal_audit_approval(dataclasses.replace(
            approval, approval_id=f"unsafe-{len(statement)}", approval_statement=statement))
        with pytest.raises(boundary.DurableRegistryError, match=match):
            registry.register(unsafe)


def test_cross_process_consumption_has_exactly_one_winner(tmp_path):
    source, database, _ = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source)
    registry.register(approval)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(
        target=_race_worker,
        args=(str(registry.database_path), approval, f"contender-{index}", queue),
    ) for index in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(20)
        assert process.exitcode == 0
    results = [queue.get(timeout=5) for _ in processes]
    assert [state for _, state in results].count("CONSUMED") == 1
    winner = next(attempt for attempt, state in results if state == "CONSUMED")
    assert registry.consumed_by(approval.approval_id) == winner
    assert len(registry.incomplete_attempts()) == 1
    assert registry.verify()["event_count"] == 2


def test_crash_before_consumption_leaves_unused_and_after_leaves_consumed(tmp_path):
    source, database, _ = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source)
    registry.register(approval)
    context = multiprocessing.get_context("spawn")
    before = context.Process(target=_crash_before_consume)
    before.start(); before.join(20)
    assert before.exitcode == 19
    assert registry.consumed_by(approval.approval_id) is None
    after = context.Process(
        target=_consume_then_crash, args=(str(registry.database_path), approval)
    )
    after.start(); after.join(20)
    assert after.exitcode == 17
    assert registry.consumed_by(approval.approval_id) == "crash-after-consume"
    assert registry.incomplete_attempts()[0]["state"] == "CONSUMED_BEFORE_CONNECTION"


def test_reuse_after_restart_and_duplicate_attempt_are_rejected(tmp_path):
    source, database, _ = _database(tmp_path)
    first = _approval(database, source, "first")
    second = _approval(database, source, "second")
    registry = _registry(tmp_path, source)
    registry.register(first); registry.register(second)
    registry.consume(first, "fixed-attempt")
    reopened = boundary.DurableAuditRegistry(registry.database_path)
    with pytest.raises(boundary.DurableRegistryError, match="already been consumed"):
        reopened.consume(first, "new-attempt")
    with pytest.raises(boundary.DurableRegistryError, match="approval or attempt"):
        reopened.consume(second, "fixed-attempt")


def test_terminal_events_and_incomplete_attempts_are_auditable(tmp_path):
    source, database, _ = _database(tmp_path)
    registry = _registry(tmp_path, source)
    for index, state in enumerate(("COMPLETED", "ABORTED", "FAILED"), start=1):
        approval = _approval(database, source, f"terminal-{index}")
        registry.register(approval)
        registry.consume(approval, f"attempt-{index}")
        registry.record_terminal(approval.approval_id, f"attempt-{index}", state,
                                 {"message": "sanitized"})
    assert registry.incomplete_attempts() == ()
    assert registry.verify()["event_count"] == 9
    with pytest.raises(boundary.DurableRegistryError, match="already has"):
        registry.record_terminal("terminal-1", "attempt-1", "FAILED")


def test_terminal_event_details_redact_secrets_and_private_paths(tmp_path):
    source, database, _ = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source)
    registry.register(approval); registry.consume(approval, "redacted-attempt")
    registry.record_terminal(
        approval.approval_id, "redacted-attempt", "FAILED",
        {"message": "api_secret=hidden C:\\Users\\person\\private.sqlite"},
    )
    connection = sqlite3.connect(registry.database_path)
    detail = connection.execute(
        "SELECT detail_json FROM events WHERE event_type='AUDIT_FAILED'"
    ).fetchone()[0]
    connection.close()
    assert "hidden" not in detail and "C:\\Users" not in detail
    assert "<redacted>" in detail and "<redacted-path>" in detail


def test_ledger_and_projection_corruption_are_detected(tmp_path):
    source, database, _ = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source)
    registry.register(approval); registry.consume(approval, "attempt")
    connection = sqlite3.connect(registry.database_path)
    connection.execute("DROP TRIGGER events_no_update")
    connection.execute("UPDATE events SET detail_json='{}' WHERE sequence=1")
    connection.commit(); connection.close()
    with pytest.raises(boundary.DurableRegistryError, match="hash-chain"):
        registry.verify()


def test_consumption_occurs_before_first_target_connection(tmp_path, monkeypatch):
    source, database, provenance = _database(tmp_path)
    approval = _approval(database, source)
    registry = _registry(tmp_path, source); registry.register(approval)
    original = audit.ReadOnlyCatalogConnection

    def guarded_connection(*args, **kwargs):
        assert registry.consumed_by(approval.approval_id) == "ordered-attempt"
        return original(*args, **kwargs)

    monkeypatch.setattr(audit, "ReadOnlyCatalogConnection", guarded_connection)
    result = audit.execute_approved_stage_1_3_audit(
        target_path=database, synthetic_root=source, approval=approval,
        registry=registry, output_root=tmp_path / "output",
        provenance_roots=[provenance], attempt_id="ordered-attempt",
        evaluated_at=NOW, mode="GOVERNED_SYNTHETIC_EXECUTION",
    )
    assert result.status == "COMPLETED"
    assert registry.incomplete_attempts() == ()
    assert registry.verify()["event_count"] == 3
    catalog = json.loads((tmp_path / "output" / "ordered-attempt" /
                          "schema_catalog_inventory.json").read_text())
    assert catalog["market_row_reads"] == 0
    emitted = "".join(path.read_text(errors="ignore") for path in
                      (tmp_path / "output" / "ordered-attempt").iterdir())
    assert "NEVER_READ" not in emitted and "123.45" not in emitted


def test_production_locator_is_typed_disabled_and_never_reads_configuration(monkeypatch):
    calls: list[str] = []

    def forbidden_reader(*args, **kwargs):
        calls.append("read")
        pytest.fail("configuration value was read")

    monkeypatch.setattr(Path, "resolve", lambda *args, **kwargs: pytest.fail("path resolved"))
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: pytest.fail("connected"))
    contract = boundary.ProductionLocatorContract()
    assert contract.state == "PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING"
    assert contract.permitted_stages == (1, 2, 3)
    with pytest.raises(boundary.ProductionBoundaryError, match="DISABLED"):
        boundary.execute_production_stage_1_3_audit(
            locator=contract, configuration_reader=forbidden_reader
        )
    assert calls == []


def test_every_production_interlock_is_fail_closed_and_r9d_is_deliberately_impossible():
    result = boundary.evaluate_production_interlocks(boundary.ProductionInterlockEvidence())
    required = {
        "reviewed_pdf_current", "reviewed_pdf_covers_exact_binding",
        "research_state_fingerprint_matches", "activation_object_exact",
        "durable_approval_registered", "file_identity_matches", "stages_exact",
        "resource_envelope_matches", "expected_outputs_match",
        "approval_unused_and_unexpired", "source_commit_clean_and_reviewed",
        "protected_evidence_unchanged", boundary.DELIBERATE_INTERLOCK,
    }
    assert required <= set(result["failures"])
    assert result["permitted"] is False
    almost = boundary.ProductionInterlockEvidence(**{
        field.name: True for field in dataclasses.fields(boundary.ProductionInterlockEvidence)
    })
    assert boundary.evaluate_production_interlocks(almost)["permitted"] is False


def test_runtime_network_broker_and_dependency_injection_are_rejected():
    source = Path(boundary.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, ast.Import) for alias in node.names}
    imports |= {(node.module or "").split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 0}
    assert not imports & {"requests", "urllib", "httpx", "kiteconnect", "streamlit",
                          "yfinance", "market_intel.research"}
    for label in ("kite", "broker", "recommendation", "portfolio", "http_client"):
        with pytest.raises(boundary.ProductionBoundaryError, match="injection"):
            boundary.execute_production_stage_1_3_audit(
                dependency_injections={label: object()}
            )


def test_evidence_store_is_atomic_bounded_separate_and_immutable(tmp_path):
    source, _, _ = _database(tmp_path)
    store = boundary.DurableAuditEvidenceStore.create_synthetic(
        tmp_path / "evidence", forbidden_roots=[source], maximum_bytes=4096
    )
    final = store.finalize(
        attempt_id="evidence-attempt", approval_id="approval",
        event_head_sha256="a" * 64,
        artifacts={"completion_report.md": b"synthetic completion"},
        terminal_state="COMPLETED",
    )
    manifest = json.loads((final / "root_audit_manifest.json").read_text())
    assert manifest["restore_verification_state"] == boundary.RESTORE_STATE
    assert manifest["backup_verified"] is False
    assert manifest["canonical"] is False and manifest["promotion_eligible"] is False
    assert manifest["artifact_hashes"]["completion_report.md"] == sha256_file(
        final / "completion_report.md"
    )
    assert not (store.root / ".tmp-evidence-attempt").exists()
    with pytest.raises(boundary.ProductionBoundaryError, match="immutable"):
        store.finalize(
            attempt_id="evidence-attempt", approval_id="approval",
            event_head_sha256="a" * 64,
            artifacts={"completion_report.md": b"replacement"}, terminal_state="FAILED")


def test_evidence_store_rejects_colocation_unexpected_output_and_overflow(tmp_path):
    source, _, _ = _database(tmp_path)
    with pytest.raises(boundary.ProductionBoundaryError, match="separate"):
        boundary.DurableAuditEvidenceStore.create_synthetic(
            source / "evidence", forbidden_roots=[source], maximum_bytes=100
        )
    store = boundary.DurableAuditEvidenceStore.create_synthetic(
        tmp_path / "evidence", forbidden_roots=[source], maximum_bytes=300
    )
    with pytest.raises(boundary.ProductionBoundaryError, match="unexpected"):
        store.finalize(
            attempt_id="unexpected", approval_id="approval", event_head_sha256="b" * 64,
            artifacts={"market_rows.csv": b"forbidden"}, terminal_state="ABORTED")
    with pytest.raises(boundary.ProductionBoundaryError, match="limit"):
        store.finalize(
            attempt_id="overflow", approval_id="approval", event_head_sha256="b" * 64,
            artifacts={"completion_report.md": b"x" * 301}, terminal_state="FAILED")


def test_activation_template_is_exactly_bound_but_non_executable():
    template = json.loads((ROOT / "specs" /
                           "fno_production_activation_template_v1.json").read_text())
    assert template["template_only"] is True and template["usable"] is False
    assert template["audit_execution_authorized"] is False
    assert template["locator_resolution_authorized"] is False
    assert template["proposal_binding"] == {
        "proposal_id": audit.PROPOSAL_ID,
        "proposal_manifest_sha256": audit.PROPOSAL_MANIFEST_SHA256,
        "audit_scope_sha256": audit.AUDIT_SCOPE_SHA256,
        "resource_envelope_sha256": audit.RESOURCE_ENVELOPE_SHA256,
        "expected_outputs_sha256": audit.EXPECTED_OUTPUTS_SHA256,
    }
    for field in ("production_locator_configuration_sha256",
                  "database_sampled_identity_root", "exact_one_use_approval_id",
                  "activation_payload_sha256"):
        assert template[field] is None


def test_pdf_v2_is_byte_exact_reviewed_historical_evidence_but_stale_after_r9d():
    record = json.loads((ROOT / "docs" / "project_status" /
                         "pre_research_review_record_v2.json").read_text())
    assert sha256_file(ROOT / record["pdf_path"]) == (
        "765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf"
    )
    assert record["reviewer_approval"]["approval_kind"] == "EXPLICIT_POST_REPORT_REVIEW"
    assert record["review_status"] == "REPORT_STALE"
    assert record["report_current"] is False
    assert record["research_execution_status"] == "PDF_V2_STALE_AFTER_R9D_IMPLEMENTATION"
    policy = json.loads((ROOT / "specs" / "pre_research_review_policy_v1.json").read_text())
    current = compute_research_state_fingerprint(ROOT, policy)
    assert current["sha256"] == record["staleness"]["current_research_state_fingerprint"]
    assert current["sha256"] != record["research_state_fingerprint"]


def test_protected_evidence_and_entrypoint_delta_are_unchanged_or_fail_closed():
    assert sha256_file(ROOT / "evidence/governance/canary_execution_anchor_v1.json") == (
        "01e6bc77af74180d970802f6fb8a5d1c5533cd392d7ceb042cf5e4b27a16c698"
    )
    assert sha256_file(ROOT / "tests/fixtures/momentum_golden_v1/expected.json") == (
        "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f"
    )
    delta = json.loads((ROOT / "specs/research_r9d_entrypoint_delta_v1.json").read_text())
    assert delta["unsafe_bypass_count"] == 0
    assert delta["real_database_access_capability"] is False
    assert delta["production_locator_state"] == boundary.PRODUCTION_LOCATOR_STATE


def test_r9d_source_does_not_read_production_configuration_or_offer_cli():
    source = Path(boundary.__file__).read_text(encoding="utf-8")
    assert "tomllib" not in source and "config.toml" not in source
    assert "__main__" not in source
    assert "configuration_reader(" not in source
