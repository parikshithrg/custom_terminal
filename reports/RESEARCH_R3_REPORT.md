# Research Reconciliation R.3

## Baseline and scope

R.3 began from clean, synchronized commit
`671ac6137492f502f60f1a712736d03e72b69528`. The completed implementation is
present as an uncommitted working-tree change for review. It implements
prospective governance for future research. No real hypothesis, strategy,
backtest, market-data request, Kite request or legacy metric evaluation was
executed.

## Contracts and implementation

- Added immutable family-version registration with zero substantive R.3
  families.
- Added complete, canonical, hash-locked preregistration.
- Added immutable dataset/input declarations with capability preflight.
- Added a single governed laboratory gateway and thin dependency-neutral
  `dtest` adapter.
- Added mandatory root manifests for completed, failed and aborted attempts.
- Added declared artifact inventories, unexpected-output isolation and atomic
  finalization.
- Added an append-only, hash-chained governance event catalog with sequence
  validation.
- Added validation, one-use test and replication access controls.
- Added a `market_intel` canonical future-evidence importer and separate
  append-only catalog.
- Added a sanitized frozen-versus-live divergence monitor.
- Added synthetic fixtures and offline tests only.

## Behavior proved with synthetic runs

- Incomplete preregistrations and missing dataset hashes fail preflight.
- Failed/unknown required capabilities fail unless a limited exploratory run is
  explicitly and permanently non-promotable.
- Configuration, dirty-state and environment fingerprints are bound.
- Duplicate attempt IDs and silent family/preregistration edits are rejected.
- Successful, failed and aborted attempts all retain root manifests.
- Failure details are sanitized.
- Undeclared outputs remain outside canonical inventory.
- Catalog tampering and event-sequence breaks are detectable.
- Test access is single-use and cannot be reissued for the same family version.
- Ungoverned outputs and Kite/current-market historical references are rejected.
- Two identical synthetic executions produce byte-identical artifacts and root
  manifests under fixed IDs and timestamps.

## Legacy divergence

The live sibling log has 34 rows versus the frozen 32. Two added IDs have no R.3
governed manifests and are classified `POST_FREEZE_UNGOVERNED_ROWS`. One frozen
row ID differs in the live file. No changed or added metrics were imported or
interpreted, and neither log was modified.

## Verification

- `python -m pytest -q`: **166 passed**.
- separate `Data test` suite with its documented `PYTHONPATH`: **289 passed**,
  with five existing SWIG deprecation warnings.
- `python -m pytest tests/test_research_r3_governance.py -q`: **30 passed**.
- JSON/specification validation: **38 files valid**.
- Python compilation across `src`, `Data test/dtest`, `scripts` and `tests`:
  **passed**.
- The focused suite executed the same synthetic attempt twice with fixed IDs
  and timestamps: all declared artifact and root-manifest bytes matched.
- Hash-chain verification and intentional tamper/sequence-break tests passed.
- Git diff and exact-byte hash checks found no protected-evidence change.

## Files changed

- Contracts and gateway: `src/research_contracts/governance.py`,
  `src/research_contracts/divergence.py` and package exports.
- Laboratory adapter: `Data test/dtest/governance/`.
- Canonical importer: `src/market_intel/foundation/future_evidence.py` and
  foundation exports.
- Machine-readable contracts: the four R.3 JSON specifications under `specs/`.
- Anchors/results: `evidence/governance/` and its byte-stable Git attribute.
- Command, fixtures and tests: `scripts/check_legacy_log_divergence.py`,
  `tests/fixtures/research_r3/` and `tests/test_research_r3_governance.py`.
- Reports: this report plus `FUTURE_RUN_GOVERNANCE.md`,
  `SPLIT_ACCESS_GOVERNANCE.md` and `LEGACY_LOG_DIVERGENCE.md`.

## Protected evidence

The protected-path Git diff against `671ac61` is empty. Exact-byte checks also
confirm the frozen snapshot (`124886d4…`), neutral R.2 ledger (`79df7b78…`),
repository-local 31-row log (`80d80aa9…`), live sibling log (`1e26df87…`),
status PDF (`940efd19…`) and legacy evidence catalog (`ef62824f…`) are unchanged.
The momentum specification, golden fixtures, old runs/manifests, historical
trust verdicts, Kite contracts/allowlist and NSE response state have no diff.

## Safest next milestone

Implement R.4 as a no-execution integration review: inventory every existing
laboratory entry point, require each future canonical path to call the gateway,
and add an explicit user-approval object for the first real governed run. Do not
authorize or execute a hypothesis during that review.

## Decision

The prospective execution and import boundary is implemented. It makes governed
state and tampering detectable but does not prevent the filesystem owner from
reading or rewriting local files outside the governed tools.

`FUTURE_RUN_GOVERNANCE_READY`
