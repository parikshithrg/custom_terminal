from __future__ import annotations

import copy
import csv
import json
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
    compare_legacy_logs,
    label_ungoverned_output,
    lock_preregistration,
    register_family,
    sha256_file,
    validate_input_declaration,
    validate_preregistration,
)
from research_contracts.legacy_ledger import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "research_r3"
FROZEN = ROOT / "evidence" / "legacy" / "legacy_hypothesis_ledger_v1" / "hypothesis_log.csv"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return path


def _ids():
    counter = 0

    def next_id():
        nonlocal counter
        counter += 1
        return f"synthetic-event-{counter:03d}"

    return next_id


def _success_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    (temp / "predictions.csv").write_text("id,value\nA,1\nB,2\nC,3\n", encoding="utf-8")
    (temp / "evidence.json").write_bytes(canonical_json_bytes({
        "synthetic": True, "mean": 2, "promotion_eligible": False
    }))
    return {"lifecycle_result": "TRAIN_REJECTED"}


def _failure_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    (temp / "predictions.csv").write_text("id,value\nA,1\n", encoding="utf-8")
    raise RuntimeError("sensitive provider detail must be sanitized")


def _abort_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    raise GovernedAbort("synthetic operator abort")


def _unexpected_runner(temp: Path, prereg: dict, inputs: dict) -> dict:
    result = _success_runner(temp, prereg, inputs)
    (temp / "undeclared_debug.txt").write_text("not canonical", encoding="utf-8")
    return result


def _setup(
    tmp_path: Path, *, split: str = "train", runner=_success_runner,
    capability: str = "PASS", limited: bool = False,
    attempt_id: str = "synthetic-attempt-001",
):
    family = _load("synthetic_family_v1.json")
    prereg = _load("synthetic_preregistration_v1.json")
    inputs = _load("synthetic_input_declaration_v1.json")
    prereg["split_requested"] = split
    prereg["limited_data_non_promotable"] = limited
    prereg["code_entry_point"] = "synthetic:runner"
    inputs["dataset_split_version"] = f"synthetic_{split}_v1"
    inputs["population_capability_assessment"]["price_history_complete"] = capability
    catalog = GovernanceCatalog(tmp_path / "governance.jsonl", event_id_factory=_ids())
    family_path, family_hash = register_family(
        family, registry_root=tmp_path / "families", catalog=catalog,
        actor="SYNTHETIC_TEST", timestamp="2026-01-01T00:00:00+00:00",
    )
    prereg_path, prereg_hash = lock_preregistration(
        prereg, family_path=family_path, prereg_root=tmp_path / "preregistrations",
        catalog=catalog, actor="SYNTHETIC_TEST", timestamp="2026-01-01T00:00:00+00:00",
    )
    input_path = _write(tmp_path / "inputs.json", inputs)
    gateway = GovernedExecutionGateway(
        catalog=catalog, attempts_root=tmp_path / "attempts",
        runner_registry={"synthetic:runner": runner}, actor="SYNTHETIC_TEST",
        clock=lambda: "2026-01-01T00:00:00+00:00",
        attempt_id_factory=lambda: attempt_id,
    )
    return {
        "family": family, "family_path": family_path, "family_hash": family_hash,
        "prereg": prereg, "prereg_path": prereg_path, "prereg_hash": prereg_hash,
        "inputs": inputs, "input_path": input_path, "catalog": catalog,
        "gateway": gateway,
    }


def _authorize(ctx: dict, split: str):
    return authorize_split_access(
        catalog=ctx["catalog"], family=ctx["family"], prereg=ctx["prereg"],
        preregistration_sha256=ctx["prereg_hash"],
        dataset_split_version=ctx["inputs"]["dataset_split_version"], split=split,
        reason="synthetic access test", actor="SYNTHETIC_TEST",
        timestamp="2026-01-01T00:00:00+00:00", authorization_id=f"{split}-auth-001",
    )


def test_family_version_is_immutable(tmp_path):
    ctx = _setup(tmp_path)
    changed = copy.deepcopy(ctx["family"])
    changed["primary_metric"] = "silently_changed"
    with pytest.raises(GovernanceError, match="immutable governed object differs"):
        register_family(
            changed, registry_root=tmp_path / "families", catalog=ctx["catalog"],
            actor="SYNTHETIC_TEST",
        )


