from __future__ import annotations

import copy
import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from market_intel.foundation.future_evidence import (
    CanonicalFutureEvidenceCatalog,
    validate_governed_bundle,
)
from research_contracts import (
    GovernedAbort,
    GovernedExecutionGateway,
    GovernanceCatalog,
    GovernanceError,
    authorize_split_access,
    canonical_hash,
    lock_preregistration,
    mark_development_output,
    preview_governed_run,
    register_family,
    register_run_approval,
    seal_approval,
)
from research_contracts.legacy_ledger import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "research_r3"
NOW = "2026-01-01T00:00:00+00:00"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return path


def _event_ids():
    counter = 0
    def next_id():
        nonlocal counter
        counter += 1
        return f"r4-event-{counter:03d}"
    return next_id


def _runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    (temp / "predictions.csv").write_text("id,value\nA,1\n", encoding="utf-8")
    (temp / "evidence.json").write_bytes(canonical_json_bytes({"synthetic": True}))
    return {"lifecycle_result": "TRAIN_REJECTED"}


def _failed_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    (temp / "predictions.csv").write_text("id,value\nA,1\n", encoding="utf-8")
    raise RuntimeError("details must remain sanitized")


def _aborted_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    raise GovernedAbort("synthetic abort")


def _setup(tmp_path: Path, *, split: str = "train", runner=_runner,
           permitted_splits: list[str] | None = None):
    family = _load("synthetic_family_v1.json")
    prereg = _load("synthetic_preregistration_v1.json")
    inputs = _load("synthetic_input_declaration_v1.json")
    prereg["split_requested"] = split
    prereg["code_entry_point"] = "synthetic:runner"
    inputs["dataset_split_version"] = f"synthetic_{split}_v1"
    catalog = GovernanceCatalog(tmp_path / "governance.jsonl", event_id_factory=_event_ids())
    family_path, _ = register_family(
        family, registry_root=tmp_path / "families", catalog=catalog,
        actor="SYNTHETIC_TEST", timestamp=NOW,
    )
    prereg_path, prereg_hash = lock_preregistration(
        prereg, family_path=family_path, prereg_root=tmp_path / "preregistrations",
        catalog=catalog, actor="SYNTHETIC_TEST", timestamp=NOW,
    )
    input_path = _write(tmp_path / "inputs.json", inputs)
    if split != "train":
        authorize_split_access(
            catalog=catalog, family=family, prereg=prereg,
            preregistration_sha256=prereg_hash,
            dataset_split_version=inputs["dataset_split_version"], split=split,
            reason="synthetic split authorization", actor="SYNTHETIC_TEST",
            timestamp=NOW, authorization_id=f"{split}-authorization",
        )
    approval = seal_approval({
        "approval_schema_version": "governed_run_approval_v1",
        "approval_id": "synthetic-r4-approval",
        "family_id": family["family_id"], "family_version": family["version"],
        "experiment_id": prereg["experiment_id"], "experiment_version": prereg["version"],
        "experiment_specification_sha256": prereg_hash,
        "preregistration_sha256": prereg_hash,
        "input_declaration_sha256": canonical_hash(inputs),
        "allowed_dataset_snapshots": [{
            "dataset_id": item["dataset_id"], "version": item["version"],
            "snapshot_sha256": item["snapshot_sha256"],
        } for item in inputs["datasets"]],
        "permitted_split_access": permitted_splits if permitted_splits is not None else [split],
        "maximum_compute_budget": {"wall_time_seconds": 60, "memory_mb": 256, "attempts": 1},
        "compute_budget_enforcement": {
            "attempts": "ENFORCED_BY_ONE_TIME_APPROVAL",
            "wall_time_seconds": "DECLARED_NOT_ENFORCED",
            "memory_mb": "DECLARED_NOT_ENFORCED",
        },
        "authorized_gateway_action": "GovernedExecutionGateway.run",
        "issued_at": "2025-01-01T00:00:00+00:00",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "one_time_use_status": "UNUSED_AT_ISSUE",
        "approving_identity": "SYNTHETIC_LOCAL_USER",
        "approval_reason": "synthetic R.4 contract test only",
        "template_only": False,
    })
    approval_path, _ = register_run_approval(
        approval, approval_root=tmp_path / "approvals", catalog=catalog,
        actor="SYNTHETIC_TEST", timestamp=NOW,
    )
    gateway = GovernedExecutionGateway(
        catalog=catalog, attempts_root=tmp_path / "attempts",
        runner_registry={"synthetic:runner": runner}, actor="SYNTHETIC_TEST",
        clock=lambda: NOW, attempt_id_factory=lambda: "r4-attempt-001",
        approval_path=approval_path,
    )
    return locals()


