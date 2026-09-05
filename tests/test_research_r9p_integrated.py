"""Offline/static R.9P preservation and scope checks; root environment has no APSW."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "investigations" / "r9p"


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_recorded_matrix_passes_and_failure_outputs_are_separate():
    result = load("results_v1.json")
    assert result["passed"] and len(result["acceptance"]) == 10
    assert all(result["acceptance"].values())
    assert all(not item["success_published"] for item in result["adversarial_cases"].values())
    assert result["adversarial_cases"]["timeout_descendant"]["descendant_dead"]
    assert result["experimental_workers_remaining"] == 0


def test_manifest_hashes_reconcile():
    manifest = load("manifest_v1.json")
    for item in manifest["artifacts"]:
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert manifest["completion"] == "INTEGRATED_SYNTHETIC_BOUNDARY_ACCEPTANCE_PASSED_PRODUCTION_BLOCKED"


def test_attempt_approval_and_terminal_contract_is_explicit():
    source = (ROOT / "tools" / "r9p_integrated.py").read_text(encoding="utf-8")
    for term in ("attempt_id", "approval_id", "seal_sha256", "BEGIN IMMEDIATE",
                 "APPROVAL_CONSUMED", "TARGET_CONNECTION_ATTEMPT",
                 "TARGET_CONNECTION_ESTABLISHED", "OPERATION_TEMPLATE_EXECUTED",
                 "BUDGET_FAILURE", "CONTAINMENT_TERMINATION", "FINAL_TERMINAL_PUBLISHED"):
        assert term in source
    assert "consumed_at" in source and "terminal" in source


def test_fixed_synthetic_interface_has_no_production_locator_or_sql_input():
    source = (ROOT / "tools" / "r9p_integrated.py").read_text(encoding="utf-8")
    assert 'len(sys.argv) != 1' in source
    assert "--database" not in source and "--config" not in source and "--sql" not in source
    assert "getenv(" not in source and "environ[" not in source
    assert "private_fno_binding" not in source and "paths.fno_db" not in source
    assert "requests" not in source and "http" not in source.lower()
    assert "PENDING_OFFICIAL_FORMAT_EVIDENCE" in source


def test_restricted_vfs_and_job_controls_are_integrated():
    source = (ROOT / "tools" / "r9p_integrated.py").read_text(encoding="utf-8")
    inherited = (ROOT / "tools" / "r9n_adversarial.py").read_text(encoding="utf-8")
    for term in ("AssignProcessToJobObject", "ResumeThread", "CreateProcessW", "0x2000 | 0x100",
                 "acquire_guard", "before_connection", "immediately_after_connection",
                 "between_operations", "before_publication", "after_connection_close"):
        assert term in source
    for term in ("SQLITE_OPEN_READONLY", "SECOND_CONNECTION", "xRead", "enable_load_extension(False)",
                 "set_authorizer", "set_progress_handler"):
        assert term in inherited


def test_root_dependencies_and_production_interlock_are_unchanged():
    assert hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest() == "a6fcded2b042f3ab65769a158f84ba44a3b646c1390fc2667e07c556c5265664"
    assert hashlib.sha256((ROOT / "requirements.txt").read_bytes()).hexdigest() == "654e2ca20bb0f2dac0fc5e2041e5f65ce808b7c1f401ad3cdbe46524dec841ab"
    assert hashlib.sha256((ROOT / "src/market_intel/foundation/fno_production_boundary.py").read_bytes()).hexdigest() == "dcde3cbf1cd2cb1d5e70527cacb7066daf50e9cf6e48eb6fe44df45af8fc11ea"
    assert "apsw" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "apsw" not in (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()


def test_previous_evidence_and_pdf_v7_are_byte_preserved():
    assert hashlib.sha256((ROOT / "docs/investigations/r9n/manifest_v1.json").read_bytes()).hexdigest() == "3f154a3364e0ed87f1b2eeefd659b848fa5d71824e36589f79bf5a2b59913e0f"
    assert hashlib.sha256((ROOT / "output/pdf/market_system_status_pre_research_review_v7.pdf").read_bytes()).hexdigest() == "804c555b4ac422f26f2c6ce5c7d98e1a4e7af6f3f81037b5cd40e950ae1691a7"


def test_r9p_artifacts_have_no_secret_or_private_path():
    text = "\n".join(path.read_text(encoding="utf-8") for path in [
        ROOT / "tools/r9p_integrated.py", ROOT / "tools/r9p_regression.py",
        BASE / "ACCEPTANCE_MATRIX.md", BASE / "results_v1.json",
    ])
    assert not re.search(r"(?i)(api[_-]?secret|access[_-]?token|password)\s*[:=]\s*\S+", text)
    assert "C:\\Users\\" not in text and "Data test/config/config.toml" not in text
