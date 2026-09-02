# Research R.9A - Exact Local F&O Audit Authorization Proposal

## Baseline and prerequisite verification

R.9A began from clean synchronized `main` commit
`b4768207a9a322f7ba676c0d3c47262b37afe44c`. The 21-page reviewed PDF remains
unchanged at SHA-256
`cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c`.
The review record is `REPORT_REVIEWED_APPROVED` for
`BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING`; it grants no empirical authority.
The research-state fingerprint remains
`40a18b14949d13b383dd549fe1d37c86881a61acf2d98bac9db2e6770d820e01`.
Protected evidence is unchanged and `version2.0` remains external.

No real database path was resolved or committed. No database header, database
byte, observation, pragma or SQL statement was read. No connection was made,
full hash computed, external source contacted, market data acquired, score
calculated, or analysis/backtest/trade performed.

## Proposed authorization

Proposal `local_fno_audit_stage_1_3_v1` requests one later execution of only:

1. file location and bounded sampled identity freeze;
2. SQLite read-only safety and catalog metadata;
3. already-local provenance and retention inventory.

Stages 4-6, `quick_check`, `integrity_check`, market-row queries, external
acquisition and every empirical or trading action are excluded. A future
implementation must be separately committed and reviewed before an approval can
be used. The included approval template is deliberately unusable.

## Resource envelope

- 64 deterministic 4 MiB chunks plus the 100-byte SQLite header per identity pass.
- 268,435,556 bytes per pass; no more than five checkpoints.
- At most 50 catalog/safety statements, each with a five-second progress deadline.
- At most 500 Stage 3 files and 512 MiB of Stage 3 reads.
- Declared 20-minute total duration, 512 MiB memory, 25 MiB output and 128 MiB temporary storage.
- Statement cancellation and write rejection must be code-enforced; total time and memory are declared, not OS-enforced.

## Identity and mutation protection

Size, modification time, header hash, sampled chunk hashes/Merkle root and
source-directory sidecars are captured immediately before opening, after each
stage and before finalization. Any change aborts without repair or retry.

## Expected audit outputs

A later approved audit may emit only sanitized identity, safety, catalog,
query-plan, provenance, rights, event-log, root-manifest and completion-report
artifacts. Historical completeness and point-in-time fitness remain
`NOT_EVALUATED`; research eligibility remains `NOT_APPROVED`.

## Proposal hashes

- Package content SHA-256: `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd`
- Proposal manifest SHA-256: `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8`
- Audit scope SHA-256: `86af643f9c88a1162ecaecf76d22e4e74b5d39816f6e6117eb6105b726588d8d`
- Resource envelope SHA-256: `1aec4f54a6e3cf88cfa1ecde91b5b8c1579886d38a5282e5131471b2694436b5`
- Expected outputs SHA-256: `b1d05cfba2de056156d07c4f93512372af9eafd6f2de7d682404050e742f0d8a`

## Verification

- Focused R.9A proposal suite: 12 passed.
- Complete root suite: 252 passed with the two established deprecated-runner warnings.
- Separate Data-test suite: 289 passed with its established third-party and noncanonical-log warnings.
- JSON parse and proposal-contract validation: 481 files passed.
- Python compilation and Git whitespace validation: passed.
- Reviewed PDF: unchanged, 21 pages, exact expected SHA-256.
- Research-state fingerprint: unchanged at `40a18b14949d13b383dd549fe1d37c86881a61acf2d98bac9db2e6770d820e01` across 230 files.
- Protected momentum, golden-fixture and manifest comparison: zero changes.
- Secret-pattern scan: one expected `<redacted>` literal in the existing Kite connector; no credential value detected.

## Authorization still required

The owner must approve the exact committed proposal using a distinct
`LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1` object that binds the final commit,
proposal manifest, scope, resources, outputs and stages 1-3. It must be explicit,
unexpired and one-use. General F&O-audit permission and market-research approval
are insufficient.

Successful proposal review will still not authorize market-row coverage or
integrity analysis, external acquisition, scoring, backtesting, recommendations,
broker actions or trading.

FNO_STAGE_1_3_PROPOSAL_READY_FOR_OWNER_APPROVAL
