# R.10E — Synthetic multi-feature evidence, calibration and score semantics

## Result

R.10E validates synthetic numerical and semantic machinery only. Every number
below comes from a deterministic fictional engineering oracle. Nothing is a
real market score, probability forecast, expected return, confidence claim,
recommendation or validated edge.

Authoritative clean source checkpoint:
`5febba77436ea577db5bc53ecd21fe0c742a134d`.

## Definitions and semantics

The shared registry requires version, meaning, dataset/schema, calendar/clock,
availability, lookback/history, scope, price basis, null/staleness policy,
direction, transform, parameter mode, implementation hash and quality gates.
A definition cannot change while retaining its version.

Materializations preserve raw value, transformed value, oriented prediction,
transformation version, fitted-through time, missing/stale state, decision
session and instant, knowledge cutoff, snapshot, calendar and source hash.

`score_0_100` is only an oriented percentile inside a declared training
calibration population. It is bounded, uses average rank for ties and clips
outside the training range. It is explicitly not probability, expected return,
confidence or recommendation. Those values have separate typed fields and
definitions.

## Components

The attempted family retains all ten component definitions: existing 12–1
momentum, short trend, negatively oriented mean reversion, volatility/risk,
liquidity, exact redundant momentum, deterministic noise, missing/stale,
corrected input and training-fitted scale. The 16-entry family ledger also
retains constant, fixed-permutation, reversed-sign, strongest-component,
equal-weight and registered-combination attempts. Negative diagnostics were not
discarded.

The registry references `momentum_12_1_v1`; its implementation, specification
and golden fixture were not modified.

## Calibration behavior

- Training-only winsorized standardization used 60 rows, lower bound -39.0 and
  fitted-through 7 February 2020.
- A tied raw value of 2 in `[1,2,2,4,5]` receives percentile score 40.0.
- Values beyond the training range receive 0.0 or 100.0 under the declared clip
  policy.
- The neighbor calibration known answer is synthetic outcome 1.8, interval
  `[1.4129310139, 2.1870689861]`, and positive-outcome probability 1.0 from five
  resolved training neighbors.
- Insufficient samples return `UNAVAILABLE`; unresolved terminal outcomes are
  counted rather than silently removed.
- Identical percentiles can map to different expected outcomes under different
  calibration populations.

No bucket boundary, direction, winsor parameter, coefficient or threshold uses
validation or holdout outcomes.

## Combination and baselines

The registered deterministic linear combination is fit on training rows only.
It drops the exact redundant momentum component and retains four independently
represented inputs. Changing validation outcomes leaves coefficients unchanged.

In the deliberately encoded oracle, combination validation MSE is approximately
`6.47e-31`, versus `14.8114` for naive equal weighting. This demonstrates the
software behavior requested; it is not market evidence. The strongest component
rank correlation is `0.9955`, sign reversal is `-0.9955`, and the fixed-seed
permutation diagnostic is `-0.1966`. Display-score averaging is prohibited.

## Multiple testing, confidence and lifecycle

Holm v1 known inputs produce thresholds 0.01667, 0.025 and 0.05; the first two
synthetic inputs reject and the null does not. These mechanics do not validate
an edge.

Confidence is categorical, not a weighted 0–100 number. The example is `LOW`
because of small effective sample, wide interval, narrow synthetic coverage and
multiple-testing burden.

The lifecycle reaches only `SYNTHETIC_VALIDATED_NONCANONICAL`. Attempts to enter
`VALIDATED_REAL_DATA` or `ACTIVE` fail even for perfect oracle evidence. The
prototype snapshot is `SYNTHETIC_ONLY_NONCANONICAL` and always `NO_DECISION`.

## Holdout and leakage challenges

R.10A's original holdout remains `UNCONSUMED_SYNTHETIC_HOLDOUT`. R.10E uses a
separate disposable known-answer holdout; only its declared test path can open
it, access is recorded, and a second use is rejected.

Named guards cover global preprocessing, validation/full-sample/holdout fitting,
future universe/calendar/event knowledge, outcome-derived direction, score
averaging, semantic mislabeling, unauthorized missing-value imputation, omitted
attempts, validation-sensitive weights, synthetic promotion, unresolved-row
drops and hash mismatch.

## Incremental behavior

Seven changes were exercised: historical feature input, feature definition,
calibration population, outcome correction, multiple-testing family, confidence
policy and calendar revision. All incremental outputs equal clean rebuilds and
all unaffected hashes remain unchanged. The ledger contains 51 causal rebuilds
and 194 verified reuses. Definition and calibration bindings prevent reuse across
mismatched semantics, while original versioned snapshots remain reproducible.

## Verification

- Direct R.10E tests: 27 passed.
- Focused R.10A–R.10E regression: 151 passed.
- Evidence package: 21 files, approximately 215 KB; 20 declared artifact hashes.
- Five Parquet and sixteen JSON files parse successfully using strict JSON.
- R.10A–R.10D roots, momentum specification and golden fixture remain unchanged.
- No real/private data, network, APSW production adoption, interlock change,
  Streamlit/version2.0 connection, genuine backtest, score publication or
  trading path was added.

## Limitations

- The oracle intentionally encodes controlled relationships and therefore says
  nothing about economic plausibility or market behavior.
- Simple neighbor calibration and least-squares combination are deliberately
  minimal; their real-data suitability is untested.
- Effective sample size equals row count in this bounded fixture; real dependent
  observations require the existing dependence-aware inference machinery.
- Cost, regime and breadth fields are contract demonstrations, not empirical
  measurements.

## Next task

Proceed to `SYNTHETIC_EVIDENCE_PUBLICATION_AND_READ_MODEL`: immutable publication,
`NO_DECISION` gating, freshness and a thin read-only boundary without presenting
synthetic outputs as live recommendations.

Before any real/private-data transition, genuine analysis/backtesting, score
publication, APSW adoption or interlock change, stop for the consolidated PDF
and explicit owner authorization.

`SYNTHETIC_MULTI_FEATURE_SCORE_SEMANTICS_VALIDATED_NONCANONICAL`
