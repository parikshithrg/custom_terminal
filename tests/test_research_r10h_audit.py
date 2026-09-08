from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/investigations/r10h/audit_v1"


def _load(name: str):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_manifest_binds_every_output():
    manifest = _load("audit_manifest.json")
    for relative, expected in manifest["outputs"].items():
        path = ROOT / relative if relative.startswith("reports/") else AUDIT / relative
        assert _sha(path) == expected


def test_all_r10_evidence_hashes_and_chain_verified():
    evidence = _load("evidence_inventory.json")
    assert evidence["verification"] == {
        "artifact_hashes_failed": 0,
        "artifact_hashes_passed": 208,
        "parquet_objects_readable": 34,
        "predecessor_mismatches": 0,
    }
    assert len(evidence["milestones"]) == 7
    assert all(row["classification"] == "SYNTHETIC_ONLY_NONCANONICAL" for row in evidence["milestones"])
    assert all(row["promotion_eligible"] is False for row in evidence["milestones"])


def test_hash_kinds_are_not_conflated_and_r10a_limitation_is_explicit():
    evidence = _load("evidence_inventory.json")
    assert set(evidence["hash_semantics"]) == {"byte_hash", "logical_table_hash", "reproducible_core_hash", "source_tree_hash", "research_state_fingerprint"}
    r10a = evidence["milestones"][0]
    assert r10a["clean_execution_start"] is False
    assert "dirty" in r10a["clean_execution_note"].lower()


def test_governance_diagnostics_are_not_hidden_or_weakened():
    governance = _load("governance_diagnostic_reconciliation.json")
    assert governance["root_suite"] == {"failed": 9, "passed": 704, "skipped": 4, "warnings": 2}
    assert len(governance["diagnostics"]) == 9
    assert sum(x["category"] == "INTENDED_HISTORICAL_GATE_NOW_STALE" for x in governance["diagnostics"]) == 8
    assert sum(x["category"] == "GENUINE_FORWARD_INVENTORY_REGRESSION" for x in governance["diagnostics"]) == 1
    assert governance["forward_remediation_required_before_pdf"] is True


def test_entrypoint_and_production_boundaries_remain_explicit():
    inventory = _load("entrypoint_capability_inventory.json")
    assert len(inventory["entrypoints"]) == 14
    assert inventory["production_apsw_dependency"] is False
    assert inventory["production_interlock"]["status"] == "UNCHANGED_ACTIVE"
    assert all(not row["network"] and not row["brokers"] and not row["promotes_lifecycle"] for row in inventory["entrypoints"])


def test_readiness_is_conditional_and_authorizes_nothing():
    result = _load("readiness_decision.json")
    assert result["completion_decision"] == "SYNTHETIC_PLATFORM_CONDITIONALLY_READY_REMEDIATIONS_REQUIRED"
    assert result["pdf_generation_ready"] is False
    assert result["authorizes"] == []
    assert len(result["required_remediations"]) == 2


def test_real_data_routes_do_not_claim_research_readiness():
    routes = _load("real_data_readiness_matrix.json")["routes"]
    assert all(row["overall"] != "READY" for row in routes)
    kite = next(row for row in routes if row["route"] == "KITE_CURRENT_DATA_API")
    assert kite["dimensions"]["historical_population"] == "NOT_APPLICABLE"
    amfi = next(row for row in routes if row["route"] == "AMFI")
    assert amfi["overall"] == "NOT_APPLICABLE"
