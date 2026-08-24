# Vertical Slice A.5 — Completion Report

## Executive decision

The audited dataset is **NOT TRUSTED** for cross-sectional equity-edge research. The project is not ready for Slice B, and `momentum_12_1_v1` must not be rerun for genuine edge approval on this snapshot.

## What Slice A proved

Slice A proved mechanical reproducibility: deterministic temporal contracts, historical calculations within a supplied panel, exact golden-fixture compatibility, immutable experiment specifications and artifacts, walk-forward mechanics, explicit execution/cost assumptions, and non-actionable lifecycle gating.

It did not prove that the supplied security population represented the historical market.

## What Slice A.5 proved

- The “430-symbol dataset” is a 430-file mixed directory: 294 current-map equities, 131 indices/benchmarks, and 5 other/unresolved series.
- All 294 current-map equities continue through the dataset end. No historical annual cohort contains a disappearing equity.
- A local independent index-event archive contains 1,699 historical symbols absent from the equity directory.
- The directory lacks exchange turnover, verified corporate actions, terminal outcomes, stable identity mappings and publication/retrieval lineage.
- A causal liquidity rule cannot repair a survivor-selected input population.

## Implementation delivered

- Categorical, versioned dataset trust contract and automatic experiment promotion gate.
- Minimal security master with issuer/instrument/listing/ISIN, alias intervals, status and predecessor/successor fields.
- Explicit terminal-state taxonomy; unknown terminal outcomes remain unresolved.
- Full 430-file audit inventory, annual coverage, gaps, invalid values, discontinuity candidates and independent-reference comparison.
- Explicit NIFTY 50 price-index metadata and benchmark audit.
- Date-effective cost schedule support while preserving the Slice A compatibility version.
- Moving decision-date block bootstrap for dependence-aware uncertainty.
- Fixed-seed distributions for benchmark, eligible-universe, matched random and neutral-rank placebo baselines.
- Targeted historical-universe, trust-gate, terminal-state, cost-schedule, inference and baseline tests.
- Concrete historical data acquisition requirements without acquiring data.

## Trust-gate state

| Capability | State |
|---|---|
| Price history complete | FAIL |
| Survivorship safe | FAIL |
| Historical universe reconstructible | FAIL |
| Corporate actions verified | UNKNOWN |
| Delisting outcomes available | FAIL |
| Exchange turnover available | FAIL |
| Publication timing known | UNKNOWN |
| Stable security identity verified | FAIL |

## Preservation and verification

- `momentum_12_1_v1` parameters were not changed.
- No conditional momentum analysis or parameter search was performed.
- The existing golden compatibility fixture passes exactly.
- The new suite has 16 passing tests.
- Previous Slice A manifests were not edited or deleted.
- Root Git metadata remains absent, so new manifests correctly report `NO_GIT_METADATA` while recording source-tree and dirty-state fingerprints.

## Rerun and readiness decision

This is state **C — dataset remains unsuitable**. Momentum was not rerun for edge approval. There is no defensible availability-derived interval that restores omitted delisted/merged names and terminal outcomes.

Slice B must wait until the mandatory inputs in `HISTORICAL_DATA_REQUIREMENTS.md` are acquired with suitable rights, ingested point-in-time, reconciled, and pass the dataset capability contract.

No score, production recommendation, portfolio optimizer, or AI decision component was built.
