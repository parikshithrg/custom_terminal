from dataclasses import asdict, replace
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from market_intel.application.evidence_read import EvidenceReadFacade
from market_intel.application.synthetic_portfolio import (
    COST_VERSION, accounting_known_answers, corporate_action_known_answers,
    filled_book, policy_known_answers, portfolio_changes, portfolio_dependency_graph,
    scenario_catalog, settlement_known_answers, synthetic_mandates,
)
from market_intel.application.synthetic_publication import synthetic_snapshot
from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.evidence.publication import PublicationError
from market_intel.foundation.incremental import execute_rebuild, graph_equivalent, plan_rebuild
from market_intel.portfolio.accounting import (
    AccountingBook, JournalEvent, LedgerLine, qmoney, qquantity, simulate_fill,
    snapshot_from_book, value_portfolio,
)
from market_intel.portfolio.contracts import (
    CLASSIFICATION, PORTFOLIO_SCHEMA_VERSION, AccountingError, CashBalance, Holding,
    PendingSyntheticTransaction, PortfolioSnapshot, SyntheticFillProposal,
)
from market_intel.portfolio.policy import CONSTRAINT_ORDER, evaluate_policy


ROOT = Path(__file__).resolve().parents[1]
AT = pd.Timestamp("2020-02-14T10:00:00Z")


def test_fixture_catalog_covers_every_required_case_and_is_fictional():
    cases = {item["case"] for item in scenario_catalog()}
    assert len(cases) == 21
    assert {"CASH_ONLY", "PARTIAL_FILL", "UNRESOLVED_DISAPPEARANCE",
            "CASH_SHARE_MERGER", "EXTERNAL_DEPOSIT_WITHDRAWAL"} <= cases
    assert all(item["classification"] == CLASSIFICATION for item in scenario_catalog())


def test_money_and_quantity_use_declared_half_even_precision():
    assert qmoney("1.005") == Decimal("1.00")
    assert qmoney("1.015") == Decimal("1.02")
    assert qquantity("1.0000005") == Decimal("1.000000")


def test_buy_known_answers_include_fee_in_weighted_average_cost():
    answer = accounting_known_answers()["buy"]
    assert answer == {"cash": Decimal("8990.00"), "quantity": Decimal("10.000000"),
                      "cost_basis": Decimal("1010.00"), "unrealized_pnl": Decimal("190.00")}


def test_sell_known_answers_realize_weighted_average_cost():
    answer = accounting_known_answers()["sell"]
    assert answer == {"cash": Decimal("9505.00"), "quantity": Decimal("6.000000"),
                      "cost_basis": Decimal("606.00"), "realized_pnl": Decimal("111.00")}


def test_portfolio_metric_known_answers():
    metrics = accounting_known_answers()["metrics"]
    assert metrics["partial_total_value"] == Decimal("10225.00")
    assert metrics["position_weights"] == {"SYN_E_00": Decimal("0.070416")}
    assert metrics["external_flow_adjusted_return"] == Decimal("0.022500")
    assert metrics["benchmark_relative_return"] == Decimal("0.012500")
    assert metrics["drawdown"] == Decimal("-0.038835")


def test_external_cash_flows_are_separate_from_investment_performance():
    flows = accounting_known_answers()["external_flows"]
    assert flows["cash"] == Decimal("9000.00")
    assert flows["net_external_flow"] == Decimal("9000.00")
    assert [item["event_type"] for item in flows["journal"]] == ["DEPOSIT", "WITHDRAWAL"]


def test_every_journal_event_balances():
    assert accounting_known_answers()["journal_balanced"] is True


def test_non_balancing_event_fails_closed():
    with pytest.raises(AccountingError, match="NON_BALANCING_LEDGER_EVENT"):
        JournalEvent("X", "BAD", AT, (LedgerLine("CASH", debit=Decimal(1)),), "a" * 64)


def test_duplicate_transaction_id_fails_closed():
    book = AccountingBook(); book.deposit("D", 10, AT, "a" * 64)
    with pytest.raises(AccountingError, match="DUPLICATE_TRANSACTION_ID"):
        book.deposit("D", 10, AT, "a" * 64)


def test_negative_quantity_fails_when_shorting_is_prohibited():
    with pytest.raises(AccountingError, match="NEGATIVE_QUANTITY_SHORTING_PROHIBITED"):
        Holding("SYN", "LIST", Decimal("-1"), Decimal(1), "SEC")


