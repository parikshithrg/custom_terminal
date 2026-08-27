# Research Reconciliation R.2

## Scope and baseline

R.2 began from clean commit `635f244`. It performed evidence preservation and
read-only translation only. No hypothesis, strategy, simulation, data
acquisition, momentum experiment or Kite request was run.

## Implementation

- Preserved the exact designated 32-row legacy CSV under a content-addressed,
  versioned package without changing either original log.
- Added a separate immutable snapshot manifest and a 13-family reviewed mapping
  covering every row ID exactly once.
- Added a dependency-neutral exporter and a thin `dtest` adapter that imports
  `research_contracts`, not `market_intel`.
- Generated canonical JSON and tabular CSV neutral ledgers without recomputing
  metrics.
- Added a `market_intel` validation importer that verifies source hashes,
  ordering, lifecycle, family version and non-production status.
- Added a separate append-only JSONL evidence catalog. Re-importing the exact
  ledger is idempotent; changing the same ledger version is rejected.
- Added offline tests for immutable bytes, mapping, evidence failures,
  determinism, import safety, catalog behavior and rollback.

## Immutable outputs

| Object | SHA-256 |
|---|---|
| Exact legacy CSV | `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d` |
| Neutral JSON ledger | `79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392` |
| Neutral tabular CSV | `730ae1fd1cb6fb6d4f2c1896a3cc052d3fb89ec5e158b0c121588214fdbf5d4d` |
| Family mapping | `e876933a7367301594448c0475b995a0cd57e13103ceec32b371cc558156eeb4` |

## Row accounting

- 32 total rows, 26 rejected and 6 accepted under the legacy vocabulary.
- 13 reviewed experiment families.
- Lifecycles: 22 `TRAIN_REJECTED`, 5 `TRAIN_PROMOTED`, 4
  `VALIDATION_REJECTED`, and 1 `VALIDATION_CONFIRMED`.
- Zero test rows and zero replication rows.
- 29 `PARTIAL_ARTIFACTS_NO_MANIFEST` rows.
- 3 `AMBIGUOUS_ARTIFACT_MATCH` rows.
- Zero verified hypothesis manifests.
- Every row has `production_eligible=false`.

## Unresolved components

Selection rule, decision clock, entry rule, exit overlay, cost-schedule version
and portfolio construction remain unresolved for all 32 rows. Holding horizon
is proved from the row itself for earnings surprise, value and quality, and
unresolved for the other 29. The adapter did not use present configuration to
fill an old-run gap.

## Import boundary

The importer registers only `LEGACY_EXPLORATORY_EVIDENCE`. It cannot write to
the production experiment catalog, rejects lifecycle escalation and production
eligibility, preserves missing-manifest states, and rejects Kite/current-market
references. The committed catalog contains one validated non-promotable import.

## Verification

- Root suite: `python -m pytest -q` — 136 passed.
- Separate laboratory suite: `python -m pytest "Data test/tests" -q` with its
  documented `PYTHONPATH` — 289 passed; five third-party SWIG deprecation
  warnings did not affect the result.
- Adapter-focused suite: `python -m pytest
  tests/test_research_r2_legacy_ledger.py -q` — 22 passed.
- All 32 JSON specifications and legacy evidence objects parsed successfully.
- `python -m compileall -q src "Data test/dtest" scripts tests` — passed.
- Two independent exports produced the same JSON hash
  `79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392`
  and CSV hash
  `730ae1fd1cb6fb6d4f2c1896a3cc052d3fb89ec5e158b0c121588214fdbf5d4d`.
- Git whitespace validation passed.
- Protected tracked paths had no diff from `635f244`.
- The original local log, PDF and live sibling log retained their respective
  SHA-256 values `80d80a…`, `940efd…` and `1e26df…`; the pinned historical
  filtered object re-verified as `124886…`.

## Files added or changed

- `.gitattributes` for byte-preserved legacy evidence paths;
- `evidence/legacy/legacy_hypothesis_ledger_v1/` with exact source bytes,
  manifests and deterministic JSON/CSV ledgers;
- `evidence/legacy/legacy_evidence_catalog_v1.jsonl`;
- `specs/legacy_ledger_contract_v1.json` and
  `specs/legacy_family_mapping_v1.json`;
- `src/research_contracts/legacy_ledger.py` and neutral exports;
- `Data test/dtest/evaluate/legacy_export.py`;
- `src/market_intel/foundation/legacy_evidence.py` and foundation exports;
- preservation, export and validation/catalog command scripts;
- four R.2 reports and focused offline tests.

## Protected evidence

The repository-local 31-row log, source PDF, momentum specification, golden
fixtures, old artifacts and manifests, historical trust verdicts, Kite
allowlist/health contracts and NSE response state are not modified.

## Decision

The ledger and adapters are usable, but the historical run manifests remain
incomplete. Preservation does not retroactively make the experiments
reproducible.

`LEGACY_LEDGER_PRESERVED_MANIFESTS_INCOMPLETE`

## Safest next implementation milestone

Implement R.3 only for future-run governance: make a root manifest, immutable
artifact bundle, family registration and one-time split-access event mandatory
before any new laboratory execution. Keep all R.2 rows exploratory and do not
test another hypothesis as part of that milestone.
