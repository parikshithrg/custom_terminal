from market_intel.foundation.official_response import (
    ClarificationStatus as S, ResponseEnvelope, assess_classifications,
    unresolved_follow_up, validate_envelope,
)


def _envelope(**changes):
    values = dict(sender_domain="nse.co.in", department="NSE Data", subject="Re: clarification",
                  response_date="2026-08-24", complete_headers=True, exact_body_available=True,
                  paraphrased_or_truncated=False, referenced_attachments=(), supplied_attachments=())
    values.update(changes)
    return ResponseEnvelope(**values)


def _answers(**changes):
    values = {"manual_download": S.PERMITTED, "immutable_local_retention": S.PERMITTED,
              "normalized_local_tables": S.PERMITTED, "derived_noncommercial_research": S.PERMITTED,
              "pre_2024_snapshots_available": S.PERMITTED, "approved_access_path": S.PERMITTED,
              "payment_required": S.PROHIBITED, "institutional_affiliation_required": S.PROHIBITED,
              "agreement_required": S.PROHIBITED}
    values.update(changes)
    return values


def test_valid_official_response_can_authorize_only_exact_manual_gate():
    assert validate_envelope(_envelope()) == []
    assert assess_classifications(_answers())["acquisition_authorized"] is True


def test_unofficial_and_incomplete_responses_fail_provenance():
    assert "unofficial_or_missing_sender_domain" in validate_envelope(_envelope(sender_domain="example.com"))
    failures = validate_envelope(_envelope(complete_headers=False, exact_body_available=False))
    assert "complete_headers_missing" in failures and "exact_complete_body_missing" in failures


def test_manual_permission_without_retention_or_derived_use_blocks():
    assert not assess_classifications(_answers(immutable_local_retention=S.PROHIBITED))["acquisition_authorized"]
    assert not assess_classifications(_answers(derived_noncommercial_research=S.PROHIBITED))["acquisition_authorized"]


def test_paid_and_agreement_paths_are_distinct():
    assert assess_classifications(_answers(payment_required=S.PAID_ONLY))["decision"] == "PAID_ONLY_ROUTE_INCOMPATIBLE_WITH_PROJECT"
    assert assess_classifications(_answers(agreement_required=S.REQUIRES_AGREEMENT))["decision"] == "APPLICATION_OR_AGREEMENT_REQUIRED"


def test_ambiguous_or_unanswered_fields_generate_follow_up_and_block():
    answers = _answers(manual_download=S.AMBIGUOUS, approved_access_path=S.NOT_ANSWERED)
    assert unresolved_follow_up(answers) == ["approved_access_path", "manual_download"]
    assert assess_classifications(answers)["acquisition_authorized"] is False


def test_referenced_missing_attachments_invalidate_response():
    failures = validate_envelope(_envelope(referenced_attachments=("terms.pdf",), supplied_attachments=()))
    assert failures == ["referenced_attachments_missing:terms.pdf"]
