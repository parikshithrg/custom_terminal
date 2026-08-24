"""Deterministic assessment of written official data-permission responses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
class Answer(StrEnum):
    YES = "YES"
    NO = "NO"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class ClarificationStatus(StrEnum):
    PERMITTED = "PERMITTED"
    PROHIBITED = "PROHIBITED"
    REQUIRES_AGREEMENT = "REQUIRES_AGREEMENT"
    PAID_ONLY = "PAID_ONLY"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_ANSWERED = "NOT_ANSWERED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


OFFICIAL_DOMAINS = {"nse.co.in", "nseindia.com"}
MANDATORY_MANUAL_GATE = {
    "manual_download", "immutable_local_retention", "normalized_local_tables",
    "derived_noncommercial_research", "pre_2024_snapshots_available", "approved_access_path",
    "payment_required", "institutional_affiliation_required", "agreement_required",
}


@dataclass(frozen=True)
class ResponseEnvelope:
    sender_domain: str | None
    department: str | None
    subject: str | None
    response_date: str | None
    complete_headers: bool
    exact_body_available: bool
    paraphrased_or_truncated: bool
    referenced_attachments: tuple[str, ...] = ()
    supplied_attachments: tuple[str, ...] = ()


def validate_envelope(envelope: ResponseEnvelope) -> list[str]:
    failures: list[str] = []
    if envelope.sender_domain is None or not any(
        envelope.sender_domain == domain or envelope.sender_domain.endswith("." + domain)
        for domain in OFFICIAL_DOMAINS
    ):
        failures.append("unofficial_or_missing_sender_domain")
    if not envelope.department:
        failures.append("responding_department_missing")
    if not envelope.subject:
        failures.append("subject_missing")
    if not envelope.response_date:
        failures.append("response_date_missing")
    if not envelope.complete_headers:
        failures.append("complete_headers_missing")
    if not envelope.exact_body_available or envelope.paraphrased_or_truncated:
        failures.append("exact_complete_body_missing")
    missing = sorted(set(envelope.referenced_attachments) - set(envelope.supplied_attachments))
    if missing:
        failures.append("referenced_attachments_missing:" + ",".join(missing))
    return failures


def assess_classifications(classifications: dict[str, ClarificationStatus]) -> dict[str, object]:
    missing = sorted(MANDATORY_MANUAL_GATE - set(classifications))
    unresolved = sorted(key for key in MANDATORY_MANUAL_GATE
                        if classifications.get(key) in {None, ClarificationStatus.AMBIGUOUS,
                                                        ClarificationStatus.NOT_ANSWERED})
    if missing or unresolved:
        return {"decision": "AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE",
                "acquisition_authorized": False, "unresolved": sorted(set(missing + unresolved))}
    if classifications["payment_required"] == ClarificationStatus.PAID_ONLY:
        return {"decision": "PAID_ONLY_ROUTE_INCOMPATIBLE_WITH_PROJECT", "acquisition_authorized": False}
    agreement_fields = {"institutional_affiliation_required", "agreement_required"}
    if any(classifications[key] == ClarificationStatus.REQUIRES_AGREEMENT for key in agreement_fields):
        return {"decision": "APPLICATION_OR_AGREEMENT_REQUIRED", "acquisition_authorized": False}
    if classifications["pre_2024_snapshots_available"] == ClarificationStatus.NOT_AVAILABLE:
        return {"decision": "OFFICIAL_HISTORICAL_SNAPSHOTS_UNAVAILABLE", "acquisition_authorized": False}
    permitted = {"manual_download", "immutable_local_retention", "normalized_local_tables",
                 "derived_noncommercial_research", "pre_2024_snapshots_available", "approved_access_path"}
    if all(classifications[key] == ClarificationStatus.PERMITTED for key in permitted):
        return {"decision": "AUTHORIZED_TO_RESUME_LOCKED_MANUAL_QUALIFICATION",
                "acquisition_authorized": True}
    return {"decision": "FOLLOW_UP_CLARIFICATION_REQUIRED", "acquisition_authorized": False}


def unresolved_follow_up(classifications: dict[str, ClarificationStatus]) -> list[str]:
    return sorted(key for key, status in classifications.items()
                  if status in {ClarificationStatus.AMBIGUOUS, ClarificationStatus.NOT_ANSWERED})


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
