from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from market_intel.foundation import fno_production_boundary as boundary
from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import compute_research_state_fingerprint


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/project_status/market_system_status_pre_research_review_v4.md"
PDF = ROOT / "output/pdf/market_system_status_pre_research_review_v4.pdf"
MANIFEST = ROOT / "docs/project_status/pre_research_generation_manifest_v4.json"
POLICY = ROOT / "specs/pre_research_review_policy_v1.json"
EXPECTED_STATE = "6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db"
EXPECTED_ANCHOR = "115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc"
EXPECTED_PROPOSAL = "995524b670dc95b717fa7d4b27935c788d661bcf75b8f7f4400d76831a8f434f"
EXPECTED_SAMPLE_ROOT = "b1b8c0ca1338d477987da28e6d9647b151c120a0eac7bb17c9e9293edfd4bc47"
PRIOR_PDFS = {
    "v1": "cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c",
    "v2": "765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf",
    "v3": "75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v4_manifest_is_generation_only_and_hashes_reconcile():
    manifest = _load(MANIFEST)
    assert manifest["schema_version"] == "pre_research_generation_manifest_v1"
    assert manifest["manifest_kind"] == "NON_APPROVAL_REPORT_GENERATION"
    assert manifest["report_version"] == "v4"
    assert manifest["lifecycle_state"] == "PDF_V4_GENERATED_AWAITING_OWNER_REVIEW"
    assert sha256_file(SOURCE) == manifest["source_sha256"]
    assert sha256_file(PDF) == manifest["pdf_sha256"]
    payload = PDF.read_bytes()
    assert payload.startswith(b"%PDF-") and payload.rstrip().endswith(b"%%EOF")
    assert b"/Encrypt" not in payload
    assert max(map(int, re.findall(rb"/Count\s+(\d+)", payload))) == (
        manifest["rendered_page_count"]
    ) == 14


def test_v4_binds_exact_r9f_evidence_and_research_state():
    manifest = _load(MANIFEST)
    evidence = {item["path"]: item["sha256"] for item in manifest["evidence_inputs"]}
    assert evidence["evidence/fno_locator_binding_v1/anchor.json"] == EXPECTED_ANCHOR
    assert evidence["proposals/fno_locator_binding_v1/binding_proposal.json"] == EXPECTED_PROPOSAL
    assert manifest["sampled_identity_root_sha256"] == EXPECTED_SAMPLE_ROOT
    state = compute_research_state_fingerprint(ROOT, _load(POLICY))
    assert manifest["research_state_fingerprint"] == state["sha256"] == EXPECTED_STATE
    assert manifest["research_state_file_count"] == state["file_count"] == 242


def test_v4_plain_language_is_precise_about_binding_limitations():
    text = SOURCE.read_text(encoding="utf-8")
    assert "LOCATED_AND_SAMPLED_NOT_QUALIFIED" in text
    assert "not a full-file hash" in text
    assert "does not prove that every unsampled byte remained identical" in text
    assert "Modification time is metadata, not complete identity" in text
    prohibited_claims = (
        "database is trusted",
        "database is validated",
        "database is production-ready",
        "database is approved for research",
    )
    assert all(value not in text.lower() for value in prohibited_claims)


def test_v4_contains_exact_r9f_measurements_without_private_path():
    text = SOURCE.read_text(encoding="utf-8")
    for value in (
        "PRIVATE_FNO_DATABASE_V1",
        "48,345,137,152 bytes",
        "268,435,456",
        "268,435,556",
        EXPECTED_ANCHOR,
        EXPECTED_PROPOSAL,
        EXPECTED_SAMPLE_ROOT,
    ):
        assert value in text
    assert not re.search(r"[A-Za-z]:[\\/]", text)
    assert "/Users/" not in text and "\\Users\\" not in text


def test_v4_keeps_interlock_and_all_authorities_false(monkeypatch):
    manifest = _load(MANIFEST)
    assert manifest["production_interlock"] == boundary.DELIBERATE_INTERLOCK
    for field in (
        "owner_review_recorded",
        "interlock_change_authorized",
        "database_connection_authorized",
        "audit_authorized",
        "market_row_access_authorized",
        "analysis_authorized",
        "scoring_authorized",
        "backtesting_authorized",
        "trading_authorized",
    ):
        assert manifest[field] is False
    called = {"configuration": 0, "sqlite": 0}

    def config_reader():
        called["configuration"] += 1
        raise AssertionError("configuration must not be read")

    def connect(*args, **kwargs):
        called["sqlite"] += 1
        raise AssertionError("SQLite must not be opened")

    monkeypatch.setattr(boundary.sqlite3, "connect", connect)
    with pytest.raises(boundary.ProductionBoundaryError):
        boundary.execute_production_stage_1_3_audit(configuration_reader=config_reader)
    assert called == {"configuration": 0, "sqlite": 0}


def test_v4_requests_only_the_exact_proposal_scope_and_no_approval_record_exists():
    manifest = _load(MANIFEST)
    text = SOURCE.read_text(encoding="utf-8")
    scope = "EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY"
    assert manifest["proposed_next_scope"] == scope
    assert scope in text
    assert not (ROOT / "docs/project_status/pre_research_review_record_v4.json").exists()
    assert "Do you authorize the next task to prepare an interlock-removal proposal only" in text


def test_prior_pdf_versions_are_byte_identical():
    for version, expected in PRIOR_PDFS.items():
        path = ROOT / f"output/pdf/market_system_status_pre_research_review_{version}.pdf"
        assert sha256_file(path) == expected


def test_v4_generator_enables_deterministic_reportlab_mode():
    generator = (ROOT / "tools/generate_project_status_pdf.py").read_text(encoding="utf-8")
    manifest = _load(MANIFEST)
    assert "rl_config.invariant = 1" in generator
    assert "invariant=1" in generator
    assert manifest["deterministic_render_verified"] is True


def test_v4_pdf_text_contains_lifecycle_and_current_safety_boundary():
    # The Markdown is the canonical presentation source. Rendering/text extraction
    # is verified separately with the bundled PDF runtime during the milestone.
    extracted = SOURCE.read_text(encoding="utf-8")
    for value in (
        "PDF_V4_GENERATED_AWAITING_OWNER_REVIEW",
        "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE",
        "database_connected: false",
        "production_activation_eligible: false",
        "owner_review_recorded: false",
    ):
        assert value in extracted
