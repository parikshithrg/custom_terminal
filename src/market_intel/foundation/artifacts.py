"""Immutable artifact hashing, Parquet writes, and the small SQLite catalog."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pandas as pd


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def frame_hash(frame: pd.DataFrame) -> str:
    ordered = frame.sort_index().sort_index(axis=1)
    payload = pd.util.hash_pandas_object(ordered, index=True).to_numpy().tobytes()
    schema = canonical_json({c: str(t) for c, t in ordered.dtypes.items()}).encode()
    return sha256_bytes(schema + payload)


def write_parquet_immutable(frame: pd.DataFrame, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path}")
    frame.to_parquet(path, index=False)
    return sha256_file(path)


def normalize_logical_path(value: str | Path) -> str:
    """Return a portable relative path for manifests and catalogs.

    Historical catalogs may contain Windows separators, so reads normalize
    them.  New writes reject absolute or parent-traversing paths: a host path
    is a runtime locator, not part of canonical artifact identity.
    """
    raw = str(value)
    windows = PureWindowsPath(raw)
    if windows.is_absolute() or Path(raw).is_absolute():
        raise ValueError(f"logical artifact path must be relative: {raw}")
    logical = PurePosixPath(raw.replace("\\", "/"))
    if not logical.parts or any(part in {"", ".", ".."} for part in logical.parts):
        raise ValueError(f"invalid logical artifact path: {raw}")
    return logical.as_posix()


class Catalog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL,
            state TEXT NOT NULL, manifest_path TEXT NOT NULL,
            manifest_hash TEXT NOT NULL, created_at TEXT NOT NULL)"""
        )
        self.db.commit()

    def record_run(self, row: dict[str, str]) -> None:
        portable = dict(row)
        portable["manifest_path"] = normalize_logical_path(portable["manifest_path"])
        self.db.execute(
            "INSERT INTO runs VALUES (:run_id,:experiment_id,:state,:manifest_path,:manifest_hash,:created_at)",
            portable,
        )
        self.db.commit()

    def runs(self) -> list[dict[str, str]]:
        """Read catalog rows with historical Windows separators normalized."""
        columns = ("run_id", "experiment_id", "state", "manifest_path", "manifest_hash", "created_at")
        rows = []
        for values in self.db.execute("SELECT * FROM runs ORDER BY run_id"):
            row = dict(zip(columns, values, strict=True))
            row["manifest_path"] = normalize_logical_path(row["manifest_path"])
            rows.append(row)
        return rows

    def close(self) -> None:
        self.db.close()