def _proposal(**changes):
    base = SyntheticFillProposal("P", "SYN_E_00", "SYN_LISTING_00", "BUY", qquantity(10),
        "SYNX-2020-03-02", pd.Timestamp("2020-03-02T04:45:00Z"), "SYN_NEXT_OPEN",
        qmoney(100), None)
    return replace(base, **changes)


def test_full_partial_and_no_fill_known_cases():
    args = dict(settled_cash_available=10000, cost_bps=10, cost_version=COST_VERSION,
                settlement_session_id="SYNX-2020-03-03", settlement_at="2020-03-03T11:30:00Z")
    full = simulate_fill(_proposal(), available_quantity=10, **args)
    partial = simulate_fill(_proposal(proposal_id="P2"), available_quantity=4, **args)
    none = simulate_fill(_proposal(proposal_id="P3"), available_quantity=0, **args)
    assert (full.fill_state, full.filled_quantity) == ("FULL_FILL", qquantity(10))
    assert (partial.fill_state, partial.filled_quantity, partial.unfilled_quantity) == (
        "PARTIAL_FILL", qquantity(4), qquantity(6))
    assert (none.fill_state, none.reason) == ("NO_FILL", "NO_LIQUIDITY")


@pytest.mark.parametrize(("changes", "kwargs", "reason"), [
    ({"proposal_id": "CASH"}, {"available_quantity": 10, "settled_cash_available": 1}, "INSUFFICIENT_CASH"),
    ({"proposal_id": "SUSP"}, {"available_quantity": 10, "settled_cash_available": 10000, "suspended": True}, "INSTRUMENT_SUSPENDED"),
    ({"proposal_id": "MISS", "reference_price": None}, {"available_quantity": 10, "settled_cash_available": 10000}, "MISSING_NEXT_OPEN_PRICE"),
    ({"proposal_id": "LIMIT"}, {"available_quantity": 10, "settled_cash_available": 10000, "position_limit_ok": False}, "LIMIT_VIOLATED_AFTER_COSTS"),
])
def test_fill_rejection_reasons_are_explicit(changes, kwargs, reason):
    result = simulate_fill(_proposal(**changes), cost_bps=10, cost_version=COST_VERSION,
        settlement_session_id="S", settlement_at="2020-03-03T11:30:00Z", **kwargs)
    assert result.fill_state == "NO_FILL" and result.reason == reason


def test_pending_buy_cannot_reuse_committed_cash_and_is_not_settled_early():
    book, data = filled_book()
    assert data["pending_cash_available"] == Decimal("8990.00")
    assert data["settlement_session"] == "SYNX-2020-02-06"  # settlement holiday is skipped
    assert not book.pending and book.unsettled_payable == 0


def test_effective_t_plus_2_t_plus_1_and_distinct_corporate_action_legs():
    answer = settlement_known_answers()
    assert answer["t_plus_2_with_holidays"]["session_id"] == "SYNX-2020-02-06"
    assert answer["t_plus_1"]["session_id"] == "SYNX-2020-03-03"
    assert answer["mixed_merger_cash_leg"]["session_id"] == "SYNX-2020-03-04"
    assert answer["mixed_merger_share_leg"]["session_id"] == "SYNX-2020-03-05"


def test_cash_overspend_after_fees_fails_closed():
    book = AccountingBook(); book.deposit("D", 100, AT, "a" * 64)
    fill = simulate_fill(_proposal(intended_quantity=qquantity(1)), available_quantity=1,
        settled_cash_available=10000, cost_bps=100, cost_version=COST_VERSION,
        settlement_session_id="S", settlement_at="2020-02-17T10:00:00Z")
    with pytest.raises(AccountingError, match="CASH_OVERSPEND_AFTER_FEES"):
        book.execute_fill("B", fill, listing_id="SYN_LISTING_00", sector="SYN_TECH",
                          execution_at=AT, evidence_hash="b" * 64)


def test_trade_settlement_must_follow_execution():
    with pytest.raises(AccountingError, match="TRADE_SETTLEMENT_BEFORE_EXECUTION"):
        PendingSyntheticTransaction("T", "I", "BUY", Decimal(1), AT, AT, Decimal(1))


