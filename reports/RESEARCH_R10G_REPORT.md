# R.10G — Synthetic mandate, portfolio accounting and decision-policy mechanics

## Result

R.10G validates a deterministic synthetic portfolio/accounting and mandate
policy boundary. It does not validate a market edge, real holdings, real data,
optimization, a recommendation, broker integration or trading.

## Contracts added

- Immutable, versioned portfolio snapshots with portfolio/mandate identity,
  valuation instant, knowledge cutoff, settled and unsettled cash, holdings,
  pending synthetic transactions, entitlements and provenance hashes.
- Two versioned mandates: a 21-session trading-style mandate and a 126-session
  allocation-style mandate. A 21-session evidence snapshot is incompatible with
  the long-horizon mandate unless a later explicit compatibility rule permits it.
- A simulation-only fill contract with full, partial and no-fill states. It has
  no broker-compatible payload, endpoint or mutation interface.
- A fixed-order constraint policy returning every PASS, BLOCK, BINDING,
  NOT_APPLICABLE or UNKNOWN result.
- A presentation-safe portfolio DTO that maps completed results without
  recalculating accounting or policy values.

## Accounting and precision

Monetary truth uses Python `Decimal`, half-even rounding to 0.01 currency units,
and quantity precision of 0.000001. Cost basis is weighted average. Every
deposit, withdrawal, simulated fill, settlement and corporate-action event has
a balanced journal entry. A buy of 10 units at 100 with a 10 fee produces cash
8,990 and cost basis 1,010. Selling four at 130 with a 5 fee leaves six units,
cost basis 606 and realized P&L 111.

Unsettled payables reduce available cash immediately. Receivables are not
reusable before settlement. The fixture proves the effective T+2 and T+1 rules,
skips settlement holidays, and gives mixed-merger cash and share legs distinct
settlement dates.

## Valuation and performance

The known complete portfolio has value 10,225, weight 0.070416, realized P&L
111, unrealized P&L 114, external-flow-adjusted return 0.022500,
benchmark-relative return 0.012500 and drawdown -0.038835. Deposits and
withdrawals remain external flows rather than investment performance.

Missing/stale prices and unresolved terminal economics produce a partial value
and `INCOMPLETE_UNRESOLVED_VALUATION`. Total return, gross/net exposure and
unrealized P&L remain null when they cannot be defended; disappearance is never
valued at zero or the last price.

## Corporate actions

- Split and bonus increase quantity from 10 to 30 without changing the 1,000
  cost basis or creating P&L.
- A declared dividend credits 20 cash at its event instant.
- The mixed merger removes the predecessor, creates five whole successor shares
  and credits 20 cash including fractional cash-in-lieu.
- The demerger preserves the parent, creates 2.5 child shares and allocates 200
  of cost basis to the child.
- Known terminal cash closes the position and realizes the declared economics.
- Unresolved terminal state remains unresolved exposure.
- A relisted successor has a distinct identity and is not automatically joined.

## Mandate and constraint behavior

The engine predeclares constraint order and evaluates identity, timing, horizon,
lifecycle, freshness, confidence, quality, calibration, universe, position,
gross/net exposure, maximum names, sector, cash buffer, turnover, liquidity,
settlement, valuation, terminal economics, rebalance cadence and provenance.
Unknown required constraints block.

The same favorable synthetic evidence produces an internal increase intent for
the compatible 21-session mandate, but the long-horizon mandate blocks it for
horizon, position and cadence reasons. Existing concentration or insufficient
cash overrides the favorable evidence. No score maps directly to an action.

## Internal policy versus external decision

Internal policy output is explicitly labelled `ENGINEERING_ONLY` and may state
a fictional increase/decrease/maintain/avoid-like intent for mechanism testing.
Every externally publishable result remains exactly:

```text
decision: NO_DECISION
reason: SYNTHETIC_NONCANONICAL_EVIDENCE
```

The read facade rejects any attempted external action and shows a prominent
synthetic/not-a-recommendation banner.

## Incremental behavior

Twelve synthetic changes cover holding, transaction, evidence bundle, price,
corporate action, terminal outcome, calendar, settlement, mandate, cost,
constraint and presentation versions. Across 528 node decisions, 78 nodes are
rebuilt and 450 are reused hash-identically. Every incremental result equals a
clean rebuild and all unaffected hashes remain unchanged.

## Verification

- Direct R.10G implementation tests: 39 passed.
- Static evidence tests: 11 passed (50 combined R.10G tests).
- Final focused R.10A–R.10G regression: 260 passed.
- Evidence package: 15 strict JSON files, 207,279 bytes and 14 manifest-bound
  artifact hashes.
- R.10A holdout remains `UNCONSUMED_SYNTHETIC_HOLDOUT`.
- R.10A–R.10F evidence roots, momentum specification and golden fixture are
  bound and unchanged.
- No Streamlit/version2.0 change, broker import or mutation path, real/private
  data, network access, APSW adoption, production interlock change, live score,
  recommendation or trade was introduced.
- The known stale owner-review fingerprint diagnostics are retained for the
  later consolidated review; historical review records were not rewritten.

## Limitations

- Accounting is a bounded weighted-average prototype, not a tax-lot, custody or
  statutory accounting system.
- Currency conversion and taxes are declared unsupported rather than inferred.
- Liquidity and prices are fictional inputs; no slippage or optimizer is built.
- The portfolio read model is not connected to a UI or production application.
- No result establishes real-data fitness or investment efficacy.

## Recommended next task

Perform one final synthetic readiness audit across R.10A–R.10G. Consolidate
architectural gaps and decide whether the project is ready for the mandatory
owner-reviewed PDF before any real-data transition.

`SYNTHETIC_MANDATE_PORTFOLIO_POLICIES_VALIDATED_NONCANONICAL`
