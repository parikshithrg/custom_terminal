from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import fitz

from research_contracts.legacy_ledger import canonical_json_bytes, sha256_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs/project_status/consolidated_pre_real_data_status_v1.json"
REPORT_PATH = ROOT / "reports/CONSOLIDATED_PRE_REAL_DATA_STATUS.md"
PDF_PATH = ROOT / "output/pdf/CONSOLIDATED_PRE_REAL_DATA_STATUS_V1.pdf"
COMPLETION_PATH = ROOT / "docs/investigations/r10j/status_pdf_v1/completion.json"
MANIFEST_PATH = ROOT / "docs/investigations/r10j/status_pdf_v1/manifest.json"
SOURCE_COMMIT = "b7c6124c6e6a353b61078a950652b763db3467bf"
R10I_FINGERPRINT = "19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6"
WARNING = "NO ANALYSIS, BACKTESTING, SCORING, RECOMMENDATION OR TRADING AUTHORIZED"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _builder_module():
    path = ROOT / "tools/r10j_consolidated_status.py"
    spec = importlib.util.spec_from_file_location("r10j_consolidated_status", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pdf_text() -> tuple[int, str]:
    with fitz.open(PDF_PATH) as document:
        pages = [page.get_text() for page in document]
    return len(pages), "\n".join(pages)


def test_structured_source_deterministically_generates_markdown() -> None:
    status = _load(STATUS_PATH)
    expected = _builder_module().render_status_markdown(status)
    assert REPORT_PATH.read_text(encoding="utf-8") == expected


def test_document_control_records_verified_source_checkpoint_without_granting_authority() -> None:
    status = _load(STATUS_PATH)
    control = status["document_control"]
    sync = control["synchronization"]
    assert control["source_commit"] == SOURCE_COMMIT
    assert sync["status"] == "VERIFIED_SYNCHRONIZED"
    assert sync["local_main"] == sync["origin_main_after_fetch"] == sync["remote_ref_from_ls_remote"] == SOURCE_COMMIT
    assert sync["ahead"] == sync["behind"] == 0
    assert control["owner_review_status"] == "NOT_RECORDED"
    assert control["next_task_approval_status"] == "NOT_RECORDED"
    assert control["warning"] == WARNING


def test_canonical_readiness_and_fingerprint_are_not_overstated() -> None:
    status = _load(STATUS_PATH)
    readiness = status["current_readiness"]
    assert readiness["synthetic_infrastructure"] == "MECHANICALLY_VALIDATED_NONCANONICAL"
    assert readiness["historical_market_data"] == "NOT_QUALIFIED"
    assert readiness["historical_population"] == "FAIL_3_OF_12_PAIRS"
    assert readiness["real_data_research"] == "NOT_AUTHORIZED"
    assert readiness["economic_edges"] == "NONE_VALIDATED"
    assert status["validation"]["r10i_authoritative_git_fingerprint"] == R10I_FINGERPRINT
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert R10I_FINGERPRINT in report
    assert "`e0870bd...` was a stale pre-refresh working-tree value" in report
    assert "`236fddae...` was a post-refresh working-tree value" in report
    assert "e0870bd050c2906f1aa81ead3ffe66871031db106e5ee39c046c5a011184759c" not in report
    assert "236fddae8660e373eccdc6bb34a67a0dc0baaf7e91ff6203f4d24a43193a172f" not in report


def test_synthetic_results_are_explicitly_non_economic() -> None:
    status = _load(STATUS_PATH)
    synthetic = [item for item in status["milestones"] if item["id"].startswith("R.10") and item["id"] <= "R.10G"]
    assert synthetic
    assert all(item["status"] == "SYNTHETIC_NONCANONICAL" for item in synthetic)
    text = " ".join(REPORT_PATH.read_text(encoding="utf-8").split())
    assert "They do not estimate a real return, validate a market relationship, or justify a score." in text
    assert "Economically validated edges:** none." in text


def test_next_stage_and_owner_decisions_remain_separate_and_unrecorded() -> None:
    status = _load(STATUS_PATH)
    stage = status["proposed_next_milestone"]
    review = status["owner_review"]
    assert stage["id"] == "LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1"
    assert stage["authorization"] == "NOT_AUTHORIZED_UNTIL_SEPARATELY_APPROVED_AFTER_REPORT_REVIEW"
    assert review["report_accuracy_approval"] == "UNRECORDED"
    assert review["next_milestone_approval"] == "UNRECORDED"
    assert review["report_accuracy_approval"] is not review["next_milestone_approval"] or review["report_accuracy_approval"] == "UNRECORDED"


def test_all_prohibited_authorities_remain_false() -> None:
    safety = _load(STATUS_PATH)["safety_boundaries"]
    assert safety["analysis_only_product"] is True
    assert all(value is False for key, value in safety.items() if key != "analysis_only_product")


def test_pdf_has_all_pages_sections_and_critical_warnings() -> None:
    page_count, extracted = _pdf_text()
    text = " ".join(extracted.split())
    assert page_count == 15
    required = [
        "Table of contents",
        "Executive summary",
        "What we are trying to build",
        "What has been completed - foundation",
        "What remains blocked or unknown",
        "Test and evidence status",
        "Safety and authority boundaries",
        "Proposed next development stage",
        "Owner review - separate decisions required",
        WARNING,
        SOURCE_COMMIT,
        "LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION",
        "_STAGE_1",
    ]
    assert all(value in text for value in required)
    with fitz.open(PDF_PATH) as document:
        assert all(page.get_text().strip() for page in document)


def test_completion_and_manifest_bind_the_final_artifacts() -> None:
    completion = _load(COMPLETION_PATH)
    manifest = _load(MANIFEST_PATH)
    assert completion["completion_state"] == "CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF_READY_FOR_OWNER_REVIEW"
    assert completion["source_commit"] == SOURCE_COMMIT
    assert completion["owner_review_status"] == "NOT_RECORDED"
    assert completion["next_task_approval_status"] == "NOT_RECORDED"
    assert completion["pdf_verification"]["page_count"] == 15
    assert completion["pdf_verification"]["visual_inspection"] == "PASS_15_PAGES_NO_MATERIAL_DEFECTS"
    for relative, expected in manifest["outputs"].items():
        assert sha256_file(ROOT / relative) == expected
    payload = dict(manifest)
    expected_payload = payload.pop("payload_sha256")
    expected_root = payload.pop("root_sha256")
    actual_payload = sha256_bytes(canonical_json_bytes(payload))
    assert actual_payload == expected_payload
    root_payload = {"manifest_payload_sha256": actual_payload, "outputs": manifest["outputs"]}
    assert sha256_bytes(canonical_json_bytes(root_payload)) == expected_root


def test_renderer_declares_deterministic_reportlab_output() -> None:
    renderer = (ROOT / "tools/generate_project_status_pdf.py").read_text(encoding="utf-8")
    assert "rl_config.invariant = 1" in renderer
    assert "partial(Canvas, invariant=1, pageCompression=1)" in renderer