def test_snapshot_rejects_naive_times_future_transactions_and_current_holdings():
    book = AccountingBook(); book.deposit("D", 100, AT, "a" * 64)
    with pytest.raises(AccountingError, match="NAIVE_TIMESTAMP"):
        snapshot_from_book(book, portfolio_id="P", mandate_id="M",
                           valuation_instant="2020-01-01", knowledge_cutoff=AT)
    future_holding = Holding("I", "L", Decimal(1), Decimal(1), "S", acquired_at=AT + pd.Timedelta(days=1))
    with pytest.raises(AccountingError, match="CURRENT_HOLDINGS_HISTORICAL_SUBSTITUTION"):
        PortfolioSnapshot(PORTFOLIO_SCHEMA_VERSION, "P", "M", "SYN", AT, AT,
            CashBalance("SYN", Decimal(1)), (future_holding,), (), (), ("P",), ("E",), ("a" * 64,))


def test_snapshot_rejects_currency_and_bad_provenance_hash():
    book = AccountingBook(currency="SYN"); book.deposit("D", 100, AT, "a" * 64)
    with pytest.raises(AccountingError, match="ARTIFACT_HASH_MISMATCH"):
        snapshot_from_book(book, portfolio_id="P", mandate_id="M", valuation_instant=AT,
                           knowledge_cutoff=AT, provenance_hashes=("bad",))
    with pytest.raises(AccountingError, match="UNSUPPORTED_CURRENCY_OR_MISSING_FX"):
        PortfolioSnapshot(PORTFOLIO_SCHEMA_VERSION, "P", "M", "USD", AT, AT,
            CashBalance("SYN", Decimal(1)), (), (), (), ("P",), ("E",), ("a" * 64,))


def test_missing_and_stale_prices_produce_incomplete_not_zero_valuation():
    book, _ = filled_book(); book.mark_price("SYN_E_00", None, at=AT, artifact_hash="a" * 64)
    missing = value_portfolio(book, valuation_at=AT)
    assert missing.valuation_status == "INCOMPLETE_UNRESOLVED_VALUATION"
    assert missing.total_return is None and missing.gross_exposure is None
    book.mark_price("SYN_E_00", 120, at=AT - pd.Timedelta(days=2), artifact_hash="b" * 64)
    stale = value_portfolio(book, valuation_at=AT, max_price_age=pd.Timedelta(days=1))
    assert stale.valuation_status == "INCOMPLETE_UNRESOLVED_VALUATION"


def test_split_bonus_dividend_merger_demerger_and_terminal_known_answers():
    answer = corporate_action_known_answers()
    assert answer["split_bonus"] == {"quantity": Decimal("30.000000"), "cost_basis": Decimal("1000.00")}
    assert answer["dividend_cash"] == Decimal("20.00")
    assert answer["merger"] == {"successor_quantity": Decimal("5.000000"), "cash": Decimal("20.00"), "source_removed": True}
    assert answer["demerger"] == {"source_cost": Decimal("800.00"), "child_quantity": Decimal("2.500000"), "child_cost": Decimal("200.00")}
    assert answer["terminal"] == {"cash": Decimal("800.00"), "realized_pnl": Decimal("-200.00"), "source_removed": True}


def test_unresolved_terminal_is_not_zero_or_last_price_and_relisting_is_distinct():
    answer = corporate_action_known_answers()
    assert answer["unresolved"]["valuation_status"] == "INCOMPLETE_UNRESOLVED_VALUATION"
    assert answer["unresolved"]["total_return"] is None
    assert answer["unresolved"]["unresolved_value_count"] == 1
    assert answer["relisting_auto_connected"] is False


def test_action_cannot_be_applied_twice_or_create_unproven_successor():
    book = AccountingBook(); book.holdings["I"] = Holding("I", "L", Decimal(10), Decimal(100), "S")
    book.apply_action("A", "SPLIT", "I", at=AT, evidence_hash="a" * 64, ratio=2)
    with pytest.raises(AccountingError, match="CORPORATE_ACTION_APPLIED_TWICE"):
        book.apply_action("A", "SPLIT", "I", at=AT, evidence_hash="a" * 64, ratio=2)
    with pytest.raises(AccountingError, match="SUCCESSOR_SHARES_WITHOUT_EVIDENCE"):
        book.apply_action("M", "MERGER", "I", at=AT, evidence_hash="a" * 64, ratio=1)


def test_two_mandates_interpret_same_evidence_differently_but_neither_publishes_action():
    answer = policy_known_answers(ROOT)
    assert answer["trading"]["internal_synthetic_intent"] == "INCREASE_SYNTHETIC_EXPOSURE"
    assert answer["trading"]["eligible"] is True
    assert answer["allocation"]["eligible"] is False
    assert "HORIZON_COMPATIBILITY" in answer["allocation"]["binding_constraints"]
    assert {item["external_decision"]["decision"] for item in answer.values()} == {"NO_DECISION"}


