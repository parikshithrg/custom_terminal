# Local Terminal

> Research architecture: `ARCHITECTURE_REFINEMENT.md`. Slice A: `reports/SLICE_A_REPORT.md`. Slice A.5 data-trust decision: `reports/SLICE_A5_REPORT.md`, with detailed trust findings in `reports/DATASET_TRUST_REPORT.md` and acquisition requirements in `reports/HISTORICAL_DATA_REQUIREMENTS.md`.

> Slice A.6 provider-neutral ingestion readiness: `reports/SLICE_A6_REPORT.md`. Candidate sources must be reviewed with `reports/DATA_SOURCE_EVALUATION_TEMPLATE.md` before any acquisition.

> Official-public-source feasibility and bounded qualification: `reports/PUBLIC_DATA_FEASIBILITY.md` and `reports/PUBLIC_DATA_QUALIFICATION.md`.

> Vertical Slice A.7 manual official-evidence qualification and archive readiness: `reports/SLICE_A7_REPORT.md`.

> Vertical Slice A.8 locked twelve-date historical-population qualification: `reports/SLICE_A8_REPORT.md`.

> Vertical Slice A.9 official access and rights clarification packet: `reports/SLICE_A9_REPORT.md` and `reports/NSE_DATA_CLARIFICATION_REQUEST.md`.

> Vertical Slice A.10 response evaluation gate: `reports/SLICE_A10_REPORT.md` and `reports/NSE_OFFICIAL_RESPONSE_EVALUATION.md`.

A one-stop information & analytics terminal spanning trading decisions,
long-term investment decisions, and event risk - **deliberately with no
trade execution**. This is a pages-only scaffold: every page exists and
is reachable, none are wired to real data yet.

## Current research-infrastructure status

Vertical Slices A through A.7 now provide a deterministic, local-first research foundation alongside the original Streamlit product scaffold. The quantitative infrastructure remains separate from the UI and no research result is connected to production recommendations.

### Research governance R.4

Every future canonical research attempt must now use the governed gateway with
an immutable registered family, locked preregistration, hashed input declaration,
successful side-effect-free preflight and exact registered one-use user
approval. Direct Data-test and compatibility runners are development-only and
their outputs are rejected by the future canonical importer. The old momentum
CLI is deprecated and fails before loading data.

Approval to execute is not approval to interpret, promote or trade. Test access
requires separate explicit permission. R.4 does not authorize a first real run.
The one-attempt limit is enforced; declared wall-time and memory limits are not
yet enforced by the in-process runner.

See:

- `reports/RESEARCH_R4_REPORT.md`
- `reports/LABORATORY_ENTRYPOINT_INVENTORY.md`
- `reports/FIRST_GOVERNED_RUN_APPROVAL.md`
- `reports/GOVERNED_EXECUTION_OPERATIONS.md`

Side-effect-free preview syntax:

```powershell
.\.venv\Scripts\python.exe scripts\preview_governed_run.py --help
```

### Vertical Slice A.7

A.7 added conservative qualification contracts for official Indian-market evidence:

- Lifecycle-event normalization that preserves conflicting official assertions.
- An economic-terminal gate that does not treat a final quoted price as delisting consideration.
- Historical security-snapshot versus bhavcopy population reconciliation.
- Strict NIFTY 50 PRI/TRI identity and classification checks.
- Date-effective statutory-cost coverage checks that never backfill present rates into unknown history.
- A versioned 12-date historical-population sample specification.
- A bounded 2024 one-year archive-pilot specification with completeness and abort conditions.
- Offline tests for lifecycle evidence, unresolved terminals, population reconciliation, PRI/TRI separation, cost gaps, access quarantine, schema failures, and pilot gates.

The one-year pilot was not executed. Required historical security snapshots, archive-retention permission, fully qualified PRI/TRI data, complete historical costs, and lifecycle coverage remain unproven. No archive-scale acquisition, CAPTCHA bypass, paid data, momentum rerun, Slice B research, production score, or decision-interface integration occurred.

Current readiness decision:

```text
PUBLIC_SOURCES_REQUIRE_FURTHER_MANUAL_EVIDENCE
```

Supporting reports:

