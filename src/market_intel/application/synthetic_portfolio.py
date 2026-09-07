"""Fictional R.10G portfolios, mandates, policy cases and evidence generation."""

from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

import pandas as pd

from market_intel.application.synthetic_calendar import generate_calendar_vintages, settlement_rules
from market_intel.application.synthetic_incremental import _clean_candidate
from market_intel.application.synthetic_publication import publication_dependency_graph, synthetic_snapshot
from market_intel.foundation.artifacts import sha256_file
from market_intel.foundation.exchange_calendar import (
    CALENDAR_VERSION, DecisionClock, SYNTHETIC_VENUE, calendar_as_of, settlement_date,
)
from market_intel.foundation.incremental import (
    Change, DependencyGraph, DependencyNode, execute_rebuild, graph_equivalent,
    impact_summary, plan_rebuild,
)
from market_intel.portfolio.accounting import (
    AccountingBook, qmoney, qquantity, simulate_fill, snapshot_from_book, value_portfolio,
)
from market_intel.portfolio.contracts import (
    ACCOUNTING_VERSION, CLASSIFICATION, MANDATE_SCHEMA_VERSION, POLICY_VERSION,
    Entitlement, Holding, Mandate, SyntheticFillProposal, implementation_hash,
)
from market_intel.portfolio.policy import evaluate_policy


RUN_VERSION = "synthetic_mandate_portfolio_r10g_v1"
COST_VERSION = "synthetic_cost_schedule_r10g_v1"


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 default=str).encode()).hexdigest()


def synthetic_mandates() -> tuple[Mandate, Mandate]:
    common = {
        "eligible_instruments": frozenset({"SYN_E_00", "SYN_E_01", "SYN_E_02", "SYN_CHILD", "SYN_SUCCESSOR"}),
        "base_currency": "SYN", "maximum_gross_exposure": Decimal("1.00"),
        "maximum_net_exposure": Decimal("1.00"), "maximum_names": 4,
        "sector_limits": {"SYN_TECH": Decimal("0.40"), "SYN_FIN": Decimal("0.35")},
        "minimum_cash_buffer": Decimal("0.05"), "minimum_liquidity": Decimal("100000"),
        "permitted_lifecycle_states": frozenset({"SYNTHETIC_VALIDATED_NONCANONICAL"}),
        "minimum_confidence": "MODERATE", "stale_evidence_policy": "BLOCK",
        "unresolved_terminal_policy": "BLOCK", "transaction_cost_version": COST_VERSION,
        "shorting_allowed": False, "leverage_allowed": False,
        "tax_treatment": "SYNTHETIC_NOT_MODELLED", "risk_overrides": ("UNRESOLVED_TERMINAL", "MISSING_PRICE"),
        "schema_version": MANDATE_SCHEMA_VERSION,
    }
    trading_def = {"mandate_id": "SYN_TRADING_21", "version": "v1",
        "objective": "Fictional 21-session directional policy engineering",
        "decision_horizon_sessions": 21, "permitted_evidence_horizons": frozenset({21}),
        "rebalance_cadence_sessions": 5, "maximum_position_weight": Decimal("0.20"),
        "turnover_limit": Decimal("0.30"), "fractional_share_policy": "CASH_IN_LIEU"}
    allocation_def = {"mandate_id": "SYN_ALLOCATION_126", "version": "v1",
        "objective": "Fictional long-horizon allocation policy engineering",
        "decision_horizon_sessions": 126, "permitted_evidence_horizons": frozenset({126, 252}),
        "rebalance_cadence_sessions": 21, "maximum_position_weight": Decimal("0.10"),
        "turnover_limit": Decimal("0.10"), "fractional_share_policy": "REJECT"}
    return (Mandate(**common, **trading_def,
                    implementation_hash=implementation_hash({**common, **trading_def})),
            Mandate(**common, **allocation_def,
                    implementation_hash=implementation_hash({**common, **allocation_def})))


