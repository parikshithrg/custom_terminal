"""Known-answer and adversarial tests for R.10F publication/read semantics."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from market_intel.application.evidence_read import EvidenceReadFacade
from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.application.synthetic_publication import (
    EDGE_VERSION, publication_changes, publication_dependency_graph,
    publish_sequence, synthetic_snapshot,
)
from market_intel.evidence.publication import (
    ArtifactReference, FreshnessPolicy, FreshnessStatus, ImmutableBundlePublisher,
    IndexEntry, PublicationError, PublicationIndex, assess_freshness, decision_gate,
    publication_policy, validate_snapshot,
)
from market_intel.foundation.incremental import execute_rebuild, graph_equivalent, plan_rebuild


ROOT = Path(__file__).resolve().parents[1]


def test_published_snapshot_schema_and_semantics_are_exact():
    snapshot = synthetic_snapshot(ROOT)
    validate_snapshot(snapshot, artifact_root=ROOT)
    assert snapshot.schema_version == "asset_evidence_publication_r10f_v1"
    assert snapshot.score_0_100 == 15.0
    assert snapshot.positive_outcome_probability == 1.0
    assert snapshot.expected_outcome == 1.8
    assert snapshot.confidence == "LOW" and snapshot.decision == "NO_DECISION"
    assert snapshot.classification == "SYNTHETIC_ONLY_NONCANONICAL"


@pytest.mark.parametrize("changes,reason", [
    ({"score_0_100": 101}, "SCORE_OUT_OF_BOUNDS"),
    ({"score_definition": "probability of profit"}, "AMBIGUOUS_SCORE_DEFINITION"),
    ({"positive_outcome_probability": 1.01}, "PROBABILITY_OUT_OF_BOUNDS"),
    ({"confidence": "87"}, "INVALID_CONFIDENCE_CATEGORY"),
    ({"confidence_limiting_factors": ()}, "CONFIDENCE_LIMITING_FACTORS_MISSING"),
    ({"effective_sample_size": 6}, "INVALID_SAMPLE_SIZE"),
    ({"canonical": True}, "SYNTHETIC_MARKED_CANONICAL"),
    ({"promotion_eligible": True}, "NONCANONICAL_MARKED_PROMOTION_ELIGIBLE"),
    ({"decision": "BUY"}, "SYNTHETIC_NON_NO_DECISION"),
    ({"lifecycle": "ACTIVE"}, "SYNTHETIC_LIFECYCLE_ACTIVE"),
])
def test_cross_field_semantic_failures_are_named(changes, reason):
    with pytest.raises(PublicationError, match=reason):
        validate_snapshot(replace(synthetic_snapshot(ROOT), **changes), artifact_root=ROOT)


def test_calibration_and_decision_timing_fail_closed():
    snapshot = synthetic_snapshot(ROOT)
    with pytest.raises(PublicationError, match="CALIBRATION_AFTER_DECISION_CUTOFF"):
        validate_snapshot(replace(snapshot, calibration_fitted_through=pd.Timestamp("2020-02-15T00:00:00Z")), artifact_root=ROOT)
    with pytest.raises(PublicationError, match="DECISION_AFTER_KNOWLEDGE_CUTOFF"):
        validate_snapshot(replace(snapshot, knowledge_cutoff=pd.Timestamp("2020-02-13T00:00:00Z")), artifact_root=ROOT)


def test_missing_or_mutated_artifact_fails_closed(tmp_path):
    snapshot = synthetic_snapshot(ROOT)
    missing = ArtifactReference("missing", "does-not-exist.json", "0" * 64, "COMPONENT", "v1")
    with pytest.raises(PublicationError, match="MISSING_COMPONENT_ARTIFACT"):
        validate_snapshot(replace(snapshot, artifact_references=(missing,)), artifact_root=ROOT)
    bad = replace(snapshot.artifact_references[0], sha256="0" * 64)
    with pytest.raises(PublicationError, match="ARTIFACT_HASH_MISMATCH"):
        validate_snapshot(replace(snapshot, artifact_references=(bad,)), artifact_root=ROOT)


def test_path_traversal_is_rejected():
    ref = ArtifactReference("bad", "../outside.json", "0" * 64, "SOURCE", "v1")
    with pytest.raises(PublicationError, match="PATH_TRAVERSAL_REJECTED"):
        validate_snapshot(replace(synthetic_snapshot(ROOT), artifact_references=(ref,)), artifact_root=ROOT)


def test_freshness_boundaries_corrections_and_states():
    snapshot = synthetic_snapshot(ROOT); policy = FreshnessPolicy()
    at = assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T01:00:00Z"), policy=policy)
    beyond = assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T01:00:01Z"), policy=policy)
    assert at["status"] == "CURRENT" and beyond["status"] == "AGING"
    assert assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=policy,
                            superseded=True)["status"] == "SUPERSEDED"
    assert assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=policy,
                            data_blocked=True)["status"] == "DATA_BLOCKED"
    assert assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=policy,
                            calendar_known=False)["status"] == "CALENDAR_UNKNOWN"
    assert assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-13T23:00:00Z"), policy=policy,
                            available_at=pd.Timestamp("2020-02-14T00:00:00Z"))["status"] == "NOT_YET_AVAILABLE"
    assert assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=policy,
                            correction_available_at=pd.Timestamp("2020-02-14T00:15:00Z"))["status"] == "STALE"


def test_synthetic_gate_always_returns_exact_no_decision_reason():
    result = decision_gate(synthetic_snapshot(ROOT), provenance_valid=False,
                           multiple_testing_pass=False, calibration_available=False)
    assert result == {"decision": "NO_DECISION", "reason": "SYNTHETIC_NONCANONICAL_EVIDENCE"}


@pytest.mark.parametrize("changes,kwargs,reason", [
    ({}, {"provenance_valid": False}, "PROVENANCE_MISMATCH"),
    ({"freshness_status": "STALE"}, {}, "STALE_EVIDENCE"),
    ({"data_quality_status": "BLOCKED"}, {}, "DATA_QUALITY_BLOCKED"),
    ({"lifecycle": "RESEARCHING"}, {}, "EDGE_NOT_ACTIVE"),
    ({"lifecycle": "ACTIVE"}, {"confidence_allowed": False}, "CONFIDENCE_BELOW_POLICY"),
    ({"lifecycle": "ACTIVE"}, {"unresolved_terminal": True}, "UNRESOLVED_TERMINAL_ECONOMICS"),
    ({"lifecycle": "ACTIVE"}, {"calibration_available": False}, "CALIBRATION_UNAVAILABLE"),
    ({"lifecycle": "ACTIVE"}, {"multiple_testing_pass": False}, "MULTIPLE_TESTING_GATE_FAILED"),
])
def test_non_synthetic_gate_reasons_remain_no_decision(changes, kwargs, reason):
    snapshot = replace(synthetic_snapshot(ROOT), classification="INTERNAL_TEST_ONLY", **changes)
    assert decision_gate(snapshot, **kwargs) == {"decision": "NO_DECISION", "reason": reason}


def test_atomic_bundle_hash_idempotence_and_conflict(tmp_path):
    publisher = ImmutableBundlePublisher(tmp_path / "pub")
    snapshot = synthetic_snapshot(ROOT)
    freshness = assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=FreshnessPolicy())
    policy = publication_policy(snapshot, provenance_valid=True, freshness=freshness)
    first = publisher.publish(snapshot, artifact_root=ROOT, freshness=freshness, policy=policy)
    second = publisher.publish(snapshot, artifact_root=ROOT, freshness=freshness, policy=policy)
    assert first.bundle_hash == second.bundle_hash
    with pytest.raises(PublicationError, match="IMMUTABLE_PUBLICATION_IDENTITY_CONFLICT"):
        publisher.publish(replace(snapshot, score_0_100=16), artifact_root=ROOT, freshness=freshness, policy=policy)


def test_interrupted_publication_leaves_no_partial_bundle(tmp_path):
    publisher = ImmutableBundlePublisher(tmp_path / "pub"); snapshot = synthetic_snapshot(ROOT)
    freshness = assess_freshness(snapshot, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=FreshnessPolicy())
    with pytest.raises(PublicationError, match="INJECTED_PUBLICATION_INTERRUPTION"):
        publisher.publish(snapshot, artifact_root=ROOT, freshness=freshness,
                          policy=publication_policy(snapshot, provenance_valid=True, freshness=freshness), fail_at="after_1")
    assert not list((tmp_path / "pub" / "bundles").glob("*")) if (tmp_path / "pub" / "bundles").exists() else True


def test_mutated_published_object_and_manifest_are_rejected(tmp_path):
    index, entries = publish_sequence(ROOT, tmp_path / "pub")
    bundle = entries[0].bundle; target = index.publisher.root / bundle.relative_path
    original = (target / "snapshot.json").read_bytes()
    (target / "snapshot.json").write_bytes(original + b" ")
    with pytest.raises(PublicationError, match="PUBLISHED_OBJECT_HASH_MISMATCH"):
        index.publisher.verify(bundle)


def test_history_latest_and_supersession_are_deterministic(tmp_path):
    index, entries = publish_sequence(ROOT, tmp_path / "pub")
    assert index.latest("SYN_E_00", 21, EDGE_VERSION).snapshot_id == "SYN-PUB-003"
    assert [entry.snapshot_id for entry in index.history("SYN_E_00", EDGE_VERSION)] == [
        "SYN-PUB-006", "SYN-PUB-005", "SYN-PUB-004", "SYN-PUB-003", "SYN-PUB-002", "SYN-PUB-001"]
    assert entries[0].bundle.bundle_hash != entries[1].bundle.bundle_hash


def test_supersession_cycle_fails_closed(tmp_path):
    publisher = ImmutableBundlePublisher(tmp_path / "pub"); index = PublicationIndex(publisher)
    snapshots = [synthetic_snapshot(ROOT, snapshot_id="A", supersedes="B"),
                 synthetic_snapshot(ROOT, snapshot_id="B", supersedes="A", decision_instant="2020-02-14T00:30:00Z")]
    for snapshot in snapshots:
        freshness = {"status": "CURRENT", "reason": "TEST", "policy_version": "v1", "evaluation_instant": str(snapshot.decision_instant)}
        bundle = publisher.publish(snapshot, artifact_root=ROOT, freshness=freshness,
                                   policy=publication_policy(snapshot, provenance_valid=True, freshness=freshness))
        entry = IndexEntry(snapshot.snapshot_id, snapshot.snapshot_version, snapshot.instrument_id, 21, EDGE_VERSION,
                           bundle, snapshot.lifecycle, "CURRENT", snapshot.classification, "NO_DECISION",
                           snapshot.supersedes_snapshot_id, str(snapshot.decision_instant))
        if snapshot.snapshot_id == "B":
            with pytest.raises(PublicationError, match="SUPERSESSION_CYCLE"): index.add(entry)
            assert [item.snapshot_id for item in index.history("SYN_E_00", EDGE_VERSION)] == ["A"]
        else: index.add(entry)


def test_read_facade_maps_stored_fields_without_recalculation(tmp_path):
    index, _ = publish_sequence(ROOT, tmp_path / "pub"); facade = EvidenceReadFacade(index)
    dto = facade.get_latest(instrument_id="SYN_E_00", horizon_sessions=21, edge_family_version=EDGE_VERSION)
    assert dto.score_0_100 == 18.0 and dto.expected_outcome == 1.8
    assert dto.positive_outcome_probability == 1.0 and dto.confidence == "LOW"
    assert dto.decision == "NO_DECISION" and dto.decision_reason == "SYNTHETIC_NONCANONICAL_EVIDENCE"
    assert "NOT LIVE" in dto.warning_banner
    assert len(facade.list_snapshots(instrument_id="SYN_E_00", edge_family_version=EDGE_VERSION, limit=2)) == 2


def test_read_facade_rejects_unbounded_and_mutating_interfaces(tmp_path):
    index, _ = publish_sequence(ROOT, tmp_path / "pub"); facade = EvidenceReadFacade(index)
    with pytest.raises(PublicationError, match="INVALID_PAGINATION"):
        facade.list_snapshots(instrument_id="SYN_E_00", edge_family_version=EDGE_VERSION, limit=51)
    with pytest.raises(PublicationError, match="INVALID_TYPED_IDENTIFIER"):
        facade.list_snapshots(instrument_id="../secret", edge_family_version=EDGE_VERSION)
    with pytest.raises(PublicationError, match="ARBITRARY_SQL_PROHIBITED"): facade.query_sql("select *")
    with pytest.raises(PublicationError, match="ARBITRARY_FILESYSTEM_PATH_PROHIBITED"): facade.open_path("C:/private")
    with pytest.raises(PublicationError, match="READ_ONLY_FACADE_WRITE_PROHIBITED"): facade.write({})


def test_incremental_publication_changes_equal_clean_rebuilds():
    graph = publication_dependency_graph("env")
    for change in publication_changes().values():
        plan = plan_rebuild(graph, change); clean = _clean_candidate(graph, plan, change.change_id)
        incremental, ledger = execute_rebuild(graph, clean, plan)
        assert graph_equivalent(incremental, clean)
        assert any(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger)
    presentation = plan_rebuild(graph, publication_changes()["presentation_schema"])
    assert presentation["presentation_read_model"]["state"] == "REBUILT_INPUT_CHANGED"
    assert presentation["publication_bundle"]["state"] == "UNAFFECTED"


def test_application_facade_contains_no_scoring_recomputation_imports():
    source = (ROOT / "src/market_intel/application/evidence_read.py").read_text(encoding="utf-8")
    for forbidden in ("fit_percentile", "fit_outcome", "fit_linear", "assess_confidence", "percentile_score("):
        assert forbidden not in source


def test_protected_roots_momentum_and_holdout_remain_unchanged():
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r10e/run_v1/root_manifest.json": "a48915801d99c8eca7559079c597d9157e3b3699d5a5cf0759f6a4e01aabd7b3",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    manifest = json.loads((ROOT / "docs/investigations/r10a/run_v1/root_run_manifest.json").read_text())
    assert manifest["holdout"]["state"] == "UNCONSUMED_SYNTHETIC_HOLDOUT"