def test_all_constraints_are_returned_in_predeclared_order():
    result = policy_known_answers(ROOT)["trading"]
    assert tuple(item["constraint_id"] for item in result["constraints"]) == CONSTRAINT_ORDER
    assert len(result["constraints"]) == len(CONSTRAINT_ORDER)


def test_unknown_required_liquidity_blocks_instead_of_passing():
    mandate, _ = synthetic_mandates(); book, _ = filled_book()
    metrics = value_portfolio(book, valuation_at=AT)
    portfolio = snapshot_from_book(book, portfolio_id="P", mandate_id=mandate.mandate_id,
                                   valuation_instant=AT, knowledge_cutoff=AT)
    evidence = replace(synthetic_snapshot(ROOT), score_0_100=85, confidence="HIGH")
    result = evaluate_policy(evidence=evidence, portfolio=portfolio, mandate=mandate, metrics=metrics,
        proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.1"), liquidity=None,
        last_rebalance_session_ordinal=1, current_session_ordinal=10)
    lookup = {item.constraint_id: item for item in result.constraints}
    assert lookup["LIQUIDITY"].status == "UNKNOWN"
    assert "LIQUIDITY" in result.binding_constraints and result.eligible is False


@pytest.mark.parametrize(("change", "expected"), [
    ({"freshness_status": "STALE", "confidence": "HIGH"}, "FRESHNESS"),
    ({"confidence": "LOW"}, "CONFIDENCE"),
    ({"data_quality_status": "BLOCKED", "confidence": "HIGH"}, "DATA_QUALITY"),
    ({"lifecycle": "SUSPENDED", "confidence": "HIGH"}, "LIFECYCLE"),
])
def test_evidence_incompatibilities_have_named_constraint_blocks(change, expected):
    mandate, _ = synthetic_mandates(); book, _ = filled_book(); metrics = value_portfolio(book, valuation_at=AT)
    portfolio = snapshot_from_book(book, portfolio_id="P", mandate_id=mandate.mandate_id,
                                   valuation_instant=AT, knowledge_cutoff=AT)
    evidence = replace(synthetic_snapshot(ROOT), **change)
    result = evaluate_policy(evidence=evidence, portfolio=portfolio, mandate=mandate, metrics=metrics,
        proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.1"), liquidity=Decimal("500000"),
        last_rebalance_session_ordinal=1, current_session_ordinal=10)
    assert expected in result.binding_constraints and result.external_decision.decision == "NO_DECISION"


def test_risk_constraint_overrides_favorable_score():
    answer = policy_known_answers(ROOT)["insufficient_cash"]
    assert answer["internal_synthetic_intent"] == "DECREASE_SYNTHETIC_EXPOSURE"
    assert "CASH_BUFFER" in answer["binding_constraints"]


def test_same_evidence_changes_internal_result_with_current_holdings():
    mandate, _ = synthetic_mandates(); evidence = replace(synthetic_snapshot(ROOT), score_0_100=85, confidence="HIGH")
    cash_book = AccountingBook(); cash_book.deposit("D", 10000, AT, "a" * 64)
    cash_metrics = value_portfolio(cash_book, valuation_at=AT)
    cash_snapshot = snapshot_from_book(cash_book, portfolio_id="CASH", mandate_id=mandate.mandate_id,
                                       valuation_instant=AT, knowledge_cutoff=AT)
    no_position = evaluate_policy(evidence=evidence, portfolio=cash_snapshot, mandate=mandate,
        metrics=cash_metrics, proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.15"),
        liquidity=Decimal("500000"), last_rebalance_session_ordinal=1, current_session_ordinal=10)
    concentrated, _ = filled_book(); concentrated.cash = Decimal("100.00")
    concentrated.mark_price("SYN_E_00", 1000, at=AT, artifact_hash="b" * 64)
    concentrated_metrics = value_portfolio(concentrated, valuation_at=AT)
    concentrated_snapshot = snapshot_from_book(concentrated, portfolio_id="FULL", mandate_id=mandate.mandate_id,
                                                valuation_instant=AT, knowledge_cutoff=AT)
    above = evaluate_policy(evidence=evidence, portfolio=concentrated_snapshot, mandate=mandate,
        metrics=concentrated_metrics, proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.3"),
        liquidity=Decimal("500000"), last_rebalance_session_ordinal=1, current_session_ordinal=10)
    assert no_position.internal_synthetic_intent == "INCREASE_SYNTHETIC_EXPOSURE"
    assert above.internal_synthetic_intent == "DECREASE_SYNTHETIC_EXPOSURE"
    assert "POSITION_LIMIT" in above.binding_constraints
    assert no_position.external_decision.decision == above.external_decision.decision == "NO_DECISION"


