"""Immutable raw-object storage and canonical acquisition manifests."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
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
    retention_classification: str = "UNSPECIFIED"
    data_classification: str = "UNCLASSIFIED"
    retry_count: int = 0
    error_state: str | None = None
    stored_payload: str | None = None
    source_organization: str | None = None
    source_url: str | None = None
    http_status: int | None = None
    response_metadata: dict[str, str] = field(default_factory=dict)
    retry_history: tuple[str, ...] = ()
    retrieval_outcome: str = "SUCCEEDED"
    quarantine_reason: str | None = None


def bytes_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_immutable(
    obj: ProviderObject, *, raw_root: Path, parser_version: str,
    retrieved_at: datetime | None = None, portable_paths: bool = False,
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
        with tempfile.NamedTemporaryFile(dir=target_dir, prefix=".payload-", delete=False) as stream:
            temporary = Path(stream.name)
        try:
            shutil.copyfile(obj.local_path, temporary)
            if bytes_hash(temporary) != source_hash:
                raise IOError("raw payload changed during acquisition")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    timestamp = (retrieved_at or datetime.now(timezone.utc)).isoformat()
    manifest = RawObjectManifest(
        manifest_version="raw_object_manifest_v1", provider=obj.provider,
        dataset=obj.dataset.value, source_identity=obj.source_identity,
        retrieval_timestamp=timestamp, request_parameters=obj.request_parameters,
        expected_event_date=obj.expected_event_date, content_hash=source_hash,
        byte_size=target.stat().st_size, schema_parser_version=parser_version,
        licensing_retention_notes=obj.licensing_notes,
        acquisition_status=AcquisitionStatus.SUCCEEDED,
        retention_classification=obj.retention_classification,
        data_classification=obj.data_classification,
        stored_payload=target.name if portable_paths else str(target),
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
        temporary_manifest = manifest_path.with_name(f".manifest-{source_hash[:12]}.tmp")
        temporary_manifest.write_text(payload, encoding="utf-8")
        try:
            os.replace(temporary_manifest, manifest_path)
        finally:
            temporary_manifest.unlink(missing_ok=True)
    return target, manifest


def verify_raw_object(manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = Path(manifest["stored_payload"])
    if not target.is_absolute():
        target = manifest_path.parent / target
    return (target.exists() and target.stat().st_size == manifest["byte_size"]
            and bytes_hash(target) == manifest["content_hash"])
