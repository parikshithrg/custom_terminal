from __future__ import annotations

import ast
import dataclasses
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from market_intel.foundation import local_fno_audit as audit


NOW = datetime.now(timezone.utc)


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    source = tmp_path / "synthetic_source"
    source.mkdir()
    (source / ".synthetic_audit_fixture").write_text("synthetic only", encoding="utf-8")
    database = source / "fixture.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        "CREATE TABLE prices(id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, close REAL);"
        "CREATE INDEX idx_prices_symbol ON prices(symbol);"
        "CREATE VIEW price_symbols AS SELECT symbol FROM prices;"
        "INSERT INTO prices(symbol, close) VALUES ('SYNTH', 100.0);"
    )
    connection.close()
    provenance = tmp_path / "provenance"
    provenance.mkdir()
    (provenance / "manifest.json").write_text(
        json.dumps({"source": "synthetic", "retention": "test only", "api_secret": "do-not-emit"}),
        encoding="utf-8",
    )
    output = tmp_path / "audit_output"
    return source, database, provenance, output


def _approval(database: Path, source: Path, **changes) -> audit.AuditApproval:
    identity = audit.capture_file_identity(database, synthetic_root=source)
    value = audit.AuditApproval(
        schema_version="local_data_audit_stage_1_3_approval_v1",
        approval_type=audit.AUDIT_APPROVAL_TYPE,
        approval_id="synthetic-approval-001",
        proposal=audit.ProposalIdentity(),
        approved_locator_key="synthetic.fixture.path",
        approved_locator_sha256=audit.synthetic_locator_hash(),
        approved_database_identity_root=identity.sampled_root_sha256,
        approved_stages=(1, 2, 3),
        approved_resources=audit.approved_resource_contract(),
        approved_outputs=audit.PERMITTED_OUTPUTS,
        fixture_classification=audit.SYNTHETIC_FIXTURE_CLASS,
        issued_at=(NOW - timedelta(minutes=1)).isoformat(),
        expires_at=(NOW + timedelta(minutes=10)).isoformat(),
        approved_by="synthetic-test-owner",
        approval_statement="Approve one synthetic-only Stage 1-3 audit test.",
    )
    value = dataclasses.replace(value, **changes)
    return audit.seal_audit_approval(value)


def _run(tmp_path: Path, *, approval=None, registry=None, **kwargs):
    source, database, provenance, output = _fixture(tmp_path)
    approval = approval or _approval(database, source)
    registry = registry or audit.AuditApprovalRegistry()
    if registry.consumed_by(approval.approval_id) is None:
        registry.register(approval)
    result = audit.execute_approved_stage_1_3_audit(
        target_path=database, synthetic_root=source, approval=approval,
        registry=registry, output_root=output, provenance_roots=[provenance],
        attempt_id=kwargs.pop("attempt_id", "attempt-001"), evaluated_at=NOW,
        mode="GOVERNED_SYNTHETIC_EXECUTION", **kwargs,
    )
    return result, source, database, provenance, output, approval, registry


def test_proposal_dry_run_makes_no_connection_or_attempt(monkeypatch):
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: pytest.fail("connected"))
    result = audit.execute_approved_stage_1_3_audit()
    assert result.status == "BLOCKED"
    assert result.attempt is None


def test_missing_approval_fails_before_path_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: pytest.fail("resolved"))
    with pytest.raises(audit.LocalFnoAuditError, match="required"):
        audit.execute_approved_stage_1_3_audit(mode="GOVERNED_SYNTHETIC_EXECUTION")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"template_only": True, "usable": False}, "template"),
        ({"approved_stages": (1, 2)}, "stage mismatch"),
        ({"approved_locator_sha256": "0" * 64}, "locator-file hash mismatch"),
        ({"fixture_classification": "PRODUCTION"}, "synthetic"),
        ({"approved_locator_key": "paths.fno_db"}, "production F&O locator"),
        ({"approved_outputs": ("not-approved.json",)}, "output mismatch"),
        ({"approved_resources": {}}, "resource mismatch"),
        ({"proposal": audit.ProposalIdentity(proposal_manifest_sha256="0" * 64)}, "proposal hash"),
    ],
)
def test_altered_contracts_fail_closed(tmp_path, change, message):
    source, database, _, _ = _fixture(tmp_path)
    approval = _approval(database, source, **change)
    registry = audit.AuditApprovalRegistry()
    with pytest.raises(audit.LocalFnoAuditError, match=message):
        registry.register(approval)