def test_preregistration_completeness_and_hash_stability(tmp_path):
    prereg = _load("synthetic_preregistration_v1.json")
    validate_preregistration(prereg)
    assert canonical_hash(prereg) == canonical_hash(copy.deepcopy(prereg))
    prereg["entry_rule"] = ""
    with pytest.raises(GovernanceError, match="incomplete"):
        validate_preregistration(prereg)


def test_locked_preregistration_is_immutable(tmp_path):
    ctx = _setup(tmp_path)
    changed = copy.deepcopy(ctx["prereg"])
    changed["holding_horizon_sessions"] = 6
    with pytest.raises(GovernanceError, match="immutable governed object differs"):
        lock_preregistration(
            changed, family_path=ctx["family_path"],
            prereg_root=tmp_path / "preregistrations", catalog=ctx["catalog"],
            actor="SYNTHETIC_TEST",
        )


def test_missing_dataset_hash_rejected(tmp_path):
    prereg = _load("synthetic_preregistration_v1.json")
    inputs = _load("synthetic_input_declaration_v1.json")
    inputs["datasets"][0]["snapshot_sha256"] = ""
    with pytest.raises(GovernanceError, match="incomplete|snapshot hash"):
        validate_input_declaration(inputs, prereg)


def test_environment_fingerprint_must_match_declared_environment():
    prereg = _load("synthetic_preregistration_v1.json")
    inputs = _load("synthetic_input_declaration_v1.json")
    inputs["environment"] = {"python": "silently-changed"}
    with pytest.raises(GovernanceError, match="environment fingerprint"):
        validate_input_declaration(inputs, prereg)


def test_failed_capability_gate_rejects_before_runner(tmp_path):
    ctx = _setup(tmp_path, capability="UNKNOWN")
    with pytest.raises(GovernanceError, match="capabilities"):
        ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )
    assert not (tmp_path / "attempts").exists()


def test_limited_exploratory_scope_runs_but_is_permanently_nonpromotable(tmp_path):
    ctx = _setup(tmp_path, capability="UNKNOWN", limited=True)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["dataset_capability_gate_passed"] is False
    assert manifest["promotion_eligible"] is False


def test_dirty_and_environment_state_are_captured(tmp_path):
    ctx = _setup(tmp_path)
    ctx["inputs"]["dirty_worktree"] = True
    ctx["inputs"]["dirty_worktree_fingerprint"] = "b" * 64
    _write(ctx["input_path"], ctx["inputs"])
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["dirty_worktree"] is True
    assert manifest["dirty_worktree_fingerprint"] == "b" * 64
    assert manifest["environment_fingerprint"] == ctx["inputs"]["environment_fingerprint"]


def test_successful_synthetic_governed_execution_and_atomic_finalization(tmp_path):
    ctx = _setup(tmp_path)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["completion_status"] == "COMPLETED"
    assert len(manifest["output_artifact_inventory"]) == 2
    assert manifest["promotion_eligible"] is False
    assert not (tmp_path / "attempts" / ".tmp-synthetic-attempt-001").exists()
    assert ctx["catalog"].events()[-1]["event_type"] == "RUN_COMPLETED"


def test_unexpected_outputs_are_listed_but_not_canonical(tmp_path):
    ctx = _setup(tmp_path, runner=_unexpected_runner)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["unexpected_outputs"] == ["undeclared_debug.txt"]
    assert "undeclared_debug.txt" not in {
        item["relative_path"] for item in manifest["output_artifact_inventory"]
    }


def test_failed_execution_still_has_root_manifest(tmp_path):
    ctx = _setup(tmp_path, runner=_failure_runner)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["completion_status"] == "FAILED"
    assert manifest["sanitized_failure_category"] == "SANITIZED_RUNNER_FAILURE"
    assert "sensitive provider detail" not in json.dumps(manifest)
    assert ctx["catalog"].events()[-1]["event_type"] == "RUN_FAILED"


