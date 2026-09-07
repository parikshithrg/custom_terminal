"""Versioned exchange calendars, session clocks, availability, and settlement.

This module is provider-neutral.  The bundled fixture is fictional and must not
be interpreted as an official exchange calendar.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


CALENDAR_VERSION = "synthetic_exchange_calendar_r10d_v1"
CLOCK_VERSION = "synthetic_session_clocks_r10d_v1"
SETTLEMENT_VERSION = "synthetic_settlement_rules_r10d_v1"
SYNTHETIC_VENUE = "SYNX"
LOCAL_TIMEZONE = "Asia/Kolkata"


class CalendarError(ValueError):
    """A named, fail-closed calendar error."""


class SessionType(StrEnum):
    NORMAL = "NORMAL"
    FULL_DAY_HOLIDAY = "FULL_DAY_HOLIDAY"
    SPECIAL_WEEKEND = "SPECIAL_WEEKEND"
    SHORTENED = "SHORTENED"
    DELAYED_OPEN = "DELAYED_OPEN"
    UNEXPECTED_CLOSURE = "UNEXPECTED_CLOSURE"


class DecisionClock(StrEnum):
    SESSION_PRE_OPEN = "SESSION_PRE_OPEN"
    SESSION_OPEN = "SESSION_OPEN"
    SESSION_CLOSE = "SESSION_CLOSE"
    POST_CLOSE_AVAILABLE = "POST_CLOSE_AVAILABLE"
    NEXT_EXECUTABLE_SESSION_OPEN = "NEXT_EXECUTABLE_SESSION_OPEN"
    INTRADAY_WITH_EXPLICIT_TIME = "INTRADAY_WITH_EXPLICIT_TIME"


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    NO_FUTURE_SESSION = "NO_FUTURE_SESSION"
    CALENDAR_CONFLICT = "CALENDAR_CONFLICT"
    MISSING_ENTRY_PRICE = "MISSING_ENTRY_PRICE"
    INSTRUMENT_SUSPENDED = "INSTRUMENT_SUSPENDED"
    LISTING_NOT_EFFECTIVE = "LISTING_NOT_EFFECTIVE"
    TERMINATED_BEFORE_ENTRY = "TERMINATED_BEFORE_ENTRY"
    RIGHT_CENSORED = "RIGHT_CENSORED"


CALENDAR_REQUIRED = {
    "calendar_id", "calendar_version", "venue", "timezone", "session_id",
    "local_session_date", "session_type", "scheduled_open", "scheduled_close",
    "trading_eligible", "settlement_eligible", "occurred", "published_at",
    "available_at", "effective_at", "revision_number", "source_record_id",
    "supersedes_record_id", "source_id", "raw_evidence_hash", "quality_flags",
}


def _aware(value: object, field: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise CalendarError(f"NAIVE_TIMESTAMP:{field}")
    return stamp.tz_convert("UTC")


def _optional_aware(value: object, field: str) -> pd.Timestamp | pd.NaT:
    if value is None or pd.isna(value):
        return pd.NaT
    return _aware(value, field)


def validate_calendar(rows: pd.DataFrame | list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows).copy()
    missing = CALENDAR_REQUIRED - set(frame)
    if missing:
        raise CalendarError("MISSING_CALENDAR_FIELDS:" + ",".join(sorted(missing)))
    if frame.empty:
        return frame
    if frame["calendar_version"].isna().any() or (frame["calendar_version"].astype(str).str.len() == 0).any():
        raise CalendarError("MISSING_CALENDAR_VERSION")
    for timezone in frame["timezone"].unique():
        try:
            ZoneInfo(str(timezone))
        except ZoneInfoNotFoundError as exc:
            raise CalendarError(f"UNKNOWN_TIMEZONE:{timezone}") from exc
    for column in ("scheduled_open", "scheduled_close", "published_at", "available_at", "effective_at"):
        frame[column] = [_optional_aware(value, column) for value in frame[column]]
    if frame["source_record_id"].duplicated().any():
        raise CalendarError("DUPLICATE_SOURCE_RECORD_ID")
    if frame.duplicated(["calendar_version", "venue", "session_id", "source_id", "revision_number"]).any():
        raise CalendarError("DUPLICATE_SESSION_REVISION")
    active = frame[frame["trading_eligible"]]
    if active[["scheduled_open", "scheduled_close"]].isna().any().any():
        raise CalendarError("TRADING_SESSION_MISSING_BOUNDARY")
    if (active["scheduled_close"] <= active["scheduled_open"]).any():
        raise CalendarError("CLOSE_NOT_AFTER_OPEN")
    for (_, venue), group in active.groupby(["calendar_version", "venue"]):
        records_for_overlap = group.to_dict("records")
        for position, left in enumerate(records_for_overlap):
            for right in records_for_overlap[position + 1:]:
                if left["session_id"] == right["session_id"]:
                    continue  # revisions of one session intentionally overlap
                if (left["scheduled_open"] < right["scheduled_close"]
                        and right["scheduled_open"] < left["scheduled_close"]):
                    raise CalendarError(f"OVERLAPPING_SESSIONS:{venue}")
    records = {str(row.source_record_id): row for row in frame.itertuples()}
    for row in frame.itertuples():
        parent_id = None if pd.isna(row.supersedes_record_id) else str(row.supersedes_record_id)
        if row.revision_number == 1 and parent_id is not None:
            raise CalendarError("INVALID_REVISION_CHAIN")
        if row.revision_number > 1:
            parent = records.get(parent_id)
            if (parent is None or parent.session_id != row.session_id
                    or parent.revision_number != row.revision_number - 1
                    or parent.published_at >= row.published_at):
                raise CalendarError("INVALID_REVISION_CHAIN")
    # Explicit cycle check also covers malformed non-linear chains.
    parents = {str(r.source_record_id): None if pd.isna(r.supersedes_record_id)
               else str(r.supersedes_record_id) for r in frame.itertuples()}
    for start in parents:
        seen: set[str] = set()
        cursor: str | None = start
        while cursor is not None:
            if cursor in seen:
                raise CalendarError("CYCLIC_REVISION_CHAIN")
            seen.add(cursor)
            cursor = parents.get(cursor)
    return frame.sort_values(["local_session_date", "published_at", "source_id", "revision_number"],
                             kind="stable").reset_index(drop=True)


def calendar_as_of(frame: pd.DataFrame, *, calendar_version: str, venue: str,
                   knowledge_cutoff: pd.Timestamp, decision_clock: DecisionClock,
                   view: str = "KNOWN") -> pd.DataFrame:
    if not calendar_version:
        raise CalendarError("MISSING_CALENDAR_VERSION")
    try:
        DecisionClock(decision_clock)
    except ValueError as exc:
        raise CalendarError("UNKNOWN_DECISION_CLOCK") from exc
    cutoff = _aware(knowledge_cutoff, "knowledge_cutoff")
    work = validate_calendar(frame)
    work = work[(work.calendar_version == calendar_version) & (work.venue == venue)]
    if view == "KNOWN":
        work = work[(work.published_at <= cutoff) & (work.available_at <= cutoff)]
    elif view != "FINAL":
        raise CalendarError("UNKNOWN_CALENDAR_VIEW")
    if work.empty:
        return work
    latest = (work.sort_values(["session_id", "source_id", "revision_number", "published_at"], kind="stable")
              .drop_duplicates(["session_id", "source_id"], keep="last"))
    conflicts: list[bool] = []
    for _, group in latest.groupby("session_id", sort=False):
        columns = ["session_type", "scheduled_open", "scheduled_close", "trading_eligible", "occurred"]
        conflicts.extend([len(group[columns].drop_duplicates()) > 1] * len(group))
    latest = latest.sort_values("session_id", kind="stable").reset_index(drop=True)
    # Recompute after sorting to avoid relying on group row order.
    conflict_ids = {sid for sid, group in latest.groupby("session_id")
                    if len(group[["session_type", "scheduled_open", "scheduled_close",
                                  "trading_eligible", "occurred"]].drop_duplicates()) > 1}
    latest["conflict_state"] = latest.session_id.map(
        lambda sid: "CONFLICT" if sid in conflict_ids else "NONE")
    return latest


def executable_sessions(view: pd.DataFrame, *, require_occurred: bool = False) -> pd.DataFrame:
    if view.empty:
        return view.copy()
    if (view.conflict_state == "CONFLICT").any():
        raise CalendarError("CONFLICTING_ACTIVE_REVISIONS")
    mask = view.trading_eligible.astype(bool)
    if require_occurred:
        mask &= view.occurred.eq(True)
    return view[mask].sort_values("scheduled_open", kind="stable").reset_index(drop=True)


@dataclass(frozen=True)
class SessionResolution:
    status: ResolutionStatus
    session_id: str | None
    instant: pd.Timestamp | None
    reason: str


@dataclass(frozen=True)
class DecisionReference:
    calendar_version: str
    venue: str
    session_id: str
    clock: DecisionClock
    knowledge_cutoff: pd.Timestamp

    def validate(self, calendar_view: pd.DataFrame) -> None:
        if not self.calendar_version:
            raise CalendarError("MISSING_CALENDAR_VERSION")
        cutoff = _aware(self.knowledge_cutoff, "knowledge_cutoff")
        rows = calendar_view[(calendar_view.calendar_version == self.calendar_version)
                             & (calendar_view.venue == self.venue)
                             & (calendar_view.session_id == self.session_id)]
        if len(rows) != 1:
            raise CalendarError("DECISION_SESSION_UNRESOLVED")
        expected = clock_instant(rows.iloc[0], self.clock)
        if cutoff != expected:
            raise CalendarError("DECISION_INSTANT_OUTSIDE_SESSION")


def clock_instant(session: pd.Series | dict, clock: DecisionClock,
                  *, intraday_time: pd.Timestamp | None = None) -> pd.Timestamp:
    try:
        clock = DecisionClock(clock)
    except ValueError as exc:
        raise CalendarError("UNKNOWN_DECISION_CLOCK") from exc
    row = dict(session)
    opened = _aware(row["scheduled_open"], "scheduled_open")
    closed = _aware(row["scheduled_close"], "scheduled_close")
    if clock == DecisionClock.SESSION_PRE_OPEN:
        return opened - pd.Timedelta(minutes=15)
    if clock in {DecisionClock.SESSION_OPEN, DecisionClock.NEXT_EXECUTABLE_SESSION_OPEN}:
        return opened
    if clock == DecisionClock.SESSION_CLOSE:
        return closed
    if clock == DecisionClock.POST_CLOSE_AVAILABLE:
        return closed + pd.Timedelta(minutes=30)
    if intraday_time is None:
        raise CalendarError("MISSING_EXPLICIT_INTRADAY_TIME")
    instant = _aware(intraday_time, "intraday_time")
    if instant < opened or instant > closed:
        raise CalendarError("DECISION_INSTANT_OUTSIDE_SESSION")
    return instant


def resolve_session(view: pd.DataFrame, *, after: pd.Timestamp, ordinal: int = 1,
                    clock: DecisionClock = DecisionClock.SESSION_OPEN) -> SessionResolution:
    if ordinal < 1:
        raise CalendarError("SESSION_ORDINAL_MUST_BE_POSITIVE")
    try:
        sessions = executable_sessions(view)
    except CalendarError:
        return SessionResolution(ResolutionStatus.CALENDAR_CONFLICT, None, None,
                                 "CONFLICTING_ACTIVE_REVISIONS")
    instant = _aware(after, "after")
    future = sessions[sessions.scheduled_open > instant]
    if len(future) < ordinal:
        return SessionResolution(ResolutionStatus.NO_FUTURE_SESSION, None, None,
                                 "NO_FUTURE_EXECUTABLE_SESSION")
    row = future.iloc[ordinal - 1]
    return SessionResolution(ResolutionStatus.RESOLVED, str(row.session_id),
                             clock_instant(row, clock), "RESOLVED_FROM_VERSIONED_CALENDAR")


def previous_completed_session(view: pd.DataFrame, *, at: pd.Timestamp) -> SessionResolution:
    try:
        sessions = executable_sessions(view, require_occurred=True)
    except CalendarError:
        return SessionResolution(ResolutionStatus.CALENDAR_CONFLICT, None, None,
                                 "CONFLICTING_ACTIVE_REVISIONS")
    instant = _aware(at, "at")
    past = sessions[sessions.scheduled_close <= instant]
    if past.empty:
        return SessionResolution(ResolutionStatus.NO_FUTURE_SESSION, None, None,
                                 "NO_PREVIOUS_COMPLETED_SESSION")
    row = past.iloc[-1]
    return SessionResolution(ResolutionStatus.RESOLVED, str(row.session_id),
                             clock_instant(row, DecisionClock.SESSION_CLOSE), "RESOLVED")


def session_distance(view: pd.DataFrame, start_session_id: str, end_session_id: str) -> int:
    sessions = executable_sessions(view)
    positions = {value: position for position, value in enumerate(sessions.session_id)}
    if start_session_id not in positions or end_session_id not in positions:
        raise CalendarError("SESSION_NOT_IN_CALENDAR_VERSION")
    return positions[end_session_id] - positions[start_session_id]


def month_end_session(view: pd.DataFrame, year: int, month: int) -> pd.Series:
    sessions = executable_sessions(view)
    dates = pd.to_datetime(sessions.local_session_date)
    eligible = sessions[(dates.dt.year == year) & (dates.dt.month == month)]
    if eligible.empty:
        raise CalendarError("NO_ELIGIBLE_MONTH_END_SESSION")
    return eligible.iloc[-1]


@dataclass(frozen=True)
class AvailabilityPolicy:
    policy_id: str
    dataset_id: str
    processing_lag_minutes: int
    date_only_policy: str
    boundary_inclusive: bool = True
    version: str = "availability_policy_r10d_v1"


def information_available(*, published_at: pd.Timestamp | None, retrieved_at: pd.Timestamp | None,
                          precision: str, policy: AvailabilityPolicy,
                          knowledge_cutoff: pd.Timestamp, calendar_view: pd.DataFrame) -> tuple[bool, pd.Timestamp]:
    cutoff = _aware(knowledge_cutoff, "knowledge_cutoff")
    if published_at is None or pd.isna(published_at):
        raise CalendarError("MISSING_PUBLICATION_TIME")
    published = pd.Timestamp(published_at)
    if precision == "INTRADAY":
        published = _aware(published, "published_at")
    elif precision == "DATE_ONLY":
        if policy.date_only_policy != "NEXT_EXECUTABLE_SESSION_OPEN":
            raise CalendarError("UNSUPPORTED_DATE_ONLY_POLICY")
        local_date = published.date()
        # Date-only means the publication could have occurred at any time that
        # local day.  Availability starts at the next session after that day.
        published = (pd.Timestamp(local_date).tz_localize(LOCAL_TIMEZONE)
                     + pd.Timedelta(days=1)).tz_convert("UTC")
        resolved = resolve_session(calendar_view, after=published,
                                   clock=DecisionClock.SESSION_OPEN)
        if resolved.status != ResolutionStatus.RESOLVED:
            raise CalendarError(resolved.reason)
        published = resolved.instant
    else:
        raise CalendarError("UNKNOWN_PUBLICATION_PRECISION")
    available = published + pd.Timedelta(minutes=policy.processing_lag_minutes)
    # Retrieval is provenance only; it can delay local possession but never move
    # economic availability before publication.
    if retrieved_at is not None and not pd.isna(retrieved_at):
        retrieved = _aware(retrieved_at, "retrieved_at")
        if retrieved < published:
            raise CalendarError("RETRIEVED_BEFORE_PUBLICATION")
    eligible = available <= cutoff if policy.boundary_inclusive else available < cutoff
    return bool(eligible), available


@dataclass(frozen=True)
class SettlementRule:
    rule_id: str
    version: str
    effective_from: pd.Timestamp
    effective_to: pd.Timestamp | None
    lag_sessions: int
    leg: str = "DEFAULT"

    def __post_init__(self) -> None:
        _aware(self.effective_from, "effective_from")
        if self.effective_to is not None:
            _aware(self.effective_to, "effective_to")
        if self.lag_sessions < 0:
            raise CalendarError("NEGATIVE_SETTLEMENT_LAG")


def settlement_date(calendar_view: pd.DataFrame, *, trade_session_id: str,
                    rules: list[SettlementRule], leg: str = "DEFAULT") -> SessionResolution:
    rows = calendar_view[calendar_view.session_id == trade_session_id]
    if rows.empty:
        return SessionResolution(ResolutionStatus.NO_FUTURE_SESSION, None, None,
                                 "TRADE_SESSION_NOT_FOUND")
    trade = rows.iloc[0]
    trade_time = _aware(trade.scheduled_open, "trade_time")
    applicable = [rule for rule in rules if rule.leg == leg
                  and _aware(rule.effective_from, "effective_from") <= trade_time
                  and (rule.effective_to is None or trade_time < _aware(rule.effective_to, "effective_to"))]
    if len(applicable) != 1:
        raise CalendarError("SETTLEMENT_RULE_UNRESOLVED")
    rule = applicable[0]
    settlement = calendar_view[calendar_view.settlement_eligible.astype(bool)].sort_values(
        "local_session_date", kind="stable")
    candidates = settlement[pd.to_datetime(settlement.local_session_date)
                            > pd.Timestamp(trade.local_session_date)]
    if len(candidates) < rule.lag_sessions:
        return SessionResolution(ResolutionStatus.RIGHT_CENSORED, None, None,
                                 "SETTLEMENT_CALENDAR_ENDED")
    if rule.lag_sessions == 0:
        target = trade
    else:
        target = candidates.iloc[rule.lag_sessions - 1]
    instant = pd.Timestamp(target.local_session_date).tz_localize(LOCAL_TIMEZONE) + pd.Timedelta(hours=17)
    instant = instant.tz_convert("UTC")
    if instant < trade_time:
        raise CalendarError("SETTLEMENT_BEFORE_TRADE")
    return SessionResolution(ResolutionStatus.RESOLVED, str(target.session_id), instant,
                             f"{rule.rule_id}:{rule.version}")


def effective_session(calendar_view: pd.DataFrame, *, effective_at: pd.Timestamp,
                      holiday_policy: str = "NEXT_EXECUTABLE_SESSION_OPEN") -> SessionResolution:
    """Bind an event instant to a session boundary using an explicit policy."""
    instant = _aware(effective_at, "effective_at")
    sessions = executable_sessions(calendar_view)
    exact = sessions[sessions.scheduled_open == instant]
    if len(exact) == 1:
        row = exact.iloc[0]
        return SessionResolution(ResolutionStatus.RESOLVED, str(row.session_id), instant,
                                 "EXACT_SESSION_OPEN")
    if holiday_policy != "NEXT_EXECUTABLE_SESSION_OPEN":
        raise CalendarError("EVENT_ON_NONSESSION_WITHOUT_POLICY")
    return resolve_session(sessions, after=instant, clock=DecisionClock.SESSION_OPEN)


def validate_settlement_instant(*, trade_at: pd.Timestamp, settlement_at: pd.Timestamp,
                                allow_same_instant: bool = False) -> None:
    trade = _aware(trade_at, "trade_at")
    settlement = _aware(settlement_at, "settlement_at")
    invalid = settlement < trade if allow_same_instant else settlement <= trade
    if invalid:
        raise CalendarError("SETTLEMENT_BEFORE_TRADE")


def contract_metadata() -> dict[str, object]:
    return {
        "calendar_version": CALENDAR_VERSION,
        "clock_version": CLOCK_VERSION,
        "settlement_version": SETTLEMENT_VERSION,
        "timezone": LOCAL_TIMEZONE,
        "decision_clocks": [clock.value for clock in DecisionClock],
        "boundary_policy": "published/available exactly at cutoff is included",
        "classification": "SYNTHETIC_ONLY_NONCANONICAL",
    }
