"""Known-answer tests for R.10B incremental ingestion and rebuild contracts."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from market_intel.application.synthetic_incremental import (_base_graph, _changes,
                                                            _clean_candidate,
                                                            schema_registry)
from market_intel.foundation.contracts import AsOfRequest, materialize_as_of
from market_intel.foundation.incremental import (
    BuildState, ImmutableIdentityConflict, IncrementalError, IncrementalRawStore,
    PartialPublicationConflict, SchemaDriftError, canonical_table_hash,
    execute_rebuild, graph_equivalent, impact_summary, plan_rebuild,
    publish_artifact_set, reusable,
)
from market_intel.foundation.providers import DatasetKind, ProviderObject


ROOT = Path(__file__).resolve().parents[1]


def _object(tmp_path: Path, identity: str = "object:1", content: str = "value") -> ProviderObject:
    path = tmp_path / (hashlib.sha256((identity + content).encode()).hexdigest() + ".json")
    path.write_text(content, encoding="utf-8")
    return ProviderObject("synthetic", DatasetKind.DAILY_EQUITY, identity, path,
                          data_classification="SYNTHETIC_ONLY_NONCANONICAL")


def test_multi_object_store_is_idempotent_and_rejects_identity_conflict(tmp_path):
    store = IncrementalRawStore(tmp_path / "raw")
    obj = _object(tmp_path)
    first = store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                         raw_schema_version="v1")
    second = store.ingest(obj, parser_version="p1", retrieved_at="2020-01-02T00:00:00Z",
                          raw_schema_version="v1")
    assert first.state == "INGESTED" and second.state == "REUSED_IDENTICAL_BYTES"
    assert first.manifest_path == second.manifest_path
    with pytest.raises(ImmutableIdentityConflict, match="IMMUTABLE_SOURCE_IDENTITY_CONFLICT"):
        store.ingest(_object(tmp_path, content="different"), parser_version="p1",
                     retrieved_at="2020-01-03T00:00:00Z", raw_schema_version="v1")


@pytest.mark.parametrize("failpoint", ["after_payload", "after_manifest_stage"])
def test_prepublication_crashes_leave_only_ignored_staging_and_restart_cleanly(tmp_path, failpoint):
    store = IncrementalRawStore(tmp_path / "raw")
    obj = _object(tmp_path, identity=failpoint)
    with pytest.raises(IncrementalError, match="INJECTED"):
        store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                     raw_schema_version="v1", fail_at=failpoint)
    object_root = tmp_path / "raw" / "objects"
    assert not object_root.exists() or not list(object_root.rglob("manifest.json"))
    assert store.cleanup_staging() == 1
    assert store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                        raw_schema_version="v1").state == "INGESTED"


def test_postpublish_preindex_crash_recovers_verified_object(tmp_path):
    store = IncrementalRawStore(tmp_path / "raw")
    obj = _object(tmp_path, identity="postpublish")
    with pytest.raises(IncrementalError, match="INJECTED_AFTER_OBJECT_PUBLISH"):
        store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                     raw_schema_version="v1", fail_at="after_object_publish")
    assert store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                        raw_schema_version="v1").state == "REUSED_IDENTICAL_BYTES"


def test_conflicting_partial_final_state_fails_closed(tmp_path):
    store = IncrementalRawStore(tmp_path / "raw")
    obj = _object(tmp_path, identity="partial")
    digest = hashlib.sha256(obj.local_path.read_bytes()).hexdigest()
    target = tmp_path / "raw" / "objects" / "synthetic" / "daily_equity" / digest
    target.mkdir(parents=True)
    (target / "payload.json").write_text("wrong", encoding="utf-8")
    with pytest.raises(PartialPublicationConflict, match="CONFLICTING_PARTIAL_RAW_OBJECT"):
        store.ingest(obj, parser_version="p1", retrieved_at="2020-01-01T00:00:00Z",
                     raw_schema_version="v1")


def _valid_row(**updates):
    row = {"instrument_id": "SYN_I001", "event_time": "2020-01-02T10:00:00Z",
           "published_at": "2020-01-02T12:00:00Z", "available_at": "2020-01-02T12:00:00Z",
           "close": 100.0, "turnover": 1000.0, "source_record_id": "r1",
           "revision_number": 1, "supersedes_record_id": None}
    row.update(updates)
    return row


def test_schema_router_accepts_exact_and_versioned_additive_schema():
    registry = schema_registry()
    exact = registry.route(dataset="daily_equity", raw_schema_version="synthetic_bar_raw_v1",
                           records=[_valid_row()])
    additive = registry.route(dataset="daily_equity", raw_schema_version="synthetic_bar_raw_v1_1",
                              records=[_valid_row(trade_count=10)])
    assert exact.output_schema_version == "synthetic_incremental_bar_v1"
    assert additive.output_schema_version == "synthetic_incremental_bar_v2"
    assert exact.parser_implementation_hash != additive.parser_implementation_hash
    assert [batch.output_schema_version for batch in registry.route_mixed([
        ("synthetic_bar_raw_v1", [_valid_row()]),
        ("synthetic_bar_raw_v1_1", [_valid_row(trade_count=10)]),
    ], dataset="daily_equity")] == ["synthetic_incremental_bar_v1", "synthetic_incremental_bar_v2"]


@pytest.mark.parametrize("row,reason", [
    ({key: value for key, value in _valid_row().items() if key != "close"}, "MISSING_REQUIRED_FIELDS:close"),
    (_valid_row(close="100"), "TYPE_MISMATCH:close:number"),
    ({**{key: value for key, value in _valid_row().items() if key != "close"}, "settle": 100.0}, "MISSING_REQUIRED_FIELDS:close"),
    (_valid_row(extra=1), "UNKNOWN_FIELDS:extra"),
])
def test_schema_breaking_drift_is_quarantined(row, reason):
    result = schema_registry().route(dataset="daily_equity", raw_schema_version="synthetic_bar_raw_v1",
                                     records=[row])
    assert not result.accepted and reason in result.quarantine[0]["quality_flags"]


def test_unknown_schema_fails_and_permissive_unknown_column_is_explicit():
    registry = schema_registry()
    with pytest.raises(SchemaDriftError, match="UNKNOWN_SCHEMA_VERSION"):
        registry.route(dataset="daily_equity", raw_schema_version="unknown", records=[_valid_row()])
    permissive = registry.route(dataset="daily_equity", raw_schema_version="synthetic_bar_raw_v1",
                                records=[_valid_row(extra=1)], strict=False)
    assert len(permissive.accepted) == 1 and "extra" not in permissive.accepted[0]


def test_correction_is_visible_only_after_publication():
    frame = pd.DataFrame([
        {**_valid_row(), "dataset_version": "v1"},
        {**_valid_row(close=105.0, source_record_id="r2", revision_number=2,
                      supersedes_record_id="r1", published_at="2020-01-10T12:00:00Z",
                      available_at="2020-01-10T12:00:00Z"), "dataset_version": "v1"},
    ])
    before = materialize_as_of(frame, AsOfRequest(pd.Timestamp("2020-01-09T12:00:00Z"),
                                                  "SESSION_CLOSE", "v1"))
    after = materialize_as_of(frame, AsOfRequest(pd.Timestamp("2020-01-11T12:00:00Z"),
                                                 "SESSION_CLOSE", "v1"))
    assert before.iloc[0]["close"] == 100 and after.iloc[0]["close"] == 105


def test_impact_plans_are_causal_and_minimal():
    graph = _base_graph("env")
    late = plan_rebuild(graph, _changes()["late_session"])
    assert late["snapshot_pre"]["state"] == BuildState.UNAFFECTED
    assert late["snapshot_post"]["state"] == BuildState.REBUILT_INPUT_CHANGED
    feature = plan_rebuild(graph, _changes()["feature_correction"])
    assert feature["universe_post"]["state"] == BuildState.UNAFFECTED
    assert feature["feature_post"]["state"] == BuildState.REBUILT_INPUT_CHANGED
    benchmark = plan_rebuild(graph, _changes()["benchmark_correction"])
    assert benchmark["feature_post"]["state"] == BuildState.UNAFFECTED
    assert benchmark["outcome_post"]["state"] == BuildState.REBUILT_INPUT_CHANGED
    terminal = plan_rebuild(graph, _changes()["terminal_update"])
    assert terminal["prediction_post"]["state"] == BuildState.UNAFFECTED
    assert terminal["outcome_post"]["state"] == BuildState.REBUILT_INPUT_CHANGED
    summary = impact_summary(graph, _changes()["old_price_correction"])
    assert summary == {
        "change_id": "old_price_correction",
        "earliest_economic_time": "2020-01-02T10:00:00+00:00",
        "availability_time": "2020-01-20T12:00:00+00:00",
        "earliest_affected_downstream_time": "2020-02-10T12:30:00+00:00",
    }


def test_incremental_execution_equals_clean_candidate_and_preserves_unaffected_hashes():
    previous = _base_graph("env")
    plan = plan_rebuild(previous, _changes()["old_price_correction"])
    clean = _clean_candidate(previous, plan, "old_price_correction")
    incremental, ledger = execute_rebuild(previous, clean, plan)
    assert graph_equivalent(incremental, clean)
    assert incremental.nodes["snapshot_pre"].output_hash == previous.nodes["snapshot_pre"].output_hash
    assert incremental.nodes["fold_pre"].output_hash == previous.nodes["fold_pre"].output_hash
    assert any(item["state"] == "REUSED_HASH_IDENTICAL" for item in ledger)


def test_every_supported_update_is_deterministic_and_clean_rebuild_equivalent():
    def execute_all():
        graph = _base_graph("env")
        history = []
        for stage_id, change in _changes().items():
            plan = plan_rebuild(graph, change)
            clean = _clean_candidate(graph, plan, stage_id)
            graph, _ = execute_rebuild(graph, clean, plan)
            assert graph_equivalent(graph, clean)
            history.append({key: node.output_hash for key, node in sorted(graph.nodes.items())})
        return history
    assert execute_all() == execute_all()


@pytest.mark.parametrize("fail_at", ["after_artifact_0", "before_root_manifest"])
def test_artifact_set_publication_is_atomic_and_restartable(tmp_path, fail_at):
    target = tmp_path / "run"
    with pytest.raises(IncrementalError, match="INJECTED"):
        publish_artifact_set(target, {"normalized/data": b"one", "downstream/data": b"two"},
                             b"{}\n", fail_at=fail_at)
    assert not target.exists() and not (tmp_path / ".run.staging").exists()
    publish_artifact_set(target, {"normalized/data": b"one", "downstream/data": b"two"}, b"{}\n")
    assert (target / "root_manifest.json").read_bytes() == b"{}\n"
    with pytest.raises(FileExistsError):
        publish_artifact_set(target, {"x": b"changed"}, b"{}\n")


def test_reuse_requires_all_contract_bindings_and_blocks_stale_path_reuse():
    graph = _base_graph("env")
    node = graph.nodes["feature_pre"]
    assert reusable(node, node)
    for changed in (
        replace(node, input_hashes=("changed",)),
        replace(node, definition_hashes=("changed",)),
        replace(node, parameters_hash="changed"),
        replace(node, availability_policy="changed"),
        replace(node, schema_version="changed"),
        replace(node, environment_hash="changed"),
    ):
        assert not reusable(node, changed)
    plan = {key: {"state": "UNAFFECTED", "reason": "test"} for key in graph.nodes}
    candidate_nodes = [replace(value, output_hash="changed") if key == "feature_pre" else value
                       for key, value in graph.nodes.items()]
    from market_intel.foundation.incremental import DependencyGraph
    with pytest.raises(IncrementalError, match="BLOCKED_DEPENDENCY_INVALID:feature_pre"):
        execute_rebuild(graph, DependencyGraph(candidate_nodes), plan)


def test_canonical_logical_hash_captures_schema_null_timezone_and_ignores_input_order():
    first = pd.DataFrame({"id": ["b", "a"], "value": [pd.NA, 1],
                          "when": pd.to_datetime(["2020-01-02T00:00:00Z", "2020-01-01T00:00:00Z"])})
    second = first.iloc[::-1].reset_index(drop=True)
    assert canonical_table_hash(first, keys=("id",)) == canonical_table_hash(second, keys=("id",))
    assert canonical_table_hash(first, keys=("id",)) != canonical_table_hash(
        first.assign(value=first["value"].astype("string")), keys=("id",))


def test_r10a_evidence_remains_byte_exact():
    expected = {
        "root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580"
    }
    base = ROOT / "docs" / "investigations" / "r10a" / "run_v1"
    for name, digest in expected.items():
        assert hashlib.sha256((base / name).read_bytes()).hexdigest() == digest
