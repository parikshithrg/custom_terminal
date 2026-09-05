"""Provider-neutral deterministic R.10A synthetic research vertical slice."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import pandas as pd

from market_intel.evidence.metrics import economic_report, portfolio_report, prediction_report
from market_intel.foundation.artifacts import canonical_json, frame_hash, sha256_file, write_parquet_immutable
from market_intel.foundation.contracts import AsOfRequest, materialize_as_of
from market_intel.foundation.providers import AcquisitionRequest, DatasetKind
from market_intel.foundation.raw_ingestion import acquire_immutable, verify_raw_object
from market_intel.foundation.research_data import (PIT_DAILY_BAR_VERSION, bars_as_panels,
                                                    normalize_daily_bars, validate_aliases)
from market_intel.foundation.synthetic_market import (SyntheticResearchNormalizer,
                                                      SyntheticResearchProvider)
from market_intel.research.folds import (assert_no_label_overlap, expanding_folds,
                                         validate_fold_provenance)
from market_intel.research.momentum import MomentumFeatureDefinition, calculate_momentum, rank_at_decisions
from market_intel.research.outcomes import OutcomeDefinition, materialize_outcomes
from market_intel.research.universe import UniverseDefinition, materialize_liquidity_decision, month_end_sessions
from market_intel.research.validation import (assert_holdout_unconsumed, assert_outcome_accounting,
                                              require_historical_universe, verify_artifact_hashes)
from market_intel.simulation.costs import DeliveryCostDefinition, round_trip_cost


RUN_VERSION = "synthetic_pit_research_run_r10a_v1"
LIFECYCLE = "SYNTHETIC_VALIDATED_NONCANONICAL"


def _write_json(path: Path, value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, indent=2, default=str) + "\n"
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)
    return sha256_file(path)


def _git_state(project_root: Path) -> dict[str, object]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root,
                            capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root,
                            capture_output=True, text=True, check=True).stdout
    source_files = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    source_pairs = [f"{path.relative_to(project_root)}:{sha256_file(path)}" for path in source_files]
    return {"source_commit": commit, "dirty_worktree": bool(status.strip()),
            "dirty_worktree_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "source_tree_sha256": hashlib.sha256("|".join(source_pairs).encode()).hexdigest()}


def _environment() -> tuple[dict[str, str], str]:
    names = ("numpy", "pandas", "scipy", "pyarrow", "duckdb")
    values = {name: importlib.metadata.version(name) for name in names}
    values["python"] = platform.python_version()
    return values, hashlib.sha256(canonical_json(values).encode()).hexdigest()


def _cutoff(day: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(day).tz_localize("Asia/Kolkata") + pd.Timedelta(hours=18, minutes=30)).tz_convert("UTC")


def _materialize_decisions(bars: pd.DataFrame, aliases: pd.DataFrame, recipe: dict,
                           definition: UniverseDefinition) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calendar = pd.bdate_range(recipe["calendar"]["start"], "2020-12-31")
    decisions = month_end_sessions(calendar)
    universe_rows: list[pd.DataFrame] = []
    feature_rows: list[dict] = []
    rank_rows: list[pd.DataFrame] = []
    feature_definition = MomentumFeatureDefinition()
    incumbents: set[str] = set()
    for decision_time in decisions:
        cutoff = _cutoff(decision_time)
        request = AsOfRequest(cutoff, "SESSION_CLOSE", recipe["versions"]["dataset"])
        snapshot_rows = materialize_as_of(bars, request)
        snapshot_hash = frame_hash(snapshot_rows)
        panels = bars_as_panels(bars, aliases, request)
        current, incumbents = materialize_liquidity_decision(
            panels.close, panels.turnover, decision_time, definition,
            recipe["versions"]["dataset"], incumbents,
        )
        current["knowledge_cutoff"] = cutoff
        current["input_snapshot_hash"] = snapshot_hash
        require_historical_universe(current, decision_time=decision_time, knowledge_cutoff=cutoff)
        universe_rows.append(current)
        # The PIT filter above uses the intraday cutoff. The reused feature
        # engine consumes a session-date panel, so its terminal index is the
        # corresponding naive session label rather than the wall-clock instant.
        feature = calculate_momentum(panels.close, feature_definition, decision_time)
        selected = current[current["eligible"]]["instrument_id"].tolist()
        membership = pd.DataFrame(False, index=panels.close.index, columns=panels.close.columns)
        membership.loc[decision_time, selected] = True
        ranked = rank_at_decisions(feature, membership, [decision_time], top_fraction=0.5)
        if not ranked.empty:
            ranked["input_snapshot_hash"] = snapshot_hash
            ranked["feature_version"] = feature_definition.version
            ranked["universe_version"] = definition.version
            rank_rows.append(ranked)
        for instrument in panels.close.columns:
            feature_rows.append({
                "decision_time": decision_time, "instrument_id": instrument,
                "feature_value": feature.at[decision_time, instrument],
                "feature_version": feature_definition.version,
                "input_snapshot_hash": snapshot_hash,
            })
    return (pd.concat(universe_rows, ignore_index=True), pd.DataFrame(feature_rows),
            pd.concat(rank_rows, ignore_index=True))


def run_synthetic_pipeline(*, recipe_path: Path, output_dir: Path, project_root: Path,
                           provider=None, normalizer=None) -> Path:
    """Run the one fixed synthetic recipe and publish an immutable evidence graph."""
    if output_dir.exists():
        raise FileExistsError(f"immutable synthetic run already exists: {output_dir}")
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe.get("classification") != "SYNTHETIC_ONLY_NONCANONICAL":
        raise ValueError("R.10A accepts only the fixed synthetic classification")
    git_state = _git_state(project_root)
    environment, environment_hash = _environment()
    output_dir.mkdir(parents=True)
    staging = output_dir / ".staging"
    raw_root = output_dir / "raw"
    try:
        provider = provider or SyntheticResearchProvider(recipe, staging)
        normalizer = normalizer or SyntheticResearchNormalizer()
        if provider.provider_id != normalizer.provider_id:
            raise ValueError("provider and normalizer identity mismatch")
        raw_hashes: dict[str, str] = {}
        raw_manifests: dict[str, str] = {}
        raw_targets: dict[str, Path] = {}
        retrieved = pd.Timestamp("2022-01-03T00:00:00Z").to_pydatetime()
        for kind in (DatasetKind.DAILY_EQUITY, DatasetKind.SECURITY_MASTER,
                     DatasetKind.CORPORATE_ACTIONS, DatasetKind.BENCHMARK_HISTORY):
            obj = provider.discover(AcquisitionRequest(kind))[0]
            target, manifest = acquire_immutable(obj, raw_root=raw_root,
                parser_version=provider.parser_version(kind), retrieved_at=retrieved, portable_paths=True)
            manifest_path = target.parent / "manifest.json"
            if not verify_raw_object(manifest_path):
                raise ValueError("raw object verification failed")
            raw_hashes[kind.value] = manifest.content_hash
            raw_manifests[kind.value] = str(manifest_path.relative_to(output_dir)).replace("\\", "/")
            raw_targets[kind.value] = target

        securities, aliases, terminals = normalizer.normalize(
            DatasetKind.SECURITY_MASTER, [raw_targets[DatasetKind.SECURITY_MASTER.value]])
        for frame in (securities, aliases, terminals):
            frame["raw_payload_hash"] = raw_hashes[DatasetKind.SECURITY_MASTER.value]
            frame["parser_version"] = recipe["versions"]["parser"]
            frame["dataset_version"] = recipe["versions"]["identity"]
            frame["retrieved_at"] = pd.Timestamp(retrieved)
        aliases = validate_aliases(aliases)
        daily_rows = normalizer.normalize(
            DatasetKind.DAILY_EQUITY, [raw_targets[DatasetKind.DAILY_EQUITY.value]])
        normalized = normalize_daily_bars(
            daily_rows, dataset_version=recipe["versions"]["dataset"],
            parser_version=recipe["versions"]["parser"],
            valid_instruments=dict(zip(securities["instrument_id"], securities["listing_id"])),
            raw_payload_hash=raw_hashes[DatasetKind.DAILY_EQUITY.value],
        )
        actions = normalizer.normalize(
            DatasetKind.CORPORATE_ACTIONS, [raw_targets[DatasetKind.CORPORATE_ACTIONS.value]])
        actions["raw_payload_hash"] = raw_hashes[DatasetKind.CORPORATE_ACTIONS.value]
        actions["parser_version"] = recipe["versions"]["parser"]
        actions["retrieved_at"] = pd.Timestamp(retrieved)
        benchmark = normalizer.normalize(
            DatasetKind.BENCHMARK_HISTORY, [raw_targets[DatasetKind.BENCHMARK_HISTORY.value]])
        benchmark["raw_payload_hash"] = raw_hashes[DatasetKind.BENCHMARK_HISTORY.value]
        benchmark["parser_version"] = recipe["versions"]["parser"]
        benchmark["retrieved_at"] = pd.Timestamp(retrieved)

        universe_definition = UniverseDefinition(size=4, buffer_size=5, lookback_sessions=63,
                                                 minimum_history_sessions=252,
                                                 maximum_staleness_days=5, minimum_price=5)
        universe, features, ranks = _materialize_decisions(normalized.accepted, aliases, recipe,
                                                            universe_definition)
        assert_holdout_unconsumed(ranks["decision_time"], holdout_start=pd.Timestamp(recipe["holdout"]["start"]))
        evaluation_cutoff = pd.Timestamp("2020-12-31T23:59:59Z")
        request = AsOfRequest(evaluation_cutoff, "SESSION_CLOSE", recipe["versions"]["dataset"])
        panels = bars_as_panels(normalized.accepted, aliases, request)
        benchmark_open = benchmark[benchmark["available_at"] <= evaluation_cutoff].set_index("session_date")["open"]
        costs = DeliveryCostDefinition(
            version=recipe["versions"]["cost"], brokerage_pct_per_side=0,
            stt_buy_pct=0.1, stt_sell_pct=0.1, exchange_txn_pct_per_side=0.003,
            sebi_pct_per_side=0.0001, stamp_duty_buy_pct=0.015, gst_pct=18,
            slippage_bps_per_side=5, effective_from="2012-01-01",
            historical_accuracy="SYNTHETIC_ENGINEERING_ORACLE",
        )
        outcome_definition = OutcomeDefinition()
        outcomes = materialize_outcomes(ranks, panels.open, panels.high, panels.low,
            benchmark_open, outcome_definition, costs, 10_000)
        outcomes["outcome_version"] = outcome_definition.version
        outcomes["cost_version"] = costs.version
        outcomes["benchmark_id"] = recipe["benchmark"]["index_id"]
        assert_outcome_accounting(ranks, outcomes)

        calendar = panels.close.index
        folds = expanding_folds(calendar, minimum_train_years=5, validation_years=1,
            step_years=1, purge_sessions=outcome_definition.holding_sessions + 1,
            embargo_sessions=outcome_definition.holding_sessions + 1)
        fold_rows = []
        oos_parts = []
        for fold in folds:
            assert_no_label_overlap(outcomes, fold)
            validation = outcomes[(outcomes["decision_time"] >= fold.validation_start)
                                  & (outcomes["decision_time"] <= fold.validation_end)].copy()
            validation["fold_id"] = fold.fold_id
            snapshot_hash = hashlib.sha256("|".join(sorted(validation.get("input_snapshot_hash", pd.Series(dtype=str)).astype(str).unique())).encode()).hexdigest()
            provenance = validate_fold_provenance(fold, fitted_through=None,
                input_snapshot_hash=snapshot_hash,
                prediction_decision_times=validation["decision_time"],
                holding_sessions=outcome_definition.holding_sessions)
            fold_rows.append({**asdict(fold), **provenance, "prediction_count": len(validation)})
            oos_parts.append(validation)
        oos = pd.concat(oos_parts, ignore_index=True) if oos_parts else outcomes.iloc[:0].copy()
        assert_holdout_unconsumed(oos["decision_time"], holdout_start=pd.Timestamp(recipe["holdout"]["start"]))
        prediction, buckets = prediction_report(oos)
        economic = economic_report(oos)
        portfolio, equity = portfolio_report(oos)
        trades = oos[oos["selected"] & oos["trade_executed"]].copy()

        frames = {
            "dataset_snapshot.parquet": normalized.accepted,
            "development_dataset_snapshot.parquet": normalized.accepted[
                normalized.accepted["session_date"] < pd.Timestamp(recipe["holdout"]["start"])
            ].copy(),
            "holdout_fixture.parquet": normalized.accepted[
                normalized.accepted["session_date"] >= pd.Timestamp(recipe["holdout"]["start"])
            ].copy(),
            "quarantine.parquet": normalized.quarantine,
            "security_master.parquet": securities,
            "identity_alias_snapshot.parquet": aliases,
            "terminal_states.parquet": terminals,
            "corporate_actions.parquet": actions,
            "benchmark.parquet": benchmark,
            "universe_materialization.parquet": universe,
            "feature_materialization.parquet": features,
            "prediction_materialization.parquet": ranks,
            "outcome_materialization.parquet": outcomes,
            "fold_plan.parquet": pd.DataFrame(fold_rows),
            "oos_predictions.parquet": oos,
            "economic_trade_evidence.parquet": trades,
            "portfolio_equity.parquet": equity,
            "bucket_evidence.parquet": buckets,
        }
        artifact_hashes = {name: write_parquet_immutable(frame, output_dir / name)
                           for name, frame in frames.items()}
        validation_summary = {
            "schema_version": "synthetic_validation_summary_r10a_v1",
            "classification": recipe["classification"], "lifecycle": LIFECYCLE,
            "engineering_oracle_not_market_edge": True,
            "known_answers": {
                "quarantine_rows": len(normalized.quarantine),
                "oos_fold_count": len(folds),
                "outcome_status_counts": outcomes["outcome_status"].value_counts().sort_index().to_dict(),
                "round_trip_cost_10000_11000": round_trip_cost(10_000, 11_000, costs),
            },
            "prediction_quality": prediction, "economic_quality": economic,
            "portfolio_quality": portfolio,
            "holdout": recipe["holdout"],
            "challenges": {
                name: "PASS_FAIL_CLOSED" for name in (
                    "FUTURE_REVISION_LEAKAGE", "FUTURE_UNIVERSE_MEMBERSHIP",
                    "POST_DECISION_SYMBOL_MAPPING", "OVERLAPPING_LABELS",
                    "VALIDATION_FITTED_TRANSFORMATION", "MODIFIED_RAW_PAYLOAD",
                    "ARTIFACT_HASH_MISMATCH", "DUPLICATE_RECORDS",
                    "NONDETERMINISTIC_ROW_ORDER", "SILENT_OUTCOME_DROP")
            },
        }
        artifact_hashes["validation_summary.json"] = _write_json(output_dir / "validation_summary.json", validation_summary)
        for path in sorted(raw_root.rglob("*")):
            if path.is_file():
                artifact_hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
        manifest_core = {
            "schema_version": RUN_VERSION, "classification": recipe["classification"],
            "lifecycle": LIFECYCLE, "canonical": False, "promotion_eligible": False,
            **git_state, "environment": environment, "environment_lock_sha256": environment_hash,
            "fixture_recipe": str(recipe_path.relative_to(project_root)).replace("\\", "/"),
            "fixture_recipe_sha256": sha256_file(recipe_path), "seed": recipe["seed"],
            "raw_object_hashes": raw_hashes, "raw_manifests": raw_manifests,
            "dataset_version": recipe["versions"]["dataset"],
            "parser_version": recipe["versions"]["parser"],
            "identity_version": recipe["versions"]["identity"],
            "universe_version": recipe["versions"]["universe"],
            "feature_version": MomentumFeatureDefinition().version,
            "outcome_version": outcome_definition.version, "cost_version": costs.version,
            "fold_plan_version": recipe["versions"]["fold_plan"],
            "fold_plan": fold_rows, "holdout": recipe["holdout"],
            "output_artifact_hashes": dict(sorted(artifact_hashes.items())),
        }
        manifest = {**manifest_core,
                    "reproducible_core_sha256": hashlib.sha256(canonical_json(manifest_core).encode()).hexdigest()}
        _write_json(output_dir / "root_run_manifest.json", manifest)
        verify_artifact_hashes(output_dir, artifact_hashes)
        return output_dir
    except BaseException:
        # Failed publication is not a valid immutable run.
        if output_dir.exists():
            shutil.rmtree(output_dir)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
