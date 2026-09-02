# F&O Auditor Implementation Review

## Scope and result

R.9B implements `market_intel.foundation.local_fno_audit` as a dedicated
local-data-audit contract. It is separate from market-research approvals and is
compile-time/contract restricted to caller-supplied fixtures classified
`SYNTHETIC_AUDIT_TEST_FIXTURE` inside a marked fixture root. The production
locator key `paths.fno_db` is rejected. No code reads that configuration value.

The default entry point mode is `PROPOSAL_DRY_RUN`. It resolves no path, opens
no connection, runs no SQL, creates no attempt, and reports a blocked state.
The only executable mode is `GOVERNED_SYNTHETIC_EXECUTION`, which requires an
exact, registered, unexpired, one-use
`LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1`.

## Stage boundaries

Stage 1 verifies a regular non-symlink file, containment in a marked synthetic
root, the SQLite header, size, nanosecond modification time, and the approved
64-position/4 MiB bounded identity. Small files deduplicate identical offsets,
so a small fixture is read once at offset zero rather than repeatedly. The
identity remains a sampled change detector, not a whole-file hash.

The pre-consumption capture also serves as the immediately-before-open capture:
atomic in-memory approval consumption is the only intervening operation. This
preserves the proposal's maximum of five identity passes. Further captures run
after Stages 1, 2 and 3 and immediately before publication. Size, time, header,
sampled root, or database-associated sidecar change aborts.

Stage 2 opens one SQLite URI connection with `mode=ro`, disables extension
loading, installs an authorizer, sets and verifies `query_only=ON`, uses a
5-second busy timeout, caps attempted statements at 50, and installs a
monotonic progress callback for each statement. The statement parser and
authorizer reject DDL, DML, attachment, maintenance operations, writable
pragmas, user-table reads, multiple statements and anything outside the
catalog-only allowlist. `quick_check` and `integrity_check` are absent.

Allowed metadata is limited to `sqlite_schema`, table/view columns, declared
types and keys, indexes, foreign keys, and optional `EXPLAIN QUERY PLAN` output.
Explained statements are planned but never executed. No row count, date,
symbol, expiry, strike, coverage or market value is calculated.

Stage 3 traverses only caller-approved roots deterministically. It follows no
symlink, permits at most 500 files and 512 MiB of reads, and reads only small
metadata/document/source extensions. Other objects are inventoried by size and
anonymous handle without opening their contents. Output contains aliases,
hashes and categorical evidence status, never source paths or secret values.

## Outputs and limits

Only the nine proposal-approved filenames can be written. JSON uses sorted,
compact UTF-8 encoding; the writer enforces the 25 MiB aggregate limit and
rejects replacement or unexpected output. Each evidence object binds proposal,
approval and attempt identity. Finalization renames a task-scoped temporary
directory atomically. Completed, aborted and failed attempts all receive a
terminal event and remain noncanonical and nonpromotable.

Total wall time, process memory and filesystem quota remain declarations, as in
the proposal. Statement count/deadline, identity reads, Stage 3 file/byte limits
and output bytes are code-enforced.

## Remaining restriction

The in-memory synthetic approval registry is intentionally not a production
approval store. Enabling real access requires a separate reviewed change, a
new current status PDF, an exact production identity binding, and explicit
owner approval. R.9B contains no production-path resolution and performs no
real audit.
