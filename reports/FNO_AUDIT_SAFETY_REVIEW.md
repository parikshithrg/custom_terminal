# Local F&O Audit Stages 1-3 - Safety Review

## Write and connection protection

The proposed future implementation uses four independent controls: SQLite URI
`mode=ro`, verified `PRAGMA query_only=ON`, a strict statement allowlist, and a
denylist covering attach/detach, DDL, DML, vacuum, reindex, analyze, extension
loading and writable/journal pragmas. Every attempted statement is logged before
execution with literals and paths sanitized.

Only one connection is permitted. The approval must be atomically consumed
before it opens. The implementation must inventory source-directory sidecars
before and after the connection and abort if a WAL, journal, shared-memory file
or other unexpected sidecar appears. Temporary output belongs in a task-scoped
directory outside both the database and source directories.

No implementation or connection is created in R.9A.

## Cancellation and resource truth

| Control | Proposal value | Enforcement truth |
|---|---|---|
| Identity sample | 64 chunks of 4 MiB plus 100-byte header | Future code must enforce exact offsets and byte count |
| One identity pass | 268,435,556 bytes | Bounded by reader; not a full-file hash |
| Five checkpoints | Maximum 1,342,177,780 identity bytes | Future code-enforced count |
| Stage 2 statements | At most 50 | Future allowlist/event logger must enforce |
| Statement timeout | 5 seconds | Future SQLite progress handler with monotonic deadline |
| Stage 3 files | At most 500 and 512 MiB | Future inventory reader must count both |
| Total duration | 1,200 seconds | Declared only; not OS-enforced |
| Memory | 512 MiB | Declared only; not process-enforced |
| Output | 25 MiB | Future artifact writer must enforce byte counter |
| Temporary storage | 128 MiB | Declared and writer-checked; not an OS quota |

The sampled identity detects changes in size, time, header and selected chunks;
it is not equivalent to whole-file SHA-256. Full-file hashing is outside this
request. The `quick_check` and full `integrity_check` are excluded because R.9A
cannot prove their cost is bounded on the approximately 45 GB object.

## Database-change protection

The future audit captures the same identity immediately before opening, after
each requested stage and immediately before final evidence. It aborts on path,
size, modification-time, header or sampled-chunk change; unexpected sidecars;
any source mutation; approval mismatch/reuse/expiry; an unapproved statement;
resource breach; network attempt; or path-disclosure risk.

On abort it closes the read-only connection if open, writes only a sanitized
terminal event, and never repairs, retries, stabilizes or expands scope.

## Provenance and rights boundary

Technical readability, SQLite structural validity, source provenance, retention
rights, historical completeness, point-in-time fitness and research eligibility
are separate decisions. Stages 1-3 can address only the first four, and even
those may remain unknown. Historical completeness and point-in-time fitness are
explicitly not evaluated. Absence of a restriction is not permission, Kite
cannot fill gaps, and no paid source is proposed.

Safety conclusion: the proposal is bounded enough for owner review. Execution
remains impossible until a distinct exact approval and separately reviewed
implementation exist.
