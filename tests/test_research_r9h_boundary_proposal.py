from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from market_intel.foundation import fno_production_boundary as boundary
from market_intel.foundation.local_fno_audit import (
    AuditApproval, AuditApprovalRegistry, LocalFnoAuditError, ProposalIdentity,
    validate_audit_approval,
)
from research_contracts.legacy_ledger import canonical_json_bytes, sha256_file
from research_contracts.pre_research_review import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "proposals/fno_production_audit_boundary_v1"
MANIFEST = PACKAGE / "proposal_manifest_v1.json"
EXPECTED_MANIFEST = "a6529ec14520d163e327e2dcc7a7f469ea473D14B8D39E3EDE345BC3D49DCDC1".lower()
EXPECTED_STATE = "1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_proposal_json_has_version_and_manifest_hashes_reconcile():
    manifest = _load(MANIFEST)
    actual = {p.name for p in PACKAGE.glob("*.json") if p != MANIFEST}
    declared = {item["path"] for item in manifest["objects"]}
    assert actual == declared
    rows = []
    for item in manifest["objects"]:
        path = PACKAGE / item["path"]
        assert _load(path)["schema_version"]
        assert sha256_file(path) == item["sha256"]
        assert path.stat().st_size == item["byte_size"]
        rows.append(item)
    assert hashlib.sha256(canonical_json_bytes(rows)).hexdigest() == manifest["package_content_sha256"]
    assert sha256_file(MANIFEST) == EXPECTED_MANIFEST


def test_serialization_and_manifest_order_are_deterministic():
    manifest = _load(MANIFEST)
    assert [item["path"] for item in manifest["objects"]] == sorted(
        item["path"] for item in manifest["objects"]
    )
    for path in PACKAGE.glob("*.json"):
        value = _load(path)
        assert json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"))) == value


def _unusable_approval() -> AuditApproval:
    template = _load(PACKAGE / "approval_template_v1.json")
    return AuditApproval(
        schema_version=template["schema_version"], approval_type=template["approval_type"],
        approval_id=template["approval_id"], proposal=ProposalIdentity(),
        approved_locator_key=template["database_binding"]["approved_locator_key"],
        approved_locator_sha256=template["database_binding"]["configuration_file_sha256"],
        approved_database_identity_root=template["database_binding"]["sampled_identity_root"],
        approved_stages=tuple(template["approved_audit_stages"]),
        approved_resources=template["resource_budgets"], approved_outputs=(),
        fixture_classification="PRODUCTION_DATABASE_NOT_AUTHORIZED",
        issued_at="2000-01-01T00:00:00Z", expires_at="2000-01-01T00:01:00Z",
        approved_by=template["owner_identity_classification"],
        approval_statement=template["explicit_approval_statement"],
        template_only=True, usable=False,
        approval_payload_sha256=template["approval_payload_sha256"],
    )


def test_approval_example_is_unsealed_and_rejected_by_validator_and_registry():
    template = _load(PACKAGE / "approval_template_v1.json")
    assert template["template_only"] is True and template["usable"] is False
    assert template["approval_payload_sha256"] == "NOT_SEALED_PROPOSAL_ONLY"
    approval = _unusable_approval()
    registry = AuditApprovalRegistry()
    with pytest.raises(LocalFnoAuditError): validate_audit_approval(approval)
    with pytest.raises(LocalFnoAuditError): registry.register(approval)
    with pytest.raises(LocalFnoAuditError): registry.consume(approval, "attempt-never-starts")


def test_current_boundary_still_fails_before_configuration_or_sqlite(monkeypatch):
    called = {"configuration": 0, "sqlite": 0}
    def config_reader(): called["configuration"] += 1
    def connect(*args, **kwargs): called["sqlite"] += 1
    monkeypatch.setattr(boundary.sqlite3, "connect", connect)
    with pytest.raises(boundary.ProductionBoundaryError):
        boundary.execute_production_stage_1_3_audit(configuration_reader=config_reader)
    assert called == {"configuration": 0, "sqlite": 0}
    evidence = boundary.ProductionInterlockEvidence(**{
        item.name: True for item in fields(boundary.ProductionInterlockEvidence)
    })
    result = boundary.evaluate_production_interlocks(evidence)
    assert result["permitted"] is False
    assert result["database_access_authorized"] is False
    assert result["audit_execution_authorized"] is False
    source = Path(boundary.__file__).read_text(encoding="utf-8")
    assert "\"permitted\": False" in source
    assert boundary.DELIBERATE_INTERLOCK == "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE"


def test_entrypoint_delta_adds_no_executable_or_sensitive_capability():
    delta = _load(PACKAGE / "entrypoint_capability_delta_v1.json")
    for key in ("new_executable_production_entrypoints", "interlock_changes",
                "database_connections", "sql_executions", "network_capabilities_added",
                "broker_capabilities_added", "analysis_capabilities_added",
                "trading_capabilities_added"):
        assert delta[key] == 0
    assert list(PACKAGE.glob("*.py")) == []


def test_manifest_required_false_states_and_next_scope():
    manifest = _load(MANIFEST)
    assert manifest["completion_state"] == "FNO_PRODUCTION_AUDIT_BOUNDARY_PROPOSAL_PREPARED"
    false_fields = ("proposal_reviewed_by_owner", "interlock_change_authorized",
        "interlock_changed", "approval_issued", "approval_registered", "approval_consumed",
        "database_connected", "sql_executed", "schema_inspected", "market_rows_read",
        "audit_started", "alternative_data_acquired", "analysis_started", "scoring_started",
        "simulation_started", "backtest_started", "broker_accessed", "trading_enabled")
    assert all(manifest[field] is False for field in false_fields)
    assert manifest["next_requested_scope"] == "GENERATE_PRE_RESEARCH_STATUS_PDF_V5_ONLY"


def test_no_private_path_or_secret_in_proposal_package():
    text = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.json"))
    assert not re.search(r"[A-Za-z]:[\\/]", text)
    assert "/Users/" not in text and "\\Users\\" not in text
    assert not re.search(r"(?i)(api[_-]?secret|access[_-]?token|password)\s*[:=]\s*\S+", text)


def test_prior_pdfs_and_binding_evidence_remain_exact():
    expected = {
        "output/pdf/market_system_status_pre_research_review_v1.pdf": "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c",
        "output/pdf/market_system_status_pre_research_review_v2.pdf": "765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf",
        "output/pdf/market_system_status_pre_research_review_v3.pdf": "75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2",
        "output/pdf/market_system_status_pre_research_review_v4.pdf": "02a76f6d46bc74a69b7f0b10331ae26da1d07d60934091ce9d31c0abe8cdaec9",
        "evidence/fno_locator_binding_v1/anchor.json": "115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc",
        "proposals/fno_locator_binding_v1/binding_proposal.json": "995524b670dc95b717fa7d4b27935c788d661bcf75b8f7f4400d76831a8f434f"}
    assert all(sha256_file(ROOT / path) == digest for path, digest in expected.items())


def test_research_fingerprint_and_pdf_v4_staleness_reconcile():
    state = compute_research_state_fingerprint(ROOT, _load(ROOT / "specs/pre_research_review_policy_v1.json"))
    record = _load(ROOT / "docs/project_status/pre_research_review_record_v4.json")
    assert state["sha256"] == EXPECTED_STATE and state["file_count"] == 252
    assert record["review_status"] == "REPORT_STALE"
    assert record["staleness"]["current_research_state_fingerprint"] == EXPECTED_STATE
    assert record["staleness"]["status"] == "PDF_V4_STALE_AFTER_R9H_PROPOSAL_PREPARATION"
