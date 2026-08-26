from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_contracts import (
    CapabilityStatus,
    CorporateActionEvidence,
    EvidenceStage,
    HypothesisContract,
    LegacyLifecycle,
    PopulationCapability,
    PopulationCapabilityAssessment,
    ResolutionStatus,
    TerminalClassification,
    TerminalOutcome,
    map_legacy_lifecycle,
    reconcile_legacy_rows,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(("window", "decision", "expected"), [
    ("train", "accepted", LegacyLifecycle.TRAIN_PROMOTED),
    ("train", "rejected", LegacyLifecycle.TRAIN_REJECTED),
    ("val", "accepted", LegacyLifecycle.VALIDATION_CONFIRMED),
    ("val", "rejected", LegacyLifecycle.VALIDATION_REJECTED),
    ("test", "accepted", LegacyLifecycle.TEST_CONFIRMED),
    ("test", "rejected", LegacyLifecycle.TEST_REJECTED),
])
def test_legacy_lifecycle_mapping_is_stage_specific(window, decision, expected):
    assert map_legacy_lifecycle(window, decision) is expected


def test_ambiguous_legacy_state_remains_unresolved():
    assert map_legacy_lifecycle("train", "inconclusive") is LegacyLifecycle.UNRESOLVED_LEGACY_STATE
    assert map_legacy_lifecycle("unknown", "accepted") is LegacyLifecycle.UNRESOLVED_LEGACY_STATE


def test_reconciliation_view_does_not_mutate_or_promote_source_rows():
    source = [{"hypothesis_id": "x", "title": "idea", "split": "primary",
               "window": "train", "decision": "accepted"}]
    before = [dict(source[0])]
    result = reconcile_legacy_rows(source)
    assert source == before
    assert result[0]["lifecycle"] == "TRAIN_PROMOTED"
    assert result[0]["production_eligible"] is False


def test_derived_adjustment_factor_does_not_verify_action_type():
    evidence = CorporateActionEvidence(
        "ticker:A", "2026-01-01",
        frozenset({EvidenceStage.OBSERVED_PREV_CLOSE,
                   EvidenceStage.DISCONTINUITY_CANDIDATE,
                   EvidenceStage.FACTOR_DERIVED}),
        True, adjustment_factor=0.5,
    )
    assert EvidenceStage.ACTION_TYPE_VERIFIED not in evidence.stages
    assert evidence.authoritative_evidence_ref is None


def test_verified_corporate_action_requires_authoritative_evidence():
    with pytest.raises(ValueError, match="authoritative"):
        CorporateActionEvidence(
            "ticker:A", "2026-01-01",
            frozenset({EvidenceStage.ACTION_TYPE_VERIFIED}),
            True, action_type="SPLIT",
        )


def test_raw_prices_cannot_be_discarded_by_action_contract():
    with pytest.raises(ValueError, match="raw prices"):
        CorporateActionEvidence("ticker:A", "2026-01-01", frozenset(), False)


def test_unresolved_terminal_economics_cannot_invent_consideration():
    with pytest.raises(ValueError, match="cannot assert"):
        TerminalOutcome(
            "ticker:A", TerminalClassification.UNRESOLVED_DISAPPEARANCE,
            ResolutionStatus.UNRESOLVED, cash_consideration=10.0,
        )


def test_missing_observation_cannot_be_called_resolved_terminal_event():
    with pytest.raises(ValueError, match="cannot be resolved"):
        TerminalOutcome(
            "ticker:A", TerminalClassification.ORDINARY_MISSING_OBSERVATION,
            ResolutionStatus.RESOLVED, evidence_refs=("source",),
        )


def test_resolved_successor_requires_evidence():
    result = TerminalOutcome(
        "listing:A", TerminalClassification.MERGER_ACQUISITION,
        ResolutionStatus.RESOLVED, successor_instrument_id="instrument:B",
        evidence_refs=("official-scheme-hash",),
    )
    assert result.status is ResolutionStatus.RESOLVED


def test_traded_and_listed_population_capabilities_are_distinct():
    traded = PopulationCapabilityAssessment(
        PopulationCapability.HISTORICALLY_TRADED, CapabilityStatus.UNKNOWN,
        "NSE cash sessions", ("a8-bhavcopy-sample",),
    )
    listed = PopulationCapabilityAssessment(
        PopulationCapability.HISTORICALLY_LISTED, CapabilityStatus.FAIL,
        "NSE cash listings", ("a8-security-snapshot-sample",),
    )
    assert traded.capability != listed.capability
    assert traded.status is not CapabilityStatus.PASS
    assert listed.status is CapabilityStatus.FAIL


def test_hypothesis_contract_separates_horizon_and_overlay():
    contract = HypothesisContract(
        "momentum", "v1", "slow information diffusion", "top 20 percent 12-1 rank",
        "NSE_CLOSE", "NEXT_OPEN", 21, "PURE_TIME_EXIT", "cost-v1",
        "equal_weight", "primary", "EXPLORATORY", "momentum-family",
    )
    assert contract.holding_horizon_sessions == 21
    assert contract.exit_overlay == "PURE_TIME_EXIT"


def test_versioned_specs_preserve_failed_population_and_nonproduction_mapping():
    population = json.loads((ROOT / "specs/shared_population_capabilities_v1.json").read_text())
    shared = json.loads((ROOT / "specs/shared_research_contracts_v1.json").read_text())
    policy = json.loads((ROOT / "specs/research_promotion_policy_v1.json").read_text())
    assert population["capabilities"]["historically_listed_population_reconstructible"]["current_status"] == "FAIL"
    assert shared["legacy_mapping"]["train.accepted"] == "TRAIN_PROMOTED"
    assert "PRODUCTION_INELIGIBLE" in shared["lifecycle_states"]
    assert policy["retroactive_rule"].startswith("Existing Data test rows remain exploratory")


def test_neutral_contract_package_has_no_engine_dependency():
    source = (ROOT / "src/research_contracts/models.py").read_text(encoding="utf-8")
    assert "from dtest" not in source
    assert "from market_intel" not in source
    assert "kite" not in source.lower()