def test_expired_approval_is_rejected(tmp_path):
    source, database, _, _ = _fixture(tmp_path)
    approval = _approval(database, source, expires_at=(NOW - timedelta(seconds=1)).isoformat())
    with pytest.raises(audit.LocalFnoAuditError, match="expired"):
        audit.validate_audit_approval(approval, now=NOW)


def test_wrong_database_identity_is_rejected_before_consumption(tmp_path):
    source, database, provenance, output = _fixture(tmp_path)
    approval = _approval(database, source, approved_database_identity_root="0" * 64)
    registry = audit.AuditApprovalRegistry(); registry.register(approval)
    with pytest.raises(audit.LocalFnoAuditError, match="database-identity mismatch"):
        audit.execute_approved_stage_1_3_audit(
            target_path=database, synthetic_root=source, approval=approval,
            registry=registry, output_root=output, provenance_roots=[provenance],
            evaluated_at=NOW, mode="GOVERNED_SYNTHETIC_EXECUTION")
    assert registry.consumed_by(approval.approval_id) is None


def test_unregistered_and_altered_registered_approval_are_rejected(tmp_path):
    source, database, _, _ = _fixture(tmp_path)
    approval = _approval(database, source)
    registry = audit.AuditApprovalRegistry()
    with pytest.raises(audit.LocalFnoAuditError, match="not registered"):
        registry.consume(approval, "a")
    registry.register(approval)
    altered = dataclasses.replace(approval, approval_statement="changed")
    with pytest.raises(audit.LocalFnoAuditError, match="payload hash mismatch"):
        registry.consume(altered, "a")


def test_market_research_approval_cannot_substitute():
    with pytest.raises(audit.LocalFnoAuditError, match="market-research"):
        audit.validate_audit_approval({"approval_id": "research"})  # type: ignore[arg-type]


def test_completed_audit_is_noncanonical_catalog_only_and_atomic(tmp_path):
    result, _, _, _, output, approval, registry = _run(
        tmp_path, later_query_plans=["SELECT * FROM prices WHERE symbol = 'SYNTH'"])
    assert result.status == "COMPLETED"
    assert registry.consumed_by(approval.approval_id) == "attempt-001"
    final = output / "attempt-001"
    assert final.is_dir() and not (output / ".tmp-attempt-001").exists()
    assert {p.name for p in final.iterdir()} == set(audit.PERMITTED_OUTPUTS)
    manifest = json.loads((final / "root_audit_manifest.json").read_text())
    catalog = json.loads((final / "schema_catalog_inventory.json").read_text())
    plans = json.loads((final / "later_stage_query_plan_inventory.json").read_text())
    assert manifest["canonical"] is False and manifest["promotion_eligible"] is False
    assert catalog["market_row_reads"] == 0
    assert plans["queries_executed"] == 0 and plans["plans"]
    assert "'SYNTH'" not in "".join(p.read_text(errors="ignore") for p in final.iterdir())


def test_approval_reuse_is_rejected_before_second_attempt(tmp_path):
    result, source, database, provenance, output, approval, registry = _run(tmp_path)
    assert result.status == "COMPLETED"
    with pytest.raises(audit.LocalFnoAuditError, match="already been consumed"):
        audit.execute_approved_stage_1_3_audit(
            target_path=database, synthetic_root=source, approval=approval,
            registry=registry, output_root=output, provenance_roots=[provenance],
            attempt_id="attempt-002", evaluated_at=NOW,
            mode="GOVERNED_SYNTHETIC_EXECUTION")
    assert not (output / "attempt-002").exists()


def test_identity_deduplicates_small_fixture_chunks(tmp_path):
    source, database, _, _ = _fixture(tmp_path)
    identity = audit.capture_file_identity(database, synthetic_root=source)
    assert identity.nominal_chunk_count == 64
    assert identity.unique_chunk_count == 1
    assert identity.actual_bytes_read == 100 + database.stat().st_size


