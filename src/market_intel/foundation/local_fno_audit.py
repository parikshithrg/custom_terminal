"""Synthetic-only implementation of the bounded local F&O audit proposal.

R.9B deliberately cannot resolve ``paths.fno_db``.  The governed entry point
accepts only caller-supplied SQLite files inside a marked synthetic fixture
root.  It inventories file identity, SQLite catalog metadata, and bounded local
provenance; it never reads user-table rows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


AUDIT_APPROVAL_TYPE = "LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1"
SYNTHETIC_FIXTURE_CLASS = "SYNTHETIC_AUDIT_TEST_FIXTURE"
IDENTITY_METHOD = "SIZE_MTIME_SQLITE_HEADER_PLUS_ORDERED_64_CHUNK_MERKLE_V1"
PROPOSAL_ID = "local_fno_audit_stage_1_3_v1"
PROPOSAL_MANIFEST_SHA256 = "4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8"
AUDIT_SCOPE_SHA256 = "86af643f9c88a1162ecaecf76d22e4e74b5d39816f6e6117eb6105b726588d8d"
RESOURCE_ENVELOPE_SHA256 = "1aec4f54a6e3cf88cfa1ecde91b5b8c1579886d38a5282e5131471b2694436b5"
EXPECTED_OUTPUTS_SHA256 = "b1d05cfba2de056156d07c4f93512372af9eafd6f2de7d682404050e742f0d8a"
PERMITTED_OUTPUTS = (
    "sanitized_file_identity_manifest.json",
    "sqlite_read_only_safety_result.json",
    "schema_catalog_inventory.json",
    "later_stage_query_plan_inventory.json",
    "local_provenance_inventory.json",
    "rights_retention_evidence_matrix.json",
    "audit_event_log.jsonl",
    "root_audit_manifest.json",
    "completion_report.md",
)
MAX_CHUNKS = 64
CHUNK_SIZE = 4 * 1024 * 1024
MAX_STATEMENTS = 50
STATEMENT_TIMEOUT_SECONDS = 5.0
MAX_PROVENANCE_FILES = 500
MAX_PROVENANCE_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 25 * 1024 * 1024
SQLITE_HEADER = b"SQLite format 3\x00"


class LocalFnoAuditError(RuntimeError):
    """Fail-closed audit contract violation."""


class AuditAborted(LocalFnoAuditError):
    """A started audit was safely aborted."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise LocalFnoAuditError("approval timestamps must include a timezone")
    return parsed


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _safe_alias(index: int, kind: str) -> str:
    return f"{kind}_{index:04d}"