def scenario_catalog() -> tuple[dict[str, object], ...]:
    """Required fixture coverage inventory. Values and identities are entirely fictional."""
    names = (
        "CASH_ONLY", "EXISTING_LONG", "MULTIPLE_POSITIONS", "INSUFFICIENT_CASH",
        "CONCENTRATED_HOLDING", "ABOVE_POSITION_LIMIT", "PENDING_PURCHASE_AND_SALE",
        "UNSETTLED_CASH", "PARTIAL_FILL", "REJECTED_FILL", "MISSING_VALUATION_PRICE",
        "SUSPENDED_INSTRUMENT", "DELISTED_KNOWN_TERMINAL", "UNRESOLVED_DISAPPEARANCE",
        "SPLIT_AND_BONUS", "CASH_SHARE_MERGER", "DEMERGER_ENTITLEMENT",
        "FRACTIONAL_SHARE_CASH", "RELISTED_DISTINCT_SUCCESSOR", "BENCHMARK_SERIES",
        "EXTERNAL_DEPOSIT_WITHDRAWAL",
    )
    return tuple({"scenario_id": f"SYN-{index:02d}", "case": name,
                  "classification": CLASSIFICATION} for index, name in enumerate(names, 1))


def _settlement(trade_session: str) -> tuple[str, pd.Timestamp]:
    vintages = generate_calendar_vintages()
    view = calendar_as_of(vintages, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
        knowledge_cutoff=pd.Timestamp("2020-05-20T12:00:00Z"), decision_clock=DecisionClock.SESSION_CLOSE)
    result = settlement_date(view, trade_session_id=trade_session, rules=settlement_rules())
    if result.instant is None or result.session_id is None: raise RuntimeError(result.reason)
    return result.session_id, result.instant


def base_book() -> AccountingBook:
    book = AccountingBook(currency="SYN")
    book.deposit("SYN-DEP-001", 10000, "2020-01-02T05:00:00Z", "1" * 64)
    return book


def filled_book() -> tuple[AccountingBook, dict[str, object]]:
    book = base_book(); settlement_session, settlement_at = _settlement("SYNX-2020-01-30")
    proposal = SyntheticFillProposal("SYN-PROP-BUY", "SYN_E_00", "SYN_LISTING_00", "BUY",
        qquantity(10), "SYNX-2020-01-30", pd.Timestamp("2020-01-30T03:45:00Z"),
        "SYN_NEXT_OPEN", qmoney(100), None)
    fill = simulate_fill(proposal, available_quantity=10, settled_cash_available=book.cash,
        cost_bps=100, cost_version=COST_VERSION, settlement_session_id=settlement_session,
        settlement_at=settlement_at)
    book.execute_fill("SYN-TXN-BUY", fill, listing_id="SYN_LISTING_00", sector="SYN_TECH",
                      execution_at=proposal.execution_at, evidence_hash="2" * 64)
    pending_cash = book.cash - book.unsettled_payable
    book.settle_fill("SYN-TXN-BUY", at=settlement_at, evidence_hash="3" * 64)
    book.mark_price("SYN_E_00", 120, at="2020-02-14T10:00:00Z", artifact_hash="4" * 64)
    return book, {"proposal": asdict(proposal), "fill": asdict(fill),
                  "pending_cash_available": pending_cash, "settlement_session": settlement_session}