def test_symlink_target_and_path_escape_are_rejected(tmp_path):
    source, database, _, _ = _fixture(tmp_path)
    outside = tmp_path / "outside.sqlite"
    outside.write_bytes(database.read_bytes())
    with pytest.raises(audit.AuditAborted, match="escapes"):
        audit.capture_file_identity(outside, synthetic_root=source)
    link = source / "link.sqlite"
    try:
        link.symlink_to(database)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(audit.AuditAborted, match="symlink"):
        audit.capture_file_identity(link, synthetic_root=source)


@pytest.mark.parametrize("sql", [
    "CREATE TABLE x(a)", "DROP TABLE prices", "ALTER TABLE prices ADD x INT",
    "INSERT INTO prices VALUES(2,'X',2)", "UPDATE prices SET close=0",
    "DELETE FROM prices", "REPLACE INTO prices VALUES(2,'X',2)",
    "ATTACH DATABASE 'x' AS x", "DETACH DATABASE main", "VACUUM",
    "REINDEX", "ANALYZE", "PRAGMA journal_mode=WAL", "PRAGMA writable_schema=ON",
])
def test_ddl_dml_attach_and_writable_operations_are_rejected(tmp_path, sql):
    source, database, _, _ = _fixture(tmp_path)
    events = []
    connection = audit.ReadOnlyCatalogConnection(database, event_sink=events)
    with pytest.raises(audit.AuditAborted):
        connection.execute(sql)
    connection.close()


def test_user_table_read_is_rejected_but_catalog_and_plan_are_allowed(tmp_path):
    _, database, _, _ = _fixture(tmp_path)
    connection = audit.ReadOnlyCatalogConnection(database, event_sink=[])
    assert connection.execute("SELECT name FROM sqlite_schema ORDER BY name").fetchall()
    assert connection.execute("EXPLAIN QUERY PLAN SELECT * FROM prices").fetchall()
    with pytest.raises(audit.AuditAborted, match="allowlist"):
        connection.execute("SELECT * FROM prices")
    connection.close()


def test_extension_loading_is_disabled_and_not_exposed(tmp_path):
    _, database, _, _ = _fixture(tmp_path)
    connection = audit.ReadOnlyCatalogConnection(database, event_sink=[])
    with pytest.raises(audit.AuditAborted):
        connection.execute("SELECT load_extension('x')")
    connection.close()


def test_statement_count_limit_is_enforced(tmp_path, monkeypatch):
    _, database, _, _ = _fixture(tmp_path)
    monkeypatch.setattr(audit, "MAX_STATEMENTS", 3)
    connection = audit.ReadOnlyCatalogConnection(database, event_sink=[])
    with pytest.raises(audit.AuditAborted, match="statement-count"):
        connection.execute("PRAGMA query_only")
    connection.close()


def test_progress_handler_timeout_and_cancellation(tmp_path, monkeypatch):
    _, database, _, _ = _fixture(tmp_path)
    connection = audit.ReadOnlyCatalogConnection(database, event_sink=[])
    ticks = iter([0.0, 99.0])
    monkeypatch.setattr(audit.time, "monotonic", lambda: next(ticks, 99.0))
    aliases = ",".join(f"sqlite_schema s{i}" for i in range(10))
    with pytest.raises(audit.AuditAborted, match="sanitized SQLite failure"):
        connection.execute(f"SELECT s0.name FROM {aliases}").fetchall()
    connection.close()


def test_database_mutation_between_checkpoints_aborts_and_consumes(tmp_path, monkeypatch):
    source, database, provenance, output = _fixture(tmp_path)
    approval = _approval(database, source)
    registry = audit.AuditApprovalRegistry(); registry.register(approval)
    original = audit.capture_file_identity
    calls = 0
    def mutate(path, *, synthetic_root):
        nonlocal calls
        calls += 1
        if calls == 2:
            with Path(path).open("ab") as stream:
                stream.write(b"mutation")
        return original(path, synthetic_root=synthetic_root)
    monkeypatch.setattr(audit, "capture_file_identity", mutate)
    result = audit.execute_approved_stage_1_3_audit(
        target_path=database, synthetic_root=source, approval=approval, registry=registry,
        output_root=output, provenance_roots=[provenance], attempt_id="mutated",
        evaluated_at=NOW, mode="GOVERNED_SYNTHETIC_EXECUTION")
    assert result.status == "ABORTED"
    assert registry.consumed_by(approval.approval_id) == "mutated"


