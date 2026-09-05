# R.9P pre-execution acceptance matrix

This matrix was fixed before the integrated native run. All fixtures are newly
created, generic, synthetic SQLite files. `PENDING_OFFICIAL_FORMAT_EVIDENCE`
remains the official-schema status.

| # | Criterion | Required evidence |
|---|---|---|
| 1 | Exact approval | Sealed payload contains the explicit attempt ID and exact fixture, source, template, limit, containment and output bindings. |
| 2 | Durable one-use consumption | SQLite ledger commits consumption before worker creation; replay, duplicate IDs and a two-consumer race reject. |
| 3 | One target connection | Restricted VFS admits exactly one main read-only open and rejects reopen. |
| 4 | Whole-attempt checks | Main-file guard spans final identity verification through close; namespace checks occur before/immediately after/between operations/before publication/after close. |
| 5 | Unsupported I/O fails closed | Sidecars, non-main file categories, mmap and mutation/substitution produce diagnostics and no success artifact. |
| 6 | Exact templates only | Only hash-bound `catalog` and `columns` templates execute; arbitrary SQL and application reads reject. |
| 7 | Cumulative limits | Logical reads reserve before delegation; rows, deterministic output and connection/execute/fetch deadline are shared and fail closed. |
| 8 | No success after failure | Failed attempts publish only the separate diagnostic schema/location. |
| 9 | Terminal reconciliation | Every consumption has one terminal state or is deterministically reconciled as `SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH`. |
| 10 | Synthetic containment | No path/config/SQL public inputs; generated-root marker, recipe, exact identity, path and link checks precede SQLite. |

The native matrix also covers the requested one-byte deficit, row/output/fetch
deadline failures, late sidecar, replacement, three crash points, descendant
timeout, concurrent consumption, second connection, arbitrary SQL/application
reads, outside-root/link rejection, and three page-size layouts.

