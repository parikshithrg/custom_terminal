# Local Terminal

> Research architecture: `ARCHITECTURE_REFINEMENT.md`. Slice A: `reports/SLICE_A_REPORT.md`. Slice A.5 data-trust decision: `reports/SLICE_A5_REPORT.md`, with detailed trust findings in `reports/DATASET_TRUST_REPORT.md` and acquisition requirements in `reports/HISTORICAL_DATA_REQUIREMENTS.md`.

> Slice A.6 provider-neutral ingestion readiness: `reports/SLICE_A6_REPORT.md`. Candidate sources must be reviewed with `reports/DATA_SOURCE_EVALUATION_TEMPLATE.md` before any acquisition.

> Official-public-source feasibility and bounded qualification: `reports/PUBLIC_DATA_FEASIBILITY.md` and `reports/PUBLIC_DATA_QUALIFICATION.md`.

> Vertical Slice A.7 manual official-evidence qualification and archive readiness: `reports/SLICE_A7_REPORT.md`.

> Vertical Slice A.8 locked twelve-date historical-population qualification: `reports/SLICE_A8_REPORT.md`.

> Vertical Slice A.9 official access and rights clarification packet: `reports/SLICE_A9_REPORT.md` and `reports/NSE_DATA_CLARIFICATION_REQUEST.md`.

A one-stop information & analytics terminal spanning trading decisions,
long-term investment decisions, and event risk - **deliberately with no
trade execution**. This is a pages-only scaffold: every page exists and
is reachable, none are wired to real data yet.

## Current research-infrastructure status

Vertical Slices A through A.7 now provide a deterministic, local-first research foundation alongside the original Streamlit product scaffold. The quantitative infrastructure remains separate from the UI and no research result is connected to production recommendations.

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

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://127.0.0.1:8501`. Home is a grid of boxes (not tabs, not
a sidebar) - click any box to open that page. `runOnSave = true` is set,
so editing a page updates the running app automatically.

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

Latest verified results:

- Root suite: **42 passed**.
- Separate `Data test` suite: **289 passed**.
- All versioned JSON specifications parsed successfully.
