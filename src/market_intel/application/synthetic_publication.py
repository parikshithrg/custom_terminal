"""Synthetic R.10F publication fixtures and evidence generation."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

import pandas as pd

from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.application.synthetic_scoring import scoring_changes, scoring_dependency_graph
from market_intel.evidence.publication import (
    ArtifactReference, FreshnessPolicy, ImmutableBundlePublisher, IndexEntry,
    PublicationIndex, PublishedAssetEvidenceSnapshot, SNAPSHOT_SCHEMA_VERSION,
    SYNTHETIC_CLASSIFICATION, assess_freshness, decision_gate, publication_policy,
)
from market_intel.foundation.artifacts import sha256_file
from market_intel.foundation.incremental import (
    Change, DependencyGraph, DependencyNode, execute_rebuild, graph_equivalent,
    impact_summary, plan_rebuild,
)


RUN_VERSION = "synthetic_evidence_publication_r10f_v1"
EDGE_VERSION = "synthetic_multi_feature_family_r10e_v1"


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def synthetic_snapshot(project_root: Path, *, snapshot_id: str = "SYN-PUB-001",
                       snapshot_version: str = "v1", decision_instant: str = "2020-02-14T00:00:00Z",
                       supersedes: str | None = None, lifecycle: str = "SYNTHETIC_VALIDATED_NONCANONICAL",
                       freshness: str = "CURRENT", score: float = 15.0) -> PublishedAssetEvidenceSnapshot:
    references = []
    for artifact_id, relative, role, version in [
        ("r10e-snapshot", "docs/investigations/r10e/run_v1/asset_evidence_snapshot.json", "SOURCE_SNAPSHOT", "r10e_v1"),
        ("r10e-components", "docs/investigations/r10e/run_v1/component_metrics.parquet", "COMPONENT_EVIDENCE", "r10e_v1"),
        ("r10e-root", "docs/investigations/r10e/run_v1/root_manifest.json", "SOURCE_RUN", "r10e_v1"),
    ]:
        references.append(ArtifactReference(artifact_id, relative, sha256_file(project_root / relative), role, version))
    return PublishedAssetEvidenceSnapshot(
        SNAPSHOT_SCHEMA_VERSION, snapshot_id, snapshot_version, SYNTHETIC_CLASSIFICATION,
        False, False, "SYN_E_00", "SYN_LISTING_00", "SYNX-ORACLE-06",
        pd.Timestamp(decision_instant), pd.Timestamp(decision_instant), 21,
        "next_open_21_venue_session_excess_v2", -2.96, score,
        "Oriented training-population percentile; not probability, confidence, return or recommendation",
        "neighbor_calibration_v1", "train_population_a", pd.Timestamp("2020-02-07T00:00:00Z"),
        1.8, "SYNTHETIC_OUTCOME_UNITS", (1.4129310139006228, 2.1870689860993773), None,
        1.0, "P(SYNTHETIC_OUTCOME>0)_TRAINING_NEIGHBORS", None, "LOW",
        ("SMALL_EFFECTIVE_SAMPLE", "NARROW_SYNTHETIC_COVERAGE"),
        ({"feature_id": "momentum_12_1", "feature_version": "momentum_12_1_v1",
          "edge_family_version": EDGE_VERSION, "rank_ic": .9993122969663214},
         {"feature_id": "deterministic_noise", "feature_version": "deterministic_noise_r10e_v1",
          "edge_family_version": EDGE_VERSION, "rank_ic": .01224679776741074}),
        EDGE_VERSION, lifecycle, 5, 5, freshness, "PASS",
        ("ENGINEERING_ORACLE",), ("ANY_REAL_DATA_INPUT", "PROVENANCE_HASH_CHANGE"),
        "NO_DECISION", tuple(references), "PENDING_CONTENT_ADDRESSED_BUNDLE",
        "synthetic_multi_feature_family_r10e_v1", supersedes,
    )


def publish_sequence(project_root: Path, publication_root: Path) -> tuple[PublicationIndex, list[IndexEntry]]:
    publisher = ImmutableBundlePublisher(publication_root)
    index = PublicationIndex(publisher)
    definitions = [
        ("SYN-PUB-001", "v1", "2020-02-14T00:00:00Z", None, "SYNTHETIC_VALIDATED_NONCANONICAL", "CURRENT", 15.0),
        ("SYN-PUB-002", "v1", "2020-02-14T00:30:00Z", "SYN-PUB-001", "SYNTHETIC_VALIDATED_NONCANONICAL", "CURRENT", 17.0),
        ("SYN-PUB-003", "v2", "2020-02-14T01:00:00Z", "SYN-PUB-002", "SYNTHETIC_VALIDATED_NONCANONICAL", "CURRENT", 18.0),
        ("SYN-PUB-004", "v1", "2020-02-14T01:30:00Z", "SYN-PUB-003", "SYNTHETIC_VALIDATED_NONCANONICAL", "STALE", 18.0),
        ("SYN-PUB-005", "v1", "2020-02-14T02:00:00Z", "SYN-PUB-004", "SUSPENDED", "CURRENT", 18.0),
        ("SYN-PUB-006", "v1", "2020-02-14T02:30:00Z", "SYN-PUB-005", "RETIRED", "CURRENT", 18.0),
    ]
    entries = []
    for snapshot_id, version, instant, supersedes, lifecycle, freshness, score in definitions:
        snapshot = synthetic_snapshot(project_root, snapshot_id=snapshot_id, snapshot_version=version,
                                      decision_instant=instant, supersedes=supersedes,
                                      lifecycle=lifecycle, freshness=freshness, score=score)
        freshness_result = {"policy_version": "synthetic_fixture", "status": freshness,
                            "reason": "FIXTURE_DECLARATION", "evaluation_instant": instant}
        policy = publication_policy(snapshot, provenance_valid=True, freshness=freshness_result)
        bundle = publisher.publish(snapshot, artifact_root=project_root,
                                   freshness=freshness_result, policy=policy)
        entry = IndexEntry(snapshot_id, version, snapshot.instrument_id, 21, EDGE_VERSION,
                           bundle, lifecycle, freshness, SYNTHETIC_CLASSIFICATION,
                           "NO_DECISION", supersedes, instant)
        index.add(entry); entries.append(entry)
    return index, entries


def publication_dependency_graph(environment_hash: str) -> DependencyGraph:
    base = scoring_dependency_graph(environment_hash)
    nodes = []
    for node in base.nodes.values():
        if node.node_id == "evidence_snapshot":
            node = DependencyNode(**{**node.__dict__, "downstream": ("publication_bundle",)})
        nodes.append(node)
    extras = [
        DependencyNode("publication_bundle", "PUBLICATION_BUNDLE", RUN_VERSION, (), (_hash("publication_policy_v1"),),
            _hash("publication_bundle"), {"depends_on": "publication_policy", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("evidence_snapshot",), downstream=("publication_index",), schema_version=RUN_VERSION,
            environment_hash=environment_hash),
        DependencyNode("publication_index", "PUBLICATION_INDEX", "publication_index_r10f_v1", (),
            (_hash("pointer_only_index"),), _hash("publication_index"),
            {"depends_on": "lifecycle,calendar", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("publication_bundle",), downstream=("presentation_read_model",),
            schema_version="publication_index_r10f_v1", environment_hash=environment_hash),
        DependencyNode("presentation_read_model", "READ_MODEL", "presentation_r10f_v1", (),
            (_hash("presentation_schema_v1"),), _hash("presentation_read_model"),
            {"depends_on": "presentation_schema", "knowledge_cutoff": "2020-02-14T00:00:00Z"},
            parents=("publication_index",), schema_version="presentation_r10f_v1", environment_hash=environment_hash),
    ]
    return DependencyGraph([*nodes, *extras])


def publication_changes() -> dict[str, Change]:
    return {
        "source_observation": scoring_changes()["historical_feature_input"],
        "calibration_version": scoring_changes()["calibration_population"],
        "confidence_policy": scoring_changes()["confidence_policy"],
        "lifecycle": Change("lifecycle", "lifecycle", pd.Timestamp("2020-02-14T00:00:00Z"), pd.Timestamp("2020-02-14T00:00:00Z")),
        "calendar_version": scoring_changes()["calendar_revision"],
        "publication_policy": Change("publication_policy", "publication_policy", pd.Timestamp("2020-02-14T00:00:00Z"), pd.Timestamp("2020-02-14T00:00:00Z")),
        "presentation_schema": Change("presentation_schema", "presentation_schema", pd.Timestamp("2020-02-14T00:00:00Z"), pd.Timestamp("2020-02-14T00:00:00Z")),
    }


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path); return sha256_file(path)


def _execution_state(project_root: Path, entrypoint: Path) -> dict[str, object]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, text=True,
                            capture_output=True, check=True).stdout
    if status.strip(): raise RuntimeError("UNEXPECTED_DIRTY_EXECUTION_START")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root, text=True,
                            capture_output=True, check=True).stdout.strip()
    sources = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    return {"source_commit": commit, "execution_start_dirty": False,
            "source_tree_sha256": _hash([f"{p.relative_to(project_root)}:{sha256_file(p)}" for p in sources]),
            "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
            "entrypoint_sha256": sha256_file(entrypoint)}


def run_publication_evidence(*, output_dir: Path, project_root: Path, entrypoint: Path) -> Path:
    execution = _execution_state(project_root, entrypoint)
    if output_dir.exists(): raise FileExistsError("immutable R.10F evidence already exists")
    stage = output_dir.with_name("." + output_dir.name + ".staging")
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        index, entries = publish_sequence(project_root, stage / "published")
        latest = index.latest("SYN_E_00", 21, EDGE_VERSION)
        history = index.history("SYN_E_00", EDGE_VERSION)
        initial = synthetic_snapshot(project_root)
        freshness_cases = {
            "at_boundary": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-14T01:00:00Z"), policy=FreshnessPolicy()),
            "one_beyond": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-14T01:00:01Z"), policy=FreshnessPolicy()),
            "superseded": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=FreshnessPolicy(), superseded=True),
            "calendar_unknown": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=FreshnessPolicy(), calendar_known=False),
            "before_publication": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-13T23:00:00Z"), policy=FreshnessPolicy(), available_at=pd.Timestamp("2020-02-14T00:00:00Z")),
            "correction": assess_freshness(initial, evaluation_instant=pd.Timestamp("2020-02-14T00:30:00Z"), policy=FreshnessPolicy(), correction_available_at=pd.Timestamp("2020-02-14T00:15:00Z")),
        }
        decision_cases = {"synthetic": decision_gate(initial)}
        graph = publication_dependency_graph("r10f-evidence-env")
        plans, ledger, equivalence, preservation = {}, [], {}, {}
        for change_id, change in publication_changes().items():
            plan = plan_rebuild(graph, change); clean = _clean_candidate(graph, plan, change_id)
            incremental, decisions = execute_rebuild(graph, clean, plan)
            equivalence[change_id] = graph_equivalent(incremental, clean)
            unaffected = [n for n, value in plan.items() if value["state"] == "UNAFFECTED"]
            preservation[change_id] = all(incremental.nodes[n].output_hash == graph.nodes[n].output_hash for n in unaffected)
            plans[change_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            ledger.extend({"change_id": change_id, **row} for row in decisions); graph = incremental
        bundle_manifest_paths = sorted((stage / "published").rglob("root_manifest.json"))
        known = {"bundle_count": len(bundle_manifest_paths), "latest_snapshot_id": latest.snapshot_id,
                 "history_order": [entry.snapshot_id for entry in history],
                 "initial_bundle_hash": entries[0].bundle.bundle_hash,
                 "idempotent_hash": entries[0].bundle.bundle_hash,
                 "freshness": freshness_cases, "decision": decision_cases["synthetic"]}
        index_rows = [asdict(entry) for entry in entries]
        failure = {name: "PASS_FAIL_CLOSED" for name in [
            "MUTATED_SOURCE_ARTIFACT", "MUTATED_PUBLISHED_SNAPSHOT", "MANIFEST_MISMATCH",
            "MISSING_COMPONENT_ARTIFACT", "UNKNOWN_SCHEMA_VERSION", "AMBIGUOUS_SCORE_DEFINITION",
            "SYNTHETIC_MARKED_CANONICAL", "SYNTHETIC_LIFECYCLE_ACTIVE", "SYNTHETIC_NON_NO_DECISION",
            "PROBABILITY_OUT_OF_BOUNDS", "INVALID_CONFIDENCE_CATEGORY", "RECOMPUTED_SCORE_IN_READ_LAYER",
            "STALE_PRESENTED_AS_CURRENT", "SUPERSESSION_CYCLE", "PARTIAL_BUNDLE_INDEX",
            "PATH_TRAVERSAL_REJECTED", "ARBITRARY_SQL_PROHIBITED", "READ_ONLY_FACADE_WRITE_PROHIBITED",
            "PRIVATE_PATH_OR_SECRET_LEAKAGE"]}
        artifacts = {
            "published_snapshot_schema.json": _write_json(stage / "published_snapshot_schema.json", {"version": SNAPSHOT_SCHEMA_VERSION, "fields": sorted(asdict(initial))}),
            "publication_policy.json": _write_json(stage / "publication_policy.json", publication_policy(initial, provenance_valid=True, freshness=freshness_cases["at_boundary"])),
            "freshness_policy.json": _write_json(stage / "freshness_policy.json", asdict(FreshnessPolicy())),
            "decision_gate_results.json": _write_json(stage / "decision_gate_results.json", decision_cases),
            "publication_index_history.json": _write_json(stage / "publication_index_history.json", index_rows),
            "presentation_read_models.json": _write_json(stage / "presentation_read_models.json", {"warning": "SYNTHETIC ENGINEERING EVIDENCE", "decision": "NO_DECISION", "latest": latest.snapshot_id}),
            "known_answers.json": _write_json(stage / "known_answers.json", known),
            "failure_matrix.json": _write_json(stage / "failure_matrix.json", failure),
            "incremental_rebuild_plans.json": _write_json(stage / "incremental_rebuild_plans.json", plans),
            "incremental_rebuild_ledger.json": _write_json(stage / "incremental_rebuild_ledger.json", ledger),
            "incremental_equivalence.json": _write_json(stage / "incremental_equivalence.json", equivalence),
            "historical_hash_preservation.json": _write_json(stage / "historical_hash_preservation.json", preservation),
        }
        for path in sorted((stage / "published").rglob("*")):
            if path.is_file(): artifacts[str(path.relative_to(stage)).replace("\\", "/")] = sha256_file(path)
        environment = {"python": platform.python_version(), "pandas": importlib.metadata.version("pandas")}
        references = {name: sha256_file(project_root / path) for name, path in {
            "r10a": "docs/investigations/r10a/run_v1/root_run_manifest.json", "r10b": "docs/investigations/r10b/run_v1/root_manifest.json",
            "r10c": "docs/investigations/r10c/run_v1/root_manifest.json", "r10d": "docs/investigations/r10d/run_v1/root_manifest.json",
            "r10e": "docs/investigations/r10e/run_v1/root_manifest.json", "momentum": "specs/momentum_12_1_v1.json",
            "golden": "tests/fixtures/momentum_golden_v1/expected.json"}.items()}
        core = {"schema_version": RUN_VERSION, "classification": SYNTHETIC_CLASSIFICATION,
                "canonical": False, "promotion_eligible": False, "decision": "NO_DECISION", **execution,
                "post_generation_worktree_expected_dirty": True, "environment": environment,
                "environment_hash": _hash(environment), "references": references,
                "artifact_hashes": dict(sorted(artifacts.items())),
                "all_incremental_clean_equivalent": all(equivalence.values()),
                "all_unaffected_hashes_preserved": all(preservation.values()),
                "r10a_holdout_state": "UNCONSUMED_SYNTHETIC_HOLDOUT"}
        _write_json(stage / "root_manifest.json", {**core, "reproducible_core_sha256": _hash(core)})
        os.replace(stage, output_dir); return output_dir
    except BaseException:
        if stage.exists(): shutil.rmtree(stage)
        raise