def test_new_sidecar_between_checkpoints_aborts(tmp_path, monkeypatch):
    source, database, provenance, output = _fixture(tmp_path)
    approval = _approval(database, source)
    registry = audit.AuditApprovalRegistry(); registry.register(approval)
    original = audit.capture_file_identity
    calls = 0
    def add_sidecar(path, *, synthetic_root):
        nonlocal calls
        calls += 1
        if calls == 2:
            Path(str(path) + "-wal").write_bytes(b"new")
        return original(path, synthetic_root=synthetic_root)
    monkeypatch.setattr(audit, "capture_file_identity", add_sidecar)
    result = audit.execute_approved_stage_1_3_audit(
        target_path=database, synthetic_root=source, approval=approval, registry=registry,
        output_root=output, provenance_roots=[provenance], attempt_id="sidecar",
        evaluated_at=NOW, mode="GOVERNED_SYNTHETIC_EXECUTION")
    assert result.status == "ABORTED"


def test_stage3_limits_symlinks_and_secret_redaction(tmp_path, monkeypatch):
    root = tmp_path / "p"; root.mkdir()
    (root / "a.json").write_text('{"api_secret":"visible-only-in-input","source":"x"}')
    inventory, _ = audit._provenance_inventory([root])
    assert "visible-only-in-input" not in json.dumps(inventory)
    monkeypatch.setattr(audit, "MAX_PROVENANCE_FILES", 1)
    (root / "b.md").write_text("source")
    with pytest.raises(audit.AuditAborted, match="file-count"):
        audit._provenance_inventory([root])
    monkeypatch.setattr(audit, "MAX_PROVENANCE_FILES", 500)
    monkeypatch.setattr(audit, "MAX_PROVENANCE_BYTES", 1)
    with pytest.raises(audit.AuditAborted, match="byte limit"):
        audit._provenance_inventory([root])


def test_stage3_symlink_rejected(tmp_path):
    root = tmp_path / "p"; root.mkdir()
    target = root / "a.md"; target.write_text("source")
    link = root / "link.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(audit.AuditAborted, match="symlink"):
        audit._provenance_inventory([root])


def test_unexpected_output_and_output_limit_are_rejected(tmp_path, monkeypatch):
    writer = audit._ArtifactWriter(tmp_path)
    with pytest.raises(audit.AuditAborted, match="unexpected"):
        writer.write_text("extra.txt", "x")
    monkeypatch.setattr(audit, "MAX_OUTPUT_BYTES", 1)
    writer = audit._ArtifactWriter(tmp_path / "limited")
    writer.directory.mkdir()
    with pytest.raises(audit.AuditAborted, match="output-byte"):
        writer.write_text("completion_report.md", "too large")


def test_failed_attempt_consumes_approval_and_finalizes_terminal(tmp_path, monkeypatch):
    source, database, provenance, output = _fixture(tmp_path)
    approval = _approval(database, source)
    registry = audit.AuditApprovalRegistry(); registry.register(approval)
    monkeypatch.setattr(audit, "_catalog_inventory", lambda c: (_ for _ in ()).throw(RuntimeError("secret=never")))
    result = audit.execute_approved_stage_1_3_audit(
        target_path=database, synthetic_root=source, approval=approval, registry=registry,
        output_root=output, provenance_roots=[provenance], attempt_id="failed",
        evaluated_at=NOW, mode="GOVERNED_SYNTHETIC_EXECUTION")
    assert result.status == "FAILED" and "never" not in result.message
    assert registry.consumed_by(approval.approval_id) == "failed"
    assert (output / "failed" / "root_audit_manifest.json").is_file()


def test_source_has_no_network_broker_research_or_backtest_dependency():
    source = Path(audit.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, ast.Import) for alias in node.names}
    imports |= {(node.module or "").split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 0}
    assert not imports & {"requests", "urllib3", "kiteconnect", "market_intel.research"}
    assert "paths.fno_db" == audit.validate_audit_approval.__code__.co_consts[
        audit.validate_audit_approval.__code__.co_consts.index("paths.fno_db")]


def test_tests_do_not_read_or_resolve_production_locator():
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = "Data test" + "/config/" + "config.toml"
    assert forbidden not in source
    forbidden_import = "toml" + "lib"
    assert forbidden_import not in source
