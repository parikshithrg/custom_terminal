# Linux Readiness Audit

Audit date: 05-Oct-26  
Repository: `custom_terminal` (local checkout folder: `custon_new_terminal`)  
Branch: `main`  
Audited commit: `60b94c03f4dc7cc997a3ad6e93d0348a6a96e269`  
Audit scope: Phase 1 only; no production code, research code, datasets, configuration, or experiment output was changed.

## Executive Summary

**Status: NOT READY**

The repository is close to being portable, but a fresh Linux clone cannot currently reproduce the Windows research environment without manual knowledge that is not captured by Git:

1. The canonical legacy research configuration contains Windows-only absolute paths, and those paths are stale even on the audited Windows machine. The required files currently live under `02 Reference Projects/Dashboard`, not the configured `Desktop/Dashboard` location.
2. Existing run manifests persist hundreds of absolute Windows source paths. The local SQLite run catalog also stores Windows backslashes. These values would change or stop resolving on Linux and therefore break artifact equivalence or lookup.
3. The environment definition is split between an exact research `pyproject.toml`/partial `requirements.lock` and an unpinned UI `requirements.txt`. The current environment cannot be recreated from one locked input. The current virtual environment is Python 3.12.14, while a prior stored run records Python 3.14.6 and Ubuntu 26.04 defaults to Python 3.14.
4. There is no clean-machine validation entry point, and the standard root test command cannot presently complete from the OneDrive checkout because old `.pytest_tmp` directories are permission-locked. A migration reference must be captured from a clean Windows test location before the Linux result can be judged equivalent.

These are bounded portability and reproducibility problems, not reasons to redesign the project. The core research implementation is substantially portable: it uses `pathlib`, sorts important file discovery, uses stable tie-breaking in the strategy path, seeds stochastic work, uses IANA timezones (`Asia/Kolkata`) and UTC in core temporal contracts, and has tracked Parquet golden fixtures.

**Recommendation: CONDITIONAL GO — fix the four P0 blockers first.**

## Audit Method and Observed Baseline

- Inspected all 1,213 tracked files plus local data, artifact, environment, test, documentation, and automation areas.
- Checked active Python, configuration, tests, reports, manifests, Git attributes/ignore rules, SQLite schemas, and representative Parquet schemas.
- Searched tracked and active files for drive letters, Windows homes, `AppData`, backslash paths, Windows executables, subprocesses, native APIs, and working-directory assumptions.
- Checked tracked paths case-insensitively: **no case-colliding filenames** were found.
- Checked Git modes: all 1,213 tracked files are mode `100644`; there are currently no executable scripts.
- Inspected the external 48.35 GB SQLite database in read-only mode. It has 19 tables and no path/location columns in its schema.
- Inspected `artifacts/catalog.sqlite`: it contains relative manifest paths written with Windows backslashes.
- Read representative tracked Parquet files with PyArrow 23.0.1. They use SNAPPY compression, portable Arrow types, UTC-aware event timestamps where required, and naive session-date timestamps where the schema intentionally represents a date/session rather than an instant.
- `pip check`: **PASS** in the existing virtual environment.
- Root test collection: **1,558 tests**.
- Standard root run: **not a valid baseline**. It stopped after 1 pass and 1 setup error because `.pytest_tmp/root` could not be removed (`WinError 5`). A fresh-base attempt advanced beyond the initial tests but did not produce a reliable final summary in the constrained audit host, so no pass count is claimed.
- Deterministic core subset (`golden_fixture`, temporal contracts, historical universe, walk-forward): **6 passed, 0 failed, 0 skipped**.
- Separate legacy `Data test` suite: **289 passed, 0 failed, 0 skipped** (11 expected development-only runtime warnings, plus PyMuPDF/SWIG deprecation warnings).
- No committed credential value was found by the targeted secret scan. `.streamlit/secrets.toml` is ignored. There is no `.env.example`.

## Migration Blockers

