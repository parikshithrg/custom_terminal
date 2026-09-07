"""Known-answer and adversarial tests for R.10D session-clock semantics."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from market_intel.application.synthetic_calendar import (
    calendar_changes, calendar_dependency_graph, conflicting_calendar_vintage,
    generate_calendar_vintages, known_answers, settlement_rules,
)
from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.application.synthetic_security_events import generate_event_vintages
from market_intel.foundation.exchange_calendar import (
    CALENDAR_VERSION, SYNTHETIC_VENUE, AvailabilityPolicy, CalendarError,
    DecisionClock, DecisionReference, ResolutionStatus, SessionType,
    SettlementRule, calendar_as_of, clock_instant, effective_session,
    executable_sessions, information_available, month_end_session,
    previous_completed_session, resolve_session, session_distance,
    settlement_date, validate_calendar, validate_settlement_instant,
)
from market_intel.foundation.incremental import execute_rebuild, graph_equivalent, plan_rebuild
from market_intel.research.folds import session_ordinal_fold_boundaries
from market_intel.research.outcomes import (
    SessionAwareOutcomeDefinition, materialize_session_aware_outcomes,
)
from market_intel.research.validation import ResearchValidationError, require_shared_decision_clock


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def vintages():
    return generate_calendar_vintages()


@pytest.fixture(scope="module")
def final(vintages):
    return calendar_as_of(vintages, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
                          knowledge_cutoff=pd.Timestamp("2020-05-20T12:00:00Z"),
                          decision_clock=DecisionClock.SESSION_CLOSE)


def _as_of(vintages, cutoff):
    return calendar_as_of(vintages, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
                          knowledge_cutoff=pd.Timestamp(cutoff),
                          decision_clock=DecisionClock.SESSION_CLOSE)


def test_calendar_fixture_contains_all_declared_cases(vintages):
    assert vintages.local_session_date.min() == "2019-11-27"
    assert vintages.local_session_date.max() == "2020-05-13"
    assert set(vintages.session_type) >= {item.value for item in SessionType}
    assert "2020-02-29" in set(vintages.local_session_date)
    assert sum(vintages.local_session_date.eq("2020-01-15")) == 2


def test_timezone_conversion_and_exact_clock_boundaries(final):
    row = final[final.session_id == "SYNX-2020-01-06"].iloc[0]
    assert clock_instant(row, DecisionClock.SESSION_OPEN) == pd.Timestamp("2020-01-06T03:45:00Z")
    assert clock_instant(row, DecisionClock.SESSION_PRE_OPEN) == pd.Timestamp("2020-01-06T03:30:00Z")
    assert clock_instant(row, DecisionClock.POST_CLOSE_AVAILABLE) == pd.Timestamp("2020-01-06T10:30:00Z")
    assert clock_instant(row, DecisionClock.INTRADAY_WITH_EXPLICIT_TIME,
                         intraday_time=pd.Timestamp("2020-01-06T06:00:00Z")) == pd.Timestamp("2020-01-06T06:00:00Z")


def test_shortened_delayed_and_special_sessions_are_explicit(final):
    short = final[final.session_id == "SYNX-2019-12-31"].iloc[0]
    delayed = final[final.session_id == "SYNX-2020-01-02"].iloc[0]
    special = final[final.session_id == "SYNX-2019-12-28"].iloc[0]
    assert short.scheduled_close == pd.Timestamp("2019-12-31T07:00:00Z")
    assert delayed.scheduled_open == pd.Timestamp("2020-01-02T04:45:00Z")
    assert bool(special.trading_eligible) and not bool(special.settlement_eligible)


def test_month_end_uses_final_explicit_session(final):
    assert month_end_session(final, 2019, 11).session_id == "SYNX-2019-11-29"
    assert month_end_session(final, 2020, 2).session_id == "SYNX-2020-02-29"


def test_future_holiday_revision_does_not_leak_backward(vintages):
    before = _as_of(vintages, "2020-01-09T12:00:00Z")
    after = _as_of(vintages, "2020-01-11T12:00:00Z")
    assert bool(before[before.session_id == "SYNX-2020-01-27"].iloc[0].trading_eligible)
    assert not bool(after[after.session_id == "SYNX-2020-01-27"].iloc[0].trading_eligible)


def test_unexpected_closure_is_not_pretended_predictable(vintages):
    planned = _as_of(vintages, "2020-01-15T03:00:00Z")
    corrected = _as_of(vintages, "2020-01-17T12:00:00Z")
    assert planned[planned.session_id == "SYNX-2020-01-15"].iloc[0].session_type == "NORMAL"
    assert corrected[corrected.session_id == "SYNX-2020-01-15"].iloc[0].session_type == "UNEXPECTED_CLOSURE"
    assert not bool(corrected[corrected.session_id == "SYNX-2020-01-15"].iloc[0].occurred)


def test_future_time_revision_and_final_view_are_separate(vintages):
    before = _as_of(vintages, "2020-02-19T12:00:00Z")
    after = _as_of(vintages, "2020-02-21T12:00:00Z")
    assert before[before.session_id == "SYNX-2020-03-02"].iloc[0].scheduled_close == pd.Timestamp("2020-03-02T10:00:00Z")
    assert after[after.session_id == "SYNX-2020-03-02"].iloc[0].scheduled_close == pd.Timestamp("2020-03-02T07:30:00Z")


def test_conflicting_assertions_block_scheduling(vintages):
    conflict = conflicting_calendar_vintage(vintages)
    view = _as_of(conflict, "2020-03-01T12:00:00Z")
    assert set(view[view.session_id == "SYNX-2020-03-10"].conflict_state) == {"CONFLICT"}
    result = resolve_session(view, after=pd.Timestamp("2020-03-09T10:01:00Z"))
    assert result.status == ResolutionStatus.CALENDAR_CONFLICT


def test_next_and_nth_session_skip_nontrading_dates(final):
    entry = resolve_session(final, after=pd.Timestamp("2020-01-24T10:00:00Z"))
    exit_ = resolve_session(final, after=entry.instant, ordinal=21)
    assert entry.session_id == "SYNX-2020-01-28"
    assert exit_.session_id == "SYNX-2020-02-28"
    assert session_distance(final, entry.session_id, exit_.session_id) == 21


def test_previous_completed_session_and_no_future_status(final):
    previous = previous_completed_session(final, at=pd.Timestamp("2020-01-27T12:00:00Z"))
    assert previous.session_id == "SYNX-2020-01-24"
    assert resolve_session(final, after=pd.Timestamp("2020-05-13T10:01:00Z")).status == ResolutionStatus.NO_FUTURE_SESSION


def test_decision_reference_requires_exact_versioned_clock(final):
    DecisionReference(CALENDAR_VERSION, SYNTHETIC_VENUE, "SYNX-2020-01-06",
                      DecisionClock.SESSION_CLOSE, pd.Timestamp("2020-01-06T10:00:00Z")).validate(final)
    with pytest.raises(CalendarError, match="DECISION_INSTANT_OUTSIDE_SESSION"):
        DecisionReference(CALENDAR_VERSION, SYNTHETIC_VENUE, "SYNX-2020-01-06",
                          DecisionClock.SESSION_CLOSE, pd.Timestamp("2020-01-06T09:59:59Z")).validate(final)


def test_cross_section_uses_one_shared_decision_instant(final):
    rows = pd.DataFrame([
        {"instrument_id": "A", "decision_time": pd.Timestamp("2020-01-06T10:00:00Z"),
         "calendar_version": CALENDAR_VERSION, "venue": SYNTHETIC_VENUE,
         "session_id": "SYNX-2020-01-06", "decision_clock": "SESSION_CLOSE"},
        {"instrument_id": "B", "decision_time": pd.Timestamp("2020-01-06T10:00:00Z"),
         "calendar_version": CALENDAR_VERSION, "venue": SYNTHETIC_VENUE,
         "session_id": "SYNX-2020-01-06", "decision_clock": "SESSION_CLOSE"},
    ])
    require_shared_decision_clock(rows, final)
    rows.loc[1, "session_id"] = "SYNX-2020-01-07"
    with pytest.raises(ResearchValidationError, match="CROSS_SECTIONAL_CLOCK_MISMATCH"):
        require_shared_decision_clock(rows, final)


def test_availability_boundary_is_inclusive_and_retrieval_never_advances_it(final):
    policy = AvailabilityPolicy("p", "daily", 20, "NEXT_EXECUTABLE_SESSION_OPEN")
    eligible, available = information_available(
        published_at=pd.Timestamp("2020-01-24T10:00:00Z"),
        retrieved_at=pd.Timestamp("2020-01-25T10:00:00Z"), precision="INTRADAY",
        policy=policy, knowledge_cutoff=pd.Timestamp("2020-01-24T10:20:00Z"),
        calendar_view=final)
    assert eligible and available == pd.Timestamp("2020-01-24T10:20:00Z")
    assert not information_available(
        published_at=pd.Timestamp("2020-01-24T10:00:01Z"), retrieved_at=None,
        precision="INTRADAY", policy=policy,
        knowledge_cutoff=pd.Timestamp("2020-01-24T10:20:00Z"), calendar_view=final)[0]


def test_date_only_publication_uses_conservative_next_session(final):
    policy = AvailabilityPolicy("p", "event", 0, "NEXT_EXECUTABLE_SESSION_OPEN")
    _, available = information_available(
        published_at=pd.Timestamp("2020-01-24"), retrieved_at=None, precision="DATE_ONLY",
        policy=policy, knowledge_cutoff=pd.Timestamp("2020-01-28T03:45:00Z"), calendar_view=final)
    assert available == pd.Timestamp("2020-01-28T03:45:00Z")


def test_dataset_specific_lags_are_not_universal(final):
    short = AvailabilityPolicy("short", "benchmark", 10, "NEXT_EXECUTABLE_SESSION_OPEN")
    long = AvailabilityPolicy("long", "event", 60, "NEXT_EXECUTABLE_SESSION_OPEN")
    arguments = dict(published_at=pd.Timestamp("2020-01-24T10:00:00Z"), retrieved_at=None,
                     precision="INTRADAY", knowledge_cutoff=pd.Timestamp("2020-01-24T10:20:00Z"),
                     calendar_view=final)
    assert information_available(policy=short, **arguments)[0]
    assert not information_available(policy=long, **arguments)[0]


@pytest.mark.parametrize("published,retrieved,code", [
    (pd.Timestamp("2020-01-01"), None, "NAIVE_TIMESTAMP:published_at"),
    (pd.Timestamp("2020-01-01T10:00:00Z"), pd.Timestamp("2020-01-01T09:00:00Z"),
     "RETRIEVED_BEFORE_PUBLICATION"),
])
def test_invalid_publication_provenance_fails_closed(final, published, retrieved, code):
    with pytest.raises(CalendarError, match=code):
        information_available(published_at=published, retrieved_at=retrieved, precision="INTRADAY",
                              policy=AvailabilityPolicy("p", "d", 0, "NEXT_EXECUTABLE_SESSION_OPEN"),
                              knowledge_cutoff=pd.Timestamp("2020-01-02T00:00:00Z"), calendar_view=final)


def _outcome_inputs(final):
    sessions = executable_sessions(final)
    ids = list(sessions.session_id)
    opens = pd.DataFrame({"SYN_C_I001": np.arange(len(ids), dtype=float) + 100}, index=ids)
    benchmark = pd.Series(np.arange(len(ids), dtype=float) + 1000, index=ids)
    ranked = pd.DataFrame([{"prediction_id": "p1", "instrument_id": "SYN_C_I001",
                            "decision_session_id": "SYNX-2020-01-24", "selected": True}])
    return ranked, opens, benchmark


def test_session_aware_outcome_uses_shared_venue_entry_and_exit(final):
    ranked, opens, benchmark = _outcome_inputs(final)
    result = materialize_session_aware_outcomes(
        ranked, opens, benchmark, final, SessionAwareOutcomeDefinition()).iloc[0]
    assert result.entry_session_id == "SYNX-2020-01-28"
    assert result.exit_session_id == "SYNX-2020-02-28"
    assert result.outcome_status == "RESOLVED"


def test_missing_instrument_bar_does_not_shift_market_exit(final):
    ranked, opens, benchmark = _outcome_inputs(final)
    opens.loc["SYNX-2020-02-28", "SYN_C_I001"] = np.nan
    result = materialize_session_aware_outcomes(
        ranked, opens, benchmark, final, SessionAwareOutcomeDefinition()).iloc[0]
    assert result.exit_session_id == "SYNX-2020-02-28"
    assert result.outcome_status == "MISSING_EXIT_PRICE"


@pytest.mark.parametrize("state,status", [
    ("SUSPENDED", "INSTRUMENT_SUSPENDED"),
    ("NOT_LISTED", "LISTING_NOT_EFFECTIVE"),
    ("TERMINATED", "TERMINATED_BEFORE_ENTRY"),
])
def test_instrument_state_does_not_remove_market_session(final, state, status):
    ranked, opens, benchmark = _outcome_inputs(final)
    result = materialize_session_aware_outcomes(
        ranked, opens, benchmark, final, SessionAwareOutcomeDefinition(),
        instrument_states={("SYN_C_I001", "SYNX-2020-01-28"): state}).iloc[0]
    assert result.outcome_status == status and result.entry_session_id == "SYNX-2020-01-28"


def test_right_censoring_uses_calendar_end(final):
    ranked, opens, benchmark = _outcome_inputs(final)
    ranked.loc[0, "decision_session_id"] = "SYNX-2020-04-14"
    result = materialize_session_aware_outcomes(
        ranked, opens, benchmark, final, SessionAwareOutcomeDefinition()).iloc[0]
    assert result.outcome_status == "RIGHT_CENSORED"


def test_fold_boundaries_use_22_session_window(final):
    fold = session_ordinal_fold_boundaries(
        final, validation_boundary_session_id="SYNX-2020-02-10",
        validation_end_session_id="SYNX-2020-04-10", holding_sessions=21)
    sessions = executable_sessions(final)
    assert fold["purge_sessions"] == fold["embargo_sessions"] == 22
    positions = {sid: i for i, sid in enumerate(sessions.session_id)}
    assert positions[fold["validation_start_session_id"]] - positions["SYNX-2020-02-10"] == 22
    assert positions["SYNX-2020-02-10"] - positions[fold["train_end_session_id"]] == 23


def test_t_plus_two_and_t_plus_one_skip_settlement_closure(final):
    old = settlement_date(final, trade_session_id="SYNX-2020-01-30", rules=settlement_rules())
    new = settlement_date(final, trade_session_id="SYNX-2020-03-02", rules=settlement_rules())
    assert old.session_id == "SYNX-2020-02-06"
    assert new.session_id == "SYNX-2020-03-03"


def test_cash_and_share_legs_can_settle_on_different_sessions(final):
    cash = settlement_date(final, trade_session_id="SYNX-2020-03-02",
                           rules=settlement_rules(), leg="CASH")
    shares = settlement_date(final, trade_session_id="SYNX-2020-03-02",
                             rules=settlement_rules(), leg="SHARES")
    assert cash.session_id == "SYNX-2020-03-04"
    assert shares.session_id == "SYNX-2020-03-05"


def test_settlement_before_trade_fails_closed():
    with pytest.raises(CalendarError, match="SETTLEMENT_BEFORE_TRADE"):
        validate_settlement_instant(trade_at=pd.Timestamp("2020-01-02T10:00:00Z"),
                                    settlement_at=pd.Timestamp("2020-01-02T09:59:59Z"))


def test_security_event_effectiveness_resolves_holiday_explicitly(final):
    events = generate_event_vintages()
    split = events[events.event_id == "EV_SPLIT"].iloc[0]
    resolved = effective_session(final, effective_at=split.effective_at)
    assert split.effective_at == pd.Timestamp("2020-02-03T03:45:00Z")
    assert resolved.session_id == "SYNX-2020-02-05"


def test_security_event_clocks_remain_distinct(final):
    events = generate_event_vintages().set_index("event_id")
    merger = events.loc["EV_SHARE_MERGER"]
    delist = events.loc["EV_DELIST"]
    relist = events.loc["EV_RELIST"]
    assert merger.published_at < merger.effective_at < merger.settlement_at
    assert effective_session(final, effective_at=merger.effective_at).session_id == "SYNX-2020-04-01"
    assert delist.effective_at < delist.settlement_at
    assert effective_session(final, effective_at=relist.effective_at).session_id == "SYNX-2020-05-11"
    assert relist.source_instrument_id != relist.successor_instrument_id


def test_incremental_calendar_changes_are_minimal_and_clean_equivalent():
    graph = calendar_dependency_graph("env")
    for change in calendar_changes().values():
        plan = plan_rebuild(graph, change)
        clean = _clean_candidate(graph, plan, change.change_id)
        incremental, ledger = execute_rebuild(graph, clean, plan)
        assert graph_equivalent(incremental, clean)
        assert any(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger)
    settlement = plan_rebuild(graph, calendar_changes()["settlement_rule"])
    assert settlement["settlement"]["state"] == "REBUILT_INPUT_CHANGED"
    assert settlement["session_outcomes"]["state"] == "UNAFFECTED"


@pytest.mark.parametrize("mutator,code", [
    (lambda rows: rows.append(dict(rows[0])), "DUPLICATE_SOURCE_RECORD_ID"),
    (lambda rows: rows[0].update(scheduled_close=rows[0]["scheduled_open"]), "CLOSE_NOT_AFTER_OPEN"),
    (lambda rows: rows[0].update(scheduled_open="2020-01-01 09:15"), "NAIVE_TIMESTAMP:scheduled_open"),
    (lambda rows: rows[0].update(timezone="Unknown/Nowhere"), "UNKNOWN_TIMEZONE"),
    (lambda rows: rows[0].update(calendar_version=""), "MISSING_CALENDAR_VERSION"),
])
def test_malformed_calendar_contracts_fail_closed(vintages, mutator, code):
    rows = vintages.head(1).to_dict("records")
    mutator(rows)
    with pytest.raises(CalendarError, match=code):
        validate_calendar(rows)


def test_overlapping_distinct_sessions_fail_closed(vintages):
    rows = vintages[vintages.trading_eligible].head(2).to_dict("records")
    rows[1]["scheduled_open"] = rows[0]["scheduled_open"]
    rows[1]["scheduled_close"] = rows[0]["scheduled_close"]
    with pytest.raises(CalendarError, match="OVERLAPPING_SESSIONS"):
        validate_calendar(rows)


def test_unknown_clocks_and_intraday_outside_session_fail(final):
    row = final[final.session_id == "SYNX-2020-01-06"].iloc[0]
    with pytest.raises(CalendarError, match="UNKNOWN_DECISION_CLOCK"):
        clock_instant(row, "free form")
    with pytest.raises(CalendarError, match="DECISION_INSTANT_OUTSIDE_SESSION"):
        clock_instant(row, DecisionClock.INTRADAY_WITH_EXPLICIT_TIME,
                      intraday_time=pd.Timestamp("2020-01-06T11:00:00Z"))


def test_no_weekday_or_instrument_row_fallback_in_new_paths():
    source = (ROOT / "src/market_intel/foundation/exchange_calendar.py").read_text(encoding="utf-8")
    outcome = (ROOT / "src/market_intel/research/outcomes.py").read_text(encoding="utf-8")
    assert "bdate_range" not in source
    assert "weekday()" not in source
    assert "open_.index" in outcome  # preserved legacy v1
    assert "executable_sessions(calendar_view)" in outcome  # explicit v2


def test_known_answer_bundle_is_exact():
    answers = known_answers()
    assert answers["local_open_to_utc"] == "2020-01-06 03:45:00+00:00"
    assert answers["non_session_month_end_resolves_to"] == "SYNX-2019-11-29"
    assert answers["session_distance"] == 21
    assert answers["publication_at_boundary"]["available"] is True


def test_protected_evidence_and_momentum_are_unchanged():
    expected = {
        "docs/investigations/r10a/run_v1/root_run_manifest.json": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "docs/investigations/r10b/run_v1/root_manifest.json": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
        "docs/investigations/r10c/run_v1/root_manifest.json": "bf5722abab22ca1920186a7ff2572c8095d1cb75fbd442ed00e5f8dbd0893ce6",
        "specs/momentum_12_1_v1.json": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "tests/fixtures/momentum_golden_v1/expected.json": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
