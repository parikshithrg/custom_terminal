"""Offline prerequisite assessment only; no executable news-source activation."""
from dataclasses import dataclass
import re

REQUIRED_BINDINGS = (
    "publisher_binding", "consumer_scope_binding", "permission_evidence_binding",
    "identity_semantics_binding", "timestamp_policy_binding", "provenance_policy_binding",
    "freshness_policy_binding", "missingness_policy_binding", "retention_policy_binding",
    "execution_approval_binding",
)


@dataclass(frozen=True, slots=True)
class NewsReadiness:
    consumer_id: str
    status: str
    missing_prerequisites: tuple[str, ...]
    can_fetch: bool = False
    can_score: bool = False

    def __post_init__(self):
        if self.consumer_id != "news_calendar" or self.can_fetch is not False or self.can_score is not False:
            raise ValueError("Source activation and sentiment execution are not implemented")


def assess_news_readiness(evidence=None):
    """Hash claims are metadata, not authenticated approval or source evidence."""
    if evidence is None:
        evidence = {}
    if type(evidence) is not dict or set(evidence) - set(REQUIRED_BINDINGS):
        raise ValueError("Unexpected prerequisite bindings")
    missing = tuple(key for key in REQUIRED_BINDINGS
                    if not isinstance(evidence.get(key), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", evidence[key]))
    return NewsReadiness("news_calendar",
        "UNAVAILABLE_MISSING_PREREQUISITES" if missing else
        "METADATA_BOUND_NOT_VERIFIED_EXECUTION_DISABLED", missing)
