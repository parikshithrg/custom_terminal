from __future__ import annotations

import ast
import copy
import json
import socket
from pathlib import Path

import pytest

from research_contracts import (
    CANARY_LIFECYCLE_RESULT,
    CANARY_RUNNER_ENTRY_POINT,
    GovernanceCatalog,
    GovernanceError,
    canonical_hash,
    can_promote_lifecycle_result,
    lock_preregistration,
    preview_governed_run,
    register_family,
    register_run_approval,
    review_canary_proposal,
    run_governance_canary,
    seal_approval,
    sha256_file,
    validate_canary_output_directory,
)
from research_contracts.legacy_ledger import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "proposals" / "first_governed_run"
NOW = "2026-08-28T08:00:00+00:00"


def _load(name: str) -> dict:
    return json.loads((PROPOSAL / name).read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return path


def _event_ids():
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"r5-forecast-event-{counter:03d}"

    return next_id


def _preflight(
    *, family_path: Path, prereg_path: Path, input_path: Path,
    approval_path: Path | None, catalog: GovernanceCatalog, root: Path,
) -> dict:
    return preview_governed_run(
        family_path=family_path,
        preregistration_path=prereg_path,
        input_declaration_path=input_path,
        approval_path=approval_path,
        catalog=catalog,
        attempts_root=root / "attempts",
        canonical_catalog_path=root / "canonical.jsonl",
        registered_runner_entry_points=[CANARY_RUNNER_ENTRY_POINT],
        evaluated_at=NOW,
    )


def test_proposal_review_is_read_only_and_quarantined(tmp_path):
    real_catalog = tmp_path / "real_governance.jsonl"
    canonical_catalog = tmp_path / "real_canonical.jsonl"
    before = sorted(str(path) for path in tmp_path.rglob("*"))
    first = review_canary_proposal(PROPOSAL)
    second = review_canary_proposal(PROPOSAL)
    assert first == second
    assert first["proposal_only"] is True
    assert first["execution_authorized"] is False
    assert first["side_effects"] == "NONE"
    assert not real_catalog.exists()
    assert not canonical_catalog.exists()
    assert before == sorted(str(path) for path in tmp_path.rglob("*"))


def test_proposal_objects_are_not_registered_objects_and_approval_cannot_register(tmp_path):
    manifest = _load("proposal_manifest_v1.json")
    assert manifest["registration_status"] == "NOT_REGISTERED"
    assert manifest["preregistration_status"] == "NOT_LOCKED"
    assert manifest["canonical_evidence_status"] == "NONE_CREATED"
    approval = _load("proposed_approval_payload_v1.json")
    catalog = GovernanceCatalog(tmp_path / "catalog.jsonl")
    with pytest.raises(GovernanceError, match="template"):
        register_run_approval(
            approval, approval_root=tmp_path / "approvals", catalog=catalog,
            actor="R5_TEST", timestamp=NOW,
        )
    assert not catalog.path.exists()
    assert not (tmp_path / "approvals").exists()


def test_canary_lifecycle_is_permanently_nonpromotable():
    assert CANARY_LIFECYCLE_RESULT == "INFRASTRUCTURE_CANARY_COMPLETED"
    assert can_promote_lifecycle_result(CANARY_LIFECYCLE_RESULT) is False
    assert _load("expected_output_declaration_v1.json")["promotion_eligible"] is False
    assert _load("family_definition_candidate_v1.json")["retirement_state"] == "PERMANENTLY_NONPROMOTABLE"


def test_runner_is_deterministic_and_accepts_only_exact_synthetic_input(tmp_path):
    prereg = _load("preregistration_candidate_v1.json")
    inputs = _load("synthetic_input_declaration_candidate_v1.json")
    left, right = tmp_path / "left", tmp_path / "right"
    assert run_governance_canary(left, prereg, inputs) == {
        "lifecycle_result": CANARY_LIFECYCLE_RESULT
    }
    assert run_governance_canary(right, prereg, inputs) == {
        "lifecycle_result": CANARY_LIFECYCLE_RESULT
    }
    assert {
        path.name: path.read_bytes() for path in left.iterdir()
    } == {
        path.name: path.read_bytes() for path in right.iterdir()
    }
    expected = _load("expected_output_declaration_v1.json")
    assert validate_canary_output_directory(left, expected)["validation_result"] == "PASS"
    changed = copy.deepcopy(inputs)
    changed["datasets"][0]["snapshot_sha256"] = "0" * 64
    with pytest.raises(GovernanceError, match="fixture hash mismatch"):
        run_governance_canary(tmp_path / "changed", prereg, changed)
    changed = copy.deepcopy(inputs)
    changed["benchmark_version"] = "not_the_declared_canary_contract"
    with pytest.raises(GovernanceError, match="stable input binding mismatch"):
        run_governance_canary(tmp_path / "changed-contract", prereg, changed)
    changed_prereg = copy.deepcopy(prereg)
    changed_prereg["seeds"] = [1]
    with pytest.raises(GovernanceError, match="changed preregistration"):
        run_governance_canary(tmp_path / "changed-prereg", changed_prereg, inputs)


def test_unexpected_or_changed_canary_artifact_fails_validation(tmp_path):
    prereg = _load("preregistration_candidate_v1.json")
    inputs = _load("synthetic_input_declaration_candidate_v1.json")
    output = tmp_path / "output"
    run_governance_canary(output, prereg, inputs)
    (output / "undeclared.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(GovernanceError, match="unexpected"):
        validate_canary_output_directory(output, _load("expected_output_declaration_v1.json"))
    (output / "undeclared.txt").unlink()
    (output / "synthetic_result.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(GovernanceError, match="artifact hash mismatch"):
        validate_canary_output_directory(output, _load("expected_output_declaration_v1.json"))


def test_canary_has_no_network_or_market_provider_dependency(monkeypatch, tmp_path):
    def blocked_socket(*args, **kwargs):
        raise AssertionError("network dependency reached")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    run_governance_canary(
        tmp_path / "offline",
        _load("preregistration_candidate_v1.json"),
        _load("synthetic_input_declaration_candidate_v1.json"),
    )
    tree = ast.parse((ROOT / "src" / "research_contracts" / "canary.py").read_text(encoding="utf-8"))
    imported = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
    }
    assert imported <= {"csv", "json"}
    imported_from = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 0
    }
    assert imported_from <= {"__future__", "pathlib", "typing"}


def test_preflight_forecast_all_six_stages_without_real_side_effects(tmp_path):
    family = _load("family_definition_candidate_v1.json")
    prereg = _load("preregistration_candidate_v1.json")
    inputs = _load("synthetic_input_declaration_candidate_v1.json")
    proposal_catalog = GovernanceCatalog(tmp_path / "forecast.jsonl", event_id_factory=_event_ids())
    family_candidate = PROPOSAL / "family_definition_candidate_v1.json"
    prereg_candidate = PROPOSAL / "preregistration_candidate_v1.json"
    input_candidate = PROPOSAL / "synthetic_input_declaration_candidate_v1.json"

    stage1 = _preflight(
        family_path=family_candidate, prereg_path=prereg_candidate,
        input_path=input_candidate, approval_path=None,
        catalog=proposal_catalog, root=tmp_path,
    )
    categories = {item["category"] for item in stage1["issues"]}
    assert {"FAMILY_NOT_REGISTERED", "PREREGISTRATION_NOT_LOCKED", "RUN_APPROVAL_MISSING"} <= categories

    family_path, _ = register_family(
        family, registry_root=tmp_path / "families", catalog=proposal_catalog,
        actor="R5_TEMP_FORECAST", timestamp=NOW,
    )
    stage2 = _preflight(
        family_path=family_path, prereg_path=prereg_candidate, input_path=input_candidate,
        approval_path=None, catalog=proposal_catalog, root=tmp_path,
    )
    categories = {item["category"] for item in stage2["issues"]}
    assert "FAMILY_NOT_REGISTERED" not in categories
    assert {"PREREGISTRATION_NOT_LOCKED", "RUN_APPROVAL_MISSING"} <= categories

    prereg_path, prereg_hash = lock_preregistration(
        prereg, family_path=family_path, prereg_root=tmp_path / "preregistrations",
        catalog=proposal_catalog, actor="R5_TEMP_FORECAST", timestamp=NOW,
    )
    input_path = _write(tmp_path / "inputs.json", inputs)
    stage3 = _preflight(
        family_path=family_path, prereg_path=prereg_path, input_path=input_path,
        approval_path=None, catalog=proposal_catalog, root=tmp_path,
    )
    assert {item["category"] for item in stage3["issues"]} == {"RUN_APPROVAL_MISSING"}

    approval = seal_approval({
        "approval_schema_version": "governed_run_approval_v1",
        "approval_id": "r5-temporary-forecast-only",
        "family_id": family["family_id"], "family_version": family["version"],
        "experiment_id": prereg["experiment_id"], "experiment_version": prereg["version"],
        "experiment_specification_sha256": prereg_hash,
        "preregistration_sha256": prereg_hash,
        "input_declaration_sha256": canonical_hash(inputs),
        "allowed_dataset_snapshots": [{
            "dataset_id": item["dataset_id"], "version": item["version"],
            "snapshot_sha256": item["snapshot_sha256"],
        } for item in inputs["datasets"]],
        "permitted_split_access": ["train"],
        "maximum_compute_budget": {"wall_time_seconds": 5, "memory_mb": 64, "attempts": 1},
        "compute_budget_enforcement": {
            "attempts": "ENFORCED_BY_ONE_TIME_APPROVAL",
            "wall_time_seconds": "DECLARED_NOT_ENFORCED",
            "memory_mb": "DECLARED_NOT_ENFORCED",
        },
        "authorized_gateway_action": "GovernedExecutionGateway.run",
        "issued_at": "2026-08-28T07:50:00+00:00",
        "expires_at": "2026-08-28T08:20:00+00:00",
        "one_time_use_status": "UNUSED_AT_ISSUE",
        "approving_identity": "R5_TEMP_TEST_ONLY",
        "approval_reason": "temporary forecast simulation; not real authorization",
        "template_only": False,
    })
    approval_path, approval_hash = register_run_approval(
        approval, approval_root=tmp_path / "approvals", catalog=proposal_catalog,
        actor="R5_TEMP_FORECAST", timestamp=NOW,
    )
    stage4 = _preflight(
        family_path=family_path, prereg_path=prereg_path, input_path=input_path,
        approval_path=approval_path, catalog=proposal_catalog, root=tmp_path,
    )
    assert stage4["execution_permitted"] is True
    assert stage4["approval"]["status"] == "VALID_UNUSED"

    authorization = proposal_catalog.append(
        event_type="RUN_AUTHORIZED", actor_classification="R5_TEMP_FORECAST",
        object_refs={
            "run_attempt_id": "forecast-only-attempt", "experiment_key": "governance_canary_execution_v1__v1",
            "family_key": "governance_canary__v1", "split": "train",
            "approval_id": approval["approval_id"],
        },
        object_hashes={
            "preregistration_sha256": prereg_hash,
            "family_sha256": sha256_file(family_path),
            "input_declaration_sha256": canonical_hash(inputs),
            "approval_sha256": approval_hash,
        },
        reason="temporary preflight forecast only", resulting_state="AUTHORIZED", timestamp=NOW,
    )
    proposal_catalog.append(
        event_type="RUN_STARTED", actor_classification="R5_TEMP_FORECAST",
        object_refs={
            "run_attempt_id": "forecast-only-attempt",
            "experiment_key": "governance_canary_execution_v1__v1",
            "family_key": "governance_canary__v1", "approval_id": approval["approval_id"],
        },
        object_hashes={
            "authorization_event_sha256": authorization["event_sha256"],
            "approval_sha256": approval_hash,
        },
        reason="temporary consumption forecast; runner not invoked",
        resulting_state="RUNNING", timestamp=NOW,
    )
    stage5 = _preflight(
        family_path=family_path, prereg_path=prereg_path, input_path=input_path,
        approval_path=approval_path, catalog=proposal_catalog, root=tmp_path,
    )
    assert stage5["approval"]["status"] == "INVALID"
    assert "already been consumed" in json.dumps(stage5["issues"])
    stage6 = _preflight(
        family_path=family_path, prereg_path=prereg_path, input_path=input_path,
        approval_path=approval_path, catalog=proposal_catalog, root=tmp_path,
    )
    assert stage6 == stage5
    assert not (tmp_path / "attempts").exists()
    assert not (tmp_path / "canonical.jsonl").exists()


def test_future_exact_approval_remains_mandatory():
    catalog = GovernanceCatalog(PROPOSAL / "does-not-exist-governance.jsonl")
    preview = _preflight(
        family_path=PROPOSAL / "family_definition_candidate_v1.json",
        prereg_path=PROPOSAL / "preregistration_candidate_v1.json",
        input_path=PROPOSAL / "synthetic_input_declaration_candidate_v1.json",
        approval_path=PROPOSAL / "proposed_approval_payload_v1.json",
        catalog=catalog, root=PROPOSAL / "does-not-exist-runtime",
    )
    assert preview["execution_permitted"] is False
    assert preview["approval"]["status"] == "INVALID"
    assert not catalog.path.exists()
    assert not (PROPOSAL / "does-not-exist-runtime").exists()


def test_entrypoint_inventory_delta_is_exact_and_has_no_unsafe_bypass():
    base = json.loads((ROOT / "specs" / "laboratory_entrypoint_inventory_v1.json").read_text())
    delta = json.loads((ROOT / "specs" / "research_r5_entrypoint_delta_v1.json").read_text())
    assert base["unsafe_bypass_count"] == 0
    assert delta["effective_totals"]["UNSAFE_BYPASS"] == 0
    assert delta["effective_totals"]["TOTAL"] == (
        len(base["executable_paths"]) + len(base["callable_entrypoints"])
        + len(delta["added_callable_entrypoints"])
    )
    entry = delta["added_callable_entrypoints"][0]
    assert (ROOT / entry["path"]).is_file()
    assert entry["classification"] == "DEVELOPMENT_ONLY_NONCANONICAL"