def _preview(ctx: dict, approval_path: Path | None = None):
    return preview_governed_run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
        approval_path=ctx["approval_path"] if approval_path is None else approval_path,
        catalog=ctx["catalog"], attempts_root=ctx["tmp_path"] / "attempts",
        canonical_catalog_path=ctx["tmp_path"] / "canonical.jsonl",
        registered_runner_entry_points=["synthetic:runner"], evaluated_at=NOW,
    )


def test_preflight_is_deterministic_side_effect_free_and_does_not_consume_approval(tmp_path):
    ctx = _setup(tmp_path)
    before = ctx["catalog"].path.read_bytes()
    first = _preview(ctx); second = _preview(ctx)
    assert first == second
    assert first["execution_permitted"] is True
    assert first["approval"]["status"] == "VALID_UNUSED"
    assert first["side_effects"] == "NONE"
    assert ctx["catalog"].path.read_bytes() == before
    assert not (tmp_path / "attempts").exists()


def test_missing_approval_fails_closed_in_preflight_and_gateway(tmp_path):
    ctx = _setup(tmp_path)
    result = preview_governed_run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"], approval_path=None,
        catalog=ctx["catalog"], attempts_root=tmp_path / "attempts",
        canonical_catalog_path=tmp_path / "canonical.jsonl",
        registered_runner_entry_points=["synthetic:runner"], evaluated_at=NOW,
    )
    assert result["execution_permitted"] is False
    assert result["approval"]["status"] == "MISSING"
    ctx["gateway"].approval_path = None
    with pytest.raises(GovernanceError, match="approval is required"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )


@pytest.mark.parametrize("mutation,match", [
    (lambda value: value.update({"approval_reason": "altered"}), "payload hash"),
    (lambda value: value.update({"expires_at": "2025-06-01T00:00:00+00:00"}), "payload hash"),
])
def test_altered_approval_fails_closed(tmp_path, mutation, match):
    ctx = _setup(tmp_path)
    altered = copy.deepcopy(ctx["approval"]); mutation(altered)
    altered_path = _write(tmp_path / "altered.json", altered)
    with pytest.raises(GovernanceError, match=match):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"], approval_path=altered_path,
        )


def test_expired_but_unaltered_approval_fails(tmp_path):
    ctx = _setup(tmp_path)
    expired = copy.deepcopy(ctx["approval"])
    expired["expires_at"] = "2025-06-01T00:00:00+00:00"
    expired["approval_id"] = "expired-approval"
    expired = seal_approval(expired)
    expired_path, _ = register_run_approval(
        expired, approval_root=tmp_path / "approvals", catalog=ctx["catalog"],
        actor="SYNTHETIC_TEST", timestamp=NOW,
    )
    with pytest.raises(GovernanceError, match="not currently valid"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"], approval_path=expired_path,
        )


def test_changing_inputs_invalidates_approval(tmp_path):
    ctx = _setup(tmp_path)
    changed = copy.deepcopy(ctx["inputs"])
    changed["datasets"][0]["snapshot_sha256"] = "b" * 64
    changed_path = _write(tmp_path / "changed-inputs.json", changed)
    with pytest.raises(GovernanceError, match="input-declaration hash"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=changed_path,
        )


def test_changed_family_or_preregistration_cannot_start(tmp_path):
    family_ctx = _setup(tmp_path / "family")
    changed_family = copy.deepcopy(family_ctx["family"])
    changed_family["allowed_diagnostic_scope"] = ["changed-after-registration"]
    _write(family_ctx["family_path"], changed_family)
    with pytest.raises(GovernanceError, match="exact registered family"):
        family_ctx["gateway"].run(
            family_path=family_ctx["family_path"], preregistration_path=family_ctx["prereg_path"],
            input_declaration_path=family_ctx["input_path"],
        )

    prereg_ctx = _setup(tmp_path / "prereg")
    changed_prereg = copy.deepcopy(prereg_ctx["prereg"])
    changed_prereg["selection_rule"] = "changed after lock"
    _write(prereg_ctx["prereg_path"], changed_prereg)
    with pytest.raises(GovernanceError, match="locked preregistration"):
        prereg_ctx["gateway"].run(
            family_path=prereg_ctx["family_path"], preregistration_path=prereg_ctx["prereg_path"],
            input_declaration_path=prereg_ctx["input_path"],
        )


