# Linux Migration Validation

This repository uses Python **3.12.14** for the Windows-to-Linux reference
environment. Install the packages pinned in `requirements.lock`, then install
the local package:

```bash
python -m pip install -r requirements.lock
python -m pip install -e .
```

The external market-data snapshot is intentionally not discovered by filename
or location. Bind the exact copied snapshot on each machine before running a
research command or the migration validator:

```bash
export DTEST_PRICE_DIR=/data/terminal-builder/prices
export DTEST_FNO_DB=/data/terminal-builder/fno.db
export DTEST_INDUSTRY_MAP=/data/terminal-builder/nifty500.csv
export DTEST_ARTIFACTS_DIR=/var/tmp/terminal-builder/artifacts
export DTEST_RUNS_DIR=/var/tmp/terminal-builder/runs
```

Do not point these variables at a similar, refreshed, or partial dataset. The
expected file inventory and hashes are declared in
`config/data_snapshot_manifest.json`.

Run the full migration gate from a clean checkout:

```bash
python scripts/validate_environment.py
```

It checks the selected Python version, every locked package, clean Git state,
the required bindings, the full price-data inventory, exact database and map
hashes, read-only SQLite integrity, tracked Parquet readability, and both test
suites. It writes an ignored validation record under `artifacts/`.

`--quick`, `--skip-tests`, and `--allow-dirty` are development diagnostics
only. They intentionally cannot produce an operational PASS.