- `reports/OFFICIAL_LIFECYCLE_QUALIFICATION.md`
- `reports/HISTORICAL_POPULATION_QUALIFICATION.md`
- `reports/BSE_SEBI_RECONCILIATION.md`
- `reports/BENCHMARK_PUBLIC_DATA_QUALIFICATION.md`
- `reports/HISTORICAL_COST_SCHEDULE_QUALIFICATION.md`
- `reports/ONE_YEAR_PILOT_READINESS.md`

Machine-readable outputs:

- `specs/official_lifecycle_sample_v2.json`
- `specs/historical_population_sample_12_dates_v1.json`
- `specs/one_year_archive_pilot_2024_v1.json`
- `specs/public_official_a7_trust_v1.json`
- `specs/a7_qualification_result_v1.json`

The recommended next milestone is to prove ordinary, retainable access to paired official NSE security snapshots and bhavcopies for the fixed 12 dates, then execute only that population qualification before reconsidering the 2024 pilot.

### Vertical Slice A.8

The fixed sample retrieved 12/12 official bhavcopies but only 3/12 dated MII security snapshots. The three modern pairs preserved 1,488, 1,611, and 1,557 snapshot-only/non-trading EQ securities and had no price-only EQ rows. Nine older pairs remain incomplete because NSE's website dissemination of the dated MII file began on 2024-02-05; no current security list was substituted.

The current NSE Terms of Use prohibit systematic automated collection. Further acquisition stopped, raw objects remain outside Git, and retention/derived-use permission requires written review. Direct and event-derived historical-population reconstruction both fail for the locked interval.

Current decision: `HISTORICAL_POPULATION_RECONSTRUCTION_INCOMPLETE`.

### Vertical Slice A.9

An official clarification request is ready for `marketdata@nse.co.in`, with the NSE Economic Policy & Research route at `nseri@nse.co.in`. No message was transmitted from this workspace and acquisition remains stopped. A deterministic response gate requires an authoritative, retained, hashed written reply before manual access, retention, derived research, or pre-2024 availability can be treated as permitted.

Current gate: `AWAITING_OFFICIAL_WRITTEN_RESPONSE`.

### Vertical Slice A.10

No official response bytes, headers, or attachments were present in the supplied task or attachment registry. All fourteen permission questions therefore remain `NOT_ANSWERED`; no acquisition or research-scope promotion is authorized. The response evaluator now validates official domains, headers, exact bodies, referenced attachments, permission categories, and mandatory acquisition gates.

Current decision: `AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`.

## Run it

```
pip install -r requirements.txt
pip install -e .
streamlit run app.py
```

Opens at `http://127.0.0.1:8501`. Home is a grid of boxes (not tabs, not
a sidebar) - click any box to open that page. `runOnSave = true` is set,
so editing a page updates the running app automatically.

## Kite Connect daily login

Open **Markets Data Library → Data Coverage → Kite Connection**. Enter the
API key and API secret, open the Zerodha login link, then paste the returned
one-time `request_token` (or complete redirect URL) and create the daily
session. Repeat after Kite's access token expires.

The API secret and one-time request token are removed from application state
after every exchange attempt. The access token remains only in Streamlit
session memory until provider rejection, disconnect, or process termination.
These values are not intentionally saved to files, databases, logs, artifacts,
or Git. Removal of Python references is not a claim of secure memory erasure.

The application allowlists only these Kite GET endpoints:

- `/user/profile` for bounded session validation;
- `/instruments` for an ephemeral current instrument inventory;
- `/quote`, `/quote/ohlc`, and `/quote/ltp` for user-requested snapshots.

The token exchange at `/session/token` is the sole allowed authentication POST
and is isolated from market-data methods. No order, order modification,
cancellation, basket, GTT, funds-transfer, holdings-mutation, order-margin, or
WebSocket order-update functionality is implemented. The user's token may have
broader account permissions; this application allows only the declared data
endpoints. Quotes are limited to 25 current inventory entries per request and
cached in memory for 15 seconds. Provider entitlements can still limit results.