def test_unregistered_approval_and_runner_mismatch_fail_closed(tmp_path):
    ctx = _setup(tmp_path)
    unregistered = copy.deepcopy(ctx["approval"])
    unregistered["approval_id"] = "not-registered"
    unregistered = seal_approval(unregistered)
    unregistered_path = _write(tmp_path / "unregistered.json", unregistered)
    with pytest.raises(GovernanceError, match="exact registered user approval"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"], approval_path=unregistered_path,
        )

    mismatched_gateway = GovernedExecutionGateway(
        catalog=ctx["catalog"], attempts_root=tmp_path / "attempts-other",
        runner_registry={}, actor="SYNTHETIC_TEST", clock=lambda: NOW,
        approval_path=ctx["approval_path"],
    )
    with pytest.raises(GovernanceError, match="runner entry point is not registered"):
        mismatched_gateway.run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )


def test_artifact_destinations_cannot_escape_attempt_directory():
    prereg = _load("synthetic_preregistration_v1.json")
    prereg["expected_artifacts"][0]["relative_path"] = "../escape.csv"
    from research_contracts import validate_preregistration
    with pytest.raises(GovernanceError, match="inside the attempt directory"):
        validate_preregistration(prereg)


def test_validation_only_approval_cannot_expose_test_split(tmp_path):
    ctx = _setup(tmp_path, split="test", permitted_splits=["validation"])
    with pytest.raises(GovernanceError, match="does not permit"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )


def test_unapproved_validation_runner_cannot_start(tmp_path):
    ctx = _setup(tmp_path, split="validation")
    events = [e for e in ctx["catalog"].events() if e["event_type"] != "VALIDATION_ACCESS_GRANTED"]
    ctx["catalog"].path.write_bytes(b"".join(canonical_json_bytes(e) for e in events[:3]))
    with pytest.raises(GovernanceError, match="validation access"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )


def test_approval_is_consumed_once_and_reuse_fails(tmp_path):
    ctx = _setup(tmp_path)
    args = dict(family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
                input_declaration_path=ctx["input_path"])
    ctx["gateway"].run(**args)
    with pytest.raises(GovernanceError, match="already been consumed"):
        ctx["gateway"].run(**args)


def test_approval_registration_is_idempotent(tmp_path):
    ctx = _setup(tmp_path)
    before = len(ctx["catalog"].events())
    path, _ = register_run_approval(
        ctx["approval"], approval_root=tmp_path / "approvals", catalog=ctx["catalog"],
        actor="SYNTHETIC_TEST", timestamp=NOW,
    )
    assert path == ctx["approval_path"]
    assert len(ctx["catalog"].events()) == before


def test_crash_before_start_event_leaves_approval_unconsumed(monkeypatch, tmp_path):
    ctx = _setup(tmp_path)
    original_append = ctx["catalog"].append

    def fail_before_start(**kwargs):
        if kwargs.get("event_type") == "RUN_STARTED":
            raise RuntimeError("synthetic crash before atomic start/consumption event")
        return original_append(**kwargs)

    monkeypatch.setattr(ctx["catalog"], "append", fail_before_start)
    with pytest.raises(RuntimeError, match="before atomic start"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )
    assert not any(
        event["event_type"] == "RUN_STARTED"
        and event["object_refs"].get("approval_id") == ctx["approval"]["approval_id"]
        for event in ctx["catalog"].events()
    )
    monkeypatch.setattr(ctx["catalog"], "append", original_append)
    ctx["gateway"].attempt_id_factory = lambda: "r4-attempt-002"
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    assert bundle.name == "r4-attempt-002"


@pytest.mark.parametrize("runner,status", [
    (_runner, "COMPLETED"), (_failed_runner, "FAILED"), (_aborted_runner, "ABORTED")
])
def test_every_started_attempt_retains_approval_reference(tmp_path, runner, status):
    ctx = _setup(tmp_path, runner=runner)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["completion_status"] == status
    assert manifest["run_approval_reference"]["approval_id"] == ctx["approval"]["approval_id"]
    validation = validate_governed_bundle(
        bundle_path=bundle, family_path=ctx["family_path"],
        preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
    )
    assert validation["promotion_eligible"] is False


