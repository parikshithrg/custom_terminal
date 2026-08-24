"""Deterministic assessment of written official data-permission responses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Answer(StrEnum):
    YES = "YES"
    NO = "NO"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OfficialResponse:
    organization: str
    responder_name: str
    responder_role: str
    received_at: str
    source_message_hash: str
    manual_download: Answer
    automated_download: Answer
    immutable_local_retention: Answer
    correction_vintage_retention: Answer
    derived_noncommercial_research: Answer
    raw_redistribution: Answer
    pre_2024_snapshots_available: Answer
    paid_relationship_required: Answer

    def __post_init__(self) -> None:
        if self.organization not in {"NSE", "NSE Data & Analytics"}:
            raise ValueError("response must come from an authoritative NSE organization")
        if len(self.source_message_hash) != 64:
            raise ValueError("exact official response SHA-256 is required")


def assess_response(response: OfficialResponse) -> dict[str, str | list[str]]:
    blockers: list[str] = []
    if response.manual_download not in {Answer.YES, Answer.CONDITIONAL}:
        blockers.append("manual_download_not_permitted")
    if response.immutable_local_retention not in {Answer.YES, Answer.CONDITIONAL}:
        blockers.append("immutable_retention_not_permitted")
    if response.derived_noncommercial_research not in {Answer.YES, Answer.CONDITIONAL}:
        blockers.append("derived_research_not_permitted")
    if response.pre_2024_snapshots_available not in {Answer.YES, Answer.CONDITIONAL}:
        blockers.append("pre_2024_snapshots_unavailable")
    if response.paid_relationship_required != Answer.NO:
        blockers.append("paid_or_unknown_relationship_requirement")
    status = "ELIGIBLE_FOR_MANUAL_SAMPLE_ACQUISITION" if not blockers else "BLOCKED"
    return {"status": status, "blockers": blockers,
            "automation": "PERMITTED" if response.automated_download == Answer.YES else "PROHIBITED_OR_UNCLEAR",
            "redistribution": "PERMITTED" if response.raw_redistribution == Answer.YES else "PROHIBITED_OR_UNCLEAR"}


def pending_response_gate() -> dict[str, str]:
    return {"status": "AWAITING_OFFICIAL_WRITTEN_RESPONSE",
            "acquisition_authorized": "NO", "historical_population_capability": "FAIL"}