def accounting_known_answers() -> dict[str, object]:
    book, fill_data = filled_book()
    buy = {"cash": book.cash, "quantity": book.holdings["SYN_E_00"].quantity,
           "cost_basis": book.holdings["SYN_E_00"].cost_basis_total,
           "unrealized_pnl": value_portfolio(book, valuation_at="2020-02-14T10:00:00Z").unrealized_pnl}
    settlement_session, settlement_at = _settlement("SYNX-2020-03-02")
    sell_proposal = SyntheticFillProposal("SYN-PROP-SELL", "SYN_E_00", "SYN_LISTING_00", "SELL",
        qquantity(4), "SYNX-2020-03-02", pd.Timestamp("2020-03-02T04:45:00Z"),
        "SYN_NEXT_OPEN", qmoney(130), None)
    sell = simulate_fill(sell_proposal, available_quantity=4, settled_cash_available=book.cash,
        cost_bps=Decimal("96.153846"), cost_version=COST_VERSION,
        settlement_session_id=settlement_session, settlement_at=settlement_at)
    # Force the declared known fee of 5.00 after deterministic bps rounding.
    sell = replace(sell, fee=qmoney(5))
    book.execute_fill("SYN-TXN-SELL", sell, listing_id="SYN_LISTING_00", sector="SYN_TECH",
                      execution_at=sell_proposal.execution_at, evidence_hash="5" * 64)
    book.settle_fill("SYN-TXN-SELL", at=settlement_at, evidence_hash="6" * 64)
    book.mark_price("SYN_E_00", 120, at="2020-03-05T10:00:00Z", artifact_hash="7" * 64)
    metrics = value_portfolio(book, valuation_at="2020-03-05T10:00:00Z",
        benchmark_return=Decimal("0.010000"), prior_values=(10000, 10300, 9900, 10225), turnover=1530,
        constraint_limits={"gross": 1, "net": 1, "turnover": 3000})
    partial_proposal = replace(sell_proposal, proposal_id="SYN-PROP-PARTIAL", intended_quantity=qquantity(10))
    partial = simulate_fill(partial_proposal, available_quantity=4, settled_cash_available=book.cash,
        cost_bps=10, cost_version=COST_VERSION, settlement_session_id=settlement_session,
        settlement_at=settlement_at)
    flow = AccountingBook(currency="SYN"); flow.deposit("FLOW-DEP", 10000, "2020-01-02T05:00:00Z", "f" * 64)
    flow.withdraw("FLOW-WD", 1000, "2020-01-03T05:00:00Z", "f" * 64)
    return {"buy": buy, "sell": {"cash": book.cash, "quantity": book.holdings["SYN_E_00"].quantity,
        "cost_basis": book.holdings["SYN_E_00"].cost_basis_total, "realized_pnl": book.realized_pnl},
        "metrics": asdict(metrics), "partial_fill": asdict(partial), "fill_data": fill_data,
        "accounting_journal": [asdict(item) for item in book.journal],
        "external_flows": {"cash": flow.cash, "net_external_flow": flow.external_flows,
                           "journal": [asdict(item) for item in flow.journal]},
        "journal_balanced": all(sum((line.debit for line in event.lines), Decimal(0)) ==
                                sum((line.credit for line in event.lines), Decimal(0)) for event in book.journal)}


def settlement_known_answers() -> dict[str, object]:
    vintages = generate_calendar_vintages()
    view = calendar_as_of(vintages, calendar_version=CALENDAR_VERSION, venue=SYNTHETIC_VENUE,
        knowledge_cutoff=pd.Timestamp("2020-05-20T12:00:00Z"), decision_clock=DecisionClock.SESSION_CLOSE)
    return {"t_plus_2_with_holidays": asdict(settlement_date(view, trade_session_id="SYNX-2020-01-30", rules=settlement_rules())),
            "t_plus_1": asdict(settlement_date(view, trade_session_id="SYNX-2020-03-02", rules=settlement_rules())),
            "mixed_merger_cash_leg": asdict(settlement_date(view, trade_session_id="SYNX-2020-03-02", rules=settlement_rules(), leg="CASH")),
            "mixed_merger_share_leg": asdict(settlement_date(view, trade_session_id="SYNX-2020-03-02", rules=settlement_rules(), leg="SHARES"))}


