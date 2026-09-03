"""R.9D durable F&O audit governance with production deliberately disabled.

This module contains no locator reader and accepts no production database path.
Its durable registry and evidence store are exercised only in marked temporary
synthetic roots.  A later reviewed milestone must introduce an exact activation
binding before production locator resolution can exist.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .local_fno_audit import (
    AuditApproval,
    AuditApprovalConsumption,
    AuditApprovalRegistration,
    LocalFnoAuditError,
    PERMITTED_OUTPUTS,
    validate_audit_approval,
)


REGISTRY_SCHEMA_VERSION = "local_fno_durable_audit_registry_v1"
LOCATOR_CONTRACT_VERSION = "local_fno_production_locator_contract_v1"
ACTIVATION_CONTRACT_VERSION = "local_fno_production_activation_v1"
PRODUCTION_LOCATOR_STATE = "PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING"
SYNTHETIC_REGISTRY_MARKER = ".synthetic_r9d_audit_governance"
SYNTHETIC_EVIDENCE_MARKER = ".synthetic_r9d_audit_evidence"
TERMINAL_STATES = frozenset({"COMPLETED", "ABORTED", "FAILED"})
DELIBERATE_INTERLOCK = "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE"
RESTORE_STATE = "RESTORE_NOT_TESTED_BACKUP_NOT_CLAIMED"
RETENTION_STATE = "LOCAL_TASK_SCOPED_SYNTHETIC_ONLY"


class ProductionBoundaryError(RuntimeError):
    """Fail-closed R.9D production-boundary violation."""


class DurableRegistryError(LocalFnoAuditError):
    """Durable approval or event-ledger contract violation."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise DurableRegistryError(f"{label} is missing or unsafe")
    return value


def _sanitize_text(value: object) -> str:
    text = str(value)
    text = re.sub(
        r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*\S+",
        r"\1=<redacted>", text,
    )
    text = re.sub(r"[A-Za-z]:\\[^\s'\"]+", "<redacted-path>", text)
    text = re.sub(r"/(?:Users|home|var|tmp)/[^\s'\"]+", "<redacted-path>", text)
    return text[:300]


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _approval_json(approval: AuditApproval) -> str:
    return _canonical_bytes(asdict(approval)).decode("utf-8")


def _assert_sanitized_approval(approval: AuditApproval) -> None:
    payload = _approval_json(approval)
    if re.search(r"[A-Za-z]:[\\/]", payload) or re.search(
        r"/(?:Users|home|var|tmp)/", payload, re.IGNORECASE
    ):
        raise DurableRegistryError("approval contains a private absolute path")
    if re.search(
        r"(?i)(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*[^\s,}\"]+",
        payload,
    ):
        raise DurableRegistryError("approval contains secret-like material")


def _event_body(sequence: int, event_type: str, approval_id: str,
                attempt_id: str | None, detail: Mapping[str, Any],
                created_at: str, previous: str | None) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_type": event_type,
        "approval_id": approval_id,
        "attempt_id": attempt_id,
        "detail": dict(detail),
        "created_at": created_at,
        "previous_event_sha256": previous,
    }


@dataclass(frozen=True)
class ProductionLocatorContract:
    schema_version: str = LOCATOR_CONTRACT_VERSION
    state: str = PRODUCTION_LOCATOR_STATE
    configuration_file_reference: str = "REDACTED_CONFIGURATION_REFERENCE_PLACEHOLDER"
    configuration_key: str = "paths.fno_db"
    expected_configuration_sha256: str = "REQUIRED_AFTER_SEPARATE_BINDING_REVIEW"
    target_classification: str = "PRODUCTION_LOCAL_FNO_DATABASE"
    path_redaction_alias: str = "PRIVATE_FNO_DATABASE_ALIAS_UNBOUND"
    required_sampled_identity_root: str = "REQUIRED_AFTER_AUTHORIZED_IDENTITY_CEREMONY"
    permitted_stages: tuple[int, ...] = (1, 2, 3)
    template_only: bool = True
    usable: bool = False


