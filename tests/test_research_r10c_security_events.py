"""Known-answer and adversarial tests for R.10C security-event semantics."""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.application.synthetic_security_events import (
    _event, generate_event_vintages, generate_identity_assertions, generate_raw_prices,
    known_terminal_results, _security_event_graph,
)
from market_intel.foundation.contracts import AsOfRequest
from market_intel.foundation.incremental import Change, execute_rebuild, graph_equivalent, plan_rebuild
from market_intel.foundation.security_events import (
    EVENT_DATASET_VERSION, IDENTITY_DATASET_VERSION, ConflictState, EventStatus, EventType,
    MissingObservationState, SecurityEventError, TerminalResolution, VerificationStatus,
    adjusted_price_view,
    adjustment_factors_v1, assert_acyclic_successors, event_as_of, identity_as_of,
    classify_missing_observation, integrate_terminal_outcomes, lifecycle_state,
    normalize_identity_assertions,
    normalize_security_events, resolve_symbol_as_of, resolve_terminal_economics,
    validate_successor_creation,
)


ROOT = Path(__file__).resolve().parents[1]


def _event_request(cutoff: str) -> AsOfRequest:
    return AsOfRequest(pd.Timestamp(cutoff), "SESSION_CLOSE", EVENT_DATASET_VERSION)


def _identity_request(cutoff: str) -> AsOfRequest:
    return AsOfRequest(pd.Timestamp(cutoff), "SESSION_CLOSE", IDENTITY_DATASET_VERSION)


@pytest.fixture(scope="module")
def events():
    return generate_event_vintages()


@pytest.fixture(scope="module")
def identities():
    return generate_identity_assertions()


def test_announced_event_is_known_before_effective_but_not_effective_early(events):
    view = event_as_of(events, _event_request("2020-01-15T12:00:00Z"),
                       economic_time=pd.Timestamp("2020-01-15T12:00:00Z"))
    split = view[view.event_id == "EV_SPLIT"].iloc[0]
    assert split.event_type == "SPLIT" and not split.is_effective
    later = event_as_of(events, _event_request("2020-02-04T12:00:00Z"),
                        economic_time=pd.Timestamp("2020-02-04T12:00:00Z"))
    assert later[later.event_id == "EV_SPLIT"].iloc[0].is_effective


def test_late_published_effective_event_never_leaks_into_earlier_knowledge(events):
    before = event_as_of(events, _event_request("2020-07-05T12:00:00Z"),
                         economic_time=pd.Timestamp("2020-07-05T12:00:00Z"))
    after = event_as_of(events, _event_request("2020-07-11T12:00:00Z"),
                        economic_time=pd.Timestamp("2020-07-11T12:00:00Z"))
    assert "EV_LATE" not in set(before.event_id)
    assert after[after.event_id == "EV_LATE"].iloc[0].is_effective


def test_cancellation_and_ratio_correction_preserve_prior_vintages(events):
    before_cancel = event_as_of(events, _event_request("2020-05-05T12:00:00Z"),
                                economic_time=pd.Timestamp("2020-05-05T12:00:00Z"))
    after_cancel = event_as_of(events, _event_request("2020-05-11T12:00:00Z"),
                               economic_time=pd.Timestamp("2020-05-11T12:00:00Z"))
    assert before_cancel[before_cancel.event_id == "EV_CANCEL"].iloc[0].event_status == "ACTIVE"
    assert after_cancel[after_cancel.event_id == "EV_CANCEL"].iloc[0].event_status == "CANCELLED"
    original = event_as_of(events, _event_request("2020-06-05T12:00:00Z"),
                           economic_time=pd.Timestamp("2020-06-05T12:00:00Z"))
    corrected = event_as_of(events, _event_request("2020-06-11T12:00:00Z"),
                            economic_time=pd.Timestamp("2020-06-11T12:00:00Z"))
    assert original[original.event_id == "EV_CORRECT"].iloc[0].adjustment_numerator == 2
    assert corrected[corrected.event_id == "EV_CORRECT"].iloc[0].adjustment_numerator == 3


