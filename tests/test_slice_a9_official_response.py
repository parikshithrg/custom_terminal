import pytest

from market_intel.foundation.official_response import Answer, OfficialResponse, assess_response, pending_response_gate


def _response(**changes):
    values = dict(organization="NSE Data & Analytics", responder_name="Authorized Person",
        responder_role="Data licensing", received_at="2026-08-24T00:00:00Z", source_message_hash="a" * 64,
        manual_download=Answer.YES, automated_download=Answer.NO, immutable_local_retention=Answer.YES,
        correction_vintage_retention=Answer.CONDITIONAL, derived_noncommercial_research=Answer.YES,
        raw_redistribution=Answer.NO, pre_2024_snapshots_available=Answer.YES,
        paid_relationship_required=Answer.NO)
    values.update(changes)
    return OfficialResponse(**values)


def test_authoritative_positive_manual_response_can_open_only_manual_sample():
    result = assess_response(_response())
    assert result["status"] == "ELIGIBLE_FOR_MANUAL_SAMPLE_ACQUISITION"
    assert result["automation"] == "PROHIBITED_OR_UNCLEAR"


def test_paid_or_unknown_requirement_keeps_public_project_blocked():
    assert assess_response(_response(paid_relationship_required=Answer.YES))["status"] == "BLOCKED"
    assert assess_response(_response(paid_relationship_required=Answer.UNKNOWN))["status"] == "BLOCKED"


def test_retention_and_pre_2024_availability_are_mandatory():
    result = assess_response(_response(immutable_local_retention=Answer.NO,
                                       pre_2024_snapshots_available=Answer.NO))
    assert "immutable_retention_not_permitted" in result["blockers"]
    assert "pre_2024_snapshots_unavailable" in result["blockers"]


def test_non_authoritative_or_unhashed_reply_is_rejected():
    with pytest.raises(ValueError):
        _response(organization="Unofficial forum")
    with pytest.raises(ValueError):
        _response(source_message_hash="short")


def test_no_reply_never_authorizes_acquisition():
    gate = pending_response_gate()
    assert gate["acquisition_authorized"] == "NO"
    assert gate["historical_population_capability"] == "FAIL"