@dataclass(frozen=True)
class ProductionInterlockEvidence:
    reviewed_pdf_current: bool = False
    reviewed_pdf_covers_exact_binding: bool = False
    research_state_fingerprint_matches: bool = False
    activation_object_exact: bool = False
    durable_approval_registered: bool = False
    file_identity_matches: bool = False
    stages_exact: bool = False
    resource_envelope_matches: bool = False
    expected_outputs_match: bool = False
    approval_unused_and_unexpired: bool = False
    source_commit_clean_and_reviewed: bool = False
    protected_evidence_unchanged: bool = False
    deliberate_r9d_interlock_removed_by_reviewed_commit: bool = False


def evaluate_production_interlocks(
    evidence: ProductionInterlockEvidence,
) -> dict[str, Any]:
    checks = asdict(evidence)
    failures = [name for name, passed in checks.items() if passed is not True]
    if not evidence.deliberate_r9d_interlock_removed_by_reviewed_commit:
        failures.append(DELIBERATE_INTERLOCK)
    return {
        "state": PRODUCTION_LOCATOR_STATE,
        "permitted": False,
        "checks": checks,
        "failures": tuple(dict.fromkeys(failures)),
        "database_access_authorized": False,
        "audit_execution_authorized": False,
    }


def assert_runtime_isolation(dependency_injections: Mapping[str, object] | None) -> None:
    """Reject all injected services at the production boundary in R.9D."""
    if dependency_injections:
        raise ProductionBoundaryError(
            "runtime dependency injection is prohibited at the R.9D boundary"
        )


def execute_production_stage_1_3_audit(
    *, locator: ProductionLocatorContract | None = None,
    interlocks: ProductionInterlockEvidence | None = None,
    configuration_reader: object | None = None,
    dependency_injections: Mapping[str, object] | None = None,
) -> None:
    """Always fail before configuration, filesystem, attempt, or SQLite access."""
    assert_runtime_isolation(dependency_injections)
    contract = locator or ProductionLocatorContract()
    if contract.state != PRODUCTION_LOCATOR_STATE or not contract.template_only or contract.usable:
        raise ProductionBoundaryError("unreviewed production locator contract rejected")
    result = evaluate_production_interlocks(interlocks or ProductionInterlockEvidence())
    if not result["permitted"]:
        raise ProductionBoundaryError(PRODUCTION_LOCATOR_STATE)
    # Deliberately unreachable in R.9D. configuration_reader is never invoked.
    raise ProductionBoundaryError(DELIBERATE_INTERLOCK)


