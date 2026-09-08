from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from market_intel.foundation import fno_production_boundary as boundary
from tools.r10k_preaccess_gate import (
    ATTEMPT_ID,
    BOUND_HASHES,
    NEXT_MILESTONE,
    OVERALL_VERDICT,
    build_capability_matrix,
    declared_resources,
    evaluate_preaccess_gate,
    render_report,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10k/stage1_attempt_v1"


def _load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preaccess_gate_reproduces_committed_evidence() -> None:
    actual = evaluate_preaccess_gate(ROOT)
    assert actual == _load("approval_gate.json")
    assert actual["gate_decision"] == OVERALL_VERDICT
    assert actual["database_opened"] is False
    assert actual["locator_resolved"] is False
    assert actual["approval_consumed"] is False


def test_r10j_and_binding_inputs_are_exactly_hash_bound() -> None:
    gate = _load("approval_gate.json")
    assert gate["bound_hashes"] == BOUND_HASHES
    for relative, expected in BOUND_HASHES.items():
        assert _sha(ROOT / relative) == expected
        assert gate["actual_hashes"][relative] == expected


def test_owner_approval_is_valid_but_does_not_override_safety_failures() -> None:
    gates = _load("approval_gate.json")["gates"]
    for name in (
        "separate_owner_decisions", "exact_scope_authorized",
        "prohibited_actions_remain_unauthorized",
    ):
        assert gates[name] == "PASS"
    for name in (
        "usable_production_locator_contract",
        "usable_exact_one_use_production_approval",
        "exact_attempt_id_bound_in_approval",
        "usable_production_activation",
        "production_interlocks_permit_access",
        "target_specific_logical_read_budget_enforced",
        "sidecar_consistency_policy_resolved",
    ):
        assert gates[name] == "FAIL"


def test_production_boundary_remains_deliberately_impossible() -> None:
    values = {
        name: True for name in boundary.ProductionInterlockEvidence.__dataclass_fields__
    }
    values["deliberate_r9d_interlock_removed_by_reviewed_commit"] = False
    evidence = boundary.ProductionInterlockEvidence(**values)
    result = boundary.evaluate_production_interlocks(evidence)
    assert result["permitted"] is False
    assert boundary.DELIBERATE_INTERLOCK in result["failures"]
    assert result["database_access_authorized"] is False


def test_attempt_is_registered_once_and_never_consumed() -> None:
    registration = _load("attempt_registration.json")
    consumption = _load("approval_consumption_record.json")
    assert registration["attempt_id"] == ATTEMPT_ID
    assert registration["attempt_id_prior_occurrence_count"] == 0
    assert registration["terminal_state"] == "ABORTED_PRE_ACCESS_SAFETY_BOUNDARY"
    assert consumption["exact_production_one_use_approval_present"] is False
    assert consumption["durable_production_registration_present"] is False
    assert consumption["consumed"] is False


def test_resource_ledger_proves_zero_target_use() -> None:
    expected = declared_resources()
    actual = _load("resource_ledger.json")
    assert actual == expected
    assert all(value == 0 for value in actual["actual"].values())
    access = _load("database_access_result.json")
    assert access["database_file_opened"] is False
    assert access["sqlite_connection_opened"] is False
    assert access["database_unchanged_claim"] == "NOT_MADE_TARGET_NOT_ACCESSED"


def test_capabilities_are_not_inferred_after_preaccess_abort() -> None:
    matrix = _load("capability_matrix.json")
    assert matrix == build_capability_matrix()
    allowed = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE", "NOT_TESTED_SAFETY_BOUNDARY"}
    assert set(matrix["results"].values()) <= allowed
    assert matrix["results"]["read_only_safety"] == "FAIL"
    verdict = _load("qualification_verdict.json")
    assert verdict["overall_verdict"] == OVERALL_VERDICT
    assert verdict["recommended_next_milestone"] == NEXT_MILESTONE
    assert verdict["next_milestone_authorized"] is False


def test_report_is_deterministically_derived_and_has_no_private_path() -> None:
    gate = evaluate_preaccess_gate(ROOT)
    expected = render_report(gate, build_capability_matrix(), declared_resources())
    report = (ROOT / "reports/LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1.md").read_text(encoding="utf-8")
    assert report == expected
    assert OVERALL_VERDICT in report and NEXT_MILESTONE in report
    assert "database was not opened" in report
    combined = report + "\n" + "\n".join(path.read_text(encoding="utf-8") for path in RUN.glob("*"))
    assert not re.search(r"[A-Za-z]:[\\/]", combined)
    assert not re.search(r"[/\\](?:Users|home)[/\\]", combined, re.I)


def test_lifecycle_is_terminal_without_database_or_research_events() -> None:
    events = [json.loads(line) for line in (RUN / "lifecycle_events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [item["sequence"] for item in events] == [1, 2, 3, 4]
    assert events[-1]["event"] == "AUDIT_ABORTED"
    assert not {"DATABASE_OPENED", "SQL_ATTEMPTED", "RESEARCH_STARTED"} & {item["event"] for item in events}


def test_preaccess_evaluator_has_no_database_or_locator_entrypoint() -> None:
    source = (ROOT / "tools/r10k_preaccess_gate.py").read_text(encoding="utf-8")
    for prohibited in (
        "import sqlite3", "from sqlite3", "config.toml", "paths.fno_db",
        "requests.", "urllib.", "socket.", "connect(",
    ):
        assert prohibited not in source
    assert "if __name__" not in source


def test_completion_and_manifest_validate() -> None:
    completion = _load("completion.json")
    manifest = _load("root_manifest.json")
    assert completion["overall_qualification_verdict"] == OVERALL_VERDICT
    assert completion["database_opened"] is False
    assert completion["recommended_next_milestone"] == NEXT_MILESTONE
    for relative, expected in manifest["artifact_hashes"].items():
        assert _sha(ROOT / relative) == expected
    body = dict(manifest)
    expected_payload = body.pop("payload_sha256")
    assert hashlib.sha256(
        (json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    ).hexdigest() == expected_payload