| Issue | File(s) | Why it matters | Severity | Recommended fix | Estimated effort |
|---|---|---|---|---|---|
| Required research inputs use stale Windows absolute paths | `Data test/config/config.toml:22-24,84`; loader in `Data test/dtest/config.py` | Linux cannot resolve `C:/Users/...`. The configured Windows paths are also absent on the current machine; the actual source is under `02 Reference Projects/Dashboard`. A wrong replacement can silently change the input snapshot. | P0 / BLOCKER | Add explicit per-machine bindings for price data, F&O DB, industry map, artifact root, and runs root. Keep the tracked config semantic and non-secret. Validate existence plus content identity before any run. Do not auto-discover a “similar” dataset. | 2-3 hours |
| Artifact identity includes host-specific paths | Existing ignored run manifests under `artifacts/runs/**/manifest.json`; `artifacts/catalog.sqlite` | Existing manifests contain `C:\Users\...\Dashboard\data\...`. Re-running on Linux necessarily changes those strings and therefore can change manifest or reproducible hashes even when data bytes are identical. The catalog uses `artifacts\runs\...`, which is not a Linux path. | P0 / BLOCKER | Define platform-neutral dataset identity: dataset ID + content hash + POSIX relative logical names. Keep the original Windows path only as non-canonical provenance if needed. Write new catalog paths with `/`; on read, normalize historical `\` entries. Preserve existing artifacts byte-for-byte as historical evidence. | 2-4 hours |
| No single reproducible Python environment | `pyproject.toml`, `requirements.lock`, `requirements.txt` | Core research packages are pinned, but the lock omits the UI stack. UI requirements are ranges. The installed environment differs from `requirements.lock` and includes transitive packages not captured there. Python is specified only as `>=3.12`; current Windows is 3.12.14, an existing manifest records 3.14.6, and Ubuntu 26.04 defaults to 3.14. | P0 / BLOCKER | Choose and record one Python minor for the migration reference, then generate one complete lock for research + UI + tests on that minor. Fastest Ubuntu path is Python 3.14, but only after producing the Windows reference with the same minor and confirming the golden/reference experiment. Do not copy `.venv`. | 2-4 hours |
| No clean Windows baseline and no one-command Linux validator | `pyproject.toml` pytest `--basetemp=.pytest_tmp/root`; no `scripts/validate_environment.py` | Linux equivalence cannot be declared if the Windows side has no clean final test/reference result. OneDrive/old test directories currently block the standard command. | P0 / BLOCKER | Run the baseline from a clean non-OneDrive temp root, save JUnit/summary plus reference hashes, and add the validator proposed below. The validator must use a fresh OS temp directory and never reuse `.pytest_tmp/root`. | 2-3 hours plus test runtime |

## Non-blocking Improvements

### P1 — FIX DURING MIGRATION

1. **Provide a non-secret local configuration template.** Add `.env.example` or an equivalent documented `config.local.toml.example` containing only variable names/placeholders for data roots. Keep Kite tokens out of files; the current Streamlit session-memory behavior is appropriate.
2. **Add `scripts/bootstrap_linux.sh`.** It should create a fresh environment, install the complete lock, validate configuration, and call the validation entry point. It must not download market data or invent missing paths.
3. **Fix hidden/legacy cross-project imports.** `views/_blackswan_data.py:60` and `views/td_trade_management.py:29` hard-code `C:\Users\parik\OneDrive\Desktop\Dashboard`. Both are currently hidden or legacy paths, so they do not block the present routed application, but they will fail if re-enabled.
4. **Make the fixture builder portable.** `tools/build_golden_fixture.py:40` points to the old Windows Dashboard data folder. Accept an explicit validated input directory instead. Do not rebuild the tracked golden fixture as part of migration.
5. **Make optional PDF generation explicit.** `Data test/scripts/build_hypothesis_report_pdf.py:151` embeds a Windows path, and `reportlab` is imported by reporting scripts but absent from both declared dependency sets and the current environment. Put it in an optional `report` extra if those generators must run on Linux.
6. **Classify Windows-native historical investigations.** `tools/r9k_windows_feasibility.py` intentionally uses Win32 APIs; `tools/r9p_integrated.py` uses Win32 job/process APIs and an APSW `win32` VFS. Keep their recorded evidence, skip their runtime probes on Linux, and make the skip/report explicit. Do not port these historical experiments unless they become an active production requirement.
7. **Remove host-local time from legacy UI/data helpers.** `views/_blackswan_data.py` and `views/_news_data.py` use naive `datetime.now()`. `tools/download_nse_fno_reports.py` and the quarantine retention helper use `date.today()`. Use an explicit `Asia/Kolkata` or UTC clock at the boundary so Linux host timezone cannot change a session date.
8. **Document Linux commands.** README operational examples are PowerShell-only (`.venv\Scripts\python.exe`, `$env:PYTHONPATH`). Add Bash equivalents without removing Windows instructions.

### P2 — AFTER MIGRATION

1. Add Linux CI for the root suite, legacy suite, golden fixture, SQLite read-only check, and Parquet schema/hash check.
2. Add `* text=auto eol=lf` (with existing evidence-specific exceptions preserved) and set the executable bit on future `.sh` files.
3. Clean or archive ignored `.pytest_tmp*`, `artifacts/pytest-*`, `artifacts/r10*_tmp`, local caches, `Local Terminal/`, and `Local Terminal.zip` after verified migration. Do not delete governed evidence indiscriminately.
4. Add a deterministic-order lint/test for the few non-sorted filesystem iterations (`official_http.py`, canary/audit inventory helpers). Core strategy discovery is already sorted.
5. Split optional dependencies into named extras such as `ui`, `test`, `report`, and `windows-investigation` while preserving one generated lock.
6. After byte/hash verification, remove duplicate external 45 GB F&O database copies or move them into a documented backup policy. Do not do this during the initial migration.

## Data Migration Inventory

| Data | Location | Size | Migrate? | Regenerable? | Risk |
|---|---|---:|---|---|---|
| Git repository and tracked fixtures/evidence | Git remote + current checkout | `.git` 55.19 MiB; tracked working content is well below 0.5 GiB | Yes, by clone at audited commit | Yes from Git | LOW once commit is fixed |
| Daily price CSV collection (430 files) | `C:\Users\parik\OneDrive\Desktop\02 Reference Projects\Dashboard\data` | 77.43 MiB | **MUST MIGRATE** | Not safely from current repository alone | HIGH: wrong folder changes universe/features |
| F&O SQLite database | `...\02 Reference Projects\Dashboard\fno.db` | 48,345,137,152 bytes / 46,105.52 MiB | **MUST MIGRATE** if F&O work is required | Not safely/quickly regenerable | CRITICAL: largest transfer; hash before/after |
| Industry/universe map | `...\02 Reference Projects\Dashboard\market_gate\data\nifty500.csv` | 5,630 bytes | **MUST MIGRATE** | Possibly reacquirable, but use the exact audited bytes | HIGH: membership changes results |
| Acquired fundamentals | `Data test/data/fundamentals` | 8.04 MiB | **MUST MIGRATE** | Not assumed | HIGH: point-in-time filing history |
| Index reconstitution evidence | `Data test/data/index_reconstitution` | 2.69 MiB | **MUST MIGRATE** | Not assumed | HIGH: historical membership |
| Insider-trading disclosures | `Data test/data/insider_trading` | 39.38 MiB | **MUST MIGRATE** | Not assumed | HIGH: historical PIT evidence |
| Macro series | `Data test/data/macro` | 2.85 MiB | **MUST MIGRATE** | Technically reacquirable but would create a new snapshot | MEDIUM |
| Shareholding history | `Data test/data/shareholding` | 1.08 MiB | **MUST MIGRATE** | Not assumed | HIGH: historical PIT evidence |
| Tracked sentiment log | `data/sentiment_history.csv` | <0.01 MiB | Via Git | Yes only by changing history, so preserve | LOW |
| Selected governed/local research evidence and reference runs | ignored `artifacts/governed_research`, `artifacts/governance_ceremonies`, `artifacts/runs`, relevant raw/qualification folders | Included in 347.27 MiB total local `artifacts/` | **MUST MIGRATE selectively**, with inventory and hashes | Some are not regenerable without consuming approvals or reacquiring data | HIGH |
| Test-generated artifacts/caches | `artifacts/pytest-*`, `artifacts/r10*_tmp`, `.pytest_tmp*`, `.pytest_cache` | Large share of 347.27 MiB artifacts; exact split not needed for migration | SHOULD NOT MIGRATE | Yes | LOW; stale locks currently disrupt tests |
| Derived bhav/parquet caches and legacy run outputs | configured artifact root; `Data test/runs` | Local and ignored; included in `Data test` total 89.87 MiB where present | Migrate only reference outputs; regenerate caches after validation | Usually yes from exact inputs | MEDIUM |
| Local SQLite run catalog | `artifacts/catalog.sqlite` | 12 KiB | Prefer regenerate after path fix | Yes | MEDIUM: contains Windows separators |
| Tracked research Parquet evidence | `docs/investigations/**`, `tests/fixtures/**`, tracked `artifacts/data_audit/**` | Included in Git | Via Git | Yes from Git | LOW; verify hashes/readability |
| Python virtual environment | `.venv` | 582.37 MiB | **SHOULD NOT MIGRATE** | Yes from complete lock | HIGH if copied; venvs are platform-specific |
| Imported reference tree and ZIP | `Local Terminal/` 106.22 MiB; `Local Terminal.zip` about 37.9 MiB | 144+ MiB | SHOULD NOT MIGRATE with operational environment; archive separately if wanted | Reference-only | LOW |
| Output PDFs/images | `output/` | 2.59 MiB | Tracked items arrive via Git; copy ignored owner artifacts if needed | Some can regenerate, some are signed-off evidence | MEDIUM |

### Required transfer procedure

1. Freeze writes to the source datasets and databases.
2. Record SHA-256, byte size, and relative logical name for every mandatory file; for the 430 CSVs also record a sorted inventory hash.
3. Copy to Linux using a resumable binary-safe tool.
4. Recompute SHA-256 and byte size on Linux before configuring the application.
5. Open SQLite strictly read-only and run `PRAGMA quick_check`; do not let WAL/journal sidecars accompany a supposedly quiescent snapshot unless they are part of a deliberately captured consistent copy.
6. Read every required Parquet footer/schema and compare logical table hashes before any experiment runs.

## Dependency Assessment

| Dependency | Current version | Linux support | Action |
|---|---:|---|---|
| Python | 3.12.14 active; 3.14.6 in an existing run manifest; project says `>=3.12` | Yes; Ubuntu 26.04 default is 3.14 | P0: select one minor/patch baseline and record it |
| NumPy | 2.5.1 | Linux wheels; compiled numerical code | Keep exact; compare numerical outputs |
| pandas | 3.0.3 | Linux wheels | Keep exact |
| SciPy | 1.17.1 | Linux wheels; BLAS backend can differ | Keep exact; tolerance-check statistical floats |
| PyArrow | 23.0.1 | Linux wheels | Keep exact; compare logical tables, not only Parquet container bytes |
| DuckDB | 1.4.4 | Linux wheels | Keep exact |
| beautifulsoup4 | 4.15.0 | Pure Python | Keep exact |
| PyMuPDF | 1.26.4 | Linux wheels | Keep exact; no GUI package required for current headless extraction/tests |
| requests | 2.34.2 installed; partial lock says 2.34.2 | Cross-platform | Keep exact with CA certificates |
| pytest | 9.0.2 | Cross-platform | Keep exact; move basetemp outside synced checkout |
| Streamlit | 1.64.0 installed; declared `>=1.60.0` | Cross-platform | Pin exact in complete lock |
| feedparser | 6.0.14 installed; declared `>=6.0.0` | Cross-platform | Pin exact |
| yfinance | 1.7.0 installed; declared `>=0.2.0` | Cross-platform; network behavior is not deterministic research input | Pin exact; keep live UI separate from reference experiment |
| PyYAML | 6.0.3 installed; declared `>=6.0` | Linux wheels | Pin exact |
| vaderSentiment | 3.3.2 | Pure Python | Pin exact |
| ReportLab | Not installed or declared | Linux-supported | Add optional `report` extra only if PDF generators are required |
| APSW | Not installed or production-declared | Linux-supported generally, but project probes hard-code Windows VFS behavior | Do not add to production/bootstrap; historical Windows investigation only |
| SQLite | Python stdlib runtime | Portable database format | Use read-only URI for source DB; validate SQLite runtime version and quick check |

The existing `requirements.lock` is not a full environment lock: installed `idna`, `urllib3`, and `tzdata` already differ, and the complete Streamlit/UI dependency graph is absent. `requirements.txt` and `pyproject.toml` are both needed today, so neither alone recreates the audited environment.

## Windows-specific Code

| File | Line/Area | Issue | Severity | Proposed fix |
|---|---:|---|---|---|
| `Data test/config/config.toml` | 22-24 | Required price, F&O DB, and industry map use `C:/Users/.../Dashboard` | BLOCKER | Bind per-machine locations without changing semantic config |
| `Data test/config/config.toml` | 84 | Derived cache defaults to `C:/Users/.../AppData/Local` | SHOULD FIX | Existing `DTEST_ARTIFACTS_DIR` works; document Linux value and include in template |
| `tools/build_golden_fixture.py` | 40 | Golden-source folder hard-coded to Windows | SHOULD FIX | Require explicit input root and identity check |
| `views/_blackswan_data.py` | 60 | Windows Dashboard path inserted into `sys.path` | SHOULD FIX | Package/import the dependency or use validated configured project root; currently legacy/hidden |
| `views/td_trade_management.py` | 29 | Same Windows cross-project import | SHOULD FIX | Same; page currently hidden |
| `Data test/scripts/build_hypothesis_report_pdf.py` | 151 | Windows path embedded into generated PDF text | SHOULD FIX | Derive a platform-neutral project label; do not include host path |
| `tools/r9k_windows_feasibility.py` | module | Deliberate Win32 ctypes/process/job/file-lock experiment | HARMLESS for Linux operations | Preserve evidence; mark runtime test Windows-only |
| `tools/r9p_integrated.py` | process supervision and descendant test | Win32 `CREATE_NO_WINDOW`, `CreateProcessW`, Job Objects | HARMLESS for current production; SHOULD FIX if rerun is required | Do not run on Linux; document as archived Windows-only research probe |
| `tools/r9m_vfs_evaluation.py`, `tools/r9n_adversarial.py`, `tools/r9p_integrated.py` | APSW VFS base | Hard-coded APSW VFS name `win32` | HARMLESS for current production | Archived/restricted experiment; no Linux bootstrap dependency |
| `README.md`, experiment plans/manifests | command examples | PowerShell syntax and `.venv\Scripts\python.exe` | SHOULD FIX | Add Bash/Linux equivalents; historical manifests remain immutable |
| Tests containing `C:\Users`, `D:\private`, `/home/` | test fixtures/redaction assertions | Deliberate adversarial examples, not operational paths | HARMLESS | Keep unchanged |
| Historical JSON/PDF/evidence mentioning Windows commands | recorded evidence | Immutable record of Windows execution | HARMLESS | Keep unchanged; do not rewrite hashes |

There are no tracked UNC operational paths and no tracked filenames that differ only by capitalization.

## SQLite Portability

- SQLite database bytes are platform-independent and the external `fno.db` can be copied to Linux if it is captured while quiescent and verifies by hash plus `PRAGMA quick_check`.
- The external F&O DB schema has 19 tables and no columns named like path/file/directory/location/URI. No schema-level persisted Windows path was found.
- Research readers use SQLite URI read-only mode in the legacy F&O loaders. Preserve that behavior.
- `artifacts/catalog.sqlite` has one `runs` table whose `manifest_path` rows use Windows backslashes. This catalog should be regenerated or normalized after the path-contract fix; copying it unchanged is not useful on Linux.
- WAL-enabled governance databases must be migrated as consistent snapshots. Copying only the main file while a writer is active can lose committed WAL content.
- Do not place the 48 GB read-mostly database in a cloud-synced live-write directory.

## Parquet Portability

- Tracked and local files are readable with pandas/PyArrow 23.0.1 and use SNAPPY, a Linux-supported codec included in PyArrow wheels.
- Core code uses pandas `read_parquet`/`to_parquet`; Polars is not used. DuckDB is present but is not the Parquet write engine in the core artifact writer.
- Representative schemas use explicit UTC-aware timestamps for instants and timestamp/date-like session fields for exchange sessions. This is portable if the same schema and package versions are used.
- Absolute paths were found in JSON run manifests, not in the representative Parquet schemas inspected.
- Exact Parquet bytes should be preserved for copied historical evidence. For new Windows-versus-Linux runs, compare Arrow schema, row count, ordered logical content hash, null pattern, and values. Raw Parquet byte equality is desirable but should not be the sole equivalence rule because container metadata/encoding can vary by build.

## Time and Timezone Behavior

### Good

- Core exchange calendar and research contracts use `Asia/Kolkata` through `zoneinfo` and convert instants to UTC.
- Synthetic and canonical evidence uses UTC-aware `datetime.now(timezone.utc)` for audit timestamps.
- The legacy deterministic harness fixes `meta.as_of = 2026-08-13`; train/validation/test windows do not depend on the host clock.

### Risks

- Legacy UI helpers use naive `datetime.now()` and `datetime.now().date()`. A Linux host configured to UTC can produce a different India calendar day near midnight and can shift UI lookback cutoffs.
- Two operational tools use `date.today()` for future-date/retention decisions. That is acceptable only if the intended clock is documented; otherwise bind it explicitly.
- Naive CSV date parsing is acceptable for session dates but must never be treated as an instant without localizing to the declared exchange timezone.

The Linux host timezone need not be globally changed if all application boundaries are explicit. The validator should nevertheless prove that `ZoneInfo("Asia/Kolkata")` loads and that known session-open conversions match the tracked tests.

## Reproducibility Risks

### CRITICAL

- Different or missing external data because paths are not portable and the tracked paths are stale.
- Existing run/artifact hashes include absolute Windows path strings.

### HIGH

- Incomplete environment lock and no selected Python baseline.
- No clean full Windows test/reference result against which Linux can be compared.
- Copying an active SQLite/WAL database without a consistent snapshot.
- Failing to migrate the acquired point-in-time datasets that cannot be reconstructed safely from the repository.

### MEDIUM

- SciPy/NumPy floating-point differences from Python/BLAS/platform changes near signal thresholds.
- Naive host-local dates in legacy UI and operational helpers.
- A few filesystem iterations are not explicitly sorted, although core price discovery and strategy ranking are deterministic.
- The local catalog uses Windows separators.
- Linux will skip deliberate Win32-native R.9K runtime probes; the expected skip set must be documented rather than treated as an unexplained coverage loss.

### LOW

- Mixed Windows working-tree line endings. Git index content is predominantly LF and evidence-specific `-text` rules preserve immutable bytes.
- The repository folder contains a space-bearing legacy project (`Data test`). Quoting is required, but Linux supports it.
- No capitalization collisions were found.

## Determinism Assessment

- Randomized analytical components use explicit seeds (`default_rng(42)` or passed seeds); the legacy harness also sets Python and NumPy seeds.
- Price/universe discovery is sorted. Momentum ranking uses a stable sort with `instrument_id` as a deterministic tie-breaker.
- Important data frames are explicitly sorted before hashing/output.
- The full environment, Python version, BLAS/runtime identity, and locale are not currently locked by one bootstrap input.
- The validator should set `PYTHONHASHSEED=0`, `TZ=Asia/Kolkata` for host-clock-sensitive smoke tests, and a UTF-8 locale (`C.UTF-8`), while core research should continue to use explicit clocks rather than depend on these settings.
- Compare boundary decisions (universe membership, ranks at cutoffs, signals, fills) exactly. A tiny numerical difference is not acceptable if it changes a discrete decision even when aggregate metrics are close.

## Existing Tests

| Suite | Collected | Passed | Failed/Error | Skipped | Audit conclusion |
|---|---:|---:|---:|---:|---|
| Root suite | 1,558 | Not claimed | Standard command stopped after 1 pass with 1 basetemp setup error | Not reached | Baseline blocked by stale permission-locked `.pytest_tmp` state; rerun cleanly before migration |
| Deterministic cross-platform core subset | 6 | 6 | 0 | 0 | PASS |
| Legacy `Data test` suite | 289 | 289 | 0 | 0 | PASS |

The root suite includes useful cross-platform determinism coverage (golden feature hash, temporal contracts, historical universe, stable ranking, walk-forward purging/embargo, artifact hashes, and platform-aware Windows probe skips). It does not yet provide one Linux migration acceptance test that binds environment + external dataset inventory + full reference output.

Minimum additional tests before declaring Linux operational:

1. Same complete dependency lock installs on a clean Windows reference and Linux target.
2. Mandatory external-file inventory hashes match exactly.
3. Golden fixture checks all intended features, ranks/signals, outcomes/trades, and metrics, not only the current legacy feature hash.
4. Reference experiment produces exact discrete decisions and schema/logical hashes, with documented tolerance only for continuous floating outputs.
5. SQLite copy opens read-only, passes quick check, and returns fixed schema/table counts.
6. All required Parquet files read and match schema, row count, and logical hash.
7. Timezone boundary tests pass with the Linux host set to both UTC and Asia/Kolkata.
8. Expected Linux skips are enumerated; unexpected skips fail validation.

## Reference Experiment

Use the tracked **`momentum_golden_v1` 12-1 momentum vertical slice** as the first Windows-to-Linux reference because it is small, committed, offline, deterministic, and already has source hashes and expected research facts:

- Fixture: `tests/fixtures/momentum_golden_v1/`
- Current test: `tests/test_golden_fixture.py`
- Expected contract: `tests/fixtures/momentum_golden_v1/expected.json`
- Symbols: the eight tracked equities in `expected.json`
- Benchmark: tracked NIFTY 50 fixture
- Window: 2013-01-01 through 2016-12-31
- Existing exact feature hash: use the actual value already stored in `expected.json`; do not replace it during migration.

### Comparison contract

Compare exactly:

- Git commit and clean/dirty state.
- Python and package versions.
- Every input file SHA-256 and the sorted inventory hash.
- Experiment definition/config canonical JSON.
- Arrow schemas, column order, row counts, date/session keys, symbol/instrument IDs, universe membership, ranks, selected signal rows, trade identifiers, entry/exit dates, reasons, share counts, and null patterns.
- Existing expected hashes and any existing canonical logical table hashes.
- Manifest dataset IDs, content hashes, parser/feature/outcome/cost/universe versions, and artifact inventory.

Compare with numerical tolerance:

- Floating feature values, returns, prices derived through floating arithmetic, statistical metrics, and portfolio/equity values: start with `rtol=1e-12`, `atol=1e-12` for 64-bit outputs. Any failure requires investigation; do not widen tolerance merely to pass.
- No tolerance is permitted when a difference changes ordering, a threshold decision, a signal, a trade, a cost bracket, or a reported count.

Do not require new Parquet container bytes to match if logical content/schema match and the writer build records different non-semantic metadata. Copied historical Parquet files must remain byte-identical.

After the golden slice passes, perform one full governed/reference run against the exact migrated 430-file price snapshot. Existing local momentum manifests are useful evidence but are not sufficient as the migration oracle because they contain `NO_GIT_METADATA`, dirty-worktree state, platform-specific source paths, and mixed Python versions.

## Git Portability

- `.gitignore` correctly excludes `.venv`, Python caches, pytest caches/temp roots, Streamlit secrets, generated artifacts, local DB/SQLite files, legacy imported source, and large legacy data/run outputs.
- No tracked `.venv`, `__pycache__`, `.pytest_cache`, `.pyc`, IDE cache, log, build, or dist path was found.
- No case-insensitive filename collisions were found.
- No Git LFS pointer configuration was found. The 48 tracked Parquet files are small evidence/fixture files and do not currently require LFS.
- `.gitattributes` marks binary formats correctly and deliberately preserves historical evidence bytes. It does not define a repository-wide LF policy.
- All tracked files are `100644`; a future bootstrap script must be committed executable (`100755`).
- Historical evidence that intentionally records CRLF or Windows command lines must not be normalized, because tests bind some evidence byte-for-byte.

## Required Linux Packages

For Ubuntu 26.04, the minimal justified OS installation is:

```bash
sudo apt update
sudo apt install --yes git python3 python3-venv python3-pip ca-certificates
```

Ubuntu 26.04's default `python3` is 3.14. The project must first decide whether to use that baseline or install a separately managed exact Python matching the Windows reference. Do not overwrite Ubuntu's system Python.

`build-essential` and `python3-dev` are **not required in the minimum list** while all locked dependencies resolve to compatible wheels. Install them only if the completed lock proves a source build is necessary:

```bash
sudo apt install --yes build-essential python3-dev
```

No separate system SQLite, DuckDB, Arrow, Java, Node.js, browser, or GUI package is required by the audited research/test path. `sqlite3` CLI is optional for manual diagnostics; Python's stdlib SQLite is the application dependency.

Pip-installed packages must come from the completed lock, not from the current ranged `requirements.txt` alone.

## Proposed Bootstrap Process

Create `scripts/bootstrap_linux.sh` during remediation. Intended clean-machine sequence:

1. Fail unless the OS is Linux and the repository is at the expected commit (or record the explicit commit under validation).
2. Verify the selected Python minor/patch.
3. Create `.venv` with `python3 -m venv .venv`; never copy the Windows environment.
4. Upgrade/install the agreed packaging tools and install the single complete hash-locked dependency set plus the editable local package.
5. Copy a local config template to an untracked local config only if the user has not already created one. Never write tokens.
6. Validate all mandatory data variables/paths. Refuse ambiguous discovery.
7. Verify the frozen file inventory, byte sizes, and SHA-256 hashes.
8. Run `python scripts/validate_environment.py --preflight`.
9. Run root tests and the separate `Data test` tests with basetemp under the OS temp directory.
10. Run the tracked golden reference comparison.
11. Only after all checks pass, allow ordinary development commands such as Streamlit startup.

The bootstrap must not install host packages, download market data, mutate SQLite, rewrite manifests, regenerate golden fixtures, or run live/provider-dependent acquisition.

## Migration Validation

The simplest compatible design is:

```bash
.venv/bin/python scripts/validate_environment.py
```

It should be read-only by default and return non-zero on any required failure. Required checks:

1. **Repository**: commit, dirty state, case-collision scan, required files, expected Git mode for bootstrap.
2. **Runtime**: Python version, platform, UTF-8 behavior, `ZoneInfo("Asia/Kolkata")`, SQLite runtime, package versions, `pip check`.
3. **Configuration**: all required non-secret variables present; paths absolute after resolution; no Windows drive syntax on Linux; no accidental path overlap between source and writable artifacts.
4. **Data identity**: mandatory files/directories exist; exact inventory/size/SHA-256 matches the migration manifest.
5. **SQLite**: quiescent sidecar policy, read-only open, table/schema inventory, `PRAGMA quick_check`, no write attempt.
6. **Parquet**: open every required file, validate schema/row count/logical hash and timezone metadata.
7. **Tests**: root and legacy commands use fresh system-temp basetemp; collect/pass/fail/skip counts recorded; unexpected skips fail.
8. **Reference experiment**: golden/reference discrete outputs exact; continuous outputs within the fixed tolerance; no changed decisions.
9. **Artifacts**: output directory writable, source directories not written, paths serialized in platform-neutral form, manifest contract complete.
10. **Final summary**: emit a machine-readable JSON report plus a short console result. Do not include secrets or private absolute paths in the shareable report.

Suggested subcommands may be `--preflight`, `--tests`, and `--reference`, but one no-argument command must run the complete acceptance sequence.

## Storage Requirement

Measured current usage relevant to migration:

- Canonical candidate F&O DB: 46,105.52 MiB (about 45.03 GiB).
- Price CSV collection: 77.43 MiB.
- Acquired `Data test/data`: about 54.04 MiB.
- Local repository artifacts: 347.27 MiB, much of it regenerable test output.
- `.venv`: 582.37 MiB; do not migrate.
- `.git`: 55.19 MiB.
- `Data test` tree: 89.87 MiB including its acquired data and local outputs.
- Ignored imported reference tree: 106.22 MiB; ZIP about 37.9 MiB; not operationally required.

The operational dataset is dominated by the 45 GiB SQLite file. Safe migration needs room for the source copy, destination copy, verification/work files, a fresh environment, artifacts, and growth.

- **Absolute practical minimum free Linux space: 100 GiB** if transfer staging is external and only one verified DB copy is retained.
- **Recommended minimum: 120 GiB free** on the Linux data volume.
- **Preferred for continued research and local backup headroom: 150-200 GiB free.**

Do not count the Windows/OneDrive source copy as the Linux backup. Keep the original read-only until Linux validation is complete.

## Estimated Remediation Time

- **Minimum time to Linux-ready:** 6-8 focused hours, excluding slow network transfer time.
- **Likely time:** 1 to 1.5 working days, including a clean Windows baseline, 46 GB transfer/hash verification, Linux environment build, and both test suites.
- **Worst reasonable case:** 2 working days if Python/package wheel differences or the full root suite expose genuine platform-dependent failures.

Recommended migration day: **Wednesday, 07-Oct-26**, after completing P0 on Monday/Tuesday. This leaves Thursday and Friday for verification and rollback without rushing the data copy.

## Priority Plan

### P0 — MUST FIX BEFORE MIGRATION

1. Portable, explicit, hash-validated bindings for all required external inputs.
2. Platform-neutral canonical path representation in new manifests/catalog records, with historical artifacts preserved.
3. One selected Python baseline and one complete locked environment.
4. Clean Windows full-suite/reference baseline plus the migration validator.

### P1 — FIX DURING MIGRATION

1. Local config/environment template.
2. Linux bootstrap script.
3. Hidden/legacy Dashboard path cleanup.
4. Portable golden-fixture builder input.
5. Optional report dependency and PDF path cleanup.
6. Explicit Linux skip policy for Windows-native historical investigations.
7. Explicit timezone clocks in legacy helpers.
8. Linux README commands.

### P2 — AFTER MIGRATION

1. Linux CI.
2. Repository-wide LF/executable policy with immutable evidence exceptions.
3. Ignored temp/cache cleanup and evidence-aware archival.
4. Additional deterministic filesystem-order checks.
5. Dependency extras organization.
6. Deduplicate large external F&O copies only after verified backup.

## GO / NO-GO

**CONDITIONAL GO — fix listed blockers first**

---

Linux readiness status: **NOT READY**  
Number of P0 blockers: **4**  
Number of P1 issues: **8**  
Number of P2 issues: **6**  
Estimated remediation time: **likely 1 to 1.5 working days; worst reasonable case 2 working days**  
Recommended migration day: **Wednesday, 07-Oct-26**  
GO / CONDITIONAL GO / NO-GO: **CONDITIONAL GO — fix listed blockers first**