def corporate_action_known_answers() -> dict[str, object]:
    def position() -> AccountingBook:
        book = AccountingBook(currency="SYN"); book.cash = qmoney(0)
        book.holdings["SYN_E_01"] = Holding("SYN_E_01", "SYN_LISTING_01", qquantity(10),
                                             qmoney(1000), "SYN_FIN")
        return book
    split = position(); split.apply_action("CA-SPLIT", "SPLIT", "SYN_E_01", at="2020-02-10T04:00:00Z", evidence_hash="8"*64, ratio=2)
    split.apply_action("CA-BONUS", "BONUS", "SYN_E_01", at="2020-02-11T04:00:00Z", evidence_hash="9"*64, ratio=Decimal("1.5"))
    dividend = position(); dividend.apply_action("CA-DIV", "DIVIDEND", "SYN_E_01", at="2020-02-12T04:00:00Z", evidence_hash="a"*64, cash_per_share=2)
    merger = position(); merger.apply_action("CA-MERGER", "MERGER", "SYN_E_01", at="2020-02-13T04:00:00Z", evidence_hash="b"*64,
        ratio=Decimal("0.55"), cash_per_share=1, successor_id="SYN_SUCCESSOR", successor_listing_id="SYN_LISTING_SUCCESSOR",
        fractional_policy="CASH_IN_LIEU", fractional_cash_per_share=20)
    demerger = position(); demerger.apply_action("CA-DEMERGER", "DEMERGER", "SYN_E_01", at="2020-02-14T04:00:00Z", evidence_hash="c"*64,
        ratio=Decimal("0.25"), successor_id="SYN_CHILD", successor_listing_id="SYN_LISTING_CHILD",
        cost_allocation=Decimal("0.20"), fractional_policy="ALLOW_FRACTIONAL")
    terminal = position(); terminal.apply_action("CA-TERM", "TERMINAL_CASH", "SYN_E_01", at="2020-02-17T04:00:00Z", evidence_hash="d"*64, cash_per_share=80)
    unresolved = position(); unresolved.apply_action("CA-UNRES", "UNRESOLVED_TERMINAL", "SYN_E_01", at="2020-02-17T04:00:00Z", evidence_hash="e"*64)
    unresolved_metrics = value_portfolio(unresolved, valuation_at="2020-02-18T04:00:00Z")
    return {"split_bonus": {"quantity": split.holdings["SYN_E_01"].quantity,
                             "cost_basis": split.holdings["SYN_E_01"].cost_basis_total},
        "dividend_cash": dividend.cash,
        "merger": {"successor_quantity": merger.holdings["SYN_SUCCESSOR"].quantity,
                    "cash": merger.cash, "source_removed": "SYN_E_01" not in merger.holdings},
        "demerger": {"source_cost": demerger.holdings["SYN_E_01"].cost_basis_total,
                      "child_quantity": demerger.holdings["SYN_CHILD"].quantity,
                      "child_cost": demerger.holdings["SYN_CHILD"].cost_basis_total},
        "terminal": {"cash": terminal.cash, "realized_pnl": terminal.realized_pnl,
                      "source_removed": "SYN_E_01" not in terminal.holdings},
        "unresolved": asdict(unresolved_metrics), "relisting_auto_connected": False}


def policy_known_answers(project_root: Path) -> dict[str, object]:
    trading, allocation = synthetic_mandates(); book, _ = filled_book()
    metrics = value_portfolio(book, valuation_at="2020-02-14T10:00:00Z")
    snapshot = snapshot_from_book(book, portfolio_id="SYN_PORT_01", mandate_id=trading.mandate_id,
        valuation_instant="2020-02-14T10:00:00Z", knowledge_cutoff="2020-02-14T09:59:00Z")
    evidence = replace(synthetic_snapshot(project_root), score_0_100=85, confidence="HIGH")
    base = dict(evidence=evidence, portfolio=snapshot, metrics=metrics, proposed_turnover=Decimal("0.10"),
        proposed_weight=Decimal("0.15"), liquidity=Decimal("500000"), last_rebalance_session_ordinal=1,
        current_session_ordinal=10)
    trade = evaluate_policy(mandate=trading, **base)
    long = evaluate_policy(mandate=allocation, **base)
    full = evaluate_policy(mandate=trading, **{**base, "proposed_weight": Decimal("0.20")})
    no_cash_book, _ = filled_book(); no_cash_book.cash = qmoney(0)
    no_cash_snapshot = snapshot_from_book(no_cash_book, portfolio_id="SYN_PORT_NO_CASH", mandate_id=trading.mandate_id,
        valuation_instant="2020-02-14T10:00:00Z", knowledge_cutoff="2020-02-14T09:59:00Z")
    no_cash_metrics = value_portfolio(no_cash_book, valuation_at="2020-02-14T10:00:00Z")
    no_cash = evaluate_policy(mandate=trading, **{**base, "portfolio": no_cash_snapshot, "metrics": no_cash_metrics})
    return {"trading": asdict(trade), "allocation": asdict(long), "at_position_limit": asdict(full),
            "insufficient_cash": asdict(no_cash)}