def test_conflicting_sources_remain_visible_and_are_not_row_order_resolved(events):
    view = event_as_of(events, _event_request("2020-06-10T12:00:00Z"),
                       economic_time=pd.Timestamp("2020-06-10T12:00:00Z"))
    conflict = view[view.event_id == "EV_CONFLICT"]
    assert len(conflict) == 2
    assert set(conflict.adjustment_numerator) == {2, 3}
    assert set(conflict.conflict_state) == {ConflictState.CONFLICT}


def test_conflicting_terminal_classifications_remain_explicit():
    rows = [
        _event("EV_TERMINAL_CONFLICT", EventType.DELISTING, "SYN_C_I020",
               "2020-08-01T12:00:00Z", "2020-08-10T03:45:00Z", source="SYN_SOURCE_A",
               cash_consideration_per_share=50.0),
        _event("EV_TERMINAL_CONFLICT", EventType.DISAPPEARANCE, "SYN_C_I020",
               "2020-08-02T12:00:00Z", "2020-08-10T03:45:00Z", source="SYN_SOURCE_B",
               verification_status=VerificationStatus.UNRESOLVED.value),
    ]
    view = event_as_of(normalize_security_events(rows), _event_request("2020-08-03T12:00:00Z"),
                       economic_time=pd.Timestamp("2020-08-03T12:00:00Z"))
    assert len(view) == 2 and set(view.conflict_state) == {ConflictState.CONFLICT}


def test_rename_continuity_and_ticker_reuse_are_dated_and_identity_safe(identities):
    before = resolve_symbol_as_of(identities, exchange="SYNX", symbol="ORBIT_OLD",
                                  request=_identity_request("2020-02-01T12:00:00Z"),
                                  economic_time=pd.Timestamp("2020-02-01T12:00:00Z"))
    after = resolve_symbol_as_of(identities, exchange="SYNX", symbol="ORBIT_NEW",
                                 request=_identity_request("2020-03-03T12:00:00Z"),
                                 economic_time=pd.Timestamp("2020-03-03T12:00:00Z"))
    reused = resolve_symbol_as_of(identities, exchange="SYNX", symbol="ORBIT_OLD",
                                  request=_identity_request("2021-01-05T12:00:00Z"),
                                  economic_time=pd.Timestamp("2021-01-05T12:00:00Z"))
    assert before == after == "SYN_C_I001"
    assert reused == "SYN_C_I013"
    with pytest.raises(SecurityEventError, match="ALIAS_UNRESOLVED"):
        resolve_symbol_as_of(identities, exchange="SYNX", symbol="ORBIT_NEW",
                             request=_identity_request("2020-02-01T12:00:00Z"),
                             economic_time=pd.Timestamp("2020-02-01T12:00:00Z"))


def test_relisting_and_demerged_child_use_new_identity_and_no_precreation_history(identities):
    before_child = identity_as_of(identities, _identity_request("2020-04-05T12:00:00Z"),
                                  pd.Timestamp("2020-04-05T12:00:00Z"))
    after_child = identity_as_of(identities, _identity_request("2020-04-07T12:00:00Z"),
                                 pd.Timestamp("2020-04-07T12:00:00Z"))
    assert "SYN_C_I108" not in set(before_child.instrument_id)
    assert "SYN_C_I108" in set(after_child.instrument_id)
    relisted = identity_as_of(identities, _identity_request("2020-05-12T12:00:00Z"),
                              pd.Timestamp("2020-05-12T12:00:00Z"))
    assert "SYN_C_I011" not in set(relisted.instrument_id)
    assert "SYN_C_I012" in set(relisted.instrument_id)


def test_successor_creation_and_graph_are_valid(events, identities):
    assert_acyclic_successors(events)
    validate_successor_creation(events, identities)
    bad = events.copy()
    bad.loc[bad.event_id == "EV_SHARE_MERGER", "successor_instrument_id"] = "SYN_C_I005"
    with pytest.raises(SecurityEventError, match="CYCLIC_SUCCESSOR"):
        cycle = pd.concat([bad, pd.DataFrame([_event(
            "EV_BACK", EventType.SHARE_MERGER, "SYN_C_I105", "2020-03-02T12:00:00Z",
            "2020-04-02T03:45:00Z", successor_instrument_id="SYN_C_I005",
            share_numerator=1, share_denominator=1,
            ratio_orientation="SUCCESSOR_SHARES_PER_SOURCE_SHARES")])], ignore_index=True)
        assert_acyclic_successors(cycle)


