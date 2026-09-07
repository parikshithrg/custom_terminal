import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/investigations/r10g/run_v1"


def _load(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_root_binds_exact_clean_checkpoint_and_noncanonical_decision():
    root = _load("root_manifest.json")
    assert root["source_commit"] == "803029792cfae66f59ec090b97586cd29f842963"
    assert root["execution_start_dirty"] is False
    assert root["classification"] == "SYNTHETIC_ONLY_NONCANONICAL"
    assert root["canonical"] is False and root["promotion_eligible"] is False
    assert (root["external_decision"], root["external_decision_reason"]) == (
        "NO_DECISION", "SYNTHETIC_NONCANONICAL_EVIDENCE")
    assert root["r10a_holdout_state"] == "UNCONSUMED_SYNTHETIC_HOLDOUT"


def test_all_declared_artifacts_exist_and_hash_exactly():
    root = _load("root_manifest.json")
    assert len(root["artifact_hashes"]) == 14
    for relative, expected in root["artifact_hashes"].items():
        path = RUN / relative
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_prior_roots_momentum_and_golden_are_bound_without_duplication():
    refs = _load("root_manifest.json")["references"]
    assert refs == {
        "golden": "d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f",
        "momentum": "1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5",
        "r10a": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
        "r10b": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
        "r10c": "bf5722abab22ca1920186a7ff2572c8095d1cb75fbd442ed00e5f8dbd0893ce6",
        "r10d": "2f9ca92b086625d10904475254f17fe2cae135d7488d99e40738a05b618fca75",
        "r10e": "a48915801d99c8eca7559079c597d9157e3b3699d5a5cf0759f6a4e01aabd7b3",
        "r10f": "7eba19c2a2cbd16bd6ff66f7435813135bcb4cb3ae287117c78187d6ac4b1955",
    }


def test_accounting_and_fill_known_answers_are_exact():
    answer = _load("accounting_known_answers.json")
    assert answer["buy"] == {"cash": "8990.00", "cost_basis": "1010.00",
                              "quantity": "10.000000", "unrealized_pnl": "190.00"}
    assert answer["sell"] == {"cash": "9505.00", "cost_basis": "606.00",
                               "quantity": "6.000000", "realized_pnl": "111.00"}
    assert answer["partial_fill"]["filled_quantity"] == "4.000000"
    assert answer["partial_fill"]["unfilled_quantity"] == "6.000000"
    assert answer["journal_balanced"] is True
    assert answer["external_flows"]["net_external_flow"] == "9000.00"


def test_valuation_and_performance_known_answers_are_exact():
    metrics = _load("accounting_known_answers.json")["metrics"]
    assert metrics["partial_total_value"] == "10225.00"
    assert metrics["position_weights"] == {"SYN_E_00": "0.070416"}
    assert metrics["external_flow_adjusted_return"] == "0.022500"
    assert metrics["benchmark_relative_return"] == "0.012500"
    assert metrics["drawdown"] == "-0.038835"


def test_corporate_action_and_terminal_answers_preserve_economics():
    answer = _load("corporate_action_known_answers.json")
    assert answer["split_bonus"] == {"cost_basis": "1000.00", "quantity": "30.000000"}
    assert answer["merger"] == {"cash": "20.00", "source_removed": True,
                                 "successor_quantity": "5.000000"}
    assert answer["demerger"] == {"child_cost": "200.00", "child_quantity": "2.500000",
                                   "source_cost": "800.00"}
    assert answer["unresolved"]["total_return"] is None
    assert answer["unresolved"]["unresolved_value_count"] == 1


def test_settlement_versions_and_mixed_legs_are_distinct():
    answer = _load("settlement_known_answers.json")
    assert answer["t_plus_2_with_holidays"]["session_id"] == "SYNX-2020-02-06"
    assert answer["t_plus_1"]["session_id"] == "SYNX-2020-03-03"
    assert answer["mixed_merger_cash_leg"]["session_id"] == "SYNX-2020-03-04"
    assert answer["mixed_merger_share_leg"]["session_id"] == "SYNX-2020-03-05"


def test_two_mandates_and_external_no_decision_are_exact():
    policies = _load("policy_known_answers.json")
    assert policies["trading"]["eligible"] is True
    assert policies["trading"]["internal_synthetic_intent"] == "INCREASE_SYNTHETIC_EXPOSURE"
    assert policies["allocation"]["eligible"] is False
    assert "HORIZON_COMPATIBILITY" in policies["allocation"]["binding_constraints"]
    for result in policies.values():
        assert result["external_decision"] == {"decision": "NO_DECISION",
                                                "reason": "SYNTHETIC_NONCANONICAL_EVIDENCE"}


def test_failure_matrix_scenarios_and_incremental_evidence_are_complete():
    assert len(_load("failure_matrix.json")) == 22
    assert set(_load("failure_matrix.json").values()) == {"PASS_FAIL_CLOSED"}
    assert len(_load("scenario_catalog.json")) == 21
    ledger = _load("incremental_rebuild_ledger.json")
    assert len(ledger) == 528
    assert sum(row["state"] == "REBUILT_INPUT_CHANGED" for row in ledger) == 78
    assert sum(row["state"] == "REUSED_HASH_IDENTICAL" for row in ledger) == 450
    assert all(_load("incremental_equivalence.json").values())
    assert all(_load("historical_hash_preservation.json").values())


def test_presentation_is_explicitly_synthetic_and_not_recommendation():
    model = _load("presentation_read_model.json")
    assert model["external_decision"] == "NO_DECISION"
    assert model["internal_policy_label"] == "ENGINEERING_ONLY"
    assert "NOT A RECOMMENDATION" in model["banner"]


def test_all_json_is_strict_and_has_no_private_or_credential_material():
    texts = []
    for path in RUN.rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        texts.append(raw)
    combined = "\n".join(texts).lower()
    assert "c:\\users\\" not in combined
    for phrase in ("api_secret=", "access_token=", "request_token=", "password=",
                   "private_fno_binding"):
        assert phrase not in combined