def test_aborted_execution_still_has_root_manifest(tmp_path):
    ctx = _setup(tmp_path, runner=_abort_runner)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["completion_status"] == "ABORTED"
    assert manifest["sanitized_failure_category"] == "RUNNER_DECLARED_ABORT"
    assert ctx["catalog"].events()[-1]["event_type"] == "RUN_ABORTED"


def test_duplicate_run_attempt_rejected(tmp_path):
    ctx = _setup(tmp_path)
    args = dict(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    ctx["gateway"].run(**args)
    with pytest.raises(GovernanceError, match="duplicate run-attempt"):
        ctx["gateway"].run(**args)


def test_hash_chain_detects_tampering(tmp_path):
    ctx = _setup(tmp_path)
    events = ctx["catalog"].events()
    assert GovernanceCatalog.verify(events) == events[-1]["event_sha256"]
    events[0]["reason"] = "tampered"
    with pytest.raises(GovernanceError, match="hash mismatch"):
        GovernanceCatalog.verify(events)


def test_event_sequence_violation_rejected(tmp_path):
    catalog = GovernanceCatalog(tmp_path / "events.jsonl", event_id_factory=_ids())
    with pytest.raises(GovernanceError, match="lacks authorization"):
        catalog.append(
            event_type="RUN_STARTED", actor_classification="SYNTHETIC_TEST",
            object_refs={"run_attempt_id": "missing"}, object_hashes={},
            reason="invalid sequence", resulting_state="RUNNING",
            timestamp="2026-01-01T00:00:00+00:00",
        )
    assert not catalog.path.exists()


def test_validation_requires_exact_authorization(tmp_path):
    ctx = _setup(tmp_path, split="validation")
    args = dict(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    with pytest.raises(GovernanceError, match="authorization"):
        ctx["gateway"].run(**args)
    event = _authorize(ctx, "validation")
    bundle = ctx["gateway"].run(**args)
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["split_access_event"]["event_id"] == event["event_id"]


def test_one_time_test_authorization_cannot_be_reused(tmp_path):
    ctx = _setup(tmp_path, split="test")
    _authorize(ctx, "test")
    args = dict(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    ctx["gateway"].run(**args)
    with pytest.raises(GovernanceError, match="already granted"):
        _authorize(ctx, "test")
    second_gateway = GovernedExecutionGateway(
        catalog=ctx["catalog"], attempts_root=tmp_path / "attempts",
        runner_registry={"synthetic:runner": _success_runner}, actor="SYNTHETIC_TEST",
        clock=lambda: "2026-01-01T00:00:00+00:00",
        attempt_id_factory=lambda: "synthetic-attempt-002",
    )
    with pytest.raises(GovernanceError, match="already been consumed"):
        second_gateway.run(**args)


def test_replication_requires_registration_event(tmp_path):
    ctx = _setup(tmp_path, split="replication")
    args = dict(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    with pytest.raises(GovernanceError, match="authorization"):
        ctx["gateway"].run(**args)
    event = _authorize(ctx, "replication")
    bundle = ctx["gateway"].run(**args)
    manifest = json.loads((bundle / "root_manifest.json").read_text())
    assert manifest["split_access_event"]["event_id"] == event["event_id"]


def test_ungoverned_output_rejected_by_canonical_importer(tmp_path):
    output = tmp_path / "direct-script-output"
    label_ungoverned_output(output, reason="direct synthetic development script")
    ctx = _setup(tmp_path / "governance")
    with pytest.raises(GovernanceError, match="root manifest is missing"):
        validate_governed_bundle(
            bundle_path=output, family_path=ctx["family_path"],
            preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
        )


def test_governed_bundle_import_and_catalog_idempotency(tmp_path):
    ctx = _setup(tmp_path)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    validation = validate_governed_bundle(
        bundle_path=bundle, family_path=ctx["family_path"],
        preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
    )
    assert validation["classification"] == "CANONICAL_COMPLETED_EVIDENCE"
    assert validation["promotion_eligible"] is False
    catalog = CanonicalFutureEvidenceCatalog(tmp_path / "canonical.jsonl")
    _, appended = catalog.register(validation, imported_at="2026-01-01T00:00:00+00:00")
    assert appended is True
    _, appended = catalog.register(validation, imported_at="2099-01-01T00:00:00+00:00")
    assert appended is False


@pytest.mark.parametrize("runner,status", [
    (_failure_runner, "FAILED"),
    (_abort_runner, "ABORTED"),
])
def test_failed_and_aborted_attempts_import_as_governed_evidence(tmp_path, runner, status):
    ctx = _setup(tmp_path, runner=runner)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    validation = validate_governed_bundle(
        bundle_path=bundle, family_path=ctx["family_path"],
        preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
    )
    assert validation["classification"] == "CANONICAL_GOVERNED_ATTEMPT"
    assert validation["completion_status"] == status
    assert validation["promotion_eligible"] is False


def test_importer_rejects_silently_changed_family_file(tmp_path):
    ctx = _setup(tmp_path)
    bundle = ctx["gateway"].run(
        family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
        input_declaration_path=ctx["input_path"],
    )
    changed = copy.deepcopy(ctx["family"])
    changed["allowed_diagnostic_scope"] = ["silently_changed"]
    _write(ctx["family_path"], changed)
    with pytest.raises(GovernanceError, match="exact registered family"):
        validate_governed_bundle(
            bundle_path=bundle, family_path=ctx["family_path"],
            preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
        )


def test_missing_root_manifest_is_never_canonical(tmp_path):
    ctx = _setup(tmp_path)
    empty = tmp_path / "empty"; empty.mkdir()
    with pytest.raises(GovernanceError, match="root manifest"):
        validate_governed_bundle(
            bundle_path=empty, family_path=ctx["family_path"],
            preregistration_path=ctx["prereg_path"], catalog=ctx["catalog"],
        )


def test_current_kite_data_rejected_as_historical_input():
    prereg = _load("synthetic_preregistration_v1.json")
    inputs = _load("synthetic_input_declaration_v1.json")
    inputs["datasets"][0]["dataset_id"] = "kite_current_instrument_inventory"
    with pytest.raises(GovernanceError, match="current"):
        validate_input_declaration(inputs, prereg)


def test_legacy_evidence_remains_nonpromotable():
    ledger = json.loads((ROOT / "evidence" / "legacy" / "legacy_hypothesis_ledger_v1" / "neutral_ledger.json").read_text())
    assert ledger["evidence_classification"] == "LEGACY_EXPLORATORY_EVIDENCE"
    assert ledger["production_eligible"] is False
    assert all(row["production_eligible"] is False for row in ledger["rows"])


def test_divergence_detection_is_id_only_and_sanitized(tmp_path):
    frozen = tmp_path / "frozen.csv"
    live = tmp_path / "live.csv"
    frozen.write_text("hypothesis_id,metric,decision\na,SECRET_OLD,rejected\nb,X,rejected\n")
    live.write_text("hypothesis_id,metric,decision\na,SECRET_NEW,rejected\nb,X,rejected\nc,DO_NOT_IMPORT,accepted\n")
    report = compare_legacy_logs(frozen_path=frozen, live_path=live)
    assert report["added_row_ids"] == ["c"]
    assert report["modified_historical_row_ids"] == ["a"]
    assert report["added_row_classification"] == "POST_FREEZE_UNGOVERNED_ROWS"
    assert report["metrics_imported_or_interpreted"] is False
    assert "SECRET" not in json.dumps(report) and "DO_NOT_IMPORT" not in json.dumps(report)


def test_frozen_legacy_snapshot_is_unchanged():
    assert sha256_file(FROZEN) == "124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d"


def test_synthetic_execution_is_byte_deterministic_twice(tmp_path):
    hashes = []
    for name in ("one", "two"):
        ctx = _setup(tmp_path / name)
        bundle = ctx["gateway"].run(
            family_path=ctx["family_path"], preregistration_path=ctx["prereg_path"],
            input_declaration_path=ctx["input_path"],
        )
        hashes.append({
            path.name: sha256_file(path)
            for path in bundle.iterdir() if path.is_file()
        })
    assert hashes[0] == hashes[1]


def test_dtest_gateway_has_no_market_intel_import():
    source = (ROOT / "Data test" / "dtest" / "governance" / "gateway.py").read_text()
    assert "from market_intel" not in source
    assert "import market_intel" not in source
