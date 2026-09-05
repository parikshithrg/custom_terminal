# Synthetic Research Operating Model v1

Recorded: 5 September 2026

## Purpose

The project exists to build an evidence-backed score-based decision-support
system for Indian markets. Its core path is:

```text
raw inputs
-> validation and normalization
-> point-in-time datasets
-> historical universe
-> deterministic features and outcomes
-> backtesting and walk-forward validation
-> evidence-backed scores and decision support
```

Engineering rigor must improve trust without consuming more effort than the
risk warrants. The repeated PDF and approval cycle used before R.9O was
disproportionate for disposable synthetic-data engineering.

## Standing synthetic-development authority

Until the project owner revokes or changes this policy, work may proceed without
a new PDF or owner approval for each iteration when it is limited to:

- generating disposable, unmistakably synthetic datasets;
- developing or refactoring non-production pipeline components;
- implementing schema validation, normalization and data-quality controls;
- building deterministic feature, outcome, simulation, backtesting and
  walk-forward-validation engines;
- testing leakage prevention, point-in-time behavior, purging, embargo,
  transaction costs, portfolio accounting and reproducibility;
- running bounded synthetic failure and adversarial tests;
- continuing isolated APSW candidate engineering outside production packages;
- recording routine work through automated tests and concise Markdown notes.

Synthetic fixtures should use official NSE field names, formats and identifier
rules once the applicable official specification has been obtained and bound.
Until then they must use clearly generic fields or explicitly disclose partial
provenance. Synthetic values must never be presented as market observations.

This standing authority supersedes repeated experiment-by-experiment approval
ceremonies for synthetic infrastructure work. It does not rewrite historical
records or convert old non-approval artifacts into approvals. Exact one-use
controls may still be developed and tested as product behavior without requiring
a new owner decision for every disposable synthetic run.

## What synthetic validation proves

Synthetic validation can prove that the machinery produces known expected
answers, rejects malformed data, fails closed, prevents tested forms of leakage
and emits reproducible artifacts. Synthetic backtests and forward simulations
are engineering tests.

Synthetic results cannot prove that a market edge exists, estimate real-world
profitability or establish resistance to economic overfitting. Those conclusions
require separately approved point-in-time real data, untouched holdouts,
walk-forward testing and later forward observation.

“Error free” is not a defensible absolute data claim. The operational objective
is typed and standardized data whose defects are detected, quantified, traced
to provenance and blocked or explicitly represented instead of being silently
accepted.

## Consolidated workflow

1. Build the ingestion and analytical pipeline on synthetic data.
2. Test missing values, duplicates, revisions, corporate actions, timestamp
   errors, identity changes, schema changes and failure recovery.
3. Validate deterministic features, outcomes, costs and portfolio accounting
   against known answers.
4. Run synthetic backtests and walk-forward scenarios to test the engines,
   including leakage, purge and embargo controls.
5. Hold one consolidated readiness review before the first real-data transition.
6. After explicit authorization, ingest approved real data and qualify its
   provenance, coverage, identity and point-in-time correctness.
7. Preregister real hypotheses, use untouched holdouts and conduct genuine
   historical and walk-forward validation.
8. Forward-test qualifying evidence before publishing an actionable score.

Routine synthetic milestones need code review, tests and a concise status note;
they do not require a new owner PDF. A new PDF is reserved for a material gate,
such as the consolidated real-data transition review.

## Mandatory pause points

Explicit owner authorization is still required before:

- first access to a private or real market dataset under a new scope;
- bulk external-data acquisition;
- adding APSW or another evaluated component to production dependencies;
- changing or removing `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`;
- executing a production/private database audit;
- publishing or promoting a score based on real data;
- connecting research recommendations to an operational decision interface;
- expanding into any broker mutation or trade-execution capability.

Broker mutation and trade execution remain prohibited. Current read-only Kite
capabilities retain their previously documented scope.

## Immediate engineering direction

Proceed with the integrated synthetic research pipeline and its bounded tests.
The current APSW candidate remains isolated and non-production. Official NSE
F&O schema provenance remains pending and must not be guessed. Real-data access,
data qualification, market-edge claims and score promotion remain outside the
standing synthetic authority.

This policy favors a top-tier quantitative-research discipline: fast iteration
on reversible engineering, strict evidence at irreversible or externally
consequential gates, and an explicit distinction between software correctness
and economic validity.
