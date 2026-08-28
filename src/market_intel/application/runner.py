"""Mandatory-manifest experiment runner for Vertical Slice A."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from market_intel.evidence.metrics import economic_report, portfolio_report, prediction_report
from market_intel.evidence.baselines import baseline_distributions
from market_intel.foundation.artifacts import canonical_json, frame_hash, sha256_file, write_parquet_immutable
from market_intel.foundation.prices import PricePanels
from market_intel.foundation.quality import DatasetTrustContract, evaluate_requirements
from market_intel.research.folds import assert_no_label_overlap, expanding_folds
from market_intel.research.momentum import MomentumFeatureDefinition, calculate_momentum, rank_at_decisions
from market_intel.research.outcomes import OutcomeDefinition, materialize_outcomes
from market_intel.research.universe import UniverseDefinition, materialize_liquidity_universe
from market_intel.simulation.costs import DeliveryCostDefinition


def load_spec(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_fingerprint(project_root: Path) -> tuple[str, str, bool, str]:
    files = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    pairs = [f"{p.relative_to(project_root)}:{sha256_file(p)}" for p in files]
    tree_hash = hashlib.sha256("|".join(pairs).encode()).hexdigest()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_root, capture_output=True,
            text=True, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=project_root,
            capture_output=True, text=True, check=True,
        ).stdout
        dirty = bool(status.strip())
        dirty_hash = hashlib.sha256(status.encode()).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        commit, dirty, dirty_hash = "NO_GIT_METADATA", True, tree_hash
    return commit, tree_hash, dirty, dirty_hash


def _environment() -> tuple[dict[str, str], str]:
    names = ["numpy", "pandas", "scipy", "pyarrow", "duckdb"]
    versions = {name: importlib.metadata.version(name) for name in names}
    versions["python"] = platform.python_version()
    return versions, hashlib.sha256(canonical_json(versions).encode()).hexdigest()


def _json_write(path: Path, value: Any) -> str:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return sha256_file(path)


def run_momentum(
    *,
    panels: PricePanels,
    benchmark_open: pd.Series,
    spec: dict[str, Any],
    output_root: str | Path,
    project_root: str | Path,
    universe_definition: UniverseDefinition | None = None,
    dataset_trust: DatasetTrustContract | None = None,
    required_dataset_capabilities: tuple[str, ...] = (),
) -> Path:
    """Run fixed compatibility plus walk-forward evidence, always manifested."""
    project_root = Path(project_root)
    output_root = Path(output_root)
    spec_hash = hashlib.sha256(canonical_json(spec).encode()).hexdigest()
    source_commit, source_hash, dirty, dirty_hash = _source_fingerprint(project_root)
    environment, environment_hash = _environment()
    run_key = hashlib.sha256(
        f"{spec_hash}|{panels.snapshot.content_hash}|{source_hash}|{environment_hash}".encode()
    ).hexdigest()[:16]
    run_id = f"{spec['experiment_id']}_{run_key}"
    run_dir = output_root / run_id
    if run_dir.exists():
        raise FileExistsError(f"immutable run already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    from research_contracts.development import mark_development_output
    mark_development_output(
        run_dir,
        entrypoint="market_intel.application.runner.run_momentum (deprecated Slice A)",
    )

    feature_def = MomentumFeatureDefinition(
        lookback_sessions=int(spec["lookback_sessions"]),
        skip_sessions=int(spec["skip_sessions"]),
        minimum_history_sessions=int(spec["lookback_sessions"] + spec["skip_sessions"] + 1),
    )
    outcome_def = OutcomeDefinition(holding_sessions=int(spec["holding_sessions"]))
    cost_def = DeliveryCostDefinition()
    universe_def = universe_definition or UniverseDefinition()
    universe = materialize_liquidity_universe(
        panels.close, panels.turnover, universe_def, panels.snapshot.version
    )
    feature = calculate_momentum(panels.close, feature_def, panels.snapshot.knowledge_cutoff)
    research_start = pd.Timestamp(spec["research_start"])
    research_end = pd.Timestamp(spec["research_end"])
    decisions = sorted(
        d for d in pd.to_datetime(universe.decisions["decision_time"].unique())
        if research_start <= d <= research_end
    )
    # A universe decided at close T becomes active after T. At decision T the
    # legacy experiment therefore ranks the membership already in force from
    # the preceding rebalance. Keeping this convention is explicit parity,
    # not a same-bar look-ahead to the newly selected universe.
    decision_membership = universe.membership
    ranked = rank_at_decisions(feature, decision_membership, decisions, float(spec["top_fraction"]))
    outcomes = materialize_outcomes(
        ranked, panels.open, panels.high, panels.low, benchmark_open,
        outcome_def, cost_def, float(spec["target_value_per_trade"]),
    )

    research_calendar = panels.close.index[
        (panels.close.index >= research_start) & (panels.close.index <= research_end)
    ]
    folds = expanding_folds(
        research_calendar,
        minimum_train_years=int(spec["fold_plan"]["minimum_train_years"]),
        validation_years=int(spec["fold_plan"]["validation_years"]),
        step_years=int(spec["fold_plan"]["step_years"]),
        purge_sessions=int(spec["fold_plan"]["purge_sessions"]),
        embargo_sessions=int(spec["fold_plan"]["embargo_sessions"]),
    )
    fold_rows, oos_parts = [], []
    for fold in folds:
        assert_no_label_overlap(outcomes, fold)
        validation = outcomes[
            (outcomes["decision_time"] >= fold.validation_start)
            & (outcomes["decision_time"] <= fold.validation_end)
        ].copy()
        validation["fold_id"] = fold.fold_id
        oos_parts.append(validation)
        selected = validation[(validation["outcome_status"] == "RESOLVED") & validation["selected"] & validation["trade_executed"]]
        fold_rows.append({
            **asdict(fold), "n_selected": len(selected),
            "mean_net_excess_return_pct": float(selected["net_excess_return_pct"].mean()) if len(selected) else np.nan,
        })
    oos = pd.concat(oos_parts, ignore_index=True) if oos_parts else outcomes.iloc[:0].copy()
    prediction, buckets = prediction_report(oos)
    economic = economic_report(oos)
    portfolio, equity = portfolio_report(oos)
    baseline_seeds = [int(spec.get("seed", 42)) + i for i in range(30)]
    baselines, baseline_draws = baseline_distributions(oos, seeds=baseline_seeds)

    gates = spec["acceptance_gates"]
    positive_folds = [r for r in fold_rows if pd.notna(r["mean_net_excess_return_pct"])]
    positive_fraction = (
        sum(r["mean_net_excess_return_pct"] > 0 for r in positive_folds) / len(positive_folds)
        if positive_folds else 0.0
    )
    gate_results = {
        "survivorship_safe_dataset": panels.snapshot.survivorship_safe,
        "minimum_oos_decision_dates": prediction["effective_decision_dates"] >= gates["minimum_oos_decision_dates"],
        "mean_net_excess_return_positive": economic["mean_net_excess_return_pct"] > 0,
        "rank_ic_positive": prediction["mean_rank_ic"] > 0,
        "bucket_monotonic": bool(prediction["bucket_monotonic"]),
        "positive_fold_fraction": positive_fraction >= gates["positive_fold_fraction_minimum"],
        "no_unresolved_delistings": economic["unresolved_by_reason"].get("UNRESOLVED_DELISTING", 0) == 0,
    }
    trust_gate = (
        evaluate_requirements(dataset_trust, required_dataset_capabilities)
        if dataset_trust is not None
        else {"required_capabilities": list(required_dataset_capabilities),
              "capability_results": {}, "failed_or_unknown": {name: "UNKNOWN" for name in required_dataset_capabilities},
              "promotable": not required_dataset_capabilities}
    )
    gate_results["dataset_capability_contract"] = bool(trust_gate["promotable"])
    # Slice A is non-actionable by specification. A failed data-integrity gate
    # cannot be converted into a statistical rejection; it remains RESEARCHING.
    if not panels.snapshot.survivorship_safe or not trust_gate["promotable"]:
        state = "RESEARCHING"
    elif all(gate_results.values()):
        state = "RESEARCHING"  # confirmation required; never VALIDATED in Slice A
    else:
        state = "REJECTED"

    artifact_hashes = {}
    for name, frame in {
        "aliases": panels.aliases,
        "price_provenance": panels.provenance,
        "universe_decisions": universe.decisions,
        "feature_values": feature.stack(future_stack=True).rename("feature_value").reset_index().rename(columns={"level_0": "decision_time", "level_1": "instrument_id"}),
        "ranks_signals": ranked,
        "outcomes": outcomes,
        "oos_outcomes": oos,
        "folds": pd.DataFrame(fold_rows),
        "buckets": buckets,
        "equity_curve": equity,
        "baseline_draws": baseline_draws,
    }.items():
        artifact_hashes[f"{name}.parquet"] = write_parquet_immutable(frame, run_dir / f"{name}.parquet")
    reports = {
        "prediction": prediction, "economic": economic, "portfolio": portfolio,
        "baselines": baselines,
        "gate_results": gate_results, "positive_fold_fraction": positive_fraction,
        "dataset_trust_gate": trust_gate, "research_state": state, "non_actionable": True,
    }
    artifact_hashes["evidence.json"] = _json_write(run_dir / "evidence.json", reports)

    reproducible_core = {
        "run_id": run_id, "experiment_id": spec["experiment_id"],
        "code_commit": source_commit, "dirty_worktree": dirty,
        "dirty_worktree_fingerprint": dirty_hash,
        "source_tree_fingerprint": source_hash,
        "environment": environment, "environment_hash": environment_hash,
        "experiment_spec_hash": spec_hash,
        "input_dataset_snapshots": {panels.snapshot.dataset_id: asdict(panels.snapshot)},
        "universe_version": universe_def.version, "feature_version": feature_def.version,
        "outcome_version": outcome_def.version, "fold_definitions": fold_rows,
        "execution_cost_version": cost_def.version, "output_artifact_hashes": artifact_hashes,
        "research_state": state, "non_actionable": True,
        "dataset_trust_gate": trust_gate,
    }
    reproducible_hash = hashlib.sha256(canonical_json(reproducible_core).encode()).hexdigest()
    manifest = {
        **reproducible_core, "reproducible_core_hash": reproducible_hash,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _json_write(run_dir / "manifest.json", manifest)
    # R.4 deliberately does not update even the old SQLite run catalog. This
    # compatibility runner is useful only for synthetic regression tests and
    # its manifest is not a governed root_run_manifest_contract_v1 object.
    return run_dir