def test_development_runner_warns_marks_output_and_cannot_import(tmp_path):
    output = tmp_path / "development"
    with pytest.warns(RuntimeWarning, match="UNGOVERNED_NONCANONICAL_OUTPUT"):
        marker = mark_development_output(output, entrypoint="synthetic direct runner")
    assert json.loads(marker.read_text())["classification"] == "UNGOVERNED_NONCANONICAL_OUTPUT"
    ctx = _setup(tmp_path / "governance")
    with pytest.raises(GovernanceError, match="root manifest is missing"):
        validate_governed_bundle(
            bundle_path=output, family_path=ctx["family_path"],
            preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
        )


def test_subprocess_output_cannot_bypass_gateway_or_enter_catalog(tmp_path):
    output = tmp_path / "wrapper-output"
    subprocess.run(
        [sys.executable, "-c", "from pathlib import Path; Path(r'%s').mkdir(); Path(r'%s').write_text('partial')"
         % (output, output / "predictions.csv")],
        check=True, capture_output=True, text=True,
    )
    ctx = _setup(tmp_path / "governance")
    canonical = CanonicalFutureEvidenceCatalog(tmp_path / "canonical.jsonl")
    with pytest.raises(GovernanceError, match="root manifest is missing"):
        validate_governed_bundle(
            bundle_path=output, family_path=ctx["family_path"],
            preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
        )
    assert canonical.records() == []


def test_caller_cannot_forge_catalog_validation_result(tmp_path):
    catalog = CanonicalFutureEvidenceCatalog(tmp_path / "canonical.jsonl")
    forged = {
        "validation_result": "PASS", "run_attempt_id": "forged",
        "classification": "CANONICAL_COMPLETED_EVIDENCE", "promotion_eligible": True,
    }
    with pytest.raises(GovernanceError, match="caller-supplied validation"):
        catalog.register(forged, imported_at=NOW)
    assert catalog.records() == []


def test_safe_template_cannot_be_registered(tmp_path):
    template = json.loads((ROOT / "specs" / "governed_run_approval_template_v1.json").read_text())
    with pytest.raises(GovernanceError, match="templates cannot be registered"):
        register_run_approval(
            template, approval_root=tmp_path / "approvals",
            catalog=GovernanceCatalog(tmp_path / "catalog.jsonl"), actor="TEST",
        )


def test_entrypoint_inventory_accounts_for_every_non_test_python_main():
    inventory = json.loads(
        (ROOT / "specs" / "laboratory_entrypoint_inventory_v1.json").read_text()
    )
    discovered = set()
    for root_name in ("Data test", "scripts", "tools", "src", "views"):
        for path in (ROOT / root_name).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if "/tests/" in f"/{relative}/":
                continue
            if "__main__" in path.read_text(encoding="utf-8"):
                discovered.add(relative)
    accounted = dict(inventory["executable_paths"])
    r7_delta_path = ROOT / "specs" / "research_r7_entrypoint_delta_v1.json"
    if r7_delta_path.is_file():
        r7_delta = json.loads(r7_delta_path.read_text(encoding="utf-8"))
        for entry in r7_delta["added_executable_entrypoints"]:
            accounted[entry["path"]] = entry["classification"]
    assert discovered == set(accounted)
    assert set(accounted.values()) <= {
        "CANONICAL_GOVERNED", "DEVELOPMENT_ONLY_NONCANONICAL", "DEPRECATED", "UNSAFE_BYPASS"
    }
    assert inventory["unsafe_bypass_count"] == 0
    for entry in inventory["callable_entrypoints"]:
        assert (ROOT / entry["path"]).is_file()


def test_every_data_test_script_crosses_shared_noncanonical_config_boundary():
    for path in (ROOT / "Data test" / "scripts").glob("*.py"):
        assert "load_config" in path.read_text(encoding="utf-8"), path.name


def test_data_test_script_guard_marks_output_even_for_wrapper_stack(monkeypatch, tmp_path):
    import research_contracts.development as development
    script = ROOT / "Data test" / "scripts" / "test_momentum.py"
    monkeypatch.setattr(development.inspect, "stack", lambda: [SimpleNamespace(filename=str(script))])
    with pytest.warns(RuntimeWarning, match="UNGOVERNED_NONCANONICAL_OUTPUT"):
        marker = development.mark_data_test_script_if_present(tmp_path)
    assert marker is not None
    assert json.loads(marker.read_text())["promotion_eligible"] is False


def test_deprecated_momentum_cli_fails_before_parsing_or_loading_data(capsys):
    from market_intel.application.momentum_cli import main
    assert main() == 2
    assert "No research was executed" in capsys.readouterr().err
