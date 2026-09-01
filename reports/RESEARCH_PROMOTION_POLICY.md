# Research Promotion Policy v1

The machine-readable policy is `specs/research_promotion_policy_v1.json`.
It governs future work only. Existing runs remain exploratory legacy evidence.

## Findings from the legacy policy

- Thirty placebo seeds give coarse tail resolution. With the required plus-one
  estimator, the smallest possible empirical p-value is 1/31 = 0.0323.
- Several single-leg scripts accept when the real result beats the maximum of
  30 placebo means and portfolio Sharpe is positive. They do not require the
  bucketed t-stat to exceed a declared threshold.
- Pair scripts instead require positive mean, a placebo comparison and
  `t > 2`. Promotion gates therefore vary by script rather than experiment
  contract.
- Comparing to the maximum placebo is a conservative rank against those 30
  draws, but it is not a correction for all tried strategies, variants,
  diagnostics, sectors and split choices.
- Entry-week bucket means reduce same-week cross-sectional dependence. They do
  not remove serial dependence from 20-, 21-, 60- or 126-session overlapping
  holds, repeated securities, market-wide shocks or adaptive diagnostics.
- The Oil & Gas notes explicitly state that train and validation were screened
  together before the logged run. Stress and entry-delay diagnostics similarly
  informed follow-ups. These are exploratory families.
- There are no logged test-window rows. There is also no enforced access ledger,
  so pristine test status is not proven.

## New stage rules

Before any stage begins, the owner must review the current status PDF and the
exact proposed scope must be covered by its approved review record. The PDF
gate is a prerequisite to preregistration, not scientific evidence and not an
execution approval. Any research-relevant state change invalidates the report
binding and requires regeneration and review.

| Stage | Minimum placebo/permutation draws | Tail resolution | Promotion |
|---|---:|---:|---|
| Exploratory/development | 99 | 0.01 | none |
| Locked confirmation | 999 | 0.001 | validation confirmation only |
| One-time test | 999 | 0.001 | test confirmation only |

All empirical p-values use `(1 + exceedances) / (1 + permutations)` and can
never be zero. The placebo generator must preserve the full decision-date
cross-section, portfolio size, eligibility, execution and outcome assumptions.

## Families and multiplicity

One family includes every parameter, universe, split, sector, gate, timing and
diagnostic variant sharing an economic mechanism. Within a family, use a
preregistered max-statistic permutation over all registered variants or Holm
correction over valid p-values. Across families, publish false-discovery
exposure and use a preregistered FDR or family-wise method.

The method, alpha, primary metric and number of variants are fixed before
confirmation. A diagnostic that inspected validation makes subsequent work a
new exploratory version.

## Dependence and validation

Inference must resample whole decision-date cross-sections and use blocks at
least as long as the maximum overlapping outcome horizon. Repeated securities,
sector concentration and event clusters require reported sensitivity. Weekly
bucketing alone is insufficient for holds longer than a week.

Confirmation requires all of:

- point-in-time and dataset capability gates pass;
- multiplicity-adjusted uncertainty excludes the null in the declared
  direction;
- net economics survive the declared cost range;
- no single fold, sector, date cluster or repeated name dominates;
- effective sample size passes its preregistered threshold.

## Test, replication and production

The test window is opened once per locked family/version through a recorded
approval. Reuse creates a new exploratory version. Production eligibility
requires `TEST_CONFIRMED`, an independent `REPLICATION_CONFIRMED`, complete
population/identity/corporate-action/terminal/cost capabilities, and a
separately validated realizable portfolio implementation.

None of the current legacy rows satisfies that chain.
