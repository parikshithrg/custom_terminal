from market_intel.foundation.quality import CapabilityStatus, DatasetTrustContract, evaluate_requirements


def _contract(**overrides):
    values = dict(price_history_complete=CapabilityStatus.PASS, survivorship_safe=CapabilityStatus.PASS,
                  historical_universe_reconstructible=CapabilityStatus.PASS,
                  corporate_actions_verified=CapabilityStatus.PASS, delisting_outcomes_available=CapabilityStatus.PASS,
                  exchange_turnover_available=CapabilityStatus.PASS, publication_timing_known=CapabilityStatus.PASS,
                  stable_security_identity_verified=CapabilityStatus.PASS)
    values.update(overrides)
    return DatasetTrustContract("fixture", "v1", **values)


def test_fail_and_unknown_are_non_promotable():
    result = evaluate_requirements(_contract(survivorship_safe=CapabilityStatus.FAIL,
                                             publication_timing_known=CapabilityStatus.UNKNOWN),
                                   ["survivorship_safe", "publication_timing_known"])
    assert not result["promotable"]
    assert result["failed_or_unknown"] == {"publication_timing_known": "UNKNOWN", "survivorship_safe": "FAIL"}


def test_all_required_capabilities_must_pass():
    assert evaluate_requirements(_contract(), ["survivorship_safe"])["promotable"]
