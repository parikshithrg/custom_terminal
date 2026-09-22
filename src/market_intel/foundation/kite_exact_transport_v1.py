"""Bounded two-batch Kite quote transport; execution remains locally gated."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Callable
from urllib.parse import parse_qsl, urlsplit

from .current_market import CurrentInstrumentSnapshot
from .kite_connect import KiteSession
from .kite_equity_quote_v1 import ExactEquityEnvelope, aware, decode


SCHEMA_VERSION = "kite_exact_two_batch_transport_v1"
SCOPE_VERSION = "kite_exact_live_test_scope_v1"
API_URL = "https://api.kite.trade/quote"
BATCH_SIZE = 25
TARGET_COUNT = 50
MAX_RESPONSE_BYTES = 65_536
MAX_TOTAL_BYTES = 131_072
REQUEST_TIMEOUT_SECONDS = 20
TOTAL_DEADLINE_SECONDS = 60
OWNER_SESSION_SECONDS = 600
RESULT_RETENTION_SECONDS = 60
IST = timezone(timedelta(hours=5, minutes=30))


class ExactTransportError(RuntimeError):
    """Sanitized fail-closed transport error."""


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value)


def _canonical_bytes(value):
    def encode(item):
        if isinstance(item, datetime):
            return item.astimezone(timezone.utc).isoformat()
        raise TypeError("Unsupported binding value")
    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True, repr=False)
class ExactTargetBinding:
    binding_version: str
    created_at: datetime
    inventory_retrieved_at: datetime
    inventory_session_date: str
    constituent_csv_hash: str
    inventory_snapshot_hash: str
    targets: tuple[tuple[str, int], ...]
    binding_hash: str

    def __repr__(self):
        return ("ExactTargetBinding(targets=<50 private NSE EQ targets>, "
                f"binding_hash={self.binding_hash[:12]}...)")

    def __post_init__(self):
        if not _version(self.binding_version) or not aware(self.created_at):
            raise ValueError("Version and aware binding clock required")
        if not aware(self.inventory_retrieved_at) or self.inventory_retrieved_at > self.created_at:
            raise ValueError("Ordered aware inventory clock required")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.inventory_session_date):
            raise ValueError("Explicit inventory session date required")
        if not _hash(self.constituent_csv_hash) or not _hash(self.inventory_snapshot_hash):
            raise ValueError("Source hashes required")
        if type(self.targets) is not tuple or len(self.targets) != TARGET_COUNT:
            raise ValueError("Exactly 50 immutable targets required")
        if self.targets != tuple(sorted(self.targets)):
            raise ValueError("Targets must be sorted deterministically")
        keys = []
        tokens = []
        for target in self.targets:
            if (type(target) is not tuple or len(target) != 2 or
                    type(target[0]) is not str or
                    not re.fullmatch(r"NSE:[A-Z0-9&_.-]{1,32}", target[0]) or
                    type(target[1]) is not int or not 0 < target[1] < 2**32):
                raise ValueError("Exact NSE cash identity binding required")
            keys.append(target[0])
            tokens.append(target[1])
        if len(set(keys)) != TARGET_COUNT or len(set(tokens)) != TARGET_COUNT:
            raise ValueError("Ambiguous target binding")
        if not _hash(self.binding_hash) or self.binding_hash != _binding_hash(
                self.binding_version, self.created_at, self.inventory_retrieved_at,
                self.inventory_session_date, self.constituent_csv_hash,
                self.inventory_snapshot_hash, self.targets):
            raise ValueError("Target binding hash mismatch")

    @property
    def batches(self):
        return (self.targets[:BATCH_SIZE], self.targets[BATCH_SIZE:])

    def sanitized_summary(self):
        self.__post_init__()
        return {
            "binding_version": self.binding_version,
            "binding_hash": self.binding_hash,
            "target_count": TARGET_COUNT,
            "batch_sizes": [BATCH_SIZE, BATCH_SIZE],
            "exchange": "NSE",
            "instrument_class": "EQ",
            "contains_private_targets": False,
        }


def _binding_hash(binding_version, created_at, inventory_retrieved_at,
                  inventory_session_date, constituent_csv_hash,
                  inventory_snapshot_hash, targets):
    payload = {
        "binding_version": binding_version,
        "created_at": created_at,
        "inventory_retrieved_at": inventory_retrieved_at,
        "inventory_session_date": inventory_session_date,
        "constituent_csv_hash": constituent_csv_hash,
        "inventory_snapshot_hash": inventory_snapshot_hash,
        "targets": targets,
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def build_target_binding(*, binding_version, created_at, inventory,
                         selected_keys, constituent_csv_hash,
                         inventory_snapshot_hash):
    """Bind 50 exact eligible targets without reading files or requesting data."""
    if type(inventory) is not CurrentInstrumentSnapshot:
        raise ValueError("CurrentInstrumentSnapshot required")
    if not aware(created_at):
        raise ValueError("Aware binding clock required")
    if (inventory.provider != "kite_connect" or
            inventory.scope != "CURRENT_TRADABLE_ONLY" or
            not aware(inventory.retrieved_at) or inventory.retrieved_at > created_at):
        raise ValueError("Same-day current Kite inventory required")
    if type(selected_keys) is not tuple or len(selected_keys) != TARGET_COUNT:
        raise ValueError("Exactly 50 immutable selected keys required")
    if len(set(selected_keys)) != TARGET_COUNT:
        raise ValueError("Duplicate selected target")
    if inventory.session_date != created_at.astimezone(IST).date().isoformat():
        raise ValueError("Inventory must be declared for the binding IST date")
    lookup = {}
    for item in inventory.instruments:
        lookup.setdefault(item.provider_key, []).append(item)
    targets = []
    for key in selected_keys:
        matches = lookup.get(key, ())
        if len(matches) != 1:
            raise ValueError("Every target must have one current inventory match")
        item = matches[0]
        if (item.exchange != "NSE" or item.segment != "NSE" or
                item.instrument_type != "EQ" or item.expiry or item.quality_flags or
                type(item.provider_instrument_token) is not int or
                not 0 < item.provider_instrument_token < 2**32):
            raise ValueError("Eligible unflagged NSE EQ inventory required")
        targets.append((key, item.provider_instrument_token))
    ordered = tuple(sorted(targets))
    digest = _binding_hash(binding_version, created_at, inventory.retrieved_at,
                           inventory.session_date, constituent_csv_hash,
                           inventory_snapshot_hash, ordered)
    return ExactTargetBinding(binding_version, created_at, inventory.retrieved_at,
                              inventory.session_date, constituent_csv_hash,
                              inventory_snapshot_hash, ordered, digest)


@dataclass(frozen=True, slots=True, repr=False)
class LocalExecutionApproval:
    binding_hash: str
    approved_at: datetime
    expires_at: datetime
    authorization_state: str

    def __repr__(self):
        return ("LocalExecutionApproval(binding_hash=<redacted>, "
                f"authorization_state={self.authorization_state!r})")

    def __post_init__(self):
        if not _hash(self.binding_hash) or not aware(self.approved_at) or not aware(self.expires_at):
            raise ValueError("Hash-bound aware approval required")
        if self.authorization_state != "OWNER_CONFIRMED_LOCAL_BINDING":
            raise ValueError("Exact local owner confirmation required")
        if not self.approved_at < self.expires_at:
            raise ValueError("Approval expiry must follow approval")
        if (self.expires_at-self.approved_at).total_seconds() > OWNER_SESSION_SECONDS:
            raise ValueError("Approval exceeds ten-minute owner session")


@dataclass(frozen=True, slots=True, repr=False)
class ExactTwoBatchResult:
    schema_version: str
    scope_version: str
    binding_hash: str
    started_at: datetime
    completed_at: datetime
    as_of: datetime
    expires_at: datetime
    envelopes: tuple[ExactEquityEnvelope, ExactEquityEnvelope]
    requested_count: int
    returned_count: int
    missing_count: int
    unavailable_count: int
    total_response_bytes: int
    retention_state: str = "TRANSIENT_MEMORY_ONLY"
    readiness_state: str = "OPERATIONAL_TEST_NOT_MARKET_READY"
    currency_state: str = "NOT_VERIFIED"
    can_persist: bool = False
    can_expose_real_data: bool = False
    can_authorize_dashboard: bool = False

    def __repr__(self):
        return ("ExactTwoBatchResult(envelopes=<private transient quotes>, "
                f"binding_hash={self.binding_hash[:12]}..., "
                f"readiness_state={self.readiness_state!r})")

    def __post_init__(self):
        if (self.schema_version != SCHEMA_VERSION or self.scope_version != SCOPE_VERSION or
                not _hash(self.binding_hash)):
            raise ValueError("Unexpected exact transport result")
        if not all(aware(value) for value in (
                self.started_at, self.completed_at, self.as_of, self.expires_at)):
            raise ValueError("Aware result clocks required")
        if not self.started_at <= self.completed_at <= self.as_of < self.expires_at:
            raise ValueError("Result clocks are unordered")
        if (self.expires_at-self.as_of).total_seconds() != RESULT_RETENTION_SECONDS:
            raise ValueError("Result retention must be exactly 60 seconds")
        if type(self.envelopes) is not tuple or len(self.envelopes) != 2:
            raise ValueError("Exactly two completed envelopes required")
        if any(type(item) is not ExactEquityEnvelope for item in self.envelopes):
            raise ValueError("Exact equity envelopes required")
        for value in (self.requested_count, self.returned_count, self.missing_count,
                      self.unavailable_count, self.total_response_bytes):
            if type(value) is not int or value < 0:
                raise ValueError("Nonnegative aggregate values required")
        if self.requested_count != TARGET_COUNT or self.returned_count + self.missing_count != TARGET_COUNT:
            raise ValueError("Two-batch coverage does not reconcile")
        if self.unavailable_count > TARGET_COUNT or self.total_response_bytes > MAX_TOTAL_BYTES:
            raise ValueError("Result bounds exceeded")
        if (self.retention_state != "TRANSIENT_MEMORY_ONLY" or
                self.readiness_state != "OPERATIONAL_TEST_NOT_MARKET_READY" or
                self.currency_state != "NOT_VERIFIED" or self.can_persist is not False or
                self.can_expose_real_data is not False or
                self.can_authorize_dashboard is not False):
            raise ValueError("Operational result cannot promote or persist source data")

    def sanitized_summary(self):
        self.__post_init__()
        return {
            "schema_version": self.schema_version,
            "scope_version": self.scope_version,
            "binding_hash": self.binding_hash,
            "started_at": self.started_at.astimezone(timezone.utc).isoformat(),
            "completed_at": self.completed_at.astimezone(timezone.utc).isoformat(),
            "as_of": self.as_of.astimezone(timezone.utc).isoformat(),
            "expires_at": self.expires_at.astimezone(timezone.utc).isoformat(),
            "batch_count": 2,
            "requested_count": self.requested_count,
            "returned_count": self.returned_count,
            "missing_count": self.missing_count,
            "unavailable_count": self.unavailable_count,
            "total_response_bytes": self.total_response_bytes,
            "retention_state": self.retention_state,
            "readiness_state": self.readiness_state,
            "currency_state": self.currency_state,
            "contains_private_targets": False,
            "contains_prices": False,
        }


def _read_response(response, *, expected_params, monotonic, deadline):
    try:
        final_url = urlsplit(getattr(response, "url", ""))
        final_query = parse_qsl(final_url.query, keep_blank_values=True)
        if (getattr(response, "status_code", None) != 200 or
                final_url.scheme != "https" or final_url.hostname != "api.kite.trade" or
                final_url.port not in {None, 443} or final_url.username is not None or
                final_url.password is not None or final_url.path != "/quote" or
                final_url.fragment or (final_query and final_query != expected_params) or
                getattr(response, "history", ())):
            raise ValueError("Unexpected status, URL or redirect")
        headers = getattr(response, "headers", {})
        content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        encoding = headers.get("Content-Encoding", "").strip().lower()
        if content_type != "application/json" or encoding not in {"", "identity"}:
            raise ValueError("Unexpected response representation")
        declared = headers.get("Content-Length")
        if declared is not None:
            declared = int(declared)
            if declared < 1 or declared > MAX_RESPONSE_BYTES:
                raise ValueError("Declared response size is invalid")
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=4096):
            if monotonic() > deadline:
                raise TimeoutError("Total deadline exceeded")
            if type(chunk) is not bytes:
                raise ValueError("Response chunks must be bytes")
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("Response size limit exceeded")
            chunks.append(chunk)
        if size < 1 or (declared is not None and declared != size):
            raise ValueError("Empty or truncated response")
        return b"".join(chunks)
    except Exception:
        raise ExactTransportError("Exact quote transaction failed within frozen scope") from None


def execute_two_batch_test(*, session, http, binding, approval,
                           now: Callable[[], datetime],
                           monotonic: Callable[[], float]):
    """Execute only after exact local approval; never retry or publish partial output."""
    if type(session) is not KiteSession or type(binding) is not ExactTargetBinding or \
            type(approval) is not LocalExecutionApproval:
        raise ValueError("Session, exact binding and local approval required")
    binding.__post_init__()
    approval.__post_init__()
    if not callable(now) or not callable(monotonic):
        raise ValueError("Injected clocks required")
    started_at = now()
    if not aware(started_at):
        raise ValueError("Aware start clock required")
    if (approval.binding_hash != binding.binding_hash or
            approval.approved_at < binding.created_at or
            not approval.approved_at <= started_at < approval.expires_at or
            started_at > binding.created_at+timedelta(seconds=OWNER_SESSION_SECONDS)):
        raise ValueError("Local binding approval is missing, mismatched or expired")
    started_tick = monotonic()
    deadline = started_tick + TOTAL_DEADLINE_SECONDS
    payloads = []
    completions = []
    total_bytes = 0
    for batch in binding.batches:
        response = None
        try:
            if monotonic() > deadline:
                raise ExactTransportError("Exact quote transaction failed within frozen scope")
            response = http.get(
                API_URL,
                params=[("i", key) for key, _ in batch],
                headers={
                    "X-Kite-Version": "3",
                    "Authorization": session.authorization_header,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "Cache-Control": "no-store",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
            )
            expected_params = [("i", key) for key, _ in batch]
            payload = _read_response(response, expected_params=expected_params,
                                     monotonic=monotonic, deadline=deadline)
            total_bytes += len(payload)
            if total_bytes > MAX_TOTAL_BYTES:
                raise ExactTransportError("Exact quote transaction failed within frozen scope")
            completed = now()
            if not aware(completed) or completed < started_at or monotonic() > deadline:
                raise ExactTransportError("Exact quote transaction failed within frozen scope")
            payloads.append(payload)
            completions.append(completed)
        except ExactTransportError:
            raise
        except Exception:
            raise ExactTransportError("Exact quote transaction failed within frozen scope") from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
    as_of = now()
    if not aware(as_of) or as_of < completions[-1] or monotonic() > deadline:
        raise ExactTransportError("Exact quote transaction failed within frozen scope")
    try:
        envelopes = tuple(
            decode(payload=payload, targets=batch, retrieval_completed_at=completed,
                   as_of=as_of)
            for payload, batch, completed in zip(payloads, binding.batches, completions)
        )
        returned = sum(record.reason_codes != ("MISSING_ROW",)
                       for envelope in envelopes for record in envelope.records)
        missing = TARGET_COUNT-returned
        unavailable = sum(record.value_state == "UNAVAILABLE"
                          for envelope in envelopes for record in envelope.records)
        result = ExactTwoBatchResult(
            SCHEMA_VERSION, SCOPE_VERSION, binding.binding_hash, started_at,
            completions[-1], as_of, as_of+timedelta(seconds=RESULT_RETENTION_SECONDS),
            envelopes, TARGET_COUNT, returned, missing, unavailable, total_bytes,
        )
        result.__post_init__()
        return result
    except Exception:
        raise ExactTransportError("Combined exact quote validation failed; no result published") from None
