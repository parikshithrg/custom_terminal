"""Decimal portfolio ledger and valuation for synthetic engineering fixtures."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_EVEN
from typing import Iterable, Mapping

import pandas as pd

from .contracts import (
    ACCOUNTING_VERSION, CLASSIFICATION, PORTFOLIO_SCHEMA_VERSION, AccountingError,
    CashBalance, Holding, PortfolioSnapshot, SyntheticFill, SyntheticFillProposal, aware,
)


MONEY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.000001")


def qmoney(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)


def qquantity(value: object) -> Decimal:
    return Decimal(str(value)).quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class LedgerLine:
    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


@dataclass(frozen=True)
class JournalEvent:
    event_id: str
    event_type: str
    occurred_at: pd.Timestamp
    lines: tuple[LedgerLine, ...]
    evidence_hash: str

    def __post_init__(self) -> None:
        aware(self.occurred_at, "journal_occurred_at")
        if not self.evidence_hash:
            raise AccountingError("JOURNAL_EVIDENCE_MISSING")
        debits = sum((line.debit for line in self.lines), Decimal("0"))
        credits = sum((line.credit for line in self.lines), Decimal("0"))
        if qmoney(debits) != qmoney(credits):
            raise AccountingError("NON_BALANCING_LEDGER_EVENT")


@dataclass(frozen=True)
class PortfolioMetrics:
    valuation_status: str
    settled_cash: Decimal
    unsettled_receivable: Decimal
    unsettled_payable: Decimal
    settled_market_value: Decimal
    partial_total_value: Decimal
    gross_exposure: Decimal | None
    net_exposure: Decimal | None
    position_weights: Mapping[str, Decimal | None]
    concentration: Decimal | None
    turnover: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal | None
    total_return: Decimal | None
    external_flow_adjusted_return: Decimal | None
    benchmark_relative_return: Decimal | None
    drawdown: Decimal | None
    unresolved_value_amount: Decimal | None
    unresolved_value_count: int
    constraint_utilization: Mapping[str, Decimal | None]


class AccountingBook:
    """Small reconcilable weighted-average book; every state change has a balanced event."""

    def __init__(self, *, currency: str = "SYN", opening_nav: Decimal = Decimal("0")):
        self.currency = currency
        self.cash = qmoney(0)
        self.unsettled_receivable = qmoney(0)
        self.unsettled_payable = qmoney(0)
        self.holdings: dict[str, Holding] = {}
        self.pending: dict[str, SyntheticFill] = {}
        self.journal: list[JournalEvent] = []
        self.realized_pnl = qmoney(0)
        self.external_flows = qmoney(0)
        self.opening_nav = qmoney(opening_nav)
        self._event_ids: set[str] = set()
        self._corporate_actions: set[str] = set()

    def _record(self, event: JournalEvent) -> None:
        if event.event_id in self._event_ids:
            raise AccountingError("DUPLICATE_TRANSACTION_ID")
        self._event_ids.add(event.event_id); self.journal.append(event)

    def deposit(self, event_id: str, amount: object, at: object, evidence_hash: str) -> None:
        amount = qmoney(amount)
        if amount <= 0: raise AccountingError("INVALID_EXTERNAL_CASH_FLOW")
        self._record(JournalEvent(event_id, "DEPOSIT", aware(at, "deposit_at"),
            (LedgerLine("CASH", debit=amount), LedgerLine("EXTERNAL_CAPITAL", credit=amount)), evidence_hash))
        self.cash += amount; self.external_flows += amount

    def withdraw(self, event_id: str, amount: object, at: object, evidence_hash: str) -> None:
        amount = qmoney(amount)
        if amount <= 0 or amount > self.cash: raise AccountingError("INSUFFICIENT_SETTLED_CASH")
        self._record(JournalEvent(event_id, "WITHDRAWAL", aware(at, "withdrawal_at"),
            (LedgerLine("EXTERNAL_CAPITAL", debit=amount), LedgerLine("CASH", credit=amount)), evidence_hash))
        self.cash -= amount; self.external_flows -= amount

    def execute_fill(self, transaction_id: str, fill: SyntheticFill, *, listing_id: str,
                     sector: str, execution_at: object, evidence_hash: str) -> None:
        if fill.fill_state in {"NO_FILL", "REJECTED"} or fill.filled_quantity == 0:
            self._record(JournalEvent(transaction_id, "REJECTED_FILL", aware(execution_at, "execution_at"),
                (LedgerLine("MEMO"),), evidence_hash)); return
        if fill.simulated_fill_price is None or fill.settlement_at is None:
            raise AccountingError("FILLED_TRANSACTION_MISSING_PRICE_OR_SETTLEMENT")
        gross = qmoney(fill.filled_quantity * fill.simulated_fill_price)
        fee = qmoney(fill.fee)
        if fill.side == "BUY":
            payable = gross + fee
            if self.cash - self.unsettled_payable < payable:
                raise AccountingError("CASH_OVERSPEND_AFTER_FEES")
            lines = (LedgerLine("UNSETTLED_SECURITIES", debit=payable),
                     LedgerLine("UNSETTLED_PAYABLE", credit=payable))
            self.unsettled_payable += payable
        else:
            holding = self.holdings.get(fill.instrument_id)
            reserved = sum((pending.filled_quantity for pending in self.pending.values()
                            if pending.side == "SELL" and pending.instrument_id == fill.instrument_id),
                           Decimal(0))
            if holding is None or holding.quantity - reserved < fill.filled_quantity:
                raise AccountingError("INSUFFICIENT_SETTLED_POSITION")
            receivable = gross - fee
            lines = (LedgerLine("UNSETTLED_RECEIVABLE", debit=receivable),
                     LedgerLine("SECURITIES_PENDING_DELIVERY", credit=receivable))
            self.unsettled_receivable += receivable
        self._record(JournalEvent(transaction_id, f"{fill.side}_EXECUTION", aware(execution_at, "execution_at"),
                                  lines, evidence_hash))
        self.pending[transaction_id] = fill
        # Settlement metadata is retained in the fill; listing/sector are encoded for new buys.
        if fill.side == "BUY" and fill.instrument_id not in self.holdings:
            self.holdings[fill.instrument_id] = Holding(fill.instrument_id, listing_id, qquantity(0),
                                                        qmoney(0), sector)

    def settle_fill(self, transaction_id: str, *, at: object, evidence_hash: str) -> None:
        fill = self.pending.get(transaction_id)
        if fill is None: raise AccountingError("PENDING_TRANSACTION_NOT_FOUND")
        instant = aware(at, "settlement_at")
        if instant < aware(fill.settlement_at, "fill_settlement_at"):
            raise AccountingError("TRADE_SETTLEMENT_BEFORE_DECLARED_DATE")
        gross = qmoney(fill.filled_quantity * fill.simulated_fill_price)
        fee = qmoney(fill.fee); holding = self.holdings[fill.instrument_id]
        if fill.side == "BUY":
            total = gross + fee
            self.cash -= total; self.unsettled_payable -= total
            self.holdings[fill.instrument_id] = replace(
                holding, quantity=qquantity(holding.quantity + fill.filled_quantity),
                cost_basis_total=qmoney(holding.cost_basis_total + total))
            lines = (LedgerLine("POSITION_COST", debit=total), LedgerLine("CASH", credit=total),
                     LedgerLine("UNSETTLED_PAYABLE", debit=total),
                     LedgerLine("UNSETTLED_SECURITIES", credit=total))
        else:
            ratio = fill.filled_quantity / holding.quantity
            disposed_cost = qmoney(holding.cost_basis_total * ratio)
            proceeds = gross - fee
            pnl = qmoney(proceeds - disposed_cost)
            self.cash += proceeds; self.unsettled_receivable -= proceeds; self.realized_pnl += pnl
            remaining = qquantity(holding.quantity - fill.filled_quantity)
            self.holdings[fill.instrument_id] = replace(
                holding, quantity=remaining,
                cost_basis_total=qmoney(holding.cost_basis_total - disposed_cost))
            lines = [LedgerLine("CASH", debit=proceeds), LedgerLine("POSITION_COST", credit=disposed_cost)]
            lines.append(LedgerLine("REALIZED_PNL", credit=pnl) if pnl >= 0
                         else LedgerLine("REALIZED_PNL", debit=-pnl))
            imbalance = sum((x.debit for x in lines), Decimal(0)) - sum((x.credit for x in lines), Decimal(0))
            if imbalance > 0: lines.append(LedgerLine("SALE_CLEARING", credit=imbalance))
            elif imbalance < 0: lines.append(LedgerLine("SALE_CLEARING", debit=-imbalance))
            lines.extend((LedgerLine("SECURITIES_PENDING_DELIVERY", debit=proceeds),
                          LedgerLine("UNSETTLED_RECEIVABLE", credit=proceeds)))
            lines = tuple(lines)
        self._record(JournalEvent(f"{transaction_id}:SETTLE", f"{fill.side}_SETTLEMENT", instant,
                                  tuple(lines), evidence_hash))
        del self.pending[transaction_id]

    def apply_action(self, action_id: str, action_type: str, instrument_id: str, *, at: object,
                     evidence_hash: str, ratio: object | None = None, cash_per_share: object | None = None,
                     successor_id: str | None = None, successor_listing_id: str | None = None,
                     cost_allocation: object | None = None, fractional_policy: str = "CASH_IN_LIEU",
                     fractional_cash_per_share: object = 0) -> None:
        if action_id in self._corporate_actions: raise AccountingError("CORPORATE_ACTION_APPLIED_TWICE")
        holding = self.holdings.get(instrument_id)
        if holding is None: raise AccountingError("CORPORATE_ACTION_SOURCE_POSITION_MISSING")
        instant = aware(at, "corporate_action_at"); cash = qmoney(0); memo = qmoney(holding.cost_basis_total)
        if action_type in {"SPLIT", "BONUS"}:
            if ratio is None or Decimal(str(ratio)) <= 0: raise AccountingError("INVALID_ACTION_RATIO")
            self.holdings[instrument_id] = replace(holding, quantity=qquantity(holding.quantity * Decimal(str(ratio))))
        elif action_type == "DIVIDEND":
            if cash_per_share is None: raise AccountingError("DIVIDEND_AMOUNT_MISSING")
            cash = qmoney(holding.quantity * Decimal(str(cash_per_share))); self.cash += cash
        elif action_type in {"MERGER", "DEMERGER"}:
            if not successor_id or not successor_listing_id or ratio is None:
                raise AccountingError("SUCCESSOR_SHARES_WITHOUT_EVIDENCE")
            exact = holding.quantity * Decimal(str(ratio))
            successor_qty = (qquantity(exact) if fractional_policy == "ALLOW_FRACTIONAL"
                             else qquantity(exact.to_integral_value(rounding=ROUND_FLOOR)))
            fractional = exact - successor_qty
            if fractional and fractional_policy == "REJECT": raise AccountingError("FRACTIONAL_SHARE_UNRESOLVED")
            fraction_cash = qmoney(fractional * Decimal(str(fractional_cash_per_share)))
            cash_component = qmoney(holding.quantity * Decimal(str(cash_per_share or 0))) + fraction_cash
            allocation = Decimal(str(cost_allocation if cost_allocation is not None else (1 if action_type == "MERGER" else 0)))
            successor_cost = qmoney(holding.cost_basis_total * allocation)
            existing = self.holdings.get(successor_id, Holding(successor_id, successor_listing_id,
                                                                 qquantity(0), qmoney(0), holding.sector))
            self.holdings[successor_id] = replace(existing,
                quantity=qquantity(existing.quantity + successor_qty),
                cost_basis_total=qmoney(existing.cost_basis_total + successor_cost))
            if action_type == "MERGER": del self.holdings[instrument_id]
            else: self.holdings[instrument_id] = replace(holding,
                    cost_basis_total=qmoney(holding.cost_basis_total - successor_cost))
            cash = cash_component; self.cash += cash
        elif action_type == "TERMINAL_CASH":
            if cash_per_share is None: raise AccountingError("UNRESOLVED_TERMINAL_TREATED_AS_RESOLVED")
            cash = qmoney(holding.quantity * Decimal(str(cash_per_share))); self.cash += cash
            self.realized_pnl += qmoney(cash - holding.cost_basis_total); del self.holdings[instrument_id]
        elif action_type == "UNRESOLVED_TERMINAL":
            self.holdings[instrument_id] = replace(holding, lifecycle="UNRESOLVED_TERMINAL",
                                                    market_price=None)
        else: raise AccountingError("UNSUPPORTED_CORPORATE_ACTION")
        # Corporate actions are non-exchange transformations; memo value balances the declared event.
        amount = cash if cash else memo
        self._record(JournalEvent(action_id, action_type, instant,
            (LedgerLine(f"ACTION:{action_type}", debit=amount), LedgerLine("ACTION_CLEARING", credit=amount)),
            evidence_hash)); self._corporate_actions.add(action_id)

    def mark_price(self, instrument_id: str, price: object | None, *, at: object,
                   artifact_hash: str, lifecycle: str | None = None) -> None:
        holding = self.holdings[instrument_id]
        if price is not None and Decimal(str(price)) <= 0: raise AccountingError("NON_POSITIVE_VALUATION_PRICE")
        self.holdings[instrument_id] = replace(holding,
            market_price=None if price is None else qmoney(price), price_instant=aware(at, "price_at"),
            price_artifact_hash=artifact_hash, lifecycle=lifecycle or holding.lifecycle)


def simulate_fill(proposal: SyntheticFillProposal, *, available_quantity: object,
                  settled_cash_available: object, cost_bps: object, cost_version: str,
                  settlement_session_id: str | None, settlement_at: object | None,
                  suspended: bool = False, position_limit_ok: bool = True) -> SyntheticFill:
    """Produce a deterministic simulation result; this is deliberately not an order API."""
    intended = proposal.intended_quantity
    if suspended:
        filled, reason = Decimal(0), "INSTRUMENT_SUSPENDED"
    elif proposal.reference_price is None:
        filled, reason = Decimal(0), "MISSING_NEXT_OPEN_PRICE"
    elif not position_limit_ok:
        filled, reason = Decimal(0), "LIMIT_VIOLATED_AFTER_COSTS"
    else:
        filled = min(intended, qquantity(available_quantity))
        reason = "FULL_FILL" if filled == intended else "PARTIAL_FILL" if filled > 0 else "NO_LIQUIDITY"
        if proposal.side == "BUY" and filled > 0:
            unit_cost = proposal.reference_price * (Decimal(1) + Decimal(str(cost_bps)) / Decimal(10000))
            affordable = qquantity((Decimal(str(settled_cash_available)) / unit_cost)
                                    .to_integral_value(rounding=ROUND_FLOOR))
            filled = min(filled, affordable)
            reason = "INSUFFICIENT_CASH" if filled == 0 else "PARTIAL_INSUFFICIENT_CASH" if filled < intended else reason
    unfilled = qquantity(intended - filled)
    price = proposal.reference_price if filled > 0 else None
    fee = qmoney(Decimal(0) if price is None else filled * price * Decimal(str(cost_bps)) / Decimal(10000))
    state = "FULL_FILL" if filled == intended else "PARTIAL_FILL" if filled > 0 else "NO_FILL"
    return SyntheticFill(proposal.proposal_id, proposal.instrument_id, proposal.side, intended,
        qquantity(filled), unfilled, price, fee, state, reason, cost_version,
        settlement_session_id if filled > 0 else None,
        None if filled == 0 or settlement_at is None else aware(settlement_at, "settlement_at"))


def snapshot_from_book(book: AccountingBook, *, portfolio_id: str, mandate_id: str,
                       valuation_instant: object, knowledge_cutoff: object,
                       pending_transactions: tuple = (), entitlements: tuple = (),
                       price_references: tuple[str, ...] = ("SYN_PRICE_REF",),
                       evidence_references: tuple[str, ...] = ("SYN_EVIDENCE_REF",),
                       provenance_hashes: tuple[str, ...] = ("0" * 64,)) -> PortfolioSnapshot:
    return PortfolioSnapshot(PORTFOLIO_SCHEMA_VERSION, portfolio_id, mandate_id, book.currency,
        aware(valuation_instant, "valuation_instant"), aware(knowledge_cutoff, "knowledge_cutoff"),
        CashBalance(book.currency, book.cash, book.unsettled_receivable, book.unsettled_payable),
        tuple(sorted(book.holdings.values(), key=lambda item: item.instrument_id)),
        tuple(pending_transactions), tuple(entitlements), price_references,
        evidence_references, provenance_hashes, CLASSIFICATION, ACCOUNTING_VERSION)


def value_portfolio(book: AccountingBook, *, valuation_at: object, benchmark_return: object | None = None,
                    prior_values: Iterable[object] = (), turnover: object = 0,
                    constraint_limits: Mapping[str, object] | None = None,
                    max_price_age: pd.Timedelta | None = None) -> PortfolioMetrics:
    instant = aware(valuation_at, "valuation_at")
    resolved_values: dict[str, Decimal] = {}; unresolved: list[str] = []
    for instrument_id, holding in book.holdings.items():
        if holding.quantity == 0: continue
        if holding.market_price is None or holding.lifecycle == "UNRESOLVED_TERMINAL":
            unresolved.append(instrument_id); continue
        if (max_price_age is not None and holding.price_instant is not None
                and instant - aware(holding.price_instant, "price_instant") > max_price_age):
            unresolved.append(instrument_id); continue
        if holding.price_instant is not None and aware(holding.price_instant, "price_instant") > instant:
            raise AccountingError("FUTURE_PRICE_IN_EARLIER_VALUATION")
        resolved_values[instrument_id] = qmoney(holding.quantity * holding.market_price)
    market = qmoney(sum(resolved_values.values(), Decimal(0)))
    partial = qmoney(book.cash + book.unsettled_receivable - book.unsettled_payable + market)
    complete = not unresolved
    total = partial if complete else None
    gross = qmoney(sum((abs(v) for v in resolved_values.values()), Decimal(0))) if complete else None
    net = market if complete else None
    weights = {key: (None if total in {None, Decimal(0)} else (value / total).quantize(Decimal("0.000001")))
               for key, value in resolved_values.items()}
    concentration = max(weights.values()) if weights and complete else None
    unrealized = (qmoney(sum((resolved_values[k] - book.holdings[k].cost_basis_total
                              for k in resolved_values), Decimal(0))) if complete else None)
    denominator = book.opening_nav + book.external_flows
    adjusted = None if not complete or denominator == 0 else ((total - denominator) / denominator).quantize(Decimal("0.000001"))
    total_return = adjusted
    relative = None if adjusted is None or benchmark_return is None else qquantity(adjusted - Decimal(str(benchmark_return)))
    history = [qmoney(x) for x in prior_values] + ([total] if total is not None else [])
    drawdown = None
    if history:
        peak = history[0]; worst = Decimal(0)
        for value in history:
            peak = max(peak, value)
            if peak != 0: worst = min(worst, (value - peak) / peak)
        drawdown = qquantity(worst)
    utilization = {}
    for name, limit in (constraint_limits or {}).items():
        observed = {"gross": gross, "net": net, "turnover": qmoney(turnover)}.get(name)
        utilization[name] = None if observed is None or Decimal(str(limit)) == 0 else qquantity(observed / Decimal(str(limit)))
    return PortfolioMetrics("COMPLETE" if complete else "INCOMPLETE_UNRESOLVED_VALUATION",
        book.cash, book.unsettled_receivable, book.unsettled_payable, market, partial,
        gross, net, weights, concentration, qmoney(turnover), book.realized_pnl, unrealized,
        total_return, adjusted, relative, drawdown, None, len(unresolved), utilization)