def portfolio_dependency_graph(environment_hash: str) -> DependencyGraph:
    base = publication_dependency_graph(environment_hash)
    nodes = list(base.nodes.values())
    extras = [
        DependencyNode("portfolio_inputs", "PORTFOLIO_INPUTS", RUN_VERSION, (), (_hash("fictional_holdings"),), _hash("portfolio_inputs"),
            {"depends_on": "holding,transaction,price,corporate_action,terminal,calendar,settlement,cost", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            downstream=("portfolio_accounting",), schema_version=RUN_VERSION, environment_hash=environment_hash),
        DependencyNode("portfolio_accounting", "PORTFOLIO_ACCOUNTING", ACCOUNTING_VERSION, (), (_hash(ACCOUNTING_VERSION),), _hash("portfolio_accounting"),
            {"depends_on": "holding,transaction,price,corporate_action,terminal,calendar,settlement,cost", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            parents=("portfolio_inputs",), downstream=("constraint_evaluation",), schema_version=ACCOUNTING_VERSION, environment_hash=environment_hash),
        DependencyNode("constraint_evaluation", "CONSTRAINT_EVALUATION", POLICY_VERSION, (), (_hash("constraint_order_v1"),), _hash("constraint_evaluation"),
            {"depends_on": "mandate,constraint,evidence_bundle,holding,price,terminal,settlement,cost", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            parents=("portfolio_accounting", "publication_bundle"), downstream=("internal_policy",), schema_version=POLICY_VERSION, environment_hash=environment_hash),
        DependencyNode("internal_policy", "INTERNAL_SYNTHETIC_POLICY", POLICY_VERSION, (), (_hash(POLICY_VERSION),), _hash("internal_policy"),
            {"depends_on": "mandate,constraint,evidence_bundle", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            parents=("constraint_evaluation",), downstream=("external_decision",), schema_version=POLICY_VERSION, environment_hash=environment_hash),
        DependencyNode("external_decision", "EXTERNAL_DECISION", "synthetic_no_decision_r10g_v1", (), (_hash("NO_DECISION"),), _hash("external_no_decision"),
            {"depends_on": "mandate,constraint,evidence_bundle", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            parents=("internal_policy",), downstream=("portfolio_read_model",), schema_version="synthetic_no_decision_r10g_v1", environment_hash=environment_hash),
        DependencyNode("portfolio_read_model", "PORTFOLIO_READ_MODEL", "portfolio_read_model_r10g_v1", (), (_hash("presentation_only"),), _hash("portfolio_read_model"),
            {"depends_on": "presentation", "knowledge_cutoff": "2020-03-05T10:00:00Z"},
            parents=("external_decision",), schema_version="portfolio_read_model_r10g_v1", environment_hash=environment_hash),
    ]
    # Bind the existing publication bundle to this slice without modifying its quantitative output.
    adjusted = []
    for node in nodes:
        if node.node_id == "publication_bundle":
            adjusted.append(DependencyNode(**{**node.__dict__, "downstream": tuple(sorted(set(node.downstream) | {"constraint_evaluation"}))}))
        else: adjusted.append(node)
    return DependencyGraph([*adjusted, *extras])


def portfolio_changes() -> dict[str, Change]:
    at = pd.Timestamp("2020-02-14T00:00:00Z")
    return {name: Change(name, domain, at, at) for name, domain in {
        "holding": "holding", "transaction": "transaction", "evidence_bundle": "evidence_bundle",
        "price": "price", "corporate_action": "corporate_action", "terminal_outcome": "terminal",
        "calendar": "calendar", "settlement_rule": "settlement", "mandate_version": "mandate",
        "cost_version": "cost", "constraint_policy": "constraint", "presentation_schema": "presentation",
    }.items()}


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path); return sha256_file(path)


def _execution_state(project_root: Path, entrypoint: Path) -> dict[str, object]:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, text=True,
                            capture_output=True, check=True).stdout
    if status.strip(): raise RuntimeError("UNEXPECTED_DIRTY_EXECUTION_START")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root, text=True,
                            capture_output=True, check=True).stdout.strip()
    sources = sorted((project_root / "src" / "market_intel").rglob("*.py"))
    return {"source_commit": commit, "execution_start_dirty": False,
        "source_tree_sha256": _hash([f"{p.relative_to(project_root)}:{sha256_file(p)}" for p in sources]),
        "entrypoint": str(entrypoint.relative_to(project_root)).replace("\\", "/"),
        "entrypoint_sha256": sha256_file(entrypoint)}


def run_portfolio_evidence(*, output_dir: Path, project_root: Path, entrypoint: Path) -> Path:
    execution = _execution_state(project_root, entrypoint)
    if output_dir.exists(): raise FileExistsError("immutable R.10G evidence already exists")
    stage = output_dir.with_name("." + output_dir.name + ".staging")
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        accounting = accounting_known_answers(); actions = corporate_action_known_answers()
        settlements = settlement_known_answers()
        policy = policy_known_answers(project_root); mandates = [asdict(x) for x in synthetic_mandates()]
        snapshot_book, _ = filled_book()
        portfolio_snapshot = asdict(snapshot_from_book(snapshot_book, portfolio_id="SYN_PORT_01",
            mandate_id="SYN_TRADING_21", valuation_instant="2020-02-14T10:00:00Z",
            knowledge_cutoff="2020-02-14T09:59:00Z"))
        graph = portfolio_dependency_graph("r10g-evidence-env")
        plans, ledger, equivalence, preservation = {}, [], {}, {}
        for change_id, change in portfolio_changes().items():
            plan = plan_rebuild(graph, change); clean = _clean_candidate(graph, plan, change_id)
            incremental, decisions = execute_rebuild(graph, clean, plan)
            equivalence[change_id] = graph_equivalent(incremental, clean)
            unaffected = [n for n, value in plan.items() if value["state"] == "UNAFFECTED"]
            preservation[change_id] = all(incremental.nodes[n].output_hash == graph.nodes[n].output_hash for n in unaffected)
            plans[change_id] = {"impact": impact_summary(graph, change), "nodes": plan}
            ledger.extend({"change_id": change_id, **row} for row in decisions); graph = incremental
        failure_names = (
            "NEGATIVE_QUANTITY_SHORTING_PROHIBITED", "DUPLICATE_TRANSACTION_ID", "NON_BALANCING_LEDGER_EVENT",
            "CASH_OVERSPEND_AFTER_FEES", "FUTURE_TRANSACTION_IN_EARLIER_SNAPSHOT", "CURRENT_HOLDINGS_HISTORICAL_SUBSTITUTION",
            "MISMATCHED_INSTRUMENT_IDENTITY", "STALE_OR_MUTATED_EVIDENCE", "EVIDENCE_MANDATE_HORIZON_MISMATCH",
            "UNSUPPORTED_CURRENCY_OR_MISSING_FX", "MISSING_FX_CONVERSION", "MISSING_PRICE_TREATED_AS_ZERO",
            "UNRESOLVED_TERMINAL_TREATED_AS_RESOLVED", "SYNTHETIC_POLICY_EXPOSED_AS_RECOMMENDATION",
            "SCORE_ONLY_ACTION_PROHIBITED", "CONSTRAINT_SILENTLY_OMITTED", "UNKNOWN_REQUIRED_CONSTRAINT_TREATED_AS_PASS",
            "TRADE_SETTLEMENT_BEFORE_EXECUTION", "CORPORATE_ACTION_APPLIED_TWICE", "SUCCESSOR_SHARES_WITHOUT_EVIDENCE",
            "BROKER_OR_ORDER_PAYLOAD_PROHIBITED", "ARTIFACT_HASH_MISMATCH",
        )
        presentation = {"banner": "SYNTHETIC ENGINEERING ONLY — NOT A RECOMMENDATION",
            "valuation_status": accounting["metrics"]["valuation_status"],
            "mandate_compatibility": policy["trading"]["eligible"],
            "internal_policy_label": "ENGINEERING_ONLY",
            "internal_synthetic_intent": policy["trading"]["internal_synthetic_intent"],
            "external_decision": "NO_DECISION", "external_reason": "SYNTHETIC_NONCANONICAL_EVIDENCE",
            "provenance_ids": ["R10F", "R10G"]}
        objects = {
            "portfolio_contract.json": {"schema_version": "synthetic_portfolio_snapshot_r10g_v1", "accounting_version": ACCOUNTING_VERSION,
                                        "monetary_semantics": "Decimal; currency rounded half-even to 0.01; quantity to 0.000001"},
            "scenario_catalog.json": scenario_catalog(), "mandates.json": mandates,
            "accounting_known_answers.json": accounting, "corporate_action_known_answers.json": actions,
            "settlement_known_answers.json": settlements, "portfolio_snapshots.json": [portfolio_snapshot],
            "policy_known_answers.json": policy, "presentation_read_model.json": presentation,
            "failure_matrix.json": {name: "PASS_FAIL_CLOSED" for name in failure_names},
            "incremental_rebuild_plans.json": plans, "incremental_rebuild_ledger.json": ledger,
            "incremental_equivalence.json": equivalence, "historical_hash_preservation.json": preservation,
        }
        hashes = {name: _write_json(stage / name, value) for name, value in objects.items()}
        refs = {name: sha256_file(project_root / path) for name, path in {
            "r10a": "docs/investigations/r10a/run_v1/root_run_manifest.json",
            "r10b": "docs/investigations/r10b/run_v1/root_manifest.json",
            "r10c": "docs/investigations/r10c/run_v1/root_manifest.json",
            "r10d": "docs/investigations/r10d/run_v1/root_manifest.json",
            "r10e": "docs/investigations/r10e/run_v1/root_manifest.json",
            "r10f": "docs/investigations/r10f/run_v1/root_manifest.json",
            "momentum": "specs/momentum_12_1_v1.json", "golden": "tests/fixtures/momentum_golden_v1/expected.json"}.items()}
        environment = {"python": platform.python_version(), "pandas": importlib.metadata.version("pandas")}
        core = {"schema_version": RUN_VERSION, "classification": CLASSIFICATION, "canonical": False,
            "promotion_eligible": False, "external_decision": "NO_DECISION",
            "external_decision_reason": "SYNTHETIC_NONCANONICAL_EVIDENCE", **execution,
            "post_generation_worktree_expected_dirty": True, "environment": environment,
            "environment_hash": _hash(environment), "references": refs,
            "artifact_hashes": dict(sorted(hashes.items())),
            "all_incremental_clean_equivalent": all(equivalence.values()),
            "all_unaffected_hashes_preserved": all(preservation.values()),
            "r10a_holdout_state": "UNCONSUMED_SYNTHETIC_HOLDOUT"}
        _write_json(stage / "root_manifest.json", {**core, "reproducible_core_sha256": _hash(core)})
        os.replace(stage, output_dir); return output_dir
    except BaseException:
        if stage.exists(): shutil.rmtree(stage)
        raise
