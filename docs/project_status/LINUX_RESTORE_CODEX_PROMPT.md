# Linux restore prompt for Codex

Paste the following into a new Codex chat after Ubuntu and the ChatGPT desktop
app are installed, the external backup drive is connected, and you have opened
this repository's GitHub page or have its URL available.

```text
I am restoring the `custom_terminal` project onto this Linux machine after a
full Windows replacement. Work carefully and preserve the existing research and
data contracts.

My verified external backup is mounted at: <BACKUP_ROOT>
Restore project data beneath: <LINUX_DATA_ROOT>
Restore the Git repository beneath: <LINUX_CODE_ROOT>

Your task is to restore a working local development environment only. Do not
redesign the project, change strategy or research logic, acquire fresh market
data, call Kite/NSE/other market APIs, run a live Kite login, start a backtest,
produce a trading recommendation, or delete/overwrite any data without asking
me first.

Follow this sequence:

1. Clone `https://github.com/parikshithrg/custom_terminal.git` into
   `<LINUX_CODE_ROOT>/custom_terminal`. Record the checked-out commit and ensure
   the repository is clean. Read, in this order:
   - `docs/project_status/PROJECT_MEMORY_2026_10_05.md`
   - `docs/linux_migration.md`
   - `docs/linux_readiness_report.md`
   - `config/data_snapshot_manifest.json`

2. Verify the required backup content exists before copying anything:
   - 430 `*_DAILY.csv` price files;
   - `fno.db` (about 45 GB);
   - `nifty500.csv`;
   - `Data test/data/`;
   - any owner-selected governed/research artifacts that must be retained.
   GitHub does not contain these external datasets. Never substitute a newer,
   similar, partial, or automatically downloaded dataset.

3. Copy the verified external datasets to `<LINUX_DATA_ROOT>` using a
   resumable, binary-safe method. Do not copy Windows `.venv`, `.pytest_tmp*`,
   Python bytecode, or regenerable caches. Compare the copied data with
   `config/data_snapshot_manifest.json`: price-file count, price inventory hash,
   industry-map size/hash, and F&O database size/hash must match exactly.
   Open the F&O database read-only only; do not write, migrate, vacuum, or alter
   it.

4. Establish the exact project Python baseline, `3.12.14`. If the Linux system
   Python is different, install an isolated user-local Python 3.12.14 first;
   do not silently use another minor or patch version. Create `.venv` inside the
   clone with that exact interpreter, activate it, and install only the pinned
   project environment:

   <python-3.12.14> -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.lock
   python -m pip install -e .

   Install ordinary system prerequisites only when needed and explain any
   administrator-level action before requesting it.

5. Create a non-secret local path file at
   `~/.config/terminal-builder/data-paths.sh` with these exports, adjusted to
   the restored Linux paths:

   export DTEST_PRICE_DIR="<LINUX_DATA_ROOT>/prices"
   export DTEST_FNO_DB="<LINUX_DATA_ROOT>/fno.db"
   export DTEST_INDUSTRY_MAP="<LINUX_DATA_ROOT>/nifty500.csv"
   export DTEST_ARTIFACTS_DIR="<LINUX_DATA_ROOT>/artifacts"
   export DTEST_RUNS_DIR="<LINUX_DATA_ROOT>/runs"

   This file must contain paths only. Do not add Kite credentials, tokens,
   API keys, cookies, or other secrets. Source it only for this project.

6. From the clean repository, activate `.venv`, source the path file, and run:

   python scripts/validate_environment.py

   Keep the generated ignored validation record. Report every check, especially
   Python version, package lock, data hashes, SQLite quick check, Parquet reads,
   and both test suites. If any check fails, stop before research work and
   explain the smallest safe correction.

7. If and only if the validator reports `OPERATIONAL`, show me a concise restore
   report: checked-out commit, dataset identities, validation result, any
   non-destructive setup actions performed, and the next pending project
   milestone. Then wait for my approval before making product, research, or
   provider changes.

Important boundaries:
- The product is analysis-only and must never place, modify, or cancel trades.
- Current Kite access is transient and must be authenticated again manually;
  old Windows tokens must not be copied.
- Existing historical artifacts are evidence. Preserve them byte-for-byte.
- Do not claim Linux readiness from a quick/partial validation run.
```
