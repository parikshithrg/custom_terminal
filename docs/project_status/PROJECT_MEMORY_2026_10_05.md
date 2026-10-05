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
