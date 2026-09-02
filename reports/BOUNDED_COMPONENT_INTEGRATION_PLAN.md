# Bounded Component Integration Plan

## Scope and authority

This is a non-empirical architecture plan. `version2.0` remains a separate,
untrusted reference repository at reviewed `master` commit
`f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`. The remote reference was
rechecked on 2 September 2026 and had not changed. No code, data, research
result, strategy state, or broker behavior is imported by this plan.

`custom_terminal` remains authoritative for provenance, historical-data trust,
research definitions, preregistration, approvals, deterministic computation,
evidence, lifecycle and publication.

## Intended flow

```text
free or explicitly permitted source
  -> immutable source snapshot
  -> provenance and availability contract
  -> typed provider-neutral normalization
  -> governed feature computation
  -> non-actionable research evidence
  -> approved published read model
  -> version2.0-style display
```

The UI boundary is one-way. A display may consume an approved immutable read
model and show its status, provenance and limitations. It may not calculate
canonical evidence, access unapproved raw inputs, promote lifecycle state,
launch a backtest, create a recommendation, call a broker, or place a trade.

## Candidate component boundaries

| Candidate | Reference value | Required redesign | Initial state |
|---|---|---|---|
| Market sentiment | Regime, transcript, macro, ownership, insider and positioning ideas | Define each concept separately; qualify sources and causal clocks | EXPLORATORY_NONACTIONABLE |
| Stock-score presentation | Multi-category stock detail and comparison UI | Publish categories independently; no opaque aggregate or ranking | EXPLORATORY_NONACTIONABLE |
| F&O data access | Read-only SQLite query patterns | Complete provenance, safety and PIT audit before any feature use | PLAN_ONLY_NOT_EXECUTED |

## Interface contracts for later implementation

An approved read model must identify its schema version, publication time,
source evidence, knowledge cutoff, component lifecycle state, missingness,
staleness, limitations, and whether it is current-only or historically
qualified. The display must fail closed when an artifact is missing, stale,
unapproved or outside its declared scope.

No execution entry point is created in R.8. Future implementation requires a
separate owner-reviewed proposal and, for any empirical work, the existing
preregistration, immutable-input and one-use approval chain.

## Explicitly excluded

- Modifying or launching version2.0.
- Copying its data, scripts, results, validation labels or broker code.
- Computing sentiment or stock scores.
- Selecting formulas, thresholds or parameters from outcomes.
- Querying the F&O database.
- Acquiring external data.
- Showing recommendations or live scans.
- Simulating, backtesting or trading.

Planning decision: the architecture boundary is sufficiently explicit for
owner review, but it authorizes no implementation or empirical execution.
