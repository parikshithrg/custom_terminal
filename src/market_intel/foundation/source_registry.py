"""Versioned official-public-source feasibility registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class QualificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class OfficialSource:
    source_id: str
    dataset: str
    organization: str
    landing_page: str
    retrieval_mechanism: str
    available_date_range: str
    format_schema: str
    inactive_securities_included: str
    historical_vintages: str
    publication_timing: str
    revision_behavior: str
    terms_concerns: str
    automation_restrictions: str
    known_missing_fields: tuple[str, ...]
    qualification_status: QualificationStatus
    supporting_evidence: tuple[str, ...]


def load_source_registry(path: Path) -> tuple[str, list[OfficialSource]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = set(OfficialSource.__dataclass_fields__)
    rows = []
    for item in raw["sources"]:
        missing = required - set(item)
        if missing:
            raise ValueError(f"source {item.get('source_id')} missing {sorted(missing)}")
        item["known_missing_fields"] = tuple(item["known_missing_fields"])
        item["supporting_evidence"] = tuple(item["supporting_evidence"])
        item["qualification_status"] = QualificationStatus(item["qualification_status"])
        rows.append(OfficialSource(**item))
    return raw["registry_version"], rows
