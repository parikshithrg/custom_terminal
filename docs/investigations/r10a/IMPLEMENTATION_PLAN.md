# R.10A implementation plan and gap record

## Reused components

- Immutable raw acquisition and raw-object manifests.
- Stable instrument and alias concepts.
- The versioned liquidity universe rule.
- `momentum_12_1_v1` without economic-definition changes.
- `next_open_21_session_excess_v1` without convention changes.
- Expanding walk-forward folds, purge/embargo overlap checks, delivery-cost
  calculation, evidence metrics, portfolio accounting and immutable artifacts.

## Gaps addressed

1. Add a shared, timezone-aware as-of request requiring knowledge cutoff,
   decision clock and dataset version.
2. Add typed daily-bar revision, supersession, availability, quality and
   deterministic-order validation with an explicit quarantine.
3. Add a fictional provider and normalizer behind the existing provider
   contracts; keep research packages provider-independent.
4. Refactor the existing liquidity rule around a shared one-decision function
   so each historical decision can use its own as-of snapshot efficiently.
5. Bind fold inputs and reject validation-fitted transforms, inadequate
   purge/embargo, out-of-fold predictions and holdout consumption.
6. Publish and verify a deterministic, noncanonical artifact graph.

## Fixed execution

The generated fixture spans synthetic weekday sessions from 2012 through 2021.
The final 2021 interval is an unconsumed synthetic holdout. The executable run
ends at 2020-12-31, uses 22-session purge and embargo derived from the 21-session
outcome plus next-open entry, and performs no parameter search or market claim.

The generated evidence package is an engineering oracle. It is not canonical
market evidence, edge evidence, a score, or permission to use real data.