Kite is scoped to currently tradable instruments and current-market analysis.
Delisted securities are omitted from live views. Its current instrument list
is never substituted for a historical universe: historical research still
requires point-in-time inactive membership to avoid survivorship bias. The
connector therefore does not change the A.8–A.10 historical trust verdicts.

Detailed current-data scope: `reports/KITE_CURRENT_DATA_SCOPE.md`. A.11
implementation report: `reports/SLICE_A11_REPORT.md`.

### Ephemeral coverage health

The **Coverage Health** tab summarizes the authenticated session, validation
state, current inventory/quote ages, cache freshness, aggregate coverage,
missing results, integrity counts and sanitized provider failure category. It
never renders the full instrument dump on that tab.

Inventory, session and quote refreshes are manual with a five-second cooldown;
there are no background loops. Quote snapshots retain the 15-second in-memory
cache. A sanitized JSON summary can be downloaded on demand from memory and
contains aggregate classifications only—no account details, credentials,
tokens, raw instruments or raw quote responses.

No maintained current NSE holiday calendar is configured, so the live market
session label is deliberately `UNKNOWN`. It will not infer holidays from absent
quotes or guess from weekdays. See `reports/KITE_CURRENT_COVERAGE_HEALTH.md`
and `reports/SLICE_A12_REPORT.md`.

## Structure

17 pages across 4 sections (`views/_registry.py` is the single source of
truth for title/icon/description/section/subsections - edit there, not
in the individual page files). Organized by JOB, not by which source
project the data will eventually come from. Several pages are
**consolidated** - two related topics on one page as tabs, where they're
meant to be read together rather than checked on two separate screens:

- **Trading Desk** (5) - Trade Decision Helper (the core synthesis page),
  Market & Sector Context (regime + sector rotation), Setup Scanner,
  Options & Positioning, Trade Management (position sizing + tradebook).
- **Investment Desk** (4) - Asset Allocation & Rotation, Risk & Capital
  Protection (risk reading + its own trigger), Performance & Benchmarks
  (returns + what they're measured against), Goal Tracker.
- **News & Event Monitor** (2) - News & Calendar (feed + scheduled
  catalysts), Event Risk Assessment (Black Swan Radar + Portfolio Impact
  Mapper).
- **Markets Data Library** (6) - NOT a decision surface, the foundation
  the two desks above draw from: Correlation Explorer (market + asset
  correlations), Data Coverage (inventory + India-vs-global gap map),
  Market Gate Home (composite score + status), Lab, Backtesting
  Framework, Seasonality.

**One open architectural question, flagged on both pages rather than
silently resolved**: Lab and Backtesting Framework are two DIFFERENT
engines that both configure and run a backtest. Whether they should stay
separate or consolidate to one is undecided - each page carries a visible
note about the other.

## Not yet decided

- **Data sources.** Every page is a stub. Whether this reads Market
  Gate's data read-only (the pattern the `Data test` project already
  uses), builds its own pipeline, or something else - not decided.
- **The Lab/Backtesting Framework overlap** (see above).

## Test commands

The standard root command intentionally collects only the current `tests/` suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The separate legacy `Data test` project retains its own configuration and import root:

```powershell
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'Data test').Path
.\.venv\Scripts\python.exe -m pytest "Data test\tests" -q
```

Latest verified results through Research R.7:

- Root suite: **230 passed**.
- Separate `Data test` suite: **289 passed**.
- R.7 focused report-gate/PDF suite: **17 passed**.
- Combined R.3-R.7 governance suite: **94 passed**.

Research R.6B independently audits the completed, bounded synthetic governance
canary without rerunning it. The tracked anchor preserves only sanitized hashes
and identifiers; raw runtime evidence remains in ignored local artifact storage.
The result is permanently nonpromotable and proves governance mechanics only,
not historical data trust or investment validity. See
`reports/RESEARCH_R6_REPORT.md` and `reports/GOVERNED_CANARY_AUDIT.md`.

Research R.7 adds a permanent owner-review gate before any future market
research preregistration can lock or execute. The first 15-page status PDF is
`output/pdf/market_system_status_pre_research_review_v1.pdf`; its review record
is `REPORT_GENERATED_PENDING_REVIEW`. Reading or approving that PDF does not
replace the separate run-specific governance approval.
