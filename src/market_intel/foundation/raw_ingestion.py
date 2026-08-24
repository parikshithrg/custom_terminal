"""Immutable raw-object storage and canonical acquisition manifests."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from .providers import ProviderObject


class AcquisitionStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RawObjectManifest:
    manifest_version: str
    provider: str
    dataset: str
    source_identity: str
    retrieval_timestamp: str
    request_parameters: dict[str, str]
    expected_event_date: str | None
    content_hash: str
    byte_size: int
    schema_parser_version: str
    licensing_retention_notes: str | None
    acquisition_status: AcquisitionStatus
    retry_count: int = 0
    error_state: str | None = None
    stored_payload: str | None = None


def bytes_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_immutable(
    obj: ProviderObject, *, raw_root: Path, parser_version: str,
    retrieved_at: datetime | None = None,
) -> tuple[Path, RawObjectManifest]:
    """Copy a provider object once; an existing content-addressed object is verified."""
    source_hash = bytes_hash(obj.local_path)
    retrieval_id = source_hash[:24]
    target_dir = raw_root / obj.provider / obj.dataset.value / retrieval_id
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = obj.local_path.suffix or ".payload"
    target = target_dir / f"payload{suffix}"
    if target.exists():
        if bytes_hash(target) != source_hash:
            raise FileExistsError(f"immutable raw payload hash mismatch: {target}")
    else:
        shutil.copyfile(obj.local_path, target)
    timestamp = (retrieved_at or datetime.now(timezone.utc)).isoformat()
    manifest = RawObjectManifest(
        manifest_version="raw_object_manifest_v1", provider=obj.provider,
        dataset=obj.dataset.value, source_identity=obj.source_identity,
        retrieval_timestamp=timestamp, request_parameters=obj.request_parameters,
        expected_event_date=obj.expected_event_date, content_hash=source_hash,
        byte_size=target.stat().st_size, schema_parser_version=parser_version,
        licensing_retention_notes=obj.licensing_notes,
        acquisition_status=AcquisitionStatus.SUCCEEDED, stored_payload=str(target),
    )
    manifest_path = target_dir / "manifest.json"
    payload = json.dumps(asdict(manifest), indent=2, sort_keys=True, default=str) + "\n"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Retrieval time is evidence from the first successful acquisition.
        comparable = json.loads(payload)
        comparable["retrieval_timestamp"] = existing.get("retrieval_timestamp")
        if existing != comparable:
            raise FileExistsError(f"immutable raw manifest conflict: {manifest_path}")
        manifest = RawObjectManifest(**existing)
    else:
        manifest_path.write_text(payload, encoding="utf-8")
    return target, manifest


def verify_raw_object(manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = Path(manifest["stored_payload"])
    return (target.exists() and target.stat().st_size == manifest["byte_size"]
            and bytes_hash(target) == manifest["content_hash"])
