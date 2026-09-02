# Local F&O Database Trust-Audit Plan

## Scope

The owner permits a future local trust audit, not its execution in R.8. The
database is located only through `Data test/config/config.toml` key
`paths.fno_db`; no resolved machine path is committed. Reported size and row
count are context, not evidence of validity.

The audit asks whether the database can be trusted as a data source. It does
not evaluate a strategy, calculate a signal, query market outcomes, or authorize
research use.

## Read-only safety envelope

- Open SQLite by URI with `mode=ro`, then assert `PRAGMA query_only=ON`.
- Use one connection by default, a five-second busy timeout, a progress handler,
  a 30-second query budget and cancellable bounded statements.
- Inspect query plans before scans. Require an applicable index or abort and
  request a separate scan approval.
- Keep temporary state in memory or a task-scoped location outside the database
  directory. Never create tables, indexes or sidecar exports beside the source.
- Prohibit attach/detach, DDL, DML, vacuum, reindex, analyze, extension loading,
  writable pragmas and full-table export.
- Do not acquire missing raw files during the audit.

## Ordered audit sequence

1. **Locate and identify:** confirm configured existence; record size and
   modification time as metadata; choose full SHA-256 only if bounded, otherwise
   create an ordered chunk-hash/Merkle identity manifest.
2. **SQLite safety:** verify header, read-only behavior, bounded `quick_check`,
   schema, table/column/index inventory and query plans. A full integrity check
   requires a separate cost estimate if not bounded.
3. **Provenance:** inventory source report types, retained raw objects, retrieval
   timestamps, hashes, parser versions, corrections, backups and rights.
4. **Coverage:** obtain indexed/bounded date and partition summaries for sessions,
   symbols, stock/index instruments, futures/options, expiries and strikes.
5. **Integrity:** test bounded partitions for duplicate natural keys, impossible
   prices/volume/turnover/OI/contracts, OHLC/settlement consistency, option type,
   strike, expiry, stale rows and truncated sessions.
6. **Point-in-time fitness:** establish publication time, available-at policy,
   corrected vintages and whether the database contains final revised history
   only.
7. **Reconciliation design:** compare bounded samples to already retained raw
   NSE files and permitted independent official evidence; do not perform network
   acquisition.

## Coverage and continuity design

Coverage reporting must include minimum/maximum dates by typed table, expected
versus represented sessions, missing sessions, symbols, instrument classes,
expiries, strikes, contract transitions and schema changes. Pre/post-2024
instrument classification must be treated as a possible schema boundary, not
silently harmonized.

Contract continuity must use authoritative underlying/instrument identifiers,
expiry, option type and strike. Ticker similarity is insufficient. Symbol or
contract discontinuities remain unresolved until source evidence explains them.

## Provenance and rights gate

For every normalized table, identify the NSE report type, raw object, retrieval
method and time, content hash, parser version, corrections, retained vintages,
licensing and permitted personal-research use. If these cannot be proved, the
database may still be technically readable but cannot become a trusted
historical research input.

## Abort conditions

Abort if read-only behavior cannot be proved, the database changes during the
audit, a query requires an unapproved unbounded scan, timeout/cancellation is
unavailable, temporary storage could mutate the source directory, rights
clearly prohibit the audit, schema cannot be identified, or secrets could be
exposed.

Possible later decisions are `FNO_AUDIT_PLAN_READY`,
`FNO_PROVENANCE_INCOMPLETE`, `FNO_RETENTION_RIGHTS_UNRESOLVED`,
`FNO_AUDIT_UNSAFE`, and `FNO_DATABASE_NOT_LOCATED`.

R.8 planning result: `FNO_AUDIT_PLAN_READY`. This means only that a safe audit
sequence is specified. The audit has not been run and no F&O data is approved
for research.
