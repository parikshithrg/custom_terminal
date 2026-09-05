# R.9P integrated synthetic F&O audit-boundary report

## Outcome

The fixed synthetic-only prototype passed all ten predeclared acceptance
criteria. It integrates exact sealed one-use approval, durable pre-connection
consumption, restricted APSW logical-read metering, a one-connection VFS,
cumulative budgets, Windows Job Object containment, main-file and namespace
checks, and terminal reconciliation.

This is software-boundary evidence only. APSW remains an isolated candidate,
the production interlock remains `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`,
and `PENDING_OFFICIAL_FORMAT_EVIDENCE` remains unchanged. No real database,
private configuration, network source, market record, broker function or trade
action was accessed.

## Native observations

- APSW 3.53.4.0 / SQLite 3.53.4 ran in the existing ignored evaluation
  environment, not the root environment.
- Three generated layouts (512, 1024 and 4096-byte pages) completed the two
  exact templates with 37 total rows. Their cumulative logical read totals were
  36,484; 25,732; and 28,804 bytes respectively. Requested, reserved,
  delegated and returned bytes reconciled exactly in these successful cases.
- A one-byte-insufficient bound failed with `READ_BUDGET`. Row 36 failed a
  35-row limit before acceptance. A 10,400-byte output bound failed during the
  second template. A forced fetch-phase deadline failed with `DEADLINE`.
- Late sidecar creation and pre-open file substitution discarded buffered
  output and emitted only failure diagnostics.
- Reopen, arbitrary SQL, application-table reads, mmap and an unsupported file
  open all failed before successful publication.
- Workers were created suspended and hidden, assigned to a noninherited Job
  Object, then resumed. The timeout case killed both worker and descendant.
- Two concurrent consumers produced one winner. Replay, duplicate approval or
  attempt IDs, malformed, expired, mutated and incorrectly bound approvals all
  rejected.
- Crashes after durable consumption, before and after connection, reconciled to
  `SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH`; the event ledger prevents a stale
  pre-connection projection from concealing an observed connection event.

## Mocked failure tests

Two control-flow tests injected Job Object creation and assignment failures.
Creation failure started no worker. Assignment failure left the worker suspended
and never called resume; cleanup remained fail closed.

## Static and source guarantees

The public command accepts no arguments. Its internal worker entry accepts only
a generated opaque token, sealed attempt ID and fixed mode enumeration; it has
no database/config path, environment locator, arbitrary SQL, production
approval, private binding or network input. The fixture root, marker, recipe,
file identity and non-reparse location are checked before SQLite opens.

Successful and failed outputs have different schemas and filenames. Every
consumed approval is assigned exactly one allowed terminal state by durable
compare-and-set. The allowed SQL templates and their hashes are sealed into the
approval. No production package, dependency declaration or entry point changed.

## Remaining limitations

- Discrete namespace checkpoints do not prove continuous quiescence between
  checks. The Windows main-file guard materially narrows that gap but cannot
  freeze an entire directory namespace.
- Job Objects enforce process-tree lifetime and committed-memory policy; they do
  not enforce database-byte or temporary-storage quotas.
- Direct and adversarial VFS observations cannot prove coverage of every native
  SQLite path on every future SQLite/APSW/Windows build.
- Creating a symbolic link was unavailable under the current Windows privilege.
  Fixed-path input and reparse-point rejection are source-enforced, but that
  particular native link creation was not observed.
- Official NSE F&O headers and format parity remain unproven. Generic synthetic
  fields were intentionally used.

## Historical evidence not rerun

R.9M/R.9N evidence, PDF v7, the 252-file research fingerprint and earlier
historical research artifacts were hash-checked, not regenerated. Real-data
suites were deliberately not run because they are outside this synthetic task.

## Verification

- Isolated native regression: 6 passed.
- Focused R.9J–R.9P root static/preservation suite: 52 passed, 1 skipped
  because Windows symbolic-link privilege was unavailable.
- JSON parsing, manifest hashes, privacy/secret scan, worker cleanup and Git
  whitespace checks passed.
- Root dependency declarations, PDF v7 and the production interlock source are
  byte-identical to their recorded hashes.

## Next routine engineering task

Build the provider-neutral synthetic ingestion and analytical pipeline: typed
generic input normalization, point-in-time validation, deterministic features
and outcomes, then known-answer backtest and walk-forward tests. Keep it
synthetic and non-production under the standing operating model.

`INTEGRATED_SYNTHETIC_BOUNDARY_ACCEPTANCE_PASSED_PRODUCTION_BLOCKED`
