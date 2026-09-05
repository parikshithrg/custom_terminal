# R.10A provider-neutral synthetic point-in-time research pipeline

## Outcome

The synthetic vertical slice now runs end to end:

```text
immutable generated source recipes
-> typed daily-bar normalization and quarantine
-> causal as-of revisions
-> stable identities and dated aliases
-> historical liquidity universes
-> momentum_12_1_v1
-> next_open_21_session_excess_v1
-> expanding OOS folds
-> economic and portfolio evidence
-> immutable noncanonical artifact graph
```

This validates research machinery only. The generated prices deliberately have
simple formulaic behavior, so statistics such as perfect rank IC are properties
of an engineering oracle—not evidence of a market edge.

## Existing components reused

The implementation reuses the existing provider protocols, raw manifest,
immutable artifact helpers, stable identities, liquidity-universe definition,
12–1 momentum feature, next-open 21-session outcome, costs, expanding folds,
prediction/economic metrics and portfolio accounting. The existing universe
implementation was refactored around its own shared single-decision function;
its rule was not replaced.

`momentum_12_1_v1`, its specification and golden fixture were not changed.

## Gaps corrected

- Added a shared `AsOfRequest` requiring a timezone-aware knowledge cutoff,
  explicit decision clock and exact dataset version.
- Added causal latest-vintage materialization using `published_at` and
  `available_at`, with stable revision ordering and supersession checks.
- Added a typed normalized daily-bar contract with source-record identity,
  revision lineage and structured serialized quality flags.
- Added explicit quarantine rather than dropping duplicates, impossible OHLC,
  non-positive prices, invalid timestamps, invalid linkage or invalid revision
  chains.
- Made raw writes atomic and added portable relative raw-payload references
  while retaining compatibility with earlier absolute manifests.
- Added provider/normalizer separation and a deterministic fictional adapter.
- Added fold input bindings and fail-closed checks for inadequate purge/embargo,
  validation-fitted transforms and out-of-fold predictions.
- Added explicit outcome accounting, holdout isolation and artifact-hash checks.

## Synthetic fixture and known answers

The recipe contains eight fictional instruments across synthetic weekday
sessions from 2012–2021. It includes a dated rename, a later disappearance with
unresolved terminal value, a late listing, insufficient history, a missing
session, two duplicate rows, one invalid price row, delayed publication, a
later correction, a corporate-action marker, a benchmark, and missing future
entry and exit observations.

Exact checks include:

- 16,835 accepted daily-bar revisions and 3 quarantined rows;
- revision 1 visible before 3 July 2017 and revision 2 afterward;
- both `GAMMA_OLD` and `GAMMA_NEW` resolve to `SYN_I003` only in their dated
  intervals;
- the 28 June 2019 liquidity selection is I008, I001, I005 and I002;
- I001's 12–1 feature on that date is 0.0835636122471537 and ranks first;
- next-open and 21-session exit dates match the declared outcome contract;
- 394 resolved, 6 missing-entry and 2 unresolved-delisting/missing-exit
  prediction observations remain in the complete outcome materialization;
- a INR 10,000/11,000 round trip costs INR 33.76818 under the synthetic cost
  oracle;
- four OOS folds use 22-session purge and embargo; 2021 remains unconsumed.

Predictions and executable trades remain separate. A missing entry suppresses
execution; an entered position with a missing exit remains explicit and blocks
normal resolution.

## Leakage and mutation challenges

Focused tests fail closed with named reasons for future revisions, future
universe rows, post-decision aliases, overlapping label windows,
validation-fitted transformations, modified raw bytes, artifact-hash mismatch,
duplicate records, input-order changes and silently dropped outcomes.

Later revisions never rewrite earlier knowledge. Every decision-time universe
is recomputed from the as-of rows available at that cutoff. No current
constituent list exists in the fixture or pipeline.

## Walk-forward and determinism

The expanding plan produced four validation folds. Purge and embargo are each
the 21-session holding horizon plus the next-open boundary. The current feature
and rank rules have no fitted parameters, which is recorded as
`NO_FITTED_PARAMETERS`; no validation observation influences a transform or
cutoff. Predictions are assigned only to their OOS fold.

Two independent runs from the same recipe and declared timestamps produced
identical output-artifact maps and reproducible-core hashes. Volatile wall-clock
timestamps are absent from deterministic identities.

## Evidence package

The package in `docs/investigations/r10a/run_v1` contains four immutable raw
recipe objects and portable manifests, normalized and quarantine Parquet,
identity/alias and terminal snapshots, corporate actions, benchmark, universe,
feature, prediction, outcome, fold, OOS, trade, bucket and portfolio artifacts,
the validation summary and root run manifest. It is about 1.2 MB.

The root manifest binds baseline commit `17f3171`, dirty-tree evidence, the
environment hash, recipe and raw hashes, every definition version, fold plan,
holdout state and every output hash. All artifacts are explicitly synthetic,
noncanonical and ineligible for promotion.

## Verification

- R.10A and focused prior momentum, temporal, universe, outcome, fold, manifest
  and R.9P preservation regressions: 50 passed, with two existing development-
  only warnings from the deprecated Slice A runner.
- JSON parsing, Parquet reads/schema assertions, raw and artifact hashes,
  privacy/secret scanning and Git whitespace checks pass.
- Root dependencies contain no APSW. R.9P evidence and the production interlock
  remain byte-identical.

## Remaining pipeline gaps

- The official NSE F&O format remains `PENDING_OFFICIAL_FORMAT_EVIDENCE`; the
  fixture uses generic fields and makes no schema-parity claim.
- The generated weekday calendar is not an official exchange calendar.
- Historical costs, corporate-action economics and terminal consideration are
  synthetic declarations, not qualified external evidence.
- The pipeline has not consumed real data, measured a market relationship or
  validated a publishable score.
- A complete regime/sector robustness layer is intentionally deferred until a
  real-data transition is separately approved.

## Next smallest synthetic task

Add provider-neutral synthetic schema-drift and multi-object incremental
ingestion tests: append a new immutable session, publish a correction, rebuild
only affected snapshots/materializations, and prove unchanged historical
artifacts retain their hashes. Do not add another approval ceremony.

`SYNTHETIC_PIT_RESEARCH_PIPELINE_VALIDATED_NONCANONICAL`
