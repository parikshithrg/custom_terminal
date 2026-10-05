# Project memory and Linux handoff — 2026-10-05

This is the durable restart note for `custom_terminal` after the decision to
replace the Windows installation with Linux. It records migration state and is
not permission to access providers, acquire data, run research, generate a
recommendation, or trade.

## Latest completed checkpoint

- Branch: `main`
- Linux-readiness safeguards: committed and pushed as `15d9ee4` (`Add Linux
  migration readiness safeguards`).
- GitHub is the source for code, documentation, tests, pinned dependency lock,
  migration validator, and the snapshot identity manifest.
- The planned Linux reference runtime is Python `3.12.14`.

## What is deliberately outside GitHub

The following must be restored from the verified external backup, not
redownloaded or substituted:

- 430 daily price CSV files;
- F&O SQLite database (`fno.db`, about 45 GB);
- `nifty500.csv` industry/universe map;
- `Data test/data/` historical evidence datasets;
- owner-selected governed/research artifacts that are not regenerable.

The expected identities for the first three inputs are frozen in
`config/data_snapshot_manifest.json`. The backup must be copied and verified
before any research action. Do not migrate `.venv`, temporary test directories,
Python bytecode, or regenerable caches.

## Linux restore procedure

1. Install Ubuntu and the ChatGPT desktop app, then sign in with the owner’s
   account.
2. Use `LINUX_RESTORE_CODEX_PROMPT.md` as the first prompt in a new Codex chat.
3. Restore only the exact external data snapshot, configure non-secret
   `DTEST_*` path bindings, create the pinned Python environment, and run
   `python scripts/validate_environment.py`.
4. Resume project work only after the validator reports `OPERATIONAL`.

## Boundaries retained after migration

- The application remains analysis-only; no order execution is allowed.
- Do not carry over or save Kite credentials, request tokens, access tokens,
  cookies, or API secrets. Authenticate manually again when separately needed.
- Do not use fresh/current provider data as a substitute for historical
  point-in-time inputs.
- Existing evidence and immutable artifacts must remain byte-for-byte unchanged.
- A quick validator mode, skipped tests, a dirty Git tree, or a hash mismatch is
  not a completed migration.

## First decision after a successful restore

Read the latest repository status and owner-development sequence before any
implementation. Confirm the next owner-approved milestone; Linux restoration
itself does not broaden project scope.

## Final Windows handoff — continuation context

This note preserves the working context from the final Windows Codex chat so a
new Linux Codex chat can continue without relying on the old local session.

### Final repository state

- Latest pushed commit: `357bd9d` — `Add Linux restore handoff PDF`.
- The Windows working tree was clean immediately after that push.
- The Linux restore prompt is at
  `docs/project_status/LINUX_RESTORE_CODEX_PROMPT.md`.
- The upload-ready handoff PDF is at
  `output/pdf/linux_restore_codex_prompt.pdf`.
- The current migration assessment is documented in
  `docs/linux_readiness_report.md`.

### Validation carried out before the handoff

- Portability tests, golden-fixture tests, Data Test configuration tests, the
  Data Test suite, Python compilation, dependency consistency, snapshot
  identities, and Parquet readability were checked successfully during the
  Windows handoff work.
- A full root-test collection discovered 1,561 tests. The full root execution
  progressed beyond the earlier OneDrive temporary-directory issue, but did
  not complete inside a bounded interactive window.
- The final strict migration validator was started against the restored 45 GB
  F&O SQLite database. Its full integrity scan remained silent beyond the
  reasonable interactive window and was interrupted. This is **pending**, not
  a validation pass or a data-integrity failure.
- On Linux, run the strict validator without quick/skip flags and allow ample
  time for the F&O SQLite integrity phase. Continue normal project work only
  after it reports `OPERATIONAL`.

### Project direction to retain

- PG-terminal remains a local, analysis-only decision-support workspace;
  it must not place orders or retain broker credentials/tokens.
- The focus is actionable long/short research across indices, sectors, and the
  210 liquid F&O stocks, rather than a single overall-market call.
- Market Sentiment should tell a top-to-bottom story: regime score and its
  walk-forward evidence, index regimes, sector regimes, then stock/F&O
  follow-through. Validate signals across supported indices where history is
  sufficient; auto-populate analyses after 252 completed sessions.
- Dashboard should become a concise summary with one section per workspace
  page. Portfolio Analysis is intended to use Market Sentiment and
  Seasonality inputs, accept CSV/XLSX portfolio uploads, and offer allocation
  guidance as analysis rather than trading instructions.
- Seasonality research uses rolling 10-year EOD history. Its interpretation
  must remain evidence-led: sample size, effect size, statistical significance,
  and walk-forward behaviour matter more than a calendar pattern alone.

### First Linux-chat instruction

Start by reading this document and `LINUX_RESTORE_CODEX_PROMPT.md`, restore and
validate the external snapshot, inspect `git log` and current project status,
then ask the owner which approved milestone to implement next. Do not silently
resume provider access, data downloads, or market-analysis jobs during setup.
