"""Sanitized read-only divergence checks for mutable legacy CSV logs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable

from .legacy_ledger import canonical_json_bytes, sha256_file


DIVERGENCE_VERSION = "legacy_log_divergence_v1"


def _rows(path: str | Path) -> tuple[list[dict[str, str]], str]:
    payload = Path(path).read_bytes()
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline="")))
    return rows, hashlib.sha256(payload).hexdigest()


def compare_legacy_logs(
    *, frozen_path: str | Path, live_path: str | Path,
    governed_manifest_paths: Iterable[str | Path] = (),
) -> dict[str, Any]:
    frozen, frozen_hash = _rows(frozen_path)
    live, live_hash = _rows(live_path)
    frozen_by_id = {row["hypothesis_id"]: row for row in frozen}
    live_by_id = {row["hypothesis_id"]: row for row in live}
    added = sorted(set(live_by_id) - set(frozen_by_id))
    missing = sorted(set(frozen_by_id) - set(live_by_id))
    modified = sorted(
        row_id for row_id in set(frozen_by_id) & set(live_by_id)
        if frozen_by_id[row_id] != live_by_id[row_id]
    )
    governed_ids: set[str] = set()
    for path in governed_manifest_paths:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        row_id = value.get("source_legacy_row_id")
        if row_id:
            governed_ids.add(str(row_id))
    added_governance = {row_id: row_id in governed_ids for row_id in added}
    return {
        "divergence_version": DIVERGENCE_VERSION,
        "frozen": {"row_count": len(frozen), "sha256": frozen_hash},
        "live": {"row_count": len(live), "sha256": live_hash},
        "added_row_ids": added,
        "missing_row_ids": missing,
        "modified_historical_row_ids": modified,
        "source_diverged": bool(added or missing or modified or live_hash != frozen_hash),
        "added_rows_governed_manifest_present": added_governance,
        "added_row_classification": (
            "POST_FREEZE_UNGOVERNED_ROWS"
            if added and not any(added_governance.values())
            else "NO_UNGOVERNED_ADDITIONS"
        ),
        "metrics_imported_or_interpreted": False,
    }


def write_divergence_report(report: dict[str, Any], path: str | Path) -> str:
    target = Path(path)
    payload = canonical_json_bytes(report)
    if target.exists() and target.read_bytes() != payload:
        raise FileExistsError(f"versioned divergence report differs: {target}")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return sha256_file(target)
