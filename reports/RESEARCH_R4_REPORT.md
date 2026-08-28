# Research R.4 — Execution Path Closure and Approval Readiness

## Baseline and scope

R.4 continued from clean, synchronized `main` commit `e51e77d`. The work was
implemented without selecting, running, rerunning, interpreting or promoting a
trading hypothesis and without accessing any market, broker or external-data
network.

The two requested predecessor filenames that were absent were resolved to their
actual repository equivalents: `RESEARCH_SYSTEM_RECONCILIATION.md` and
`LEGACY_LOG_DIVERGENCE.md`. No replacement history was invented.

## Execution-path closure

The versioned inventory accounts for 60 Python executables and eight additional
callable/UI surfaces: two governed, 64 development-only, two deprecated and no
remaining unsafe bypass. `GovernedExecutionGateway.run` is the only path that
can start a future canonical attempt. The preview command is governed
administration and cannot execute.

All 50 Data-test executables cross the shared configuration boundary, which
emits a development-only warning and marker. Direct hypothesis-log writes add a
marker. The old momentum CLI fails before parsing/loading; direct compatibility
runner output is warned/marked and no longer updates its old SQLite catalog.
The call-stack convenience marker is not claimed as security enforcement: the
canonical importer independently rejects any output without exact family,
preregistration, approval, start/final events and bundle hashes.

## Approval boundary

R.4 added `governed_run_approval_v1`, immutable approval registration and
approval binding in authorization, start, root manifest and canonical import.
Templates, missing/unregistered/expired/altered/reused approvals and any family,
experiment, preregistration, input, dataset, split or runner mismatch fail
closed. Validation permission cannot expose test. Preflight does not consume;
`RUN_STARTED` is the single consumption event and every normally completed,
failed or aborted attempt retains its reference.

The one-attempt limit is enforced. Wall-time and memory are declared but not
enforced by the in-process runner; this is explicit in the approval, preflight,
manifest, contract and documentation as `DECLARED_NOT_ENFORCED`.

## Deterministic preflight

`preview_governed_run` and `scripts/preview_governed_run.py` report exact
identities/hashes, datasets, source/environment fingerprints, runner, split,
approval, destinations, blocking issues and `execution_permitted`. An explicit
evaluation timestamp makes expiry evaluation reproducible. Tests prove repeated
previews are identical and do not create directories, append events, consume
approval, import evidence or call a runner.

## Legacy divergence and protected evidence

The read-only recheck remains byte-identical to R.3: live sibling SHA-256
`1e26df878db4e33ffddbbd5882aba18053afee79e200d803e0a1401e54cc2514`,
34 rows, two post-freeze ungoverned IDs, one modified historical ID, and
classification `POST_FREEZE_UNGOVERNED_ROWS`. No row metrics were inspected,
imported or interpreted. The frozen 32-row snapshot and R.2/R.3 evidence remain
unchanged.

## Secondary findings

- Resource isolation is not implemented: wall-time and memory are operational
  declarations, not enforcement controls.
- The local hash chain makes changes detectable relative to preserved anchors;
  it cannot stop the filesystem owner from rewriting files.
- A crash after `RUN_STARTED` consumes approval and leaves a detectable,
  noncanonical incomplete attempt if no final manifest is written.
- R.4 authorizes no first real run and no promotion or actionable score.

## Files

Added approval, preflight and development-boundary modules; the preview command;
approval and inventory specifications; R.4 tests; and four reports. Updated the
R.3 gateway/catalog/root manifest, canonical importer, neutral exports, Data-test
configuration/log boundary, deprecated momentum paths and existing R.3 tests.
No protected fixture, hypothesis ledger, result artifact, historical trust
verdict, Kite contract or NSE response state was edited.

## Verification

- R.4 focused suite: **25 passed**.
- Combined R.3/R.4 governance suite: **55 passed**.
- Complete root suite: **191 passed**, with two expected development-boundary
  warnings from the synthetic compatibility-runner regression.
- Complete separate Data-test suite: **289 passed**, with five existing SWIG
  deprecation warnings and eleven expected noncanonical-log boundary warnings.
- JSON/specification/evidence/fixture parsing: **46 files valid**.
- Python compilation across `src`, `Data test/dtest`, `scripts`, `tools` and
  `tests`: **passed**.
- Executable inventory discovery equals the 60-path versioned allowlist; all
  eight callable entries exist and no `UNSAFE_BYPASS` remains.
- `git diff --check`: **passed** (Windows line-ending notices only).
- Protected-path diff against `e51e77d`: **empty**. Exact frozen, neutral,
  local-live, sibling-live, PDF, legacy-catalog and divergence hashes match R.3.

## Safest next milestone

R.5 should remain a no-execution first-run proposal review: prepare one
non-substantive candidate declaration from permitted data, estimate its actual
resource envelope, and ask the user to approve or reject that exact proposal.
Do not issue approval or execute until the user separately authorizes it.

## Primary decision

`GOVERNED_EXECUTION_PATH_READY_FOR_USER_APPROVAL`
