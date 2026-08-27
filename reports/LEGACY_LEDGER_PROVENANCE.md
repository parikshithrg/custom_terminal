# Legacy Ledger Provenance

## Designated evidence

Research Reconciliation R.2 preserves the exact 32-row ledger designated by
R.1. Its immutable package is
`evidence/legacy/legacy_hypothesis_ledger_v1/`.

| Field | Value |
|---|---|
| Snapshot version | `legacy_hypothesis_snapshot_v1` |
| Exact-byte SHA-256 | `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d` |
| Byte size | 32,665 |
| Rows | 32 |
| Accepted / rejected | 6 / 26 |
| Source commit | `c3acfaf963813ad875b1d4e72590bc16861429e2` |
| Source Git blob | `a6d627443d071644748921f3a049fb84b7a0a742` |
| Source configuration SHA-256 | `82dd7d602560c35c40062ba30df7c5fe647f78249568749928cab93adcf584c9` |

The exact bytes were recovered read-only from the pinned sibling Git object
through its checkout filters. This matters because the raw Git blob uses LF
line endings while the R.1-designated working-tree evidence used CRLF. Git's
filtered object produced exactly 32,665 bytes and the required SHA-256 before
anything was copied.

The live sibling checkout was not used as the snapshot. At R.2 inspection it
had advanced to commit `ef891c29`, contained 34 rows, and had SHA-256
`1e26df878db4e33ffddbbd5882aba18053afee79e200d803e0a1401e54cc2514`.
Neither that file nor the sibling checkout was modified.

## Immutable package

The original CSV is stored byte-for-byte. `.gitattributes` marks that one path
as `-text`, preventing Git from normalizing its CRLF content. Metadata is kept
separately in `snapshot_manifest.json`; it records the ordered row IDs, source
classification, commit and configuration evidence, current-source divergence,
and known limitations.

The preservation tool refuses a source-hash mismatch and refuses to replace a
different destination. The exporter hashes the source before and after every
read. It does not normalize, reserialize, append to, or repair the CSV.

## Relationship to the repository-local log

The ignored repository-local `Data test/runs/hypothesis_log.csv` remains a
separate 31-row object with SHA-256
`80d80aa9372f5dc0ff857acba36575c125438508ebededecd789a31ece799777`.
It was not overwritten. The immutable R.2 snapshot adds the previously located
row `7facf033cb36`, but does not insert that row into the original local log.

## Limits

- The original working log was ignored by Git.
- Its rows contain no root-run-manifest reference.
- The source configuration is not cryptographically bound to individual runs.
- A preserved result string is not proof that the run can be reproduced.
- `accepted` is a legacy row decision, not production eligibility.

Preservation is not reproduction.
