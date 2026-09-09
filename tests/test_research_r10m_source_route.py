"""Offline checks for the non-executable R10M source-route decision."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10m/source_route_v1"
ALLOWED = {"PASS", "PARTIAL", "FAIL", "UNKNOWN", "NOT_APPLICABLE", "REQUIRES_SEPARATE_AUTHORIZATION"}


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True, capture_output=True
    ).stdout


def test_capability_matrix_is_provider_neutral_and_cited() -> None:
    matrix = load("source_capability_matrix.json")
    sources = {row["id"] for row in load("official_source_inventory.json")["sources"]}
    assert matrix["decision"] == "HYBRID_FNO_ROUTE_RECOMMENDED"
    assert len(matrix["routes"]) == 5
    for route in matrix["routes"]:
        assert set(route["capabilities"].values()) <= ALLOWED
        assert set(route["evidence_ids"]) <= sources
        if "PASS" in route["capabilities"].values():
            assert route["evidence_ids"] or route["id"] == "EXISTING_LOCAL_FNO_DATABASE"


def test_official_inventory_uses_direct_https_sources() -> None:
    inventory = load("official_source_inventory.json")
    for source in inventory["sources"]:
        assert source["url"].startswith("https://")
        assert source["access"] in ALLOWED and source["retention"] in ALLOWED
    assert inventory["method"] == "DOCUMENTATION_ONLY_NO_LIVE_DATA_CALLS_OR_BULK_ACQUISITION"


def test_local_route_timebox_fails_without_sunk_cost_exception() -> None:
    value = load("local_route_timebox_decision.json")
    assert value["decision"] == "DEFER_OR_ABANDON_LOCAL_FNO_DATABASE_ROUTE"
    assert value["remaining_synthetic_implementation_milestones"] == 0
    assert not all(value["conditions"].values())
    assert value["sunk_cost_used_as_decision_factor"] is False
    assert value["database_opened"] is False


def test_stable_snapshot_requires_more_than_discrete_checks() -> None:
    value = load("stable_snapshot_decision.json")
    assert value["decision"] == "NO_DEFENSIBLE_CURRENT_STABLE_SNAPSHOT_MECHANISM"
    rows = {row["mechanism"]: row for row in value["candidates"]}
    assert rows["before-and-after identity checks"]["status"] == "FAIL"
    assert rows["owner-supplied immutable external snapshot"]["status"] == "REQUIRES_SEPARATE_AUTHORIZATION"
    assert value["database_opened"] is False


def test_calibration_is_exactly_derived_from_retained_synthetic_results() -> None:
    value = load("synthetic_resource_calibration.json")
    r9p = json.loads((ROOT / "docs/investigations/r9p/results_v1.json").read_text())
    observed = [
        {"page_size": row["page_size"], "fixture_bytes": row["bytes"], "logical_read_bytes": row["requested"], "returned_rows": row["rows"]}
        for row in r9p["layouts"]
    ]
    assert value["observations"] == observed
    assert value["proposed_metadata_only_limits"]["minimum_useful_logical_read_bytes"] < value["proposed_metadata_only_limits"]["maximum_safe_logical_read_bytes"]
    assert value["real_target_applicability"] == "UNKNOWN_UNTIL_SCHEMA_AND_INDEXES_ARE_KNOWN"
    assert value["calibration_conclusion"] == "DOES_NOT_SUPPORT_USEFUL_BOUNDED_REAL_QUALIFICATION"
    assert any(not row["bounded_without_real_schema"] for row in value["questions"])


def test_apsw_was_reviewed_but_not_installed_or_adopted() -> None:
    value = load("apsw_dependency_review.json")
    assert value["review_type"] == "NON_INSTALLING"
    assert value["installed_or_adopted"] is False
    assert value["candidate"]["sha256"] == "13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5"
    assert value["previously_demonstrated"] and value["unverified_production_assumptions"]


def test_feature_mapping_keeps_unsupported_features_hidden_or_deferred() -> None:
    value = load("website_feature_source_mapping.json")
    rows = {row["feature"]: row["state"] for row in value["features"]}
    assert rows["current option chain"] == "supportable"
    assert rows["historical option-chain replay"] == "remove/defer"
    assert rows["daily expired-option history"] == "hidden pending evidence"
    assert rows["derivatives breadth or sentiment"] == "mock-only"
    assert value["calculations_performed"] is False


def test_r9l_reconciliation_uses_historical_tree_and_limited_current_authority() -> None:
    value = load("r9l_v6_reconciliation.json")
    assert hashlib.sha256(git_bytes("d0102dc", "tests/test_research_r9l_pdf_v6.py")).hexdigest() == value["historical_test_sha256"]
    missing = subprocess.run(
        ["git", "cat-file", "-e", "d0102dc:docs/project_status/pre_research_review_record_v6.json"],
        cwd=ROOT,
        capture_output=True,
    )
    assert missing.returncode != 0
    assert value["new_scope_authorized_by_old_review"] is False
    assert value["global_pytest_collection_hook_removed"] is True
    assert not (ROOT / "tests/conftest.py").exists()


def test_paid_routes_are_excluded_and_permission_is_not_quality() -> None:
    value = load("free_vs_paid_boundary.json")
    assert value["paid_excluded"] is True
    assert value["permission_is_not_data_quality_evidence"] is True


def test_completion_and_manifest_are_deterministic() -> None:
    completion = load("completion.json")
    manifest = load("root_manifest.json")
    assert completion["completion_decision"] == "HYBRID_FNO_ROUTE_RECOMMENDED"
    assert completion["local_database_opened"] is False
    assert completion["apsw_installed_or_adopted"] is False
    for relative, expected in manifest["artifact_hashes"].items():
        assert sha(ROOT / relative) == expected
    body = dict(manifest)
    expected = body.pop("payload_sha256")
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    assert hashlib.sha256(canonical.encode()).hexdigest() == expected
