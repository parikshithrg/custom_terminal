"""Static, tracked-evidence checks only: no native probes or database access."""
import hashlib
import json
import re
from pathlib import Path

from research_contracts.pre_research_review import compute_research_state_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/project_status/pre_research_generation_manifest_v6.json"


def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def source():
    return (ROOT / load()["source_path"]).read_text(encoding="utf-8")


def test_exact_hashes_and_complete_investigation_bindings():
    m = load()
    rows = m["evidence_inputs"] + m["verification_artifacts"] + [
        {"path": m[k + "_path"], "sha256": m[k + "_sha256"]}
        for k in ("source", "pdf", "generator")]
    for row in rows:
        path = Path(row["path"])
        assert not path.is_absolute() and ".." not in path.parts
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == row["sha256"]
    paths = {r["path"] for r in m["evidence_inputs"]}
    for milestone, assessment in (("r9j", "assessment"), ("r9k", "feasibility")):
        for name in ("manifest", "results", assessment):
            assert f"docs/investigations/{milestone}/{name}_v1.json" in paths
    assert "docs/investigations/r9j/completion_manifest_v1.json" in paths
    for path in paths:
        if path.endswith(".json"):
            assert isinstance(json.loads((ROOT / path).read_text()), dict)


def test_nonapproval_generation_has_no_new_authority():
    m = load()
    assert m["manifest_kind"] == "NON_APPROVAL_REPORT_GENERATION"
    assert m["lifecycle_state"] == "PDF_V6_GENERATED_AWAITING_OWNER_ARCHITECTURE_DECISION"
    assert m["recommendation_status"] == "PROPOSED_NOT_APPROVED"
    assert m["owner_review_recorded"] is False
    assert m["execution_authority"] and all(v is False for v in m["execution_authority"].values())
    assert not (ROOT / "docs/project_status/pre_research_review_record_v6.json").exists()


def test_pdf_complete_and_visually_verified():
    m = load()
    pdf = (ROOT / m["pdf_path"]).read_bytes()
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == m["rendered_page_count"] == 5
    assert m["deterministic_render_verified"] is True
    assert m["visual_verification_result"] == "PASS_5_PAGES_NO_MATERIAL_DEFECTS"


def test_freshness_uses_explicit_evidence_not_changed_exclusions():
    m = load()
    policy = json.loads((ROOT / "specs/pre_research_review_policy_v1.json").read_text())
    state = compute_research_state_fingerprint(ROOT, policy)
    assert state["sha256"] == m["research_state_fingerprint"] == "1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef"
    assert state["file_count"] == m["research_state_file_count"] == 252
    assert m["fingerprint_policy_changed"] is False
    assert m["pdf_v5_summarizes_investigations"] is False
    assert "Mechanical research fingerprint equality does not mean PDF v5 summarizes R.9J/R.9K" in source()


def test_all_blockers_and_distinct_evidence_classes_remain_visible():
    text = source()
    for phrase in ("Sidecars and namespace/quiescence", "Target-specific logical read bytes",
                   "Temporary-storage quota", "Returned-row enforcement", "Fetch deadline",
                   "Exact SQL templates", "Explicit attempt ID", "Tested native behavior",
                   "Mocked failure path", "Source inspection", "Untested assumptions",
                   "Solving the read-byte problem alone would not resolve the other blockers",
                   "not working set", "aggregate memory cap", "not a hard real-time guarantee"):
        assert phrase.lower() in text.lower()


def test_options_questions_and_proposed_scope_not_approved():
    text = source()
    for phrase in ("A. Retain cap", "B. Reconsider resource contract", "C. Defer SQLite route",
                   "Resource protection", "Restricting data exposure", "Audit scope",
                   "No specific library is selected or approved", "fail-closed budget exhaustion",
                   "version2.0 remains separate and noncanonical", "Untested scores remain hidden"):
        assert phrase in text
    questions = text.split("### Owner questions - answers pending")[1]
    assert re.findall(r"^(\d+)\. ", questions, re.M) == ["1", "2", "3", "4"]
    assert "would not approve a dependency, implement production access or execute an audit" in questions
    assert "No answers or owner-review record have been recorded for v6" in questions


def test_interlock_and_historical_counts_not_promoted():
    m = load()
    assert m["production_interlock"] == "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE"
    assert m["database_state"] == "LOCATED_AND_SAMPLED_NOT_QUALIFIED"
    boundary = (ROOT / "src/market_intel/foundation/fno_production_boundary.py").read_text()
    assert '"permitted": False' in boundary
    assert m["production_interlock"] in boundary
    assert "Historical verification only" in source()
    assert m["verification"]["native_experiments_rerun"] is False
    assert m["verification"]["broad_suites_run"] is False


def test_no_private_paths_secrets_or_broad_whitespace_exemptions():
    m = load()
    text = source() + MANIFEST.read_text() + (ROOT / m["verification_report"]).read_text()
    assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\\Users\\", text)
    assert not re.search(r"(?i)(api_secret|access_token|password)\s*[:=]\s*\S+", text)
    attrs = (ROOT / ".gitattributes").read_text()
    exceptions = [line for line in attrs.splitlines() if "whitespace=" in line or "-whitespace" in line]
    assert exceptions == ["docs/investigations/r9k/results_v1.json whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol"]
