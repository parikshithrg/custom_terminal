"""Categorical dataset capabilities and experiment trust gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class CapabilityStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


CAPABILITIES = (
    "price_history_complete",
    "survivorship_safe",
    "historical_universe_reconstructible",
    "corporate_actions_verified",
    "delisting_outcomes_available",
    "exchange_turnover_available",
    "publication_timing_known",
    "stable_security_identity_verified",
)


@dataclass(frozen=True)
class DatasetTrustContract:
    dataset_id: str
    version: str
    price_history_complete: CapabilityStatus
    survivorship_safe: CapabilityStatus
    historical_universe_reconstructible: CapabilityStatus
    corporate_actions_verified: CapabilityStatus
    delisting_outcomes_available: CapabilityStatus
    exchange_turnover_available: CapabilityStatus
    publication_timing_known: CapabilityStatus
    stable_security_identity_verified: CapabilityStatus

    def statuses(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items() if key in CAPABILITIES}


def evaluate_requirements(
    contract: DatasetTrustContract, required: list[str] | tuple[str, ...]
) -> dict:
    unknown = sorted(set(required) - set(CAPABILITIES))
    if unknown:
        raise ValueError(f"unknown dataset capabilities: {unknown}")
    statuses = contract.statuses()
    failed = {name: statuses[name] for name in required if statuses[name] != "PASS"}
    return {
        "required_capabilities": list(required),
        "capability_results": {name: statuses[name] for name in required},
        "failed_or_unknown": failed,
        "promotable": not failed,
    }
