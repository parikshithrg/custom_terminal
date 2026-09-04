# R.9N - Pre-execution adversarial matrix

Authority: this new R.9N task only. R.9M's original authorization is completed
historical authority, not reusable production or indefinite experiment approval.
Baseline fcddaa3, clean. Pinned isolated APSW 3.53.4.0 / SQLite 3.53.4 only.
Production remains R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE.

## Meter contract

One attempt is created before its one read-only open and ends at close/failure.
Opening/header xRead requests count. Every xRead adds to requested; admission
reserves the full amount before delegation. Delegated counts attempted underlying
read lengths (even error); returned counts actual byte lengths obtained. Refused
requests add no reservation/delegation. Reservation is never refunded on errors
or short reads. Repeated offsets cost again. All statements share the same meter.
Failure is sticky. Closed/failed attempts cannot reopen or reset their meter.
Counters are diagnostic, not authority. Hostile same-process mutation is excluded.

Fixture creation, hashes, native controls, dependency imports and directory checks
are outside the meter. This is not whole-process I/O, physical storage I/O,
OS-cache accounting or all Python reads. Mapped access and all sidecar/temp file
opens must be unavailable, not silently unmetered. No support broadening.

## Matrix (write before execution)

| Group | Hypothesis and expected outcome | Evidence type |
| --- | --- | --- |
| Three layouts | 512/1024/4096 page sizes, bounded schema; sufficient passes; observed exact passes, one-under/zero fail | Native SQLite |
| Shared attempt | Repeated permitted catalog operations consume one cumulative budget | Native SQLite |
| Iteration | Derive budget from first fetch-phase read in sufficient observation; failure occurs during fetch; no completed output | Native SQLite |
| Repeated offset | Every read reserved again; exact boundary then sticky refusal | Direct native file method |
| Errors/short reads | Full reservation retained, short/error abort; continuation fails | Injected underlying responses, explicitly mocked |
| Damaged fixture | Truncated/malformed new files rejected without completed output | Native SQLite |
| Reopen/reset | Second connection and reopening same attempt rejected; meter cannot be reset by supported API | Native/facade |
| Access | Read-write/create, ATTACH, app reads, unknown SQL, temp and sidecar opens rejected | Facade, native authorizer and direct methods separately |
| Sidecar operation | Generate bounded active WAL/rollback fixture; actual catalog operation refused, even if rejection precedes xOpen | Native SQLite plus writer fixture setup |
| Cursor controls | Per-attempt row/output limits discard buffered result; checks span execute/fetch | Native SQLite; injected clock for deterministic expiry |
| mmap | Native request through restricted connection rejected; no mapping interface added | Native authorizer; R.9M source evidence reused |

Limits: each fixture <256 KiB, <=80 tables, <=3 statements/attempt, 1 MiB
read allowance for successful controls, <=200 returned rows, <=128 KiB output.
Single candidate worker; fixed CLI with no database or SQL arguments. Overall
worker timeout 30 seconds. No new library/driver/native VFS/system change.
Temporary roots created only below ignored artifacts/r9n_evaluation; remove
only each exact generated TemporaryDirectory. No production/real data paths.

Official-format branch: ordinary access to known NSE Forms & Formats landing
page/document links only, maximum one direct landing-page request (20 seconds),
bounded documentation retrieval if discoverable. No market records. If unavailable,
record PENDING_OFFICIAL_FORMAT_EVIDENCE and use clearly generic fixtures.

Report controls independently. Preserve namespace/writer/same-process limits,
no temp quota or hard real-time claim. Failed diagnostic JSON is not a successful
audit artifact. Stop after report/tests/commit; no new PDF or owner approval.
