# Local Terminal

> Research architecture: `ARCHITECTURE_REFINEMENT.md`. Slice A: `reports/SLICE_A_REPORT.md`. Slice A.5 data-trust decision: `reports/SLICE_A5_REPORT.md`, with detailed trust findings in `reports/DATASET_TRUST_REPORT.md` and acquisition requirements in `reports/HISTORICAL_DATA_REQUIREMENTS.md`.

> Slice A.6 provider-neutral ingestion readiness: `reports/SLICE_A6_REPORT.md`. Candidate sources must be reviewed with `reports/DATA_SOURCE_EVALUATION_TEMPLATE.md` before any acquisition.

A one-stop information & analytics terminal spanning trading decisions,
long-term investment decisions, and event risk - **deliberately with no
trade execution**. This is a pages-only scaffold: every page exists and
is reachable, none are wired to real data yet.

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