@pytest.mark.parametrize("mutator,code", [
    (lambda row: row.update(cash_consideration_per_share=-1), "NEGATIVE_CASH_CONSIDERATION"),
    (lambda row: row.update(adjustment_numerator=0), "NON_POSITIVE_RATIO"),
    (lambda row: row.update(ratio_orientation=None), "MISSING_RATIO_ORIENTATION"),
    (lambda row: row.update(currency="XYZ"), "UNKNOWN_CURRENCY"),
])
def test_invalid_event_economics_fail_closed(mutator, code):
    row = _event("BAD", EventType.SPLIT, "SYN_C_I001", "2020-01-01T12:00:00Z",
                 "2020-02-01T03:45:00Z", adjustment_numerator=2,
                 adjustment_denominator=1, ratio_orientation="NEW_SHARES_PER_OLD_SHARES")
    mutator(row)
    with pytest.raises(SecurityEventError, match=code):
        normalize_security_events([row])


def test_identity_conflicts_and_intervals_fail_closed(identities):
    row = identities.iloc[0].to_dict()
    overlapping = {**row, "assertion_id": "OTHER", "source_record_id": "OTHER:r1",
                   "instrument_id": "SYN_OTHER", "issuer_id": "SYN_OTHER_ISSUER"}
    with pytest.raises(SecurityEventError, match="OVERLAPPING_ALIAS"):
        normalize_identity_assertions([row, overlapping])
    invalid = {**row, "valid_to": row["valid_from"]}
    with pytest.raises(SecurityEventError, match="INVALID_IDENTITY_INTERVAL"):
        normalize_identity_assertions([invalid])
    issuer_conflict = {**row, "assertion_id": "I2", "source_record_id": "I2:r1",
                       "symbol": "DIFFERENT", "issuer_id": "OTHER"}
    with pytest.raises(SecurityEventError, match="INSTRUMENT_MULTIPLE_ISSUERS"):
        normalize_identity_assertions([row, issuer_conflict])


def test_split_and_bonus_adjustments_are_exact_and_raw_prices_remain_unchanged(events):
    factors = adjustment_factors_v1(events[events.event_id.isin(["EV_SPLIT", "EV_BONUS"])])
    assert factors.set_index("event_id").at["EV_SPLIT", "price_factor"] == 0.5
    assert factors.set_index("event_id").at["EV_BONUS", "price_factor"] == pytest.approx(2 / 3)
    raw = generate_raw_prices()
    before = raw.copy(deep=True)
    adjusted = adjusted_price_view(raw, factors)
    pd.testing.assert_frame_equal(raw, before)
    pre = adjusted[(adjusted.instrument_id == "SYN_C_I001")
                   & (adjusted.event_time == pd.Timestamp("2020-01-31T10:00:00Z"))].iloc[0]
    assert pre.close == 50 and pre.volume == 2000


def test_dividend_rights_mergers_and_delisting_are_not_generic_adjustments(events):
    factors = adjustment_factors_v1(events[events.event_id.isin(
        ["EV_DIVIDEND", "EV_RIGHTS", "EV_SHARE_MERGER", "EV_DELIST"]
    )])
    assert factors.empty


def test_conflicting_or_unverified_adjustment_blocks_publication(events):
    with pytest.raises(SecurityEventError, match="ADJUSTMENT_PUBLICATION_BLOCKED"):
        adjustment_factors_v1(event_as_of(
            events, _event_request("2020-06-10T12:00:00Z"),
            economic_time=pd.Timestamp("2020-06-10T12:00:00Z")
        ).query("event_id == 'EV_CONFLICT'"))


