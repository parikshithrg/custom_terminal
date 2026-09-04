"""Offline static evidence tests; candidate runtime is deliberately separate."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/investigations/r9m"


def result():
    return json.loads((BASE / "results_v1.json").read_text())


def test_scope_clarification_does_not_adopt_dependency_or_enable_production():
    scope = json.loads((BASE / "owner_scope_v1.json").read_text())
    assert scope["owner_clarification"] == "begin the evaluation"
    assert scope["real_database_route"] == "DEFERRED"
    assert scope["resource_requirements_changed"] is False
    assert scope["authority"]["bounded_synthetic_evaluation"] is True
    assert all(not v for k, v in scope["authority"].items() if k != "bounded_synthetic_evaluation")


def test_real_read_observations_enforce_predelegation_limits():
    r = result()
    for case in r["cases"].values():
        assert case["delegated"] <= case["limit"]
        assert case["delegated"] == sum(e[0] for e in case["read_events"])
    for name in ("zero", "small", "one_under_observed", "late_sidecar"):
        assert r["cases"][name]["published_rows"] == 0
        assert r["cases"][name]["error"] == "IOError"
    assert r["cases"]["exact_observed"]["published_rows"] == 1
    assert r["direct_repeated_exact_sticky"] == {"delegated": 32, "rejections": 2}


def test_mapping_restricted_and_sidecar_claim_narrow():
    r = result()
    assert r["native_mmap_control"] == [[16777216]]
    assert r["cases"]["mmap_requested"]["mmap"] == {"readback": [], "set_result": []}
    assert r["direct_forbidden_opens_rejected"] == 4
    report = (ROOT / "reports/RESEARCH_R9M_REPORT.md").read_text()
    assert "No xFetch interception was implemented or proven" in report
    assert "only a checkpoint" in report


def test_header_names_preserve_existing_nse_parser_but_not_fo_claim():
    r = result()
    source = (ROOT / "src/market_intel/foundation/nse_population_normalization.py").read_text()
    assert all(name in source for name in r["headers"])
    assert "not F&O UDiFF" in r["header_provenance"]
    assert r["fixture_unchanged"] and r["temporary_fixture_removed"]
    assert r["fixture_bytes"] < 128 * 1024


def test_manifest_bindings_and_no_production_dependency():
    m = json.loads((BASE / "manifest_v1.json").read_text())
    for row in m["artifacts"]:
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]
    assert "apsw" not in (ROOT / "pyproject.toml").read_text().lower()
    assert m["dependency_adopted"] is False
    assert m["production_interlock"] == "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE"


def test_no_private_inputs_and_sanitized_artifacts():
    tool = (ROOT / "tools/r9m_vfs_evaluation.py").read_text()
    for forbidden in ("config.toml", "raw_binding", "getenv", "read_csv", "requests."):
        assert forbidden not in tool
    assert "No arguments accepted; synthetic fixture only" in tool
    for path in BASE.iterdir():
        text = path.read_text()
        assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\\Users\\", text)
        assert not re.search(r"(?i)(api_secret|access_token|password)\s*[:=]\s*\S+", text)
