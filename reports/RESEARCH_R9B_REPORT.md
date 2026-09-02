# Research R.9B — Synthetic-Only Bounded F&O Auditor

## Baseline and proposal verification

R.9B started from clean synchronized `main` commit `193bf98`. Every object in
`docs/quarantined_proposals/local_fno_audit_stage_1_3` matched its committed
byte size and SHA-256. Canonical package hash
`9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd`
and manifest hash
`4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8`
both revalidated. No proposal scope, resource, identity, output or exclusion
object changed.

## Implementation

The new `market_intel.foundation.local_fno_audit` module provides typed proposal,
approval, registration, attempt, event, identity and terminal-result contracts.
Its default dry run performs no resolution, connection, SQL or attempt. Its
explicit mode accepts only a marked caller-supplied synthetic fixture and an
exact registered one-use audit approval. The production locator is rejected in
the approval contract.

Stage 1 implements the approved bounded ordered-chunk identity with deterministic
deduplication for small fixtures. Stage 2 enforces SQLite `mode=ro`, verified
`query_only`, an authorizer, statement allowlist and operation denylist,
50-statement cap, disabled extensions and per-statement monotonic cancellation.
It inventories schema/catalog metadata and query plans without user-table row
reads. Stage 3 performs bounded deterministic local provenance inventory with
no symlink following, parser execution, acquisition or network access.

Only the nine approved artifacts can be emitted. Output is deterministic,
byte-counted, sanitized, approval-bound, atomically finalized, noncanonical and
nonpromotable. Mutation or resource violations abort without repair or retry.

## Verification

- Focused R.9B adversarial suite: **42 passed, 2 skipped** (Windows symlink
  privilege unavailable; direct path-escape and code-level symlink guards pass).
- Combined R.7–R.9B governance/report-gate suite: **81 passed, 2 skipped**.
- Complete root suite: **294 passed, 2 skipped, 2 established warnings**. The
  skips are the two Windows symlink-privilege cases.
- Complete separate Data-test suite: **289 passed**, with only the established
  SWIG deprecations and development-only ledger warnings.
- JSON validation: **498 valid, 0 invalid**.
- Python compilation, protected-evidence comparison, network-dependency scan,
  entry-point reconciliation and `git diff --check`: passed.
- No test resolves or reads `Data test/config/config.toml::paths.fno_db`.
- No real database was located, opened, hashed, inspected or queried.

## Research-state and report gate

The exact reviewed PDF remains byte-identical at
`cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c`.
Adding the research-relevant auditor changed the fingerprint from
`40a18b14949d13b383dd549fe1d37c86881a61acf2d98bac9db2e6770d820e01`
to `9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31`
across 231 files. The review record is therefore marked
`REVIEWED_PDF_STALE_AFTER_AUDITOR_IMPLEMENTATION`. The PDF was not regenerated.

## Boundaries and next step

This is infrastructure safety evidence only. It does not authorize a real
audit, production database access, market-row analysis, coverage analysis,
simulation, backtesting, scoring, recommendations, broker activity or trading.

The safest next milestone is R.9C: generate and visually verify a revised status
PDF that documents the synthetic-only auditor, then request owner review. It
must not enable production access or create an execution approval in the same
milestone.

SYNTHETIC_ONLY_FNO_AUDITOR_IMPLEMENTED
