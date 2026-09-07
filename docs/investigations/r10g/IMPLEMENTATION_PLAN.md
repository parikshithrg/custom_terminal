# R.10G implementation plan

R.10G is synthetic engineering only. It adds a minimal portfolio layer below
the application/evidence boundary and does not authorize real holdings, market
data, recommendations, optimization, broker access or trading.

## Reuse

- R.10F immutable evidence and read-only publication boundary.
- R.10E score, confidence and lifecycle fields without recalculation.
- R.10D explicit session calendar and effective settlement rules.
- R.10C causal corporate-action and terminal-state semantics.
- R.10B dependency graph, causal rebuild planner and clean-equivalence checks.

## New boundary

`market_intel.portfolio` contains immutable contracts, Decimal accounting and a
predeclared constraint/policy evaluator. Application fixtures construct only
fictional portfolios. The application read facade maps completed results and
cannot perform accounting or policy evaluation.

## Rule precedence

1. Validate identity and point-in-time compatibility.
2. Validate evidence horizon, lifecycle, freshness, confidence, quality,
   calibration and universe eligibility.
3. Evaluate every portfolio, exposure, cash, turnover, liquidity, settlement,
   valuation, terminal, cadence and provenance constraint.
4. Risk blocks override favorable synthetic evidence.
5. An internal engineering intent may be emitted for diagnostics.
6. The external output is always `NO_DECISION` with reason
   `SYNTHETIC_NONCANONICAL_EVIDENCE`.

## Evidence protocol

Implementation and direct/focused regression tests precede a clean checkpoint.
Evidence is generated from that exact clean commit into an immutable staged
directory whose root manifest is written last. Evidence and the completion
report are committed separately.