def test_terminal_economic_known_answers(events):
    results = known_terminal_results(events)
    share = results["EV_SHARE_MERGER"]
    assert share.successor_quantity == 40 and share.total_proceeds == 2000
    assert share.resolution_status == TerminalResolution.RESOLVED_SUCCESSOR
    assert results["EV_CASH_MERGER"].total_proceeds == 12000
    mixed = results["EV_MIXED_MERGER"]
    assert mixed.successor_quantity == 25 and mixed.cash_amount == 2000
    assert mixed.total_proceeds == 4000 and mixed.resolution_status == TerminalResolution.RESOLVED_MIXED
    demerger = results["EV_DEMERGER"]
    assert demerger.successor_quantity == 33
    assert demerger.cash_amount == 10.0 and demerger.total_proceeds == 1990.0
    assert results["EV_DELIST"].total_proceeds == 7500
    assert results["EV_DISAPPEAR"].resolution_status == TerminalResolution.UNRESOLVED_TERMINAL
    assert results["EV_RIGHTS"].resolution_status == TerminalResolution.UNRESOLVED_TERMINAL


def test_missing_historical_successor_price_stays_unresolved(events):
    row = events[events.event_id == "EV_SHARE_MERGER"].iloc[0].to_dict()
    result = resolve_terminal_economics(row, quantity=100, successor_prices={})
    assert result.successor_quantity == 40
    assert result.total_proceeds is None
    assert result.resolution_status == TerminalResolution.UNRESOLVED_TERMINAL


def test_zero_recovery_requires_explicit_verified_declaration():
    declared = _event("EV_ZERO", EventType.DELISTING, "SYN_C_I020",
                      "2020-08-01T12:00:00Z", "2020-08-10T03:45:00Z",
                      zero_recovery_declared=True, settlement_at="2020-08-11T03:45:00Z")
    result = resolve_terminal_economics(declared, quantity=100)
    assert result.total_proceeds == 0
    assert result.resolution_status == TerminalResolution.RESOLVED_ZERO_RECOVERY
    undeclared = {**declared, "zero_recovery_declared": False,
                  "verification_status": VerificationStatus.UNRESOLVED.value}
    assert resolve_terminal_economics(undeclared, quantity=100).resolution_status == TerminalResolution.UNRESOLVED_TERMINAL


def test_suspension_resumption_and_disappearance_are_distinct(events):
    suspended = lifecycle_state(events, _event_request("2020-04-05T12:00:00Z"),
                                economic_time=pd.Timestamp("2020-04-05T12:00:00Z"),
                                instrument_id="SYN_C_I010")
    resumed = lifecycle_state(events, _event_request("2020-04-16T12:00:00Z"),
                              economic_time=pd.Timestamp("2020-04-16T12:00:00Z"),
                              instrument_id="SYN_C_I010")
    disappeared = lifecycle_state(events, _event_request("2020-04-21T12:00:00Z"),
                                   economic_time=pd.Timestamp("2020-04-21T12:00:00Z"),
                                   instrument_id="SYN_C_I011")
    assert (suspended, resumed, disappeared) == ("SUSPENDED", "ACTIVE", "UNRESOLVED_DISAPPEARANCE")


def test_missing_observation_terminal_states_are_not_conflated():
    assert classify_missing_observation(event_type=None) == MissingObservationState.ORDINARY_MISSING_OBSERVATION
    assert classify_missing_observation(event_type=EventType.SUSPENSION) == MissingObservationState.TEMPORARY_SUSPENSION
    assert classify_missing_observation(event_type=EventType.DISAPPEARANCE) == MissingObservationState.UNRESOLVED_DISAPPEARANCE
    assert classify_missing_observation(event_type=EventType.DELISTING) == MissingObservationState.PERMANENT_DELISTING
    assert classify_missing_observation(event_type=EventType.SHARE_MERGER) == MissingObservationState.MERGER_ACQUISITION
    assert classify_missing_observation(event_type=EventType.RELISTING) == MissingObservationState.RELISTING_NEW_IDENTITY
    assert classify_missing_observation(event_type=None, dataset_ended=True) == MissingObservationState.RIGHT_CENSORED