class DurableAuditRegistry:
    """SQLite-backed immutable approval registry and hash-chained event ledger."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        if not self.database_path.is_file():
            raise DurableRegistryError("durable registry is not initialized")

    @classmethod
    def create_synthetic(
        cls, root: str | Path, *, forbidden_roots: Sequence[str | Path] = (),
    ) -> "DurableAuditRegistry":
        base = Path(root)
        base.mkdir(parents=True, exist_ok=True)
        if base.is_symlink():
            raise DurableRegistryError("registry root cannot be a symlink")
        resolved = base.resolve()
        for forbidden in forbidden_roots:
            if _is_within(resolved, Path(forbidden).resolve()):
                raise DurableRegistryError("registry must be separate from source data")
        (resolved / SYNTHETIC_REGISTRY_MARKER).write_text(
            "R.9D temporary synthetic audit governance only\n", encoding="utf-8"
        )
        database = resolved / "audit_governance.sqlite"
        if database.exists():
            raise DurableRegistryError("registry already exists")
        connection = sqlite3.connect(database)
        try:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE registry_metadata(
                    schema_version TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    purpose TEXT NOT NULL
                );
                CREATE TABLE approvals(
                    approval_id TEXT PRIMARY KEY,
                    approval_payload_sha256 TEXT NOT NULL UNIQUE,
                    approval_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL
                );
                CREATE TABLE consumptions(
                    approval_id TEXT PRIMARY KEY REFERENCES approvals(approval_id),
                    attempt_id TEXT NOT NULL UNIQUE,
                    consumed_at TEXT NOT NULL
                );
                CREATE TABLE attempts(
                    attempt_id TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL UNIQUE REFERENCES approvals(approval_id),
                    state TEXT NOT NULL,
                    consumed_at TEXT NOT NULL,
                    terminal_at TEXT
                );
                CREATE TABLE events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    attempt_id TEXT,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_event_sha256 TEXT,
                    event_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER approvals_no_update BEFORE UPDATE ON approvals
                BEGIN SELECT RAISE(ABORT, 'immutable approvals'); END;
                CREATE TRIGGER approvals_no_delete BEFORE DELETE ON approvals
                BEGIN SELECT RAISE(ABORT, 'immutable approvals'); END;
                CREATE TRIGGER consumptions_no_update BEFORE UPDATE ON consumptions
                BEGIN SELECT RAISE(ABORT, 'immutable consumptions'); END;
                CREATE TRIGGER consumptions_no_delete BEFORE DELETE ON consumptions
                BEGIN SELECT RAISE(ABORT, 'immutable consumptions'); END;
                CREATE TRIGGER events_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                CREATE TRIGGER events_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                """
            )
            connection.execute(
                "INSERT INTO registry_metadata VALUES(?,?,?)",
                (REGISTRY_SCHEMA_VERSION, _utc_now(), "R9D_SYNTHETIC_TEST_ONLY"),
            )
            connection.commit()
        finally:
            connection.close()
        return cls(database)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10.0,
                                     isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection, event_type: str, approval_id: str,
        attempt_id: str | None, detail: Mapping[str, Any], created_at: str,
    ) -> str:
        row = connection.execute(
            "SELECT sequence,event_sha256 FROM events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = 1 if row is None else int(row[0]) + 1
        previous = None if row is None else str(row[1])
        body = _event_body(sequence, event_type, approval_id, attempt_id,
                           detail, created_at, previous)
        digest = _sha256(_canonical_bytes(body))
        connection.execute(
            "INSERT INTO events(sequence,event_type,approval_id,attempt_id,detail_json,"
            "created_at,previous_event_sha256,event_sha256) VALUES(?,?,?,?,?,?,?,?)",
            (sequence, event_type, approval_id, attempt_id,
             _canonical_bytes(dict(detail)).decode("utf-8"), created_at, previous, digest),
        )
        return digest

    def register(self, approval: AuditApproval) -> AuditApprovalRegistration:
        validate_audit_approval(approval)
        _assert_sanitized_approval(approval)
        _safe_identifier(approval.approval_id, "approval_id")
        payload = _approval_json(approval)
        timestamp = _utc_now()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO approvals VALUES(?,?,?,?)",
                (approval.approval_id, approval.approval_payload_sha256,
                 payload, timestamp),
            )
            self._append_event(connection, "APPROVAL_REGISTERED", approval.approval_id,
                               None, {"payload_sha256": approval.approval_payload_sha256},
                               timestamp)
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise DurableRegistryError("duplicate approval ID or payload rejected") from None
        finally:
            connection.close()
        return AuditApprovalRegistration(approval.approval_id,
                                         approval.approval_payload_sha256)

    def consume(self, approval: AuditApproval, attempt_id: str) -> AuditApprovalConsumption:
        validate_audit_approval(approval)
        _safe_identifier(attempt_id, "attempt_id")
        timestamp = _utc_now()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT approval_payload_sha256,approval_json FROM approvals WHERE approval_id=?",
                (approval.approval_id,),
            ).fetchone()
            if row is None:
                raise DurableRegistryError("audit approval is not registered")
            if row[0] != approval.approval_payload_sha256 or row[1] != _approval_json(approval):
                raise DurableRegistryError("registered audit approval was altered")
            if connection.execute(
                "SELECT 1 FROM consumptions WHERE approval_id=?", (approval.approval_id,)
            ).fetchone():
                raise DurableRegistryError("audit approval has already been consumed")
            connection.execute(
                "INSERT INTO consumptions VALUES(?,?,?)",
                (approval.approval_id, attempt_id, timestamp),
            )
            connection.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,NULL)",
                (attempt_id, approval.approval_id, "CONSUMED_BEFORE_CONNECTION", timestamp),
            )
            self._append_event(connection, "APPROVAL_CONSUMED", approval.approval_id,
                               attempt_id, {"state": "CONSUMED_BEFORE_CONNECTION"}, timestamp)
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            raise DurableRegistryError("approval or attempt already consumed") from None
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return AuditApprovalConsumption(approval.approval_id, attempt_id)

    def record_terminal(self, approval_id: str, attempt_id: str, state: str,
                        detail: Mapping[str, Any] | None = None) -> str:
        if state not in TERMINAL_STATES:
            raise DurableRegistryError("invalid terminal attempt state")
        timestamp = _utc_now()
        safe_detail = {_sanitize_text(k)[:80]: _sanitize_text(v)
                       for k, v in (detail or {}).items()}
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT approval_id,state FROM attempts WHERE attempt_id=?", (attempt_id,)
            ).fetchone()
            if row is None or row[0] != approval_id:
                raise DurableRegistryError("attempt binding is missing or mismatched")
            if row[1] in TERMINAL_STATES:
                raise DurableRegistryError("attempt already has a terminal event")
            connection.execute(
                "UPDATE attempts SET state=?,terminal_at=? WHERE attempt_id=?",
                (state, timestamp, attempt_id),
            )
            head = self._append_event(connection, f"AUDIT_{state}", approval_id,
                                      attempt_id, safe_detail, timestamp)
            connection.commit()
            return head
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def consumed_by(self, approval_id: str) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT attempt_id FROM consumptions WHERE approval_id=?", (approval_id,)
            ).fetchone()
            return None if row is None else str(row[0])
        finally:
            connection.close()

    def incomplete_attempts(self) -> tuple[dict[str, Any], ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT attempt_id,approval_id,state,consumed_at FROM attempts "
                "WHERE terminal_at IS NULL ORDER BY attempt_id"
            ).fetchall()
            return tuple({"attempt_id": row[0], "approval_id": row[1],
                          "state": row[2], "consumed_at": row[3]} for row in rows)
        finally:
            connection.close()

    def event_head(self) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT event_sha256 FROM events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            return None if row is None else str(row[0])
        finally:
            connection.close()

    def verify(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            approvals = connection.execute(
                "SELECT approval_payload_sha256,approval_json FROM approvals ORDER BY approval_id"
            ).fetchall()
            for digest, payload in approvals:
                value = json.loads(payload)
                claimed = value.pop("approval_payload_sha256", None)
                if claimed != digest or _sha256(_canonical_bytes(value)) != digest:
                    raise DurableRegistryError("approval payload tampering detected")
            rows = connection.execute(
                "SELECT sequence,event_type,approval_id,attempt_id,detail_json,created_at,"
                "previous_event_sha256,event_sha256 FROM events ORDER BY sequence"
            ).fetchall()
            previous = None
            for row in rows:
                detail = json.loads(row[4])
                body = _event_body(row[0], row[1], row[2], row[3], detail, row[5], row[6])
                if row[6] != previous or _sha256(_canonical_bytes(body)) != row[7]:
                    raise DurableRegistryError("event ledger hash-chain corruption detected")
                previous = row[7]
            attempt_rows = connection.execute(
                "SELECT attempt_id,approval_id,state,terminal_at FROM attempts ORDER BY attempt_id"
            ).fetchall()
            event_states = {
                (row[3], row[2]): row[1].removeprefix("AUDIT_")
                for row in rows if row[1] in {"AUDIT_COMPLETED", "AUDIT_ABORTED", "AUDIT_FAILED"}
            }
            for attempt_id, approval_id, state, terminal_at in attempt_rows:
                recorded = event_states.get((attempt_id, approval_id))
                if (terminal_at is None and recorded is not None) or (
                    terminal_at is not None and recorded != state
                ):
                    raise DurableRegistryError("attempt projection disagrees with event ledger")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick != ("ok",):
                raise DurableRegistryError("registry SQLite structural check failed")
            return {"schema_version": REGISTRY_SCHEMA_VERSION,
                    "approval_count": len(approvals), "event_count": len(rows),
                    "event_head_sha256": previous, "tamper_check": "PASS"}
        finally:
            connection.close()


class DurableAuditEvidenceStore:
    """Atomic immutable task-scoped store for synthetic audit outputs."""

    def __init__(self, root: Path, maximum_bytes: int) -> None:
        self.root = root
        self.maximum_bytes = maximum_bytes

    @classmethod
    def create_synthetic(
        cls, root: str | Path, *, forbidden_roots: Sequence[str | Path],
        maximum_bytes: int,
    ) -> "DurableAuditEvidenceStore":
        base = Path(root)
        base.mkdir(parents=True, exist_ok=True)
        resolved = base.resolve()
        if base.is_symlink():
            raise ProductionBoundaryError("evidence root cannot be a symlink")
        for forbidden in forbidden_roots:
            other = Path(forbidden).resolve()
            if _is_within(resolved, other) or _is_within(other, resolved):
                raise ProductionBoundaryError("evidence store must be separate from source data")
        (resolved / SYNTHETIC_EVIDENCE_MARKER).write_text(
            "R.9D temporary synthetic audit evidence only\n", encoding="utf-8"
        )
        return cls(resolved, maximum_bytes)

    def finalize(
        self, *, attempt_id: str, approval_id: str, event_head_sha256: str,
        artifacts: Mapping[str, bytes], terminal_state: str,
    ) -> Path:
        _safe_identifier(attempt_id, "attempt_id")
        _safe_identifier(approval_id, "approval_id")
        if terminal_state not in TERMINAL_STATES:
            raise ProductionBoundaryError("invalid terminal state")
        if not artifacts or not set(artifacts) <= set(PERMITTED_OUTPUTS) - {"root_audit_manifest.json"}:
            raise ProductionBoundaryError("unexpected audit evidence artifact")
        total = sum(len(value) for value in artifacts.values())
        if total > self.maximum_bytes:
            raise ProductionBoundaryError("audit evidence output limit exceeded")
        temporary = self.root / f".tmp-{attempt_id}"
        final = self.root / attempt_id
        if temporary.exists() or final.exists():
            raise ProductionBoundaryError("immutable attempt already exists")
        hashes: dict[str, str] = {}
        for name in sorted(artifacts):
            payload = artifacts[name]
            hashes[name] = _sha256(payload)
        manifest = {
            "schema_version": "local_fno_durable_evidence_manifest_v1",
            "attempt_id": attempt_id,
            "approval_id": approval_id,
            "terminal_state": terminal_state,
            "approval_event_head_sha256": event_head_sha256,
            "artifact_hashes": hashes,
            "artifact_bytes": total,
            "restore_verification_state": RESTORE_STATE,
            "backup_verified": False,
            "local_retention_state": RETENTION_STATE,
            "canonical": False,
            "promotion_eligible": False,
        }
        payload = _canonical_bytes(manifest)
        if total + len(payload) > self.maximum_bytes:
            raise ProductionBoundaryError("audit evidence output limit exceeded")
        temporary.mkdir()
        for name in sorted(artifacts):
            (temporary / name).write_bytes(artifacts[name])
        (temporary / "root_audit_manifest.json").write_bytes(payload)
        os.replace(temporary, final)
        return final