def test_timing_identity_terminal_settlement_and_provenance_all_fail_named():
    mandate, _ = synthetic_mandates(); book, _ = filled_book(); metrics = value_portfolio(book, valuation_at=AT)
    portfolio = snapshot_from_book(book, portfolio_id="P", mandate_id=mandate.mandate_id,
                                   valuation_instant=AT, knowledge_cutoff=AT)
    future_evidence = replace(synthetic_snapshot(ROOT), decision_instant=AT + pd.Timedelta(minutes=1),
                              knowledge_cutoff=AT + pd.Timedelta(minutes=1), confidence="HIGH")
    result = evaluate_policy(evidence=future_evidence, portfolio=portfolio, mandate=mandate, metrics=metrics,
        proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.1"), liquidity=Decimal("500000"),
        last_rebalance_session_ordinal=1, current_session_ordinal=10,
        provenance_valid=False, terminal_resolved=False, settlement_available=False)
    assert {"TIMING", "PROVENANCE", "UNRESOLVED_TERMINAL_ECONOMICS",
            "SETTLEMENT_AVAILABILITY"} <= set(result.binding_constraints)


def test_mismatched_listing_identity_blocks_even_with_high_score():
    mandate, _ = synthetic_mandates(); book, _ = filled_book(); metrics = value_portfolio(book, valuation_at=AT)
    portfolio = snapshot_from_book(book, portfolio_id="P", mandate_id=mandate.mandate_id,
                                   valuation_instant=AT, knowledge_cutoff=AT)
    evidence = replace(synthetic_snapshot(ROOT), listing_id="WRONG_LISTING", score_0_100=99, confidence="HIGH")
    result = evaluate_policy(evidence=evidence, portfolio=portfolio, mandate=mandate, metrics=metrics,
        proposed_turnover=Decimal("0.1"), proposed_weight=Decimal("0.1"), liquidity=Decimal("500000"),
        last_rebalance_session_ordinal=1, current_session_ordinal=10)
    assert "IDENTITY" in result.binding_constraints
    assert result.internal_synthetic_intent == "POLICY_BLOCKED"


def test_read_model_maps_precomputed_result_and_cannot_expose_recommendation():
    facade = EvidenceReadFacade(object())
    raw = {"classification": CLASSIFICATION, "portfolio_id": "SYN_PORT_01", "mandate_id": "SYN_TRADING_21",
        "valuation_status": "COMPLETE", "mandate_compatible": True,
        "constraint_results": ({"constraint_id": "CASH_BUFFER", "status": "PASS"},),
        "internal_policy_label": "ENGINEERING_ONLY", "internal_synthetic_intent": "INCREASE_SYNTHETIC_EXPOSURE",
        "external_decision": "NO_DECISION", "external_reason": "SYNTHETIC_NONCANONICAL_EVIDENCE",
        "unresolved_exposures": (), "provenance_artifact_ids": ("R10F", "R10G")}
    dto = facade.present_portfolio_result(raw)
    assert dto.external_decision == "NO_DECISION" and "NOT A RECOMMENDATION" in dto.warning_banner
    with pytest.raises(TypeError): dto.constraint_results[0]["status"] = "BLOCK"
    with pytest.raises(PublicationError, match="SYNTHETIC_POLICY_EXPOSED_AS_RECOMMENDATION"):
        facade.present_portfolio_result({**raw, "external_decision": "BUY"})


def test_incremental_changes_rebuild_causally_and_match_clean_builds():
    graph = portfolio_dependency_graph("test-env")
    for name, change in portfolio_changes().items():
        plan = plan_rebuild(graph, change)
        clean = _clean_candidate(graph, plan, name)
        incremental, ledger = execute_rebuild(graph, clean, plan)
        assert graph_equivalent(incremental, clean)
        assert len(ledger) == len(graph.nodes)
        assert all(incremental.nodes[node].output_hash == graph.nodes[node].output_hash
                   for node, state in plan.items() if state["state"] == "UNAFFECTED")
        graph = incremental


def test_no_broker_payload_or_provider_imports_in_portfolio_layer():
    source = "\n".join(path.read_text(encoding="utf-8") for path in
                       (ROOT / "src/market_intel/portfolio").glob("*.py")).lower()
    for forbidden in ("kite", "place_order", "modify_order", "cancel_order", "websocket", "requests."):
        assert forbidden not in source
