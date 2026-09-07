"""Versioned causal security events, identity continuity, and terminal economics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Iterable, Mapping

import pandas as pd

from .contracts import AsOfRequest, materialize_as_of


EVENT_DATASET_VERSION = "synthetic_security_events_r10c_v1"
IDENTITY_DATASET_VERSION = "synthetic_identity_assertions_r10c_v1"
ADJUSTMENT_VERSION = "derived_adjustment_factors_r10c_v1"
TERMINAL_POLICY_VERSION = "terminal_economics_r10c_v1"


class SecurityEventError(ValueError):
    pass


class EventType(StrEnum):
    SYMBOL_CHANGE = "SYMBOL_CHANGE"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    RIGHTS = "RIGHTS"
    SHARE_MERGER = "SHARE_MERGER"
    CASH_MERGER = "CASH_MERGER"
    MIXED_MERGER = "MIXED_MERGER"
    DEMERGER = "DEMERGER"
    SUSPENSION = "SUSPENSION"
    RESUMPTION = "RESUMPTION"
    DELISTING = "DELISTING"
    DISAPPEARANCE = "DISAPPEARANCE"
    RELISTING = "RELISTING"
    NEW_LISTING = "NEW_LISTING"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNRESOLVED = "UNRESOLVED"


class ConflictState(StrEnum):
    NONE = "NONE"
    CONFLICT = "CONFLICT"
    RESOLVED = "RESOLVED"


class EventStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class TerminalResolution(StrEnum):
    RESOLVED_CASH = "RESOLVED_CASH"
    RESOLVED_SUCCESSOR = "RESOLVED_SUCCESSOR"
    RESOLVED_MIXED = "RESOLVED_MIXED"
    RESOLVED_ZERO_RECOVERY = "RESOLVED_ZERO_RECOVERY"
    UNRESOLVED_TERMINAL = "UNRESOLVED_TERMINAL"
    TEMPORARY_SUSPENSION = "TEMPORARY_SUSPENSION"
    RIGHT_CENSORED = "RIGHT_CENSORED"
    NOT_TERMINAL = "NOT_TERMINAL"


class MissingObservationState(StrEnum):
    ORDINARY_MISSING_OBSERVATION = "ORDINARY_MISSING_OBSERVATION"
    TEMPORARY_SUSPENSION = "TEMPORARY_SUSPENSION"
    UNRESOLVED_DISAPPEARANCE = "UNRESOLVED_DISAPPEARANCE"
    PERMANENT_DELISTING = "PERMANENT_DELISTING"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    RELISTING_NEW_IDENTITY = "RELISTING_NEW_IDENTITY"
    RIGHT_CENSORED = "RIGHT_CENSORED"


EVENT_REQUIRED = {
    "event_id", "event_type", "issuer_id", "source_instrument_id", "published_at",
    "effective_at", "available_at", "source_record_id", "revision_number",
    "supersedes_record_id", "source_id", "raw_payload_hash", "parser_version",
    "dataset_version", "verification_status", "conflict_state", "event_status",
    "currency", "confidence", "quality_flags",
}

EVENT_OPTIONAL = {
    "target_instrument_id", "successor_instrument_id", "cash_consideration_per_share",
    "share_numerator", "share_denominator", "ratio_orientation",
    "fractional_share_policy", "fractional_cash_price", "adjustment_numerator",
    "adjustment_denominator", "volume_treatment", "settlement_at",
    "zero_recovery_declared", "predecessor_instrument_id", "successor_listing_id",
}


def _utc(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    for name in columns:
        frame[name] = pd.to_datetime(frame[name], utc=True, errors="coerce")
        if frame[name].isna().any():
            raise SecurityEventError(f"INVALID_TIMESTAMP:{name}")


def normalize_security_events(rows: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    """Normalize event assertions without collapsing revisions or source conflicts."""
    frame = pd.DataFrame(list(rows))
    missing = EVENT_REQUIRED - set(frame.columns)
    if missing:
        raise SecurityEventError("MISSING_EVENT_FIELDS:" + ",".join(sorted(missing)))
    for name in EVENT_OPTIONAL - set(frame.columns):
        frame[name] = None
    frame = frame[list(sorted(EVENT_REQUIRED | EVENT_OPTIONAL))].copy()
    _utc(frame, ("published_at", "effective_at", "available_at"))
    frame["settlement_at"] = pd.to_datetime(frame["settlement_at"], utc=True, errors="coerce")
    if (frame["available_at"] < frame["published_at"]).any():
        raise SecurityEventError("AVAILABLE_BEFORE_PUBLICATION")
    if (~frame["event_type"].isin(set(EventType))).any():
        raise SecurityEventError("UNKNOWN_EVENT_TYPE")
    if (~frame["verification_status"].isin(set(VerificationStatus))).any():
        raise SecurityEventError("INVALID_VERIFICATION_STATUS")
    if (~frame["conflict_state"].isin(set(ConflictState))).any():
        raise SecurityEventError("INVALID_CONFLICT_STATE")
    if (~frame["event_status"].isin(set(EventStatus))).any():
        raise SecurityEventError("INVALID_EVENT_STATUS")
    if (pd.to_numeric(frame["cash_consideration_per_share"], errors="coerce").dropna() < 0).any():
        raise SecurityEventError("NEGATIVE_CASH_CONSIDERATION")
    known_currencies = {"INR", "USD", "EUR", "GBP", "JPY"}
    supplied_currency = frame["currency"].dropna().astype(str)
    if (~supplied_currency.isin(known_currencies)).any():
        raise SecurityEventError("UNKNOWN_CURRENCY")
    ratio_types = {EventType.SHARE_MERGER, EventType.MIXED_MERGER, EventType.DEMERGER}
    ratios = frame["event_type"].isin(ratio_types)
    adjustments = frame["event_type"].isin({EventType.SPLIT, EventType.BONUS})
    if (ratios & (frame["share_numerator"].isna() | frame["share_denominator"].isna())).any():
        raise SecurityEventError("MISSING_SHARE_RATIO")
    if (adjustments & (frame["adjustment_numerator"].isna()
                       | frame["adjustment_denominator"].isna())).any():
        raise SecurityEventError("MISSING_ADJUSTMENT_RATIO")
    needs_orientation = ratios | adjustments
    if (needs_orientation & frame["ratio_orientation"].isna()).any():
        raise SecurityEventError("MISSING_RATIO_ORIENTATION")
    for numerator, denominator in (("share_numerator", "share_denominator"),
                                   ("adjustment_numerator", "adjustment_denominator")):
        values = pd.to_numeric(frame[numerator], errors="coerce")
        denominators = pd.to_numeric(frame[denominator], errors="coerce")
        if ((values.notna() & (values <= 0)) | (denominators.notna() & (denominators <= 0))).any():
            raise SecurityEventError("NON_POSITIVE_RATIO")
    if frame["source_record_id"].duplicated().any():
        raise SecurityEventError("DUPLICATE_EVENT_RECORD_IDENTITY")
    if (pd.to_numeric(frame["revision_number"], errors="coerce").fillna(0) < 1).any():
        raise SecurityEventError("INVALID_EVENT_REVISION")
    confidence = pd.to_numeric(frame["confidence"], errors="coerce")
    if confidence.isna().any() or ((confidence < 0) | (confidence > 1)).any():
        raise SecurityEventError("INVALID_EVENT_CONFIDENCE")
    records = {str(row.source_record_id): row for row in frame.itertuples()}
    # Detect cycles before validating sequence numbers so the root cause remains named.
    for record_id in records:
        seen: set[str] = set()
        cursor = record_id
        while cursor in records:
            if cursor in seen:
                raise SecurityEventError("EVENT_SUPERSESSION_CYCLE")
            seen.add(cursor)
            parent = records[cursor].supersedes_record_id
            if pd.isna(parent) or parent is None:
                break
            cursor = str(parent)
    for row in frame.itertuples():
        parent_id = None if pd.isna(row.supersedes_record_id) else str(row.supersedes_record_id)
        if row.revision_number == 1 and parent_id is not None:
            raise SecurityEventError("INVALID_EVENT_SUPERSESSION")
        if row.revision_number > 1:
            parent = records.get(parent_id)
            if (parent is None or parent.event_id != row.event_id or parent.source_id != row.source_id
                    or parent.revision_number != row.revision_number - 1
                    or parent.published_at >= row.published_at):
                raise SecurityEventError("INVALID_EVENT_SUPERSESSION")
    frame["quality_flags"] = frame["quality_flags"].map(
        lambda value: value if isinstance(value, str) else json.dumps(value or []))
    return frame.sort_values(["event_id", "source_id", "revision_number", "source_record_id"],
                             kind="stable").reset_index(drop=True)


def event_as_of(events: pd.DataFrame, request: AsOfRequest, *,
                economic_time: pd.Timestamp) -> pd.DataFrame:
    """Return latest knowable assertion per source and separate economic effectiveness."""
    if request.dataset_version != EVENT_DATASET_VERSION:
        raise SecurityEventError("EVENT_DATASET_VERSION_MISMATCH")
    normalized = normalize_security_events(events.to_dict("records"))
    work = normalized.rename(columns={"effective_at": "event_time"})
    latest = materialize_as_of(work, request, observation_keys=("event_id", "source_id"))
    latest = latest.rename(columns={"event_time": "effective_at"})
    if latest.empty:
        latest["is_effective"] = pd.Series(dtype="bool")
        return latest
    economic_time = pd.Timestamp(economic_time)
    if economic_time.tzinfo is None:
        raise SecurityEventError("ECONOMIC_TIME_REQUIRES_TIMEZONE")
    latest["is_effective"] = ((latest["effective_at"] <= economic_time)
                              & (latest["event_status"] == EventStatus.ACTIVE))
    semantic = ["event_type", "source_instrument_id", "successor_instrument_id",
                "cash_consideration_per_share", "share_numerator", "share_denominator",
                "adjustment_numerator", "adjustment_denominator", "event_status"]
    for event_id, group in latest.groupby("event_id"):
        comparable = group[semantic].astype("string").fillna("<NULL>")
        if len(group) > 1 and len(comparable.drop_duplicates()) > 1:
            latest.loc[latest["event_id"] == event_id, "conflict_state"] = ConflictState.CONFLICT
    return latest.sort_values(["event_id", "source_id"], kind="stable").reset_index(drop=True)


IDENTITY_REQUIRED = {
    "assertion_id", "issuer_id", "listing_id", "instrument_id", "exchange", "symbol",
    "valid_from", "valid_to", "published_at", "available_at", "source_record_id",
    "revision_number", "supersedes_record_id", "source_id", "raw_payload_hash",
    "verification_status", "conflict_state", "dataset_version",
    "confidence",
}


def normalize_identity_assertions(rows: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    missing = IDENTITY_REQUIRED - set(frame.columns)
    if missing:
        raise SecurityEventError("MISSING_IDENTITY_FIELDS:" + ",".join(sorted(missing)))
    _utc(frame, ("valid_from", "published_at", "available_at"))
    frame["valid_to"] = pd.to_datetime(frame["valid_to"], utc=True, errors="coerce")
    if (frame["valid_to"].notna() & (frame["valid_to"] <= frame["valid_from"])).any():
        raise SecurityEventError("INVALID_IDENTITY_INTERVAL")
    if (frame["available_at"] < frame["published_at"]).any():
        raise SecurityEventError("IDENTITY_AVAILABLE_BEFORE_PUBLICATION")
    if frame["source_record_id"].duplicated().any():
        raise SecurityEventError("DUPLICATE_IDENTITY_RECORD")
    confidence = pd.to_numeric(frame["confidence"], errors="coerce")
    if confidence.isna().any() or ((confidence < 0) | (confidence > 1)).any():
        raise SecurityEventError("INVALID_IDENTITY_CONFIDENCE")
    ordered = frame.sort_values(["exchange", "symbol", "valid_from"], kind="stable")
    for (_, symbol), group in ordered.groupby(["exchange", "symbol"]):
        items = list(group.itertuples())
        for left, right in zip(items, items[1:]):
            if pd.isna(left.valid_to) or right.valid_from < left.valid_to:
                raise SecurityEventError(f"OVERLAPPING_ALIAS:{symbol}")
    for instrument_id, group in frame.groupby("instrument_id"):
        if group["issuer_id"].nunique() > 1:
            raise SecurityEventError(f"INSTRUMENT_MULTIPLE_ISSUERS:{instrument_id}")
    return frame.sort_values(["instrument_id", "valid_from", "source_record_id"],
                             kind="stable").reset_index(drop=True)


def identity_as_of(assertions: pd.DataFrame, request: AsOfRequest,
                   economic_time: pd.Timestamp) -> pd.DataFrame:
    if request.dataset_version != IDENTITY_DATASET_VERSION:
        raise SecurityEventError("IDENTITY_DATASET_VERSION_MISMATCH")
    frame = normalize_identity_assertions(assertions.to_dict("records"))
    work = frame.rename(columns={"valid_from": "event_time"})
    latest = materialize_as_of(work, request, observation_keys=("assertion_id", "source_id"))
    latest = latest.rename(columns={"event_time": "valid_from"})
    economic_time = pd.Timestamp(economic_time)
    if economic_time.tzinfo is None:
        raise SecurityEventError("ECONOMIC_TIME_REQUIRES_TIMEZONE")
    return latest[(latest["valid_from"] <= economic_time)
                  & (latest["valid_to"].isna() | (economic_time < latest["valid_to"]))]


def assert_acyclic_successors(events: pd.DataFrame) -> None:
    edges = events[["source_instrument_id", "successor_instrument_id"]].dropna().drop_duplicates()
    graph = {str(source): set(group["successor_instrument_id"].astype(str))
             for source, group in edges.groupby("source_instrument_id")}
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise SecurityEventError("CYCLIC_SUCCESSOR_RELATIONSHIP")
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, ()):
            visit(child)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)


def validate_successor_creation(events: pd.DataFrame, identities: pd.DataFrame) -> None:
    creation = identities.groupby("instrument_id")["valid_from"].min().to_dict()
    for row in events.dropna(subset=["successor_instrument_id"]).itertuples():
        successor = str(row.successor_instrument_id)
        if successor not in creation:
            raise SecurityEventError(f"UNKNOWN_SUCCESSOR_IDENTITY:{successor}")
        if pd.Timestamp(row.effective_at) < pd.Timestamp(creation[successor]):
            raise SecurityEventError(f"SUCCESSOR_EFFECTIVE_BEFORE_CREATION:{successor}")


def resolve_symbol_as_of(assertions: pd.DataFrame, *, exchange: str, symbol: str,
                         request: AsOfRequest, economic_time: pd.Timestamp) -> str:
    visible = identity_as_of(assertions, request, economic_time)
    matches = visible[(visible["exchange"] == exchange) & (visible["symbol"] == symbol)]
    ids = tuple(sorted(matches["instrument_id"].astype(str).unique()))
    if len(ids) != 1:
        raise SecurityEventError("ALIAS_UNRESOLVED_OR_AMBIGUOUS")
    return ids[0]


def lifecycle_state(events: pd.DataFrame, request: AsOfRequest, *,
                    economic_time: pd.Timestamp, instrument_id: str) -> str:
    visible = event_as_of(events, request, economic_time=economic_time)
    relevant = visible[(visible["source_instrument_id"] == instrument_id)
                       & visible["is_effective"]]
    lifecycle_types = {EventType.SUSPENSION, EventType.RESUMPTION, EventType.DELISTING,
                       EventType.DISAPPEARANCE, EventType.RELISTING}
    relevant = relevant[relevant["event_type"].isin(lifecycle_types)].sort_values("effective_at")
    if relevant.empty:
        return "ACTIVE"
    latest = relevant.iloc[-1]["event_type"]
    return {
        EventType.SUSPENSION: "SUSPENDED",
        EventType.RESUMPTION: "ACTIVE",
        EventType.DELISTING: "TERMINATED",
        EventType.DISAPPEARANCE: "UNRESOLVED_DISAPPEARANCE",
        EventType.RELISTING: "RELISTED_NEW_IDENTITY_REQUIRED",
    }[EventType(latest)]


def classify_missing_observation(*, event_type: EventType | None,
                                 dataset_ended: bool = False) -> MissingObservationState:
    if dataset_ended:
        return MissingObservationState.RIGHT_CENSORED
    if event_type is None:
        return MissingObservationState.ORDINARY_MISSING_OBSERVATION
    if event_type == EventType.SUSPENSION:
        return MissingObservationState.TEMPORARY_SUSPENSION
    if event_type == EventType.DISAPPEARANCE:
        return MissingObservationState.UNRESOLVED_DISAPPEARANCE
    if event_type == EventType.DELISTING:
        return MissingObservationState.PERMANENT_DELISTING
    if event_type in {EventType.SHARE_MERGER, EventType.CASH_MERGER, EventType.MIXED_MERGER}:
        return MissingObservationState.MERGER_ACQUISITION
    if event_type == EventType.RELISTING:
        return MissingObservationState.RELISTING_NEW_IDENTITY
    return MissingObservationState.ORDINARY_MISSING_OBSERVATION


def adjustment_factors_v1(events: pd.DataFrame) -> pd.DataFrame:
    """Produce backward price factors; never mutate raw prices."""
    eligible = events[events["event_type"].isin({EventType.SPLIT, EventType.BONUS})].copy()
    if eligible.empty:
        return pd.DataFrame(columns=["event_id", "instrument_id", "effective_at",
                                     "price_factor", "volume_factor", "version"])
    blocked = eligible[(eligible["verification_status"] != VerificationStatus.VERIFIED)
                       | (eligible["conflict_state"] == ConflictState.CONFLICT)
                       | (eligible["event_status"] != EventStatus.ACTIVE)]
    if not blocked.empty:
        raise SecurityEventError("ADJUSTMENT_PUBLICATION_BLOCKED")
    if (~eligible["ratio_orientation"].isin({"NEW_SHARES_PER_OLD_SHARES"})).any():
        raise SecurityEventError("UNSUPPORTED_ADJUSTMENT_ORIENTATION")
    numerator = eligible["adjustment_numerator"].astype(float)
    denominator = eligible["adjustment_denominator"].astype(float)
    result = pd.DataFrame({
        "event_id": eligible["event_id"],
        "instrument_id": eligible["source_instrument_id"],
        "effective_at": eligible["effective_at"],
        "price_factor": denominator / numerator,
        "volume_factor": numerator / denominator,
        "version": ADJUSTMENT_VERSION,
    })
    return result.sort_values(["instrument_id", "effective_at", "event_id"], kind="stable").reset_index(drop=True)


def adjusted_price_view(raw_prices: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    raw_copy = raw_prices.copy(deep=True)
    adjusted = raw_prices.copy(deep=True)
    adjusted["price_view"] = "DECLARED_BACKWARD_ADJUSTED"
    for factor in factors.itertuples():
        mask = ((adjusted["instrument_id"] == factor.instrument_id)
                & (pd.to_datetime(adjusted["event_time"], utc=True) < factor.effective_at))
        for column in ("open", "high", "low", "close"):
            adjusted.loc[mask, column] = adjusted.loc[mask, column].astype(float) * factor.price_factor
        if "volume" in adjusted:
            adjusted.loc[mask, "volume"] = adjusted.loc[mask, "volume"].astype(float) * factor.volume_factor
    if not raw_prices.equals(raw_copy):
        raise AssertionError("RAW_PRICE_MUTATION")
    return adjusted


@dataclass(frozen=True)
class TerminalEconomicResult:
    event_id: str
    source_instrument_id: str
    settlement_at: pd.Timestamp | None
    cash_amount: float | None
    successor_quantity: float | None
    successor_instrument_id: str | None
    successor_price: float | None
    currency: str | None
    total_proceeds: float | None
    resolution_status: TerminalResolution
    evidence_hashes: tuple[str, ...]
    policy_version: str = TERMINAL_POLICY_VERSION


def resolve_terminal_economics(event: Mapping[str, object], *, quantity: float,
                               successor_prices: Mapping[tuple[str, pd.Timestamp], float] | None = None
                               ) -> TerminalEconomicResult:
    if quantity < 0:
        raise SecurityEventError("NEGATIVE_POSITION_QUANTITY")
    event_type = EventType(event["event_type"])
    verified = event.get("verification_status") == VerificationStatus.VERIFIED
    conflict = event.get("conflict_state") == ConflictState.CONFLICT
    evidence = (str(event.get("raw_payload_hash")),)
    settlement = pd.Timestamp(event["settlement_at"]) if pd.notna(event.get("settlement_at")) else None
    base = dict(event_id=str(event["event_id"]),
                source_instrument_id=str(event["source_instrument_id"]), settlement_at=settlement,
                currency=event.get("currency"), evidence_hashes=evidence)
    if event_type == EventType.SUSPENSION:
        return TerminalEconomicResult(**base, cash_amount=None, successor_quantity=None,
                                      successor_instrument_id=None, successor_price=None,
                                      total_proceeds=None,
                                      resolution_status=TerminalResolution.TEMPORARY_SUSPENSION)
    if not verified or conflict or event_type in {EventType.DISAPPEARANCE, EventType.RIGHTS}:
        return TerminalEconomicResult(**base, cash_amount=None, successor_quantity=None,
                                      successor_instrument_id=None, successor_price=None,
                                      total_proceeds=None,
                                      resolution_status=TerminalResolution.UNRESOLVED_TERMINAL)
    if bool(event.get("zero_recovery_declared")):
        return TerminalEconomicResult(**base, cash_amount=0.0, successor_quantity=0.0,
                                      successor_instrument_id=None, successor_price=None,
                                      total_proceeds=0.0,
                                      resolution_status=TerminalResolution.RESOLVED_ZERO_RECOVERY)
    cash_per_share = event.get("cash_consideration_per_share")
    cash = None if pd.isna(cash_per_share) or cash_per_share is None else quantity * float(cash_per_share)
    successor = event.get("successor_instrument_id")
    share_quantity = None
    successor_price = None
    fractional_cash = 0.0
    if successor and pd.notna(successor):
        if event.get("ratio_orientation") != "SUCCESSOR_SHARES_PER_SOURCE_SHARES":
            raise SecurityEventError("UNSUPPORTED_SHARE_RATIO_ORIENTATION")
        share_quantity = quantity * float(event["share_numerator"]) / float(event["share_denominator"])
        if event.get("fractional_share_policy") == "CASH_IN_LIEU":
            whole = float(int(share_quantity))
            fraction = share_quantity - whole
            price = event.get("fractional_cash_price")
            if fraction and (price is None or pd.isna(price)):
                return TerminalEconomicResult(**base, cash_amount=cash, successor_quantity=None,
                                              successor_instrument_id=str(successor), successor_price=None,
                                              total_proceeds=None,
                                              resolution_status=TerminalResolution.UNRESOLVED_TERMINAL)
            fractional_cash = fraction * float(price or 0)
            share_quantity = whole
        if settlement is None or successor_prices is None:
            return TerminalEconomicResult(**base, cash_amount=cash, successor_quantity=share_quantity,
                                          successor_instrument_id=str(successor), successor_price=None,
                                          total_proceeds=None,
                                          resolution_status=TerminalResolution.UNRESOLVED_TERMINAL)
        successor_price = successor_prices.get((str(successor), settlement))
        if successor_price is None:
            return TerminalEconomicResult(**base, cash_amount=cash, successor_quantity=share_quantity,
                                          successor_instrument_id=str(successor), successor_price=None,
                                          total_proceeds=None,
                                          resolution_status=TerminalResolution.UNRESOLVED_TERMINAL)
    cash_total = (cash or 0.0) + fractional_cash
    total = cash_total + ((share_quantity or 0.0) * (successor_price or 0.0))
    if successor and cash_total > 0:
        status = TerminalResolution.RESOLVED_MIXED
    elif successor:
        status = TerminalResolution.RESOLVED_SUCCESSOR
    elif cash is not None:
        status = TerminalResolution.RESOLVED_CASH
    else:
        status = TerminalResolution.UNRESOLVED_TERMINAL
        total = None
    return TerminalEconomicResult(**base, cash_amount=None if cash is None and fractional_cash == 0 else cash_total,
                                  successor_quantity=share_quantity,
                                  successor_instrument_id=None if not successor else str(successor),
                                  successor_price=successor_price, total_proceeds=total,
                                  resolution_status=status)


def integrate_terminal_outcomes(outcomes: pd.DataFrame,
                                resolutions: Mapping[str, TerminalEconomicResult]) -> pd.DataFrame:
    """Keep every prediction and label terminal outcomes without silent zeroing."""
    result = outcomes.copy(deep=True)
    if "event_id" not in result:
        result["event_id"] = None
    for index, row in result.iterrows():
        event_id = row.get("event_id")
        if not event_id or event_id not in resolutions:
            continue
        resolution = resolutions[event_id]
        if resolution.resolution_status in {
            TerminalResolution.RESOLVED_CASH, TerminalResolution.RESOLVED_SUCCESSOR,
            TerminalResolution.RESOLVED_MIXED, TerminalResolution.RESOLVED_ZERO_RECOVERY,
        }:
            result.at[index, "outcome_status"] = "RESOLVED_TERMINAL"
            result.at[index, "terminal_proceeds"] = resolution.total_proceeds
        elif resolution.resolution_status == TerminalResolution.TEMPORARY_SUSPENSION:
            result.at[index, "outcome_status"] = "TEMPORARY_SUSPENSION"
        else:
            result.at[index, "outcome_status"] = "UNRESOLVED_TERMINAL"
    if len(result) != len(outcomes):
        raise AssertionError("EVENT_DEPENDENT_OUTCOME_SILENTLY_OMITTED")
    return result