def test_outcome_integration_preserves_predictions_and_counts_unresolved(events):
    resolutions = known_terminal_results(events)
    outcomes = pd.DataFrame([
        {"prediction_id": "p1", "event_id": "EV_DELIST", "outcome_status": "MISSING_EXIT"},
        {"prediction_id": "p2", "event_id": "EV_DISAPPEAR", "outcome_status": "MISSING_EXIT"},
        {"prediction_id": "p3", "event_id": None, "outcome_status": "RIGHT_CENSORED"},
    ])
    result = integrate_terminal_outcomes(outcomes, resolutions)
    assert len(result) == 3 and set(result.prediction_id) == {"p1", "p2", "p3"}
    assert result.set_index("prediction_id").at["p1", "outcome_status"] == "RESOLVED_TERMINAL"
    assert result.set_index("prediction_id").at["p1", "terminal_proceeds"] == 7500
    assert result.set_index("prediction_id").at["p2", "outcome_status"] == "UNRESOLVED_TERMINAL"
    assert result.set_index("prediction_id").at["p3", "outcome_status"] == "RIGHT_CENSORED"


def test_incremental_event_changes_rebuild_only_causal_layers():
    graph = _security_event_graph("env")
    correction = Change("split_correction", "feature_input",
                        pd.Timestamp("2020-01-07T10:00:00Z"),
                        pd.Timestamp("2020-01-20T12:00:00Z"), instrument_id="SYN_C_I001")
    plan = plan_rebuild(graph, correction)
    assert plan["snapshot_pre"]["state"] == "UNAFFECTED"
    assert plan["event_knowledge_2019"]["state"] == "UNAFFECTED"
    assert plan["raw_price_history"]["state"] == "UNAFFECTED"
    assert plan["universe_post"]["state"] == "UNAFFECTED"
    assert plan["feature_post"]["state"] == "REBUILT_INPUT_CHANGED"
    clean = _clean_candidate(graph, plan, "split_correction")
    incremental, _ = execute_rebuild(graph, clean, plan)
    assert graph_equivalent(incremental, clean)
    assert incremental.nodes["snapshot_pre"].output_hash == graph.nodes["snapshot_pre"].output_hash


def test_terminal_evidence_resolves_outcome_without_rebuilding_prediction():
    graph = _security_event_graph("env")
    terminal = Change("terminal", "terminal", pd.Timestamp("2020-02-07T10:00:00Z"),
                      pd.Timestamp("2020-02-12T12:00:00Z"), instrument_id="SYN_C_I002")
    plan = plan_rebuild(graph, terminal)
    assert plan["prediction_post"]["state"] == "UNAFFECTED"
    assert plan["outcome_post"]["state"] == "REBUILT_INPUT_CHANGED"


def test_duplicate_event_identity_and_successor_before_creation_fail(events, identities):
    duplicate = pd.concat([events.iloc[[0]], events.iloc[[0]]], ignore_index=True)
    with pytest.raises(SecurityEventError, match="DUPLICATE_EVENT_RECORD_IDENTITY"):
        normalize_security_events(duplicate.to_dict("records"))
    bad = events.copy()
    bad.loc[bad.event_id == "EV_SHARE_MERGER", "effective_at"] = pd.Timestamp("2020-01-01T03:45:00Z")
    with pytest.raises(SecurityEventError, match="SUCCESSOR_EFFECTIVE_BEFORE_CREATION"):
        validate_successor_creation(bad, identities)


def test_event_supersession_cycles_fail_with_named_reason():
    first = _event("EV_CYCLE", EventType.SPLIT, "SYN_C_I030", "2020-01-01T12:00:00Z",
                   "2020-02-01T03:45:00Z", revision=2, record="cycle-a", parent="cycle-b",
                   adjustment_numerator=2, adjustment_denominator=1,
                   ratio_orientation="NEW_SHARES_PER_OLD_SHARES")
    second = _event("EV_CYCLE", EventType.SPLIT, "SYN_C_I030", "2020-01-02T12:00:00Z",
                    "2020-02-01T03:45:00Z", revision=2, record="cycle-b", parent="cycle-a",
                    adjustment_numerator=2, adjustment_denominator=1,
                    ratio_orientation="NEW_SHARES_PER_OLD_SHARES")
    with pytest.raises(SecurityEventError, match="EVENT_SUPERSESSION_CYCLE"):
        normalize_security_events([first, second])


def test_protected_momentum_and_prior_evidence_are_unchanged():
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r10b/run_v1/root_manifest.json": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }
    for relative, digest in expected.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == digest
