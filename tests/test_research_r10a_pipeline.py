"""Known-answer and adversarial tests for the R.10A synthetic PIT pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from market_intel.application.synthetic_pipeline import run_synthetic_pipeline
from market_intel.foundation.contracts import AsOfRequest, materialize_as_of
from market_intel.foundation.raw_ingestion import verify_raw_object
from market_intel.foundation.research_data import (normalize_daily_bars, resolve_alias,
                                                    validate_aliases)
from market_intel.foundation.synthetic_market import (SyntheticResearchNormalizer,
                                                      SyntheticResearchProvider,
                                                      generate_daily_rows,
                                                      generate_security_master)
from market_intel.research.folds import WalkForwardFold, validate_fold_provenance
from market_intel.research.momentum import rank_at_decisions
from market_intel.research.outcomes import OutcomeDefinition, materialize_outcomes
from market_intel.research.validation import (ResearchValidationError,
                                              assert_outcome_accounting,
                                              require_historical_universe,
                                              verify_artifact_hashes)
from market_intel.simulation.costs import DeliveryCostDefinition

ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = ROOT / "specs" / "synthetic_research_fixture_r10a_v1.json"


@pytest.fixture(scope="module")
def recipe():
    return json.loads(RECIPE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def normalized(recipe):
    rows = generate_daily_rows(recipe)
    return normalize_daily_bars(rows, dataset_version=recipe["versions"]["dataset"],
        parser_version=recipe["versions"]["parser"],
        valid_instruments={item["instrument_id"]: item["listing_id"] for item in recipe["instruments"]},
        raw_payload_hash="a" * 64)


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    output = tmp_path_factory.mktemp("r10a") / "run"
    return run_synthetic_pipeline(recipe_path=RECIPE_PATH, output_dir=output, project_root=ROOT)


def test_normalization_quarantines_without_silent_drop_and_orders_deterministically(recipe, normalized):
    assert len(normalized.quarantine) == 3
    flags = "|".join(normalized.quarantine["quality_flags"])
    assert flags.count("DUPLICATE_SOURCE_RECORD_ID") == 2
    assert "NON_POSITIVE_PRICE" in flags and "IMPOSSIBLE_OHLC" in flags
    reversed_result = normalize_daily_bars(list(reversed(generate_daily_rows(recipe))),
        dataset_version=recipe["versions"]["dataset"], parser_version=recipe["versions"]["parser"],
        valid_instruments={item["instrument_id"]: item["listing_id"] for item in recipe["instruments"]}, raw_payload_hash="a" * 64)
    pd.testing.assert_frame_equal(normalized.accepted, reversed_result.accepted)
    pd.testing.assert_frame_equal(normalized.quarantine, reversed_result.quarantine)


def test_as_of_revision_and_intraday_availability_are_causal(recipe, normalized):
    before = materialize_as_of(normalized.accepted, AsOfRequest(
        pd.Timestamp("2017-06-30T13:00:00Z"), "SESSION_CLOSE", recipe["versions"]["dataset"]))
    after = materialize_as_of(normalized.accepted, AsOfRequest(
        pd.Timestamp("2017-07-04T13:00:00Z"), "SESSION_CLOSE", recipe["versions"]["dataset"]))
    key = (pd.to_datetime(before["session_date"]) == pd.Timestamp("2017-06-15")) & (before["instrument_id"] == "SYN_I001")
    later_key = (pd.to_datetime(after["session_date"]) == pd.Timestamp("2017-06-15")) & (after["instrument_id"] == "SYN_I001")
    assert before.loc[key, "revision_number"].item() == 1
    assert after.loc[later_key, "revision_number"].item() == 2
    delayed = materialize_as_of(normalized.accepted, AsOfRequest(
        pd.Timestamp("2017-08-01T13:00:00Z"), "SESSION_CLOSE", recipe["versions"]["dataset"]))
    assert not ((delayed["instrument_id"] == "SYN_I002")
                & (pd.to_datetime(delayed["session_date"]) == pd.Timestamp("2017-08-01"))).any()
    with pytest.raises(ValueError, match="timezone-aware"):
        AsOfRequest(pd.Timestamp("2017-06-30"), "SESSION_CLOSE", recipe["versions"]["dataset"])


def test_bad_temporal_and_supersession_inputs_fail_closed(recipe):
    rows = generate_daily_rows(recipe)[:2]
    rows[0] = {**rows[0], "retrieved_at": rows[0]["published_at"] - pd.Timedelta(seconds=1)}
    result = normalize_daily_bars(rows, dataset_version=recipe["versions"]["dataset"],
        parser_version=recipe["versions"]["parser"], valid_instruments={"SYN_I001"}, raw_payload_hash="a" * 64)
    assert "RETRIEVED_BEFORE_PUBLICATION" in result.quarantine.iloc[0]["quality_flags"]
    bad = generate_daily_rows(recipe)[:2]
    bad[1] = {**bad[1], "revision_number": 2, "supersedes_record_id": "missing"}
    result = normalize_daily_bars(bad, dataset_version=recipe["versions"]["dataset"],
        parser_version=recipe["versions"]["parser"], valid_instruments={"SYN_I001"}, raw_payload_hash="a" * 64)
    assert result.quarantine["quality_flags"].str.contains("INVALID_SUPERSESSION_CHAIN").any()


def test_shared_as_of_contract_rejects_invalid_revision_chain(recipe, normalized):
    bad = normalized.accepted.head(2).copy()
    bad.loc[bad.index[1], "revision_number"] = 2
    bad.loc[bad.index[1], "supersedes_record_id"] = bad.iloc[0]["source_record_id"]
    with pytest.raises(ValueError, match="invalid supersession chain"):
        materialize_as_of(bad, AsOfRequest(
            pd.Timestamp("2022-01-03T00:00:00Z"), "SESSION_CLOSE",
            recipe["versions"]["dataset"],
        ))


def test_identity_rename_and_historical_disappearance_are_explicit(recipe):
    securities, aliases, terminal = generate_security_master(recipe)
    aliases = validate_aliases(aliases)
    assert resolve_alias(aliases, symbol="GAMMA_OLD", when=pd.Timestamp("2016-12-30T10:00:00Z")) == "SYN_I003"
    assert resolve_alias(aliases, symbol="GAMMA_NEW", when=pd.Timestamp("2017-01-03T10:00:00Z")) == "SYN_I003"
    with pytest.raises(LookupError):
        resolve_alias(aliases, symbol="GAMMA_OLD", when=pd.Timestamp("2017-01-03T10:00:00Z"))
    assert securities.set_index("instrument_id").at["SYN_I004", "status"] == "TERMINATED_UNRESOLVED"
    assert terminal.iloc[0]["resolution_status"] == "UNRESOLVED"


def test_alias_overlap_and_post_decision_mapping_reject(recipe):
    _, aliases, _ = generate_security_master(recipe)
    conflicting = pd.concat([aliases, pd.DataFrame([{
        "instrument_id": "SYN_OTHER", "listing_id": "SYN_L003", "symbol": "GAMMA_NEW",
        "valid_from": pd.Timestamp("2017-06-01T00:00:00Z"), "valid_to": pd.NaT,
        "source_id": "synthetic_formula_provider"}])], ignore_index=True)
    with pytest.raises(ValueError, match="overlapping alias"):
        validate_aliases(conflicting)
    with pytest.raises(LookupError):
        resolve_alias(aliases, symbol="GAMMA_NEW", when=pd.Timestamp("2016-12-30T10:00:00Z"))


def test_universe_feature_and_tie_known_answers(run_dir):
    universe = pd.read_parquet(run_dir / "universe_materialization.parquet")
    selected = universe[(universe["decision_time"] == pd.Timestamp("2019-06-28")) & universe["eligible"]]
    assert selected.sort_values("liquidity_rank")["instrument_id"].tolist() == ["SYN_I008", "SYN_I001", "SYN_I005", "SYN_I002"]
    assert universe[(universe["decision_time"] == pd.Timestamp("2019-06-28"))
                    & (universe["instrument_id"] == "SYN_I004")].iloc[0]["eligibility_reason"].startswith("STALE_OR_NOT_TRADING")
    features = pd.read_parquet(run_dir / "feature_materialization.parquet")
    value = features[(features["decision_time"] == pd.Timestamp("2019-06-28"))
                     & (features["instrument_id"] == "SYN_I001")].iloc[0]["feature_value"]
    assert value == pytest.approx(0.0835636122471537)
    late = universe[(universe["decision_time"] == pd.Timestamp("2016-01-29"))
                    & (universe["instrument_id"] == "SYN_I005")].iloc[0]
    assert "INSUFFICIENT_HISTORY" in late["eligibility_reason"]
    newest = universe[(universe["decision_time"] == pd.Timestamp("2020-01-31"))
                      & (universe["instrument_id"] == "SYN_I007")].iloc[0]
    assert "INSUFFICIENT_HISTORY" in newest["eligibility_reason"]
    day = pd.Timestamp("2020-01-31")
    feature = pd.DataFrame({"SYN_B": [1.0], "SYN_A": [1.0]}, index=[day])
    membership = pd.DataFrame(True, index=[day], columns=["SYN_B", "SYN_A"])
    tied = rank_at_decisions(feature, membership, [day], 0.5)
    assert tied.sort_values("rank")["instrument_id"].tolist() == ["SYN_A", "SYN_B"]


def test_outcome_timing_statuses_costs_and_trade_suppression(run_dir):
    outcomes = pd.read_parquet(run_dir / "outcome_materialization.parquet")
    missing = outcomes[(outcomes["decision_time"] == pd.Timestamp("2019-06-28"))
                       & (outcomes["instrument_id"] == "SYN_I008")].iloc[0]
    assert missing["entry_time"] == pd.Timestamp("2019-07-01")
    assert missing["outcome_status"] == "MISSING_ENTRY" and not missing["trade_executed"]
    unresolved = outcomes[(outcomes["decision_time"] == pd.Timestamp("2019-08-30"))
                          & (outcomes["instrument_id"] == "SYN_I008")].iloc[0]
    assert unresolved["entry_time"] == pd.Timestamp("2019-09-02")
    assert unresolved["exit_time"] == pd.Timestamp("2019-10-01")
    assert unresolved["outcome_status"] == "UNRESOLVED_DELISTING"
    summary = json.loads((run_dir / "validation_summary.json").read_text())
    assert summary["known_answers"]["round_trip_cost_10000_11000"] == pytest.approx(33.76818)
    assert summary["known_answers"]["outcome_status_counts"] == {
        "MISSING_ENTRY": 6, "RESOLVED": 394, "UNRESOLVED_DELISTING": 2}


def test_right_censor_and_silent_drop_are_explicit():
    dates = pd.bdate_range("2020-01-01", periods=10)
    ranks = pd.DataFrame([{"decision_time": dates[7], "instrument_id": "A",
        "feature_value": 1.0, "rank": 1, "percentile": 1.0, "selected": True}])
    prices = pd.DataFrame({"A": 100.0}, index=dates)
    result = materialize_outcomes(ranks, prices, prices + 1, prices - 1,
        pd.Series(200.0, index=dates), OutcomeDefinition(holding_sessions=3),
        DeliveryCostDefinition(), 10_000)
    assert result.iloc[0]["outcome_status"] == "RIGHT_CENSORED"
    with pytest.raises(ResearchValidationError, match="SILENT_OUTCOME_DROP"):
        assert_outcome_accounting(ranks, result.iloc[:0])


def test_fold_plan_is_purged_embargoed_oos_and_holdout_is_unconsumed(run_dir):
    folds = pd.read_parquet(run_dir / "fold_plan.parquet")
    assert len(folds) == 4
    assert set(folds["purge_sessions"]) == {22} and set(folds["embargo_sessions"]) == {22}
    assert set(folds["fit_scope"]) == {"NO_FITTED_PARAMETERS"}
    oos = pd.read_parquet(run_dir / "oos_predictions.parquet")
    assert oos["decision_time"].max() < pd.Timestamp("2021-01-01")
    assert set(oos["fold_id"]) == {"wf_01", "wf_02", "wf_03", "wf_04"}


def test_overlap_validation_fit_and_future_universe_challenges_fail_named():
    fold = WalkForwardFold("x", pd.Timestamp("2012-01-01"), pd.Timestamp("2016-12-30"),
                           pd.Timestamp("2017-02-01"), pd.Timestamp("2017-12-31"), 22, 22)
    with pytest.raises(AssertionError, match="VALIDATION_FITTED_TRANSFORMATION"):
        validate_fold_provenance(fold, fitted_through=pd.Timestamp("2017-03-01"),
            input_snapshot_hash="h", prediction_decision_times=[pd.Timestamp("2017-03-31")], holding_sessions=21)
    future = pd.DataFrame({"decision_time": [pd.Timestamp("2017-04-01")],
                           "knowledge_cutoff": [pd.Timestamp("2017-03-31T13:00:00Z")]})
    with pytest.raises(ResearchValidationError, match="FUTURE_UNIVERSE_MEMBERSHIP"):
        require_historical_universe(future, decision_time=pd.Timestamp("2017-03-31"),
                                    knowledge_cutoff=pd.Timestamp("2017-03-31T13:00:00Z"))


def test_raw_and_artifact_mutation_are_detected(run_dir, tmp_path):
    manifest = next((run_dir / "raw").rglob("manifest.json"))
    assert verify_raw_object(manifest)
    raw = manifest.parent / json.loads(manifest.read_text())["stored_payload"]
    original = raw.read_bytes()
    raw.write_bytes(original + b"mutation")
    assert not verify_raw_object(manifest)
    raw.write_bytes(original)
    assert verify_raw_object(manifest)
    artifact = tmp_path / "value.json"; artifact.write_text("one")
    with pytest.raises(ResearchValidationError, match="ARTIFACT_HASH_MISMATCH"):
        verify_artifact_hashes(tmp_path, {"value.json": hashlib.sha256(b"two").hexdigest()})


def test_provider_can_be_replaced_without_research_module_change(recipe, tmp_path):
    class ProviderProxy:
        provider_id = "synthetic_formula_provider"
        def __init__(self): self.delegate = SyntheticResearchProvider(recipe, tmp_path / "staging")
        def discover(self, request): return self.delegate.discover(request)
        def parser_version(self, dataset): return self.delegate.parser_version(dataset)
    class NormalizerProxy:
        provider_id = "synthetic_formula_provider"
        def normalize(self, dataset, paths): return SyntheticResearchNormalizer().normalize(dataset, paths)
    output = tmp_path / "replacement_run"
    run_synthetic_pipeline(recipe_path=RECIPE_PATH, output_dir=output, project_root=ROOT,
                           provider=ProviderProxy(), normalizer=NormalizerProxy())
    assert (output / "root_run_manifest.json").is_file()


def test_manifest_artifact_graph_and_portable_paths_reconcile(run_dir):
    manifest = json.loads((run_dir / "root_run_manifest.json").read_text())
    verify_artifact_hashes(run_dir, manifest["output_artifact_hashes"])
    assert not any(Path(path).is_absolute() for path in manifest["raw_manifests"].values())
    assert not manifest["canonical"] and not manifest["promotion_eligible"]
    assert manifest["feature_version"] == "momentum_12_1_v1"
    assert manifest["outcome_version"] == "next_open_21_session_excess_v1"
    holdout = pd.read_parquet(run_dir / "holdout_fixture.parquet")
    development = pd.read_parquet(run_dir / "development_dataset_snapshot.parquet")
    assert holdout["session_date"].min() >= pd.Timestamp("2021-01-01")
    assert development["session_date"].max() < pd.Timestamp("2021-01-01")


def test_equivalent_runs_have_identical_canonical_hashes(tmp_path):
    one = run_synthetic_pipeline(recipe_path=RECIPE_PATH, output_dir=tmp_path / "one", project_root=ROOT)
    two = run_synthetic_pipeline(recipe_path=RECIPE_PATH, output_dir=tmp_path / "two", project_root=ROOT)
    first = json.loads((one / "root_run_manifest.json").read_text())
    second = json.loads((two / "root_run_manifest.json").read_text())
    assert first["output_artifact_hashes"] == second["output_artifact_hashes"]
    assert first["reproducible_core_sha256"] == second["reproducible_core_sha256"]
