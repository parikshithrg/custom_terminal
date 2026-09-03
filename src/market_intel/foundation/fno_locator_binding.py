"""Filesystem-only F&O locator binding preparation.

This module deliberately contains no SQLite client or parser. It reads a single
approved TOML locator and bounded raw file bytes, then emits a sanitized,
non-activating identity anchor and proposal. Production audit activation remains
the responsibility of later reviewed code and an exact one-use approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat as stat_module
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


BINDING_SCHEMA_VERSION = "fno_production_locator_binding_anchor_v1"
PROPOSAL_SCHEMA_VERSION = "fno_production_locator_binding_proposal_v1"
PRIVATE_SCHEMA_VERSION = "fno_private_locator_binding_result_v1"
SAMPLING_ALGORITHM = "ORDERED_64_POSITION_SAMPLED_IDENTITY_V1"
SANITIZED_ALIAS = "PRIVATE_FNO_DATABASE_V1"
CONFIGURATION_KEY = "paths.fno_db"
SQLITE_MAGIC = b"SQLite format 3\x00"
HEADER_BYTES = 100
CHUNK_SIZE = 4 * 1024 * 1024
NOMINAL_SAMPLE_COUNT = 64
INTERIOR_SAMPLE_COUNT = 62
MAXIMUM_TOTAL_BYTES_READ = NOMINAL_SAMPLE_COUNT * CHUNK_SIZE + HEADER_BYTES
PREPARED = "FNO_PRODUCTION_LOCATOR_BINDING_PREPARED"
NOT_LOCATED = "FNO_DATABASE_NOT_LOCATED"
NOT_SAFE = "FNO_TARGET_NOT_REGULAR_OR_SAFE"
HEADER_INVALID = "FNO_HEADER_FORMAT_INVALID"
CHANGED = "FNO_DATABASE_CHANGED_DURING_BINDING"
SCOPE_VIOLATION = "FNO_BINDING_SCOPE_VIOLATION"
PRODUCTION_INTERLOCK = "R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE"


class LocatorBindingError(RuntimeError):
    """Fail-closed binding error that never includes a private path."""

    def __init__(self, decision: str, message: str) -> None:
        super().__init__(message)
        self.decision = decision


@dataclass(frozen=True)
class SafeFileState:
    size_bytes: int
    modification_time_ns: int
    device_id: int
    file_id: int
    regular_file: bool
    symlink: bool
    reparse_point: bool

    def stability_key(self) -> tuple[int, ...]:
        return (
            self.size_bytes,
            self.modification_time_ns,
            self.device_id,
            self.file_id,
            int(self.regular_file),
            int(self.symlink),
            int(self.reparse_point),
        )


@dataclass(frozen=True)
class SampleRecord:
    offset: int
    length: int
    sha256: str


@dataclass(frozen=True)
class PreparedBinding:
    tracked_anchor: Mapping[str, Any]
    binding_proposal: Mapping[str, Any]
    private_result: Mapping[str, Any]


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_source_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise LocatorBindingError(SCOPE_VIOLATION, "source commit is not exact")
    return value


def _read_config_locator(config_path: Path) -> tuple[str, str]:
    """Read only ``paths.fno_db`` while hashing the exact configuration bytes."""
    try:
        raw = config_path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise LocatorBindingError(NOT_LOCATED, "approved locator source is unavailable") from None
    section = ""
    matches: list[str] = []
    for original in text.splitlines():
        stripped = original.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header = re.fullmatch(r"\[\s*([^]]+?)\s*\]\s*(?:#.*)?", stripped)
        if header:
            section = header.group(1).strip()
            continue
        if section != "paths":
            continue
        key = re.match(r"^([A-Za-z0-9_-]+)\s*=", stripped)
        if key and key.group(1) == "fno_db":
            matches.append(original)
    if len(matches) != 1:
        raise LocatorBindingError(NOT_LOCATED, "approved locator key is missing or ambiguous")
    try:
        parsed = tomllib.loads("[paths]\n" + matches[0])
        value = parsed["paths"]["fno_db"]
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise LocatorBindingError(NOT_LOCATED, "approved locator value is invalid") from None
    if not isinstance(value, str) or not value.strip():
        raise LocatorBindingError(NOT_LOCATED, "approved locator value is empty")
    return value, sha256_bytes(raw)


def sample_offsets(size_bytes: int, *, chunk_size: int = CHUNK_SIZE) -> tuple[int, ...]:
    if size_bytes < HEADER_BYTES or chunk_size <= 0 or chunk_size > CHUNK_SIZE:
        raise LocatorBindingError(HEADER_INVALID, "target is too short or chunk bound is invalid")
    maximum_start = max(0, size_bytes - chunk_size)
    if maximum_start == 0:
        return (0,)
    candidates = [0, maximum_start]
    candidates.extend(
        (index * maximum_start) // (INTERIOR_SAMPLE_COUNT + 1)
        for index in range(1, INTERIOR_SAMPLE_COUNT + 1)
    )
    return tuple(sorted(set(candidates)))


def sampled_identity_root(records: tuple[SampleRecord, ...]) -> str:
    ordered = [asdict(record) for record in sorted(records, key=lambda item: item.offset)]
    return sha256_bytes(canonical_json_bytes(ordered))


def environment_fingerprint() -> str:
    public = {
        "algorithm": SAMPLING_ALGORITHM,
        "os_name": os.name,
        "platform_system": platform.system(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }
    return sha256_bytes(canonical_json_bytes(public))


def _is_reparse(info: os.stat_result) -> bool:
    flag = getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = int(getattr(info, "st_file_attributes", 0))
    return bool(attributes & flag)


def _assert_component_safety(candidate: Path) -> None:
    absolute = Path(os.path.abspath(candidate))
    existing: list[Path] = []
    cursor = absolute
    while True:
        if cursor.exists() or cursor.is_symlink():
            existing.append(cursor)
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    for component in reversed(existing):
        try:
            info = component.lstat()
        except OSError:
            raise LocatorBindingError(NOT_SAFE, "target path safety could not be established") from None
        if stat_module.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise LocatorBindingError(NOT_SAFE, "link or reparse indirection is prohibited")


def _safe_state(path: Path) -> SafeFileState:
    try:
        info = path.lstat()
    except OSError:
        raise LocatorBindingError(NOT_LOCATED, "configured target does not exist") from None
    state = SafeFileState(
        size_bytes=int(info.st_size),
        modification_time_ns=int(info.st_mtime_ns),
        device_id=int(info.st_dev),
        file_id=int(info.st_ino),
        regular_file=stat_module.S_ISREG(info.st_mode),
        symlink=stat_module.S_ISLNK(info.st_mode),
        reparse_point=_is_reparse(info),
    )
    if not state.regular_file or state.symlink or state.reparse_point:
        raise LocatorBindingError(NOT_SAFE, "configured target is not a safe regular file")
    return state


def _resolve_target(locator: str, config_path: Path) -> tuple[Path, bool]:
    configured = Path(locator)
    if not configured.is_absolute():
        configured = config_path.parent / configured
    _assert_component_safety(configured)
    try:
        absolute = Path(os.path.abspath(configured))
        resolved = configured.resolve(strict=True)
    except OSError:
        raise LocatorBindingError(NOT_LOCATED, "configured target does not exist") from None
    _assert_component_safety(resolved)
    _safe_state(resolved)
    differs = os.path.normcase(str(absolute)) != os.path.normcase(str(resolved))
    return resolved, differs


def _read_bounded(stream: Any, offset: int, length: int, budget: list[int]) -> bytes:
    if length < 0 or budget[0] + length > MAXIMUM_TOTAL_BYTES_READ:
        raise LocatorBindingError(SCOPE_VIOLATION, "raw-byte read budget would be exceeded")
    stream.seek(offset)
    payload = stream.read(length)
    budget[0] += len(payload)
    if len(payload) != length:
        raise LocatorBindingError(CHANGED, "target changed or became unreadable during binding")
    return payload


def _prepare_for_target(
    *, target: Path, configured_path_differs: bool, configuration_sha256: str,
    source_commit: str, mutation_hook: Callable[[], None] | None = None,
) -> PreparedBinding:
    source_commit = _safe_source_commit(source_commit)
    before = _safe_state(target)
    offsets = sample_offsets(before.size_bytes)
    records: list[SampleRecord] = []
    budget = [0]
    try:
        with target.open("rb", buffering=0) as stream:
            opened = os.fstat(stream.fileno())
            opened_key = (
                int(opened.st_size), int(opened.st_mtime_ns), int(opened.st_dev),
                int(opened.st_ino), int(stat_module.S_ISREG(opened.st_mode)),
                int(stat_module.S_ISLNK(opened.st_mode)), int(_is_reparse(opened)),
            )
            if opened_key != before.stability_key():
                raise LocatorBindingError(CHANGED, "target changed before raw-byte sampling")
            header_before = _read_bounded(stream, 0, HEADER_BYTES, budget)
            if not header_before.startswith(SQLITE_MAGIC):
                raise LocatorBindingError(HEADER_INVALID, "target header format is invalid")
            for offset in offsets:
                length = min(CHUNK_SIZE, before.size_bytes - offset)
                if offset == 0:
                    remainder = _read_bounded(
                        stream, HEADER_BYTES, max(0, length - HEADER_BYTES), budget
                    )
                    payload = header_before[:length] + remainder
                else:
                    payload = _read_bounded(stream, offset, length, budget)
                records.append(SampleRecord(offset, len(payload), sha256_bytes(payload)))
            if mutation_hook is not None:
                mutation_hook()
            header_after = _read_bounded(stream, 0, HEADER_BYTES, budget)
            opened_after = os.fstat(stream.fileno())
    except LocatorBindingError:
        raise
    except OSError:
        raise LocatorBindingError(NOT_SAFE, "bounded raw-byte read failed") from None
    _assert_component_safety(target)
    after = _safe_state(target)
    opened_after_key = (
        int(opened_after.st_size), int(opened_after.st_mtime_ns), int(opened_after.st_dev),
        int(opened_after.st_ino), int(stat_module.S_ISREG(opened_after.st_mode)),
        int(stat_module.S_ISLNK(opened_after.st_mode)), int(_is_reparse(opened_after)),
    )
    header_before_sha = sha256_bytes(header_before)
    header_after_sha = sha256_bytes(header_after)
    stable = (
        before.stability_key() == after.stability_key() == opened_after_key
        and header_before_sha == header_after_sha
    )
    if not stable:
        raise LocatorBindingError(CHANGED, "target changed during binding")
    samples = tuple(records)
    root = sampled_identity_root(samples)
    tracked = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "lifecycle_state": PREPARED,
        "sanitized_alias": SANITIZED_ALIAS,
        "configuration_key": CONFIGURATION_KEY,
        "configuration_file_sha256": configuration_sha256,
        "path_safety": {
            "configured_target_exists": True,
            "regular_file": True,
            "symlink": False,
            "reparse_point": False,
            "configured_and_resolved_path_differ": configured_path_differs,
            "absolute_path_disclosed": False,
        },
        "file_metadata": {
            "size_bytes": before.size_bytes,
            "modification_time_ns": before.modification_time_ns,
        },
        "header": {
            "bytes": HEADER_BYTES,
            "sha256": header_before_sha,
            "format_verdict": "SQLITE_MAGIC_PRESENT_RAW_BYTES_ONLY",
            "schema_values_interpreted": False,
        },
        "sampled_identity": {
            "algorithm_version": SAMPLING_ALGORITHM,
            "nominal_positions": NOMINAL_SAMPLE_COUNT,
            "interior_positions": INTERIOR_SAMPLE_COUNT,
            "chunk_size_bytes": CHUNK_SIZE,
            "unique_sample_count": len(samples),
            "sampled_bytes": sum(item.length for item in samples),
            "total_raw_bytes_read": budget[0],
            "maximum_total_bytes_read": MAXIMUM_TOTAL_BYTES_READ,
            "ordered_sample_root_sha256": root,
            "full_file_hash": False,
            "sample_pass_count": 1,
        },
        "stability": {
            "before_after_metadata_match": True,
            "before_after_header_match": True,
            "file_identity_match": True,
            "verdict": "STABLE_DURING_SINGLE_BOUNDED_PASS",
        },
        "source_commit": source_commit,
        "environment_fingerprint_sha256": environment_fingerprint(),
        "database_connected": False,
        "sql_executed": False,
        "schema_inspected": False,
        "market_rows_read": False,
        "audit_started": False,
        "analysis_started": False,
        "backtest_started": False,
        "trading_enabled": False,
        "production_activation_eligible": False,
        "production_interlock": PRODUCTION_INTERLOCK,
    }
    anchor_sha = sha256_bytes(canonical_json_bytes(tracked))
    proposal = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "proposal_state": "PENDING_PDF_V4_AND_EXPLICIT_OWNER_REVIEW",
        "binding_anchor_sha256": anchor_sha,
        "sanitized_alias": SANITIZED_ALIAS,
        "configuration_file_sha256": configuration_sha256,
        "sampled_identity_algorithm": SAMPLING_ALGORITHM,
        "ordered_sample_root_sha256": root,
        "unique_sample_count": len(samples),
        "total_raw_bytes_read": budget[0],
        "source_commit": source_commit,
        "requested_future_scope": "EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY",
        "database_connection_requested": False,
        "audit_execution_requested": False,
        "activation_requested": False,
        "production_activation_eligible": False,
        "later_exact_one_use_audit_approval_required": True,
        "statement": (
            "Sanitized binding proposal only. PDF v4 generation and explicit owner "
            "review are required before any interlock-removal implementation may be proposed."
        ),
    }
    private = {
        "schema_version": PRIVATE_SCHEMA_VERSION,
        "configured_path": str(target),
        "resolved_path": str(target),
        "sanitized_alias": SANITIZED_ALIAS,
        "configuration_file_sha256": configuration_sha256,
        "samples": [asdict(item) for item in samples],
        "tracked_anchor_sha256": anchor_sha,
        "binding_proposal_sha256": sha256_bytes(canonical_json_bytes(proposal)),
        "lifecycle_state": PREPARED,
    }
    return PreparedBinding(tracked, proposal, private)


def prepare_synthetic_binding(
    *, config_path: str | Path, source_commit: str,
    mutation_hook: Callable[[], None] | None = None,
) -> PreparedBinding:
    config = Path(config_path)
    locator, config_hash = _read_config_locator(config)
    target, differs = _resolve_target(locator, config)
    return _prepare_for_target(
        target=target,
        configured_path_differs=differs,
        configuration_sha256=config_hash,
        source_commit=source_commit,
        mutation_hook=mutation_hook,
    )


def prepare_production_binding(
    *, config_path: str | Path, source_commit: str,
) -> PreparedBinding:
    """Perform one approved pass with no injectable callback or database client."""
    config = Path(config_path)
    locator, config_hash = _read_config_locator(config)
    target, differs = _resolve_target(locator, config)
    return _prepare_for_target(
        target=target,
        configured_path_differs=differs,
        configuration_sha256=config_hash,
        source_commit=source_commit,
    )


def write_binding_artifacts(
    binding: PreparedBinding, *, private_path: str | Path,
    anchor_path: str | Path, proposal_path: str | Path,
) -> dict[str, str]:
    destinations = {
        "private": (Path(private_path), binding.private_result),
        "anchor": (Path(anchor_path), binding.tracked_anchor),
        "proposal": (Path(proposal_path), binding.binding_proposal),
    }
    for destination, _ in destinations.values():
        if destination.exists():
            raise LocatorBindingError(SCOPE_VIOLATION, "immutable binding artifact already exists")
    written: list[Path] = []
    temporary_paths: list[Path] = []
    try:
        for destination, value in destinations.values():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".tmp")
            if temporary.exists():
                raise LocatorBindingError(SCOPE_VIOLATION, "partial binding artifact exists")
            temporary_paths.append(temporary)
            temporary.write_bytes(canonical_json_bytes(value))
            os.replace(temporary, destination)
            written.append(destination)
    except Exception as exc:
        for destination in written:
            try:
                destination.unlink()
            except OSError:
                pass
        for temporary in temporary_paths:
            try:
                temporary.unlink()
            except OSError:
                pass
        if isinstance(exc, LocatorBindingError):
            raise
        raise LocatorBindingError(SCOPE_VIOLATION, "binding artifact publication failed") from None
    return {
        name + "_sha256": sha256_bytes(path.read_bytes())
        for name, (path, _) in destinations.items()
    }