def _sanitize_text(value: object) -> str:
    text = str(value)
    text = re.sub(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*\S+", r"\1=<redacted>", text)
    text = re.sub(r"file:(?:/{2,3})?[^\s?'\"]+", "file:<redacted>", text)
    text = re.sub(r"[A-Za-z]:\\[^\s'\"]+", "<redacted-path>", text)
    return text[:1000]


def _sanitize_sql(value: str) -> str:
    text = re.sub(r"'(?:''|[^'])*'", "?", value)
    text = re.sub(r'"(?:""|[^"])*"', "<identifier>", text)
    return _sanitize_text(text)


@dataclass(frozen=True)
class ProposalIdentity:
    proposal_id: str = PROPOSAL_ID
    proposal_manifest_sha256: str = PROPOSAL_MANIFEST_SHA256
    audit_scope_sha256: str = AUDIT_SCOPE_SHA256
    resource_envelope_sha256: str = RESOURCE_ENVELOPE_SHA256
    expected_outputs_sha256: str = EXPECTED_OUTPUTS_SHA256


@dataclass(frozen=True)
class AuditApproval:
    schema_version: str
    approval_type: str
    approval_id: str
    proposal: ProposalIdentity
    approved_locator_key: str
    approved_locator_sha256: str
    approved_database_identity_root: str
    approved_stages: tuple[int, ...]
    approved_resources: Mapping[str, Any]
    approved_outputs: tuple[str, ...]
    fixture_classification: str
    issued_at: str
    expires_at: str
    approved_by: str
    approval_statement: str
    one_use: bool = True
    template_only: bool = False
    usable: bool = True
    approval_payload_sha256: str = ""

    def body(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("approval_payload_sha256", None)
        return value


def seal_audit_approval(approval: AuditApproval) -> AuditApproval:
    return replace(approval,
                   approval_payload_sha256=_hash_bytes(_canonical_bytes(approval.body())))


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_type: str
    attempt_id: str
    approval_id: str
    detail: Mapping[str, Any]
    previous_event_sha256: str | None
    event_sha256: str


@dataclass(frozen=True)
class AuditApprovalRegistration:
    approval_id: str
    approval_payload_sha256: str
    registered: bool = True


@dataclass(frozen=True)
class AuditApprovalConsumption:
    approval_id: str
    attempt_id: str
    consumed: bool = True


@dataclass(frozen=True)
class AuditAttempt:
    attempt_id: str
    approval_id: str
    fixture_classification: str
    terminal_state: str
    output_directory: str


@dataclass(frozen=True)
class AuditTerminalResult:
    status: str
    decision: str
    attempt: AuditAttempt | None
    message: str


@dataclass(frozen=True)
class PermittedOutputContract:
    schema_version: str = "local_fno_permitted_outputs_v1"
    names: tuple[str, ...] = PERMITTED_OUTPUTS
    maximum_bytes: int = MAX_OUTPUT_BYTES


@dataclass(frozen=True)
class AuditRootManifest:
    schema_version: str
    proposal: Mapping[str, Any]
    approval_id: str
    attempt_id: str
    terminal_state: str
    fixture_classification: str
    canonical: bool
    promotion_eligible: bool
    artifact_hashes: Mapping[str, str]
    output_bytes_before_root_manifest: int
    missing_permitted_outputs: tuple[str, ...]


@dataclass(frozen=True)
class FileIdentity:
    schema_version: str
    method: str
    sanitized_database_handle: str
    size_bytes: int
    mtime_ns: int
    sqlite_header_sha256: str
    chunk_size_bytes: int
    nominal_chunk_count: int
    unique_chunk_count: int
    chunks: tuple[Mapping[str, Any], ...]
    sampled_root_sha256: str
    actual_bytes_read: int
    sidecars: tuple[Mapping[str, Any], ...]


class AuditApprovalRegistry:
    """Process-local one-use registry used only for synthetic R.9B tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._registered: dict[str, AuditApproval] = {}
        self._consumed: dict[str, str] = {}

    def register(self, approval: AuditApproval) -> AuditApprovalRegistration:
        validate_audit_approval(approval)
        with self._lock:
            if approval.approval_id in self._registered:
                raise LocalFnoAuditError("audit approval is already registered")
            self._registered[approval.approval_id] = approval
        return AuditApprovalRegistration(approval.approval_id,
                                         approval.approval_payload_sha256)

    def consume(self, approval: AuditApproval, attempt_id: str) -> AuditApprovalConsumption:
        """Atomically verify the exact registered bytes and consume once."""
        validate_audit_approval(approval)
        with self._lock:
            registered = self._registered.get(approval.approval_id)
            if registered is None:
                raise LocalFnoAuditError("audit approval is not registered")
            if registered != approval:
                raise LocalFnoAuditError("registered audit approval was altered")
            if approval.approval_id in self._consumed:
                raise LocalFnoAuditError("audit approval has already been consumed")
            self._consumed[approval.approval_id] = attempt_id
        return AuditApprovalConsumption(approval.approval_id, attempt_id)

    def consumed_by(self, approval_id: str) -> str | None:
        return self._consumed.get(approval_id)


def validate_audit_approval(approval: AuditApproval, *, now: datetime | None = None) -> None:
    if not isinstance(approval, AuditApproval):
        raise LocalFnoAuditError("market-research approval cannot substitute for audit approval")
    if approval.schema_version != "local_data_audit_stage_1_3_approval_v1" or approval.approval_type != AUDIT_APPROVAL_TYPE:
        raise LocalFnoAuditError("wrong audit approval type")
    if approval.template_only or not approval.usable or not approval.approval_id:
        raise LocalFnoAuditError("template or unusable audit approval")
    if not approval.one_use:
        raise LocalFnoAuditError("audit approval must be one-use")
    if approval.proposal != ProposalIdentity():
        raise LocalFnoAuditError("proposal hash mismatch")
    if approval.approved_stages != (1, 2, 3):
        raise LocalFnoAuditError("stage mismatch")
    if approval.approved_locator_sha256 != synthetic_locator_hash():
        raise LocalFnoAuditError("locator-file hash mismatch")
    expected_resources = {
        "chunk_size_bytes": CHUNK_SIZE, "chunk_count": MAX_CHUNKS,
        "maximum_statements": MAX_STATEMENTS,
        "statement_timeout_seconds": STATEMENT_TIMEOUT_SECONDS,
        "maximum_provenance_files": MAX_PROVENANCE_FILES,
        "maximum_provenance_bytes": MAX_PROVENANCE_BYTES,
        "maximum_output_bytes": MAX_OUTPUT_BYTES,
    }
    if dict(approval.approved_resources) != expected_resources:
        raise LocalFnoAuditError("resource mismatch")
    if approval.approved_outputs != PERMITTED_OUTPUTS:
        raise LocalFnoAuditError("output mismatch")
    if approval.fixture_classification != SYNTHETIC_FIXTURE_CLASS:
        raise LocalFnoAuditError("R.9B permits synthetic audit fixtures only")
    if approval.approved_locator_key == "paths.fno_db":
        raise LocalFnoAuditError("production F&O locator is disabled in R.9B")
    if _hash_bytes(_canonical_bytes(approval.body())) != approval.approval_payload_sha256:
        raise LocalFnoAuditError("audit approval payload hash mismatch")
    current = now or datetime.now(timezone.utc)
    if not (_parse_time(approval.issued_at) <= current <= _parse_time(approval.expires_at)):
        raise LocalFnoAuditError("audit approval is expired or not yet valid")


def _chunk_offsets(size: int) -> list[int]:
    max_start = max(0, size - CHUNK_SIZE)
    if max_start == 0:
        return [0]
    return sorted({(index * max_start) // (MAX_CHUNKS - 1) for index in range(MAX_CHUNKS)})


def capture_file_identity(path: str | Path, *, synthetic_root: str | Path) -> FileIdentity:
    candidate = Path(path)
    root = Path(synthetic_root).resolve()
    if candidate.is_symlink() or root.is_symlink():
        raise AuditAborted("symlink or path indirection is prohibited")
    resolved = candidate.resolve(strict=True)
    if not _within(resolved, root) or not (root / ".synthetic_audit_fixture").is_file():
        raise AuditAborted("target escapes the marked synthetic fixture root")
    if not resolved.is_file():
        raise AuditAborted("audit target is not a regular file")
    stat = resolved.stat()
    offsets = _chunk_offsets(stat.st_size)
    chunks: list[dict[str, Any]] = []
    with resolved.open("rb") as stream:
        header = stream.read(100)
        if not header.startswith(SQLITE_HEADER):
            raise AuditAborted("target does not have a valid SQLite header")
        for offset in offsets:
            stream.seek(offset)
            payload = stream.read(CHUNK_SIZE)
            chunks.append({"offset": offset, "byte_size": len(payload),
                           "sha256": _hash_bytes(payload)})
    sidecars = []
    for index, sidecar in enumerate(sorted(resolved.parent.glob(resolved.name + "*")), start=1):
        if sidecar == resolved:
            continue
        info = sidecar.stat()
        known_suffix = sidecar.name[len(resolved.name):]
        kind = {"-journal": "JOURNAL", "-wal": "WAL", "-shm": "SHM"}.get(
            known_suffix, _safe_alias(index, "OTHER_SIDECAR"))
        sidecars.append({"kind": kind, "size_bytes": info.st_size,
                         "mtime_ns": info.st_mtime_ns})
    return FileIdentity(
        schema_version="local_fno_file_identity_v1", method=IDENTITY_METHOD,
        sanitized_database_handle="SYNTHETIC_FNO_FIXTURE", size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns, sqlite_header_sha256=_hash_bytes(header),
        chunk_size_bytes=CHUNK_SIZE, nominal_chunk_count=MAX_CHUNKS,
        unique_chunk_count=len(chunks), chunks=tuple(chunks),
        sampled_root_sha256=_hash_bytes(_canonical_bytes(chunks)),
        actual_bytes_read=len(header) + sum(item["byte_size"] for item in chunks),
        sidecars=tuple(sidecars),
    )


def _identity_key(identity: FileIdentity) -> tuple[Any, ...]:
    return (identity.size_bytes, identity.mtime_ns, identity.sqlite_header_sha256,
            identity.sampled_root_sha256, identity.sidecars)


class ReadOnlyCatalogConnection:
    """One read-only SQLite connection with pre-execution SQL policy checks."""

    _DENIED = re.compile(r"\b(ATTACH|DETACH|CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|REPLACE|VACUUM|REINDEX|ANALYZE|LOAD_EXTENSION)\b", re.I)
    _ALLOWED_PRAGMAS = re.compile(r"^PRAGMA\s+(query_only(?:\s*=\s*ON)?|busy_timeout(?:\s*=\s*\d+)?|table_info\s*\([^)]*\)|index_list\s*\([^)]*\)|index_info\s*\([^)]*\)|foreign_key_list\s*\([^)]*\))\s*;?$", re.I)

    def __init__(self, path: Path, *, event_sink: list[dict[str, Any]]) -> None:
        uri = path.resolve().as_uri() + "?mode=ro"
        self._connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        self._connection.enable_load_extension(False)
        self._events = event_sink
        self.statement_count = 0
        self._plan_mode = False
        self._connection.set_authorizer(self._authorize)
        self.execute("PRAGMA query_only=ON")
        row = self.execute("PRAGMA query_only").fetchone()
        if row != (1,):
            self.close()
            raise AuditAborted("SQLite query_only could not be verified")
        self.execute("PRAGMA busy_timeout=5000")

    def _authorize(self, action: int, arg1: str | None, arg2: str | None,
                   database: str | None, trigger: str | None) -> int:
        denied_actions = {
            getattr(sqlite3, name) for name in (
                "SQLITE_ATTACH", "SQLITE_DETACH", "SQLITE_INSERT", "SQLITE_UPDATE",
                "SQLITE_DELETE", "SQLITE_CREATE_INDEX", "SQLITE_CREATE_TABLE",
                "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE",
                "SQLITE_CREATE_TEMP_TRIGGER", "SQLITE_CREATE_TEMP_VIEW",
                "SQLITE_CREATE_TRIGGER", "SQLITE_CREATE_VIEW", "SQLITE_DROP_INDEX",
                "SQLITE_DROP_TABLE", "SQLITE_DROP_TEMP_INDEX", "SQLITE_DROP_TEMP_TABLE",
                "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_DROP_TEMP_VIEW", "SQLITE_DROP_TRIGGER",
                "SQLITE_DROP_VIEW", "SQLITE_ALTER_TABLE", "SQLITE_REINDEX",
                "SQLITE_ANALYZE",
            ) if hasattr(sqlite3, name)
        }
        if action in denied_actions:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ and arg1 and not arg1.startswith("sqlite_") and not self._plan_mode:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA:
            name = (arg1 or "").lower()
            value = (arg2 or "").lower()
            if name not in {"query_only", "busy_timeout", "table_info", "index_list", "index_info", "foreign_key_list"}:
                return sqlite3.SQLITE_DENY
            if name == "query_only" and value not in {"", "on", "1"}:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _validate(self, sql: str) -> str:
        normalized = " ".join(sql.strip().split())
        if ";" in normalized.rstrip(";"):
            raise AuditAborted("multiple SQL statements are prohibited")
        if self._DENIED.search(normalized):
            raise AuditAborted("prohibited SQLite operation attempted")
        upper = normalized.upper()
        allowed = (
            upper.startswith("SELECT ") and re.search(r"\bFROM\s+SQLITE_(SCHEMA|MASTER)\b", upper)
            or bool(self._ALLOWED_PRAGMAS.match(normalized))
            or upper.startswith("EXPLAIN QUERY PLAN SELECT ")
        )
        if not allowed:
            raise AuditAborted("statement is outside the catalog-only allowlist")
        return normalized

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        normalized = self._validate(sql)
        self.statement_count += 1
        self._events.append({"type": "SQL_ATTEMPT", "statement": _sanitize_sql(normalized)})
        if self.statement_count > MAX_STATEMENTS:
            raise AuditAborted("statement-count limit exceeded")
        deadline = time.monotonic() + STATEMENT_TIMEOUT_SECONDS
        self._connection.set_progress_handler(
            lambda: 1 if time.monotonic() >= deadline else 0, 1
        )
        self._plan_mode = normalized.upper().startswith("EXPLAIN QUERY PLAN")
        try:
            return self._connection.execute(normalized, tuple(parameters))
        except sqlite3.Error as exc:
            raise AuditAborted(f"sanitized SQLite failure: {type(exc).__name__}") from None
        finally:
            self._plan_mode = False
            self._connection.set_progress_handler(None, 0)

    def close(self) -> None:
        self._connection.close()


def _catalog_inventory(connection: ReadOnlyCatalogConnection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE type IN ('table','view','index') ORDER BY type, name"
    ).fetchall()
    objects = []
    for object_type, name, table_name, sql in rows:
        quoted_name = '"' + str(name).replace('"', '""') + '"'
        item: dict[str, Any] = {
            "type": object_type, "name": name, "table_name": table_name,
            "declared_sql": sql,
        }
        if object_type in {"table", "view"} and not name.startswith("sqlite_"):
            item["columns"] = [
                {"position": r[0], "name": r[1], "declared_type": r[2],
                 "not_null": bool(r[3]), "default_declared": r[4] is not None,
                 "primary_key_position": r[5]}
                for r in connection.execute(f"PRAGMA table_info({quoted_name})").fetchall()
            ]
            item["foreign_keys"] = [
                {"id": r[0], "sequence": r[1], "referenced_table": r[2],
                 "from_column": r[3], "to_column": r[4], "on_update": r[5],
                 "on_delete": r[6], "match": r[7]}
                for r in connection.execute(f"PRAGMA foreign_key_list({quoted_name})").fetchall()
            ]
        if object_type == "table" and not name.startswith("sqlite_"):
            indexes = []
            for row in connection.execute(f"PRAGMA index_list({quoted_name})").fetchall():
                index_name = row[1]
                quoted_index = '"' + str(index_name).replace('"', '""') + '"'
                indexes.append({"name": index_name, "unique": bool(row[2]),
                                "origin": row[3], "partial": bool(row[4]),
                                "columns": [x[2] for x in connection.execute(
                                    f"PRAGMA index_info({quoted_index})").fetchall()]})
            item["indexes"] = indexes
        objects.append(item)
    return {"schema_version": "local_fno_schema_catalog_inventory_v1",
            "sqlite_version": sqlite3.sqlite_version, "objects": objects,
            "market_row_reads": 0}


def _provenance_inventory(roots: Sequence[str | Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    files: list[dict[str, Any]] = []
    bytes_read = 0
    allowed = {".json", ".jsonl", ".toml", ".md", ".txt", ".py", ".yaml", ".yml"}
    for root_index, raw_root in enumerate(roots, start=1):
        root = Path(raw_root)
        if root.is_symlink():
            raise AuditAborted("Stage 3 provenance root is a symlink")
        resolved_root = root.resolve(strict=True)
        for candidate in sorted(resolved_root.rglob("*"), key=lambda p: p.as_posix()):
            if candidate.is_symlink():
                raise AuditAborted("Stage 3 symlink is prohibited")
            if not candidate.is_file():
                continue
            if not _within(candidate.resolve(strict=True), resolved_root):
                raise AuditAborted("Stage 3 path escapes approved root")
            if len(files) >= MAX_PROVENANCE_FILES:
                raise AuditAborted("Stage 3 file-count limit exceeded")
            stat = candidate.stat()
            inspected = candidate.suffix.lower() in allowed
            if inspected:
                if bytes_read + stat.st_size > MAX_PROVENANCE_BYTES:
                    raise AuditAborted("Stage 3 byte limit exceeded")
                payload = candidate.read_bytes()
                bytes_read += len(payload)
                digest = _hash_bytes(payload)
                lower = payload.lower()
                status = "VERIFIED" if any(word in lower for word in
                    (b"source", b"license", b"retention", b"parser", b"manifest")) else "DECLARED_NOT_VERIFIED"
            else:
                digest = None
                status = "NOT_APPLICABLE"
            files.append({"root": _safe_alias(root_index, "provenance_root"),
                          "file": _safe_alias(len(files) + 1, "provenance_file"),
                          "extension": candidate.suffix.lower(), "size_bytes": stat.st_size,
                          "content_inspected": inspected, "sha256": digest,
                          "classification": status})
    inventory = {"schema_version": "local_fno_provenance_inventory_v1",
                 "files": files, "file_count": len(files), "bytes_read": bytes_read}
    statuses = {key: "MISSING" for key in ("source_provenance", "retention_rights",
                                             "correction_vintages", "backup_metadata")}
    if any(item["classification"] == "VERIFIED" for item in files):
        statuses["source_provenance"] = "DECLARED_NOT_VERIFIED"
    rights = {"schema_version": "local_fno_rights_retention_matrix_v1",
              "statuses": statuses,
              "absence_is_permission": False}
    return inventory, rights


class _ArtifactWriter:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.bytes_written = 0
        self.hashes: dict[str, str] = {}

    def write_json(self, name: str, value: Any) -> None:
        self._write(name, _canonical_bytes(value))

    def write_text(self, name: str, value: str) -> None:
        self._write(name, value.encode("utf-8"))

    def _write(self, name: str, payload: bytes) -> None:
        if name not in PERMITTED_OUTPUTS:
            raise AuditAborted("unexpected output rejected")
        if self.bytes_written + len(payload) > MAX_OUTPUT_BYTES:
            raise AuditAborted("output-byte limit exceeded")
        path = self.directory / name
        if path.exists():
            raise AuditAborted("immutable output already exists")
        path.write_bytes(payload)
        self.bytes_written += len(payload)
        self.hashes[name] = _hash_bytes(payload)


def _event(events: list[AuditEvent], event_type: str, attempt_id: str,
           approval_id: str, detail: Mapping[str, Any] | None = None) -> None:
    body = {"sequence": len(events) + 1, "event_type": event_type,
            "attempt_id": attempt_id, "approval_id": approval_id,
            "detail": dict(detail or {}),
            "previous_event_sha256": events[-1].event_sha256 if events else None}
    events.append(AuditEvent(**body, event_sha256=_hash_bytes(_canonical_bytes(body))))


def proposal_dry_run() -> AuditTerminalResult:
    return AuditTerminalResult(
        status="BLOCKED", decision="MISSING_EXACT_REGISTERED_AUDIT_APPROVAL",
        attempt=None,
        message="Proposal only; no path resolution, database connection, SQL, or audit attempt occurred.",
    )


def execute_approved_stage_1_3_audit(
    *, target_path: str | Path | None = None, synthetic_root: str | Path | None = None,
    approval: AuditApproval | None = None, registry: AuditApprovalRegistry | None = None,
    output_root: str | Path | None = None, provenance_roots: Sequence[str | Path] = (),
    attempt_id: str = "synthetic-audit-attempt", evaluated_at: datetime | None = None,
    later_query_plans: Sequence[str] = (), mode: str = "PROPOSAL_DRY_RUN",
) -> AuditTerminalResult:
    """Execute only a registered, one-use synthetic Stage 1-3 audit."""
    if mode == "PROPOSAL_DRY_RUN":
        return proposal_dry_run()
    if mode != "GOVERNED_SYNTHETIC_EXECUTION":
        raise LocalFnoAuditError("unsupported audit mode")
    if None in (target_path, synthetic_root, approval, registry, output_root):
        raise LocalFnoAuditError("exact synthetic audit inputs and approval are required")
    assert approval is not None and registry is not None
    validate_audit_approval(approval, now=evaluated_at)
    root = Path(synthetic_root)  # direct caller value; never a production config lookup
    path = Path(target_path)
    output = Path(output_root).resolve()
    if _within(output, path.resolve().parent) or any(_within(output, Path(r).resolve()) for r in provenance_roots):
        raise LocalFnoAuditError("audit output must be outside source and provenance directories")
    locator_hash = _hash_bytes(_canonical_bytes({
        "classification": SYNTHETIC_FIXTURE_CLASS,
        "handle": "SYNTHETIC_FNO_FIXTURE",
    }))
    if approval.approved_locator_sha256 != locator_hash:
        raise LocalFnoAuditError("locator-file hash mismatch")

    # This bounded filesystem read opens no SQLite connection and reads no rows.
    # The resulting capture serves both PRE_CONSUMPTION_BINDING and
    # IMMEDIATELY_BEFORE_OPEN because atomic in-memory consumption is the only
    # intervening operation.  Thus the proposal's five-pass maximum is kept.
    baseline = capture_file_identity(path, synthetic_root=root)
    if approval.approved_database_identity_root != baseline.sampled_root_sha256:
        raise LocalFnoAuditError("database-identity mismatch")
    registry.consume(approval, attempt_id)  # atomic and before sqlite3.connect

    temp = output / f".tmp-{attempt_id}"
    final = output / attempt_id
    if temp.exists() or final.exists():
        raise LocalFnoAuditError("attempt output already exists")
    output.mkdir(parents=True, exist_ok=True)
    temp.mkdir()
    writer = _ArtifactWriter(temp)
    events: list[AuditEvent] = []
    checkpoints = {"PRE_CONSUMPTION_AND_IMMEDIATELY_BEFORE_OPEN": asdict(baseline)}
    connection: ReadOnlyCatalogConnection | None = None
    terminal = "FAILED"
    failure = ""
    try:
        _event(events, "AUDIT_STARTED", attempt_id, approval.approval_id,
               {"fixture_classification": SYNTHETIC_FIXTURE_CLASS})
        stage1 = capture_file_identity(path, synthetic_root=root)
        checkpoints["AFTER_STAGE_1"] = asdict(stage1)
        if _identity_key(stage1) != _identity_key(baseline):
            raise AuditAborted("database mutation detected after Stage 1")

        connection = ReadOnlyCatalogConnection(path.resolve(), event_sink=[])
        safety_events = connection._events
        catalog = _catalog_inventory(connection)
        plans = []
        for sql in later_query_plans:
            statement = sql if sql.strip().upper().startswith("EXPLAIN QUERY PLAN") else f"EXPLAIN QUERY PLAN {sql}"
            plans.append({"statement": _sanitize_sql(statement),
                          "plan": connection.execute(statement).fetchall()})
        connection.close()
        connection = None
        for statement_event in safety_events:
            _event(events, statement_event["type"], attempt_id, approval.approval_id,
                   {"statement": statement_event["statement"]})
        stage2 = capture_file_identity(path, synthetic_root=root)
        checkpoints["AFTER_STAGE_2"] = asdict(stage2)
        if _identity_key(stage2) != _identity_key(baseline):
            raise AuditAborted("database mutation detected after Stage 2")

        provenance, rights = _provenance_inventory(provenance_roots)
        stage3 = capture_file_identity(path, synthetic_root=root)
        checkpoints["AFTER_STAGE_3"] = asdict(stage3)
        if _identity_key(stage3) != _identity_key(baseline):
            raise AuditAborted("database mutation detected after Stage 3")
        final_identity = capture_file_identity(path, synthetic_root=root)
        checkpoints["IMMEDIATELY_BEFORE_EVIDENCE_FINALIZATION"] = asdict(final_identity)
        if _identity_key(final_identity) != _identity_key(baseline):
            raise AuditAborted("database mutation detected before evidence finalization")

        binding = {"proposal_id": PROPOSAL_ID, "approval_id": approval.approval_id,
                   "attempt_id": attempt_id}
        writer.write_json("sanitized_file_identity_manifest.json", {
            "schema_version": "local_fno_identity_manifest_v1", **binding,
            "checkpoints": checkpoints})
        writer.write_json("sqlite_read_only_safety_result.json", {
            "schema_version": "local_fno_sqlite_safety_v1", "mode_ro": True,
            "query_only_verified": True, "single_connection": True,
            "statements_attempted": connection.statement_count if connection else len(safety_events),
            "events": safety_events, "market_row_reads": 0, **binding})
        writer.write_json("schema_catalog_inventory.json", {**catalog, **binding})
        writer.write_json("later_stage_query_plan_inventory.json", {
            "schema_version": "local_fno_query_plan_inventory_v1", "plans": plans,
            "queries_executed": 0, **binding})
        writer.write_json("local_provenance_inventory.json", {**provenance, **binding})
        writer.write_json("rights_retention_evidence_matrix.json", {**rights, **binding})
        terminal = "COMPLETED"
    except AuditAborted as exc:
        terminal = "ABORTED"
        failure = _sanitize_text(exc)
    except Exception as exc:  # preserve a terminal attempt without leaking values
        terminal = "FAILED"
        failure = f"sanitized failure: {type(exc).__name__}"
    finally:
        if connection is not None:
            connection.close()
        _event(events, f"AUDIT_{terminal}", attempt_id, approval.approval_id,
               {"message": failure or "synthetic Stage 1-3 audit completed"})
        if "audit_event_log.jsonl" not in writer.hashes:
            writer.write_text("audit_event_log.jsonl", "".join(
                _canonical_bytes(asdict(item)).decode("utf-8") for item in events))
        completion = (
            "# Synthetic F&O audit completion\n\n"
            f"- Proposal: `{PROPOSAL_ID}`\n"
            f"- Approval: `{approval.approval_id}`\n"
            f"- Attempt: `{attempt_id}`\n"
            f"- Terminal state: `{terminal}`\n"
            "- Historical completeness: `NOT_EVALUATED`\n"
            "- Point-in-time fitness: `NOT_EVALUATED`\n"
            "- Research eligibility: `NOT_APPROVED`\n"
            "- Promotion eligible: `false`\n"
        )
        writer.write_text("completion_report.md", completion)
        missing = tuple(sorted(set(PERMITTED_OUTPUTS) - set(writer.hashes)
                               - {"root_audit_manifest.json"}))
        root_manifest = AuditRootManifest(
            schema_version="local_fno_audit_root_manifest_v1",
            proposal=asdict(ProposalIdentity()), approval_id=approval.approval_id,
            attempt_id=attempt_id, terminal_state=terminal,
            fixture_classification=SYNTHETIC_FIXTURE_CLASS,
            canonical=False, promotion_eligible=False,
            artifact_hashes=dict(sorted(writer.hashes.items())),
            output_bytes_before_root_manifest=writer.bytes_written,
            missing_permitted_outputs=missing,
        )
        writer.write_json("root_audit_manifest.json", asdict(root_manifest))
        actual = {p.name for p in temp.iterdir() if p.is_file()}
        if not actual <= set(PERMITTED_OUTPUTS):
            raise LocalFnoAuditError("unexpected audit output exists")
        os.replace(temp, final)

    attempt = AuditAttempt(attempt_id, approval.approval_id, SYNTHETIC_FIXTURE_CLASS,
                           terminal, f"AUDIT_OUTPUT/{attempt_id}")
    return AuditTerminalResult(
        status=terminal,
        decision=("SYNTHETIC_ONLY_FNO_AUDITOR_IMPLEMENTED" if terminal == "COMPLETED"
                  else f"SYNTHETIC_AUDIT_{terminal}"),
        attempt=attempt, message=failure or "Synthetic-only audit completed.")


def synthetic_locator_hash() -> str:
    return _hash_bytes(_canonical_bytes({
        "classification": SYNTHETIC_FIXTURE_CLASS, "handle": "SYNTHETIC_FNO_FIXTURE"}))


def approved_resource_contract() -> dict[str, Any]:
    return {
        "chunk_size_bytes": CHUNK_SIZE, "chunk_count": MAX_CHUNKS,
        "maximum_statements": MAX_STATEMENTS,
        "statement_timeout_seconds": STATEMENT_TIMEOUT_SECONDS,
        "maximum_provenance_files": MAX_PROVENANCE_FILES,
        "maximum_provenance_bytes": MAX_PROVENANCE_BYTES,
        "maximum_output_bytes": MAX_OUTPUT_BYTES,
    }
