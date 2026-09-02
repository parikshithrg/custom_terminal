# Research R.8 - Non-Empirical Integration and Data-Audit Planning Package

## Baseline and authority

R.8 starts after Phase A commit `66eedc4`, which finalized the R.7
two-repository amendment and recorded the owner's post-generation review. The
reviewed PDF SHA-256 remains
`cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c`.
Its historical generation state is pending review; the separate current record
is `REPORT_REVIEWED_APPROVED` for
`BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING` only.

The external `version2.0` reference was rechecked at
`2026-09-02T06:34:44.3686602Z` and remains `master` commit
`f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`. It remains separate and untrusted.
R.8 did not clone it into the repository, execute it, modify it, import its data
or results, launch its dashboard, run live scans or access broker methods.

## Package contents

- `BOUNDED_COMPONENT_INTEGRATION_PLAN.md` defines the one-way published-read-model boundary.
- `MARKET_SENTIMENT_COMPONENT_PLAN.md` separates stress, positioning, tone, breadth, derivatives and macro concepts.
- `STOCK_SCORE_COMPONENT_PLAN.md` defines independent evidence categories without a combined score.
- `LOCAL_FNO_DATABASE_AUDIT_PLAN.md` specifies a staged, cancellable, read-only trust audit that has not been executed.
- `docs/research_r8/component_inventory_v1.json` inventories the three components and their prohibitions.
- `docs/research_r8/source_capability_matrix_v1.json` records source, timing, revision, missingness and trust gaps.
- `docs/research_r8/local_fno_audit_contract_v1.json` records the SQL and performance safety envelope.
- `docs/research_r8/owner_decision_record_v1.json` binds the owner's planning-only decisions and deferred questions.

These machine-readable files live under documentation, not research specs or
proposals. They are deliberately non-executable and cannot authorize empirical
work.

## Component decisions

### Market sentiment

The reference implementation mixes economically distinct ideas. R.8 preserves
six separate concepts and rejects premature aggregation. Current result:
`SENTIMENT_DEFINITION_AMBIGUOUS`; source qualification is required before any
governed feature proposal.

### Stock scores

Data quality, liquidity, market behavior, disclosures, ownership, sentiment and
derivatives context remain separate categories. Current result:
`STOCK_SCORE_DEFINITION_AMBIGUOUS`; no final score, ranking or recommendation is
defined.

### Local F&O database

The configured database path is identified without resolving or publishing the
machine-specific value. No connection or query was made. The contract starts
with metadata and provenance, requires SQLite read-only enforcement, bounded
plans, timeouts and cancellation, and prohibits mutation. Planning result:
`FNO_AUDIT_PLAN_READY`; provenance and retention rights remain unresolved until
the audit is separately approved and run.

## Deferred owner decisions

- Which current-data providers may be used for display-only diagnostics.
- Whether legacy "passed validation" labels should be renamed.

## Unchanged prohibitions

This package does not authorize data acquisition, database audit execution,
market analysis, simulation, backtesting, strategy evaluation, score
calculation, security ranking, recommendations, live scans, broker actions,
trading, lifecycle promotion or canonical evidence import. Any future empirical
task still requires a compatible current PDF, a complete preregistration,
immutable input bindings and a separate exact one-use approval.

## Verification

- Focused R.8 planning tests: 8 passed.
- Complete root suite: 240 passed with the two established deprecated-runner warnings.
- Separate Data-test suite: 289 passed with its established third-party and noncanonical-log warnings.
- JSON parse and planning-contract validation: 473 files passed.
- Python compilation and Git whitespace validation: passed.
- Reviewed PDF: 21 nonblank pages; SHA-256 remained `cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c`.
- Research-state fingerprint: unchanged at `40a18b14949d13b383dd549fe1d37c86881a61acf2d98bac9db2e6770d820e01` across 230 files.
- Protected momentum, golden-fixture and manifest comparison: zero changes.
- Secret-pattern scan: one expected `<redacted>` code literal in the existing Kite connector; no credential value detected.

## Safest next step

The owner should review the definitions, source matrix, UI boundary and F&O
audit safety envelope. If accepted, the next task should be a separate approval
to run only Stage 1-3 of the local read-only F&O trust audit, with no market
outcome query and no score work.

R8_PLANNING_PACKAGE_READY_FOR_OWNER_REVIEW
