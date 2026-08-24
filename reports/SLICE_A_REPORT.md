# Vertical Slice A report — 12–1 momentum

Date: 2026-08-24  
Status: implementation complete; research result remains non-actionable

## 1. Implementation summary

Slice A adds the smallest new architecture needed to trace:

```text
versioned price snapshot
  -> historical liquidity universe
  -> deterministic 12–1 feature and ranks
  -> explicit next-open 21-session outcome
  -> costed prediction/economic/portfolio evidence
  -> expanding walk-forward folds
  -> immutable Parquet artifacts + mandatory manifest + SQLite catalog entry
```

Retained from the legacy harness:

- Monthly liquidity universe mechanics and deterministic symbol tie-breaking.
- 252-session lookback, 21-session skip, top 20% selection.
- Signal at close, entry at next session open, pure 21-session hold, next-open exit.
- Rs 10,000 sizing basis and the exact Indian delivery cost schedule with 5 bps slippage per side.
- Per-symbol suppression while an earlier trade remains open.
- Explicit unresolved/no-fill behavior.

Added:

- Pinned project environment and lock file.
- Typed dataset snapshots, price provenance, minimal alias validity, and as-of revision behavior.
- Versioned universe, feature, outcome, cost, and immutable JSON experiment specification.
- Horizon-derived 22-session purge and embargo.
- Separate prediction, economic, and portfolio result layers.
- Artifact hashes, environment/spec/source fingerprints, SQLite run catalog, and non-actionable lifecycle state.
- A committed, deterministic 2013–2016 historical golden fixture.

Deferred intentionally:

- Production score/calibration and Trade Decision Helper integration.
- Fundamentals, news, options, optimization, AI tooling, and other edges.
- Full security-master/corporate-action reconstruction beyond the minimum alias contract.
- General-purpose orchestration beyond the single momentum runner.

## 2. Relevant code structure

```text
pyproject.toml
requirements.lock
specs/
  momentum_12_1_v1.json
src/market_intel/
  foundation/
    artifacts.py
    contracts.py
    prices.py
  research/
    folds.py
    momentum.py
    outcomes.py
    universe.py
  simulation/
    costs.py
  evidence/
    metrics.py
  application/
    momentum_cli.py
    runner.py
tests/
  fixtures/momentum_golden_v1/
  test_golden_fixture.py
  test_manifest.py
  test_outcomes_and_costs.py
  test_temporal_contracts.py
  test_universe_history.py
  test_walk_forward.py
reports/
  legacy_momentum_baseline.json
  SLICE_A_REPORT.md
```

## 3. Executable baseline

PowerShell setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

New tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp="artifacts\pytest-new"
```

Legacy tests:

```powershell
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'Data test').Path
.\.venv\Scripts\python.exe -m pytest "Data test\tests" -q --basetemp="artifacts\pytest-legacy"
```

Full available-data momentum research:

```powershell
.\.venv\Scripts\python.exe -m market_intel.application.momentum_cli `
  --price-dir "C:\Users\parik\OneDrive\Desktop\Dashboard\data" `
  --benchmark-file "C:\Users\parik\OneDrive\Desktop\Dashboard\data\NIFTY50_DAILY.csv" `
  --industry-map "C:\Users\parik\OneDrive\Desktop\Dashboard\market_gate\data\nifty500.csv" `
  --output-root "artifacts\runs"
```

Do not add `--survivorship-safe` for this directory. Its historical completeness has not been established.

## 4. Old versus new compatibility

### Golden fixture: identical

The fixture contains eight real NSE series over 2013–2016 plus NIFTY50. It is for parity only and makes no statistical claim.

| Measure | Legacy | New | Result |
|---|---:|---:|---|
| Selected signals | 68 | 68 | identical |
| Implemented trades after existing-position suppression | 47 | 47 | identical |
| Resolved trades | 45 | 45 | identical |
| Mean net return | 0.6077325682% | 0.6077325682% | identical to floating precision |
| Mean cost | 0.3236760541% | 0.3236760541% | identical |

The first new implementation produced 68 potential trades versus 47 legacy trades. This was not forced away: investigation found that the legacy simulator suppresses a new entry in a symbol while its prior position is open. The new system now retains all 68 predictions/outcomes for prediction research while marking 47 as realizable `trade_executed` observations. This cleanly separates prediction from implementation.

### Archived full legacy primary-train result

The captured archive reports 4,147 signals, 4,031 resolved trades, 0.601389% mean net return, 0.323666% mean cost, ending equity Rs 63,899, and -39.16% maximum drawdown. Its original research verdict was `rejected` because it did not beat the placebo and had weak portfolio performance.

Its output files are hash-captured in `legacy_momentum_baseline.json`, but the source cash-bhavcopy cache is absent. Therefore the archived full run is not currently source-to-result replayable.

### Available external directory: changed, not comparable

Using the available 430-file per-symbol directory over the nominal 2004–2016 interval gives 3,008 resolved implemented trades and 2.7151% mean net return. This is **not** evidence that the refactor improved momentum:

- The input universe differs from the bhavcopy universe.
- Historical completeness/survivorship safety is unproven.
- Turnover is absent and was explicitly derived as close × volume.
- Security alias history and delisting terminal values are absent.
- The legacy raw dataset snapshot is unavailable for byte-identical replay.

The discrepancy is primarily a data/universe provenance difference, not feature, ranking, execution, or cost logic: those agree exactly on the golden fixture.

## 5. Walk-forward validation report

Run artifact: `artifacts/runs/momentum_12_1_slice_a_v1_cdbf04b3f4ae90ca`

Protocol:

- Research chronology limited to 2004-01-01 through 2026-08-13.
- Expanding minimum five-year training window.
- One-year validation windows stepped annually.
- 22-session purge and 22-session embargo, derived from the 21-session outcome plus next-open execution.
- Historical liquidity universe recalculated at every month-end.
- No parameter optimization or final-holdout selection.

### Prediction quality

- 42,288 resolved OOS cross-sectional observations.
- 209 effective monthly decision dates.
- Mean monthly Spearman rank IC: **0.03169**.
- Approximate 95% interval: **0.00258 to 0.06081**.
- Quintile outcomes were **not monotonic**.

### Economic quality

- 5,309 resolved, realizable selected trades.
- Mean gross return: **2.5628%**.
- Mean transaction cost: **0.3262%**.
- Mean net return: **2.2366%**.
- Mean benchmark return over matched executable windows: **1.0093%**.
- Mean net excess return: **1.2273%**.
- Mean MAE: **-8.2907%**; mean MFE: **11.2435%**.
- Cost sensitivity mean net: 2.3366% at 0 bps/side, 2.2366% at 5 bps/side, 2.1366% at 10 bps/side.
- Positive mean excess in 11 of 18 folds (**61.1%**), only just above the predeclared 60% gate.
- Recent folds weakened: 2024–25 **-0.9447%**, 2025–26 **-1.2668%**, and partial 2026 **-0.7172%**.

These numbers are descriptive diagnostics only because the dataset integrity gate fails.

### Portfolio quality

The new portfolio layer is an equal-weight monthly approximation, deliberately labeled as such:

- 209 rebalances.
- Maximum drawdown: **-43.26%**, worse than the matched benchmark's **-31.37%**.
- Mean 25.4 implemented names per rebalance; maximum 92.
- 100% gross exposure assumption.

The very large compounded terminal wealth is not trustworthy evidence: it is amplified by survivor-only inputs and an approximation that does not reproduce the legacy five-slot, cash-constrained portfolio. It is retained as a diagnostic artifact, not a claim.

## 6. Research verdict

**State: `RESEARCHING` — non-actionable.**

The legacy survivorship-safe primary-train experiment was rejected. The new infrastructure reproduces the legacy mechanics exactly on a controlled historical fixture, but the only available broad dataset fails the predeclared survivorship-safety gate and lacks original turnover. Apparent positive walk-forward performance cannot confirm the hypothesis.

The edge is not `VALIDATED` or `ACTIVE`; no score or BUY/HOLD/REDUCE recommendation is emitted.

## 7. Remaining point-in-time and data-quality risks

1. Original cash-bhavcopy raw inputs used by the archived run are missing.
2. The available 430-symbol directory may encode survivor/coverage selection.
3. Its turnover is derived, not exchange-published.
4. Stable IDs are separate from aliases, but historical rename/merger mappings remain unverified.
5. Daily CSV files lack exact publication/retrieval history; the snapshot records a conservative availability policy, not an exchange timestamp.
6. Corporate-action handling relies on source OHLC and is not independently reconstructed for the full run.
7. One missing exit can indicate delisting, suspension, or data absence; a terminal-value source is still required for trustworthy full-market outcomes.
8. The copied workspace has no root `.git` metadata. Manifests record `NO_GIT_METADATA` plus a deterministic source-tree fingerprint, but cannot cite a commit until the flattened project is initialized/connected to Git.

## 8. Technical debt required before Slice B

- Restore and version a complete survivorship-safe NSE cash-bhavcopy dataset, including raw payload hashes and exchange turnover.
- Add historical security alias/corporate-action/delisting terminal-value evidence sufficient for the chosen research universe.
- Replace the equal-weight portfolio approximation with the shared cash/slot/concentration engine before making portfolio claims.
- Initialize or reconnect root Git history so manifests contain commit plus dirty fingerprint.
- Add an acquisition manifest that captures actual retrieval timestamps prospectively; old local CSV metadata cannot reconstruct them retrospectively.

These are trust requirements, not general architectural polish.

## 9. Possible Slice B candidates — not implemented

### A. Cross-sectional earnings-surprise continuation

- **Rationale:** earnings information diffuses gradually; standardized unexpected earnings can predict medium-horizon continuation.
- **Data:** NSE financial filings keyed by broadcast timestamp, price/universe data.
- **Horizon:** 20–60 trading days.
- **Why useful:** continuous cross-sectional feature with a direct economic event and existing source parser.
- **Risks:** restatement vintages, consolidated/standalone choice, filing-time alignment, sparse older coverage, multiple SUE definitions.

### B. Insider net-buying intensity

- **Rationale:** repeated open-market insider buying may reveal private conviction when normalized by liquidity/market capitalization.
- **Data:** SEBI PIT disclosures by filing timestamp, transaction type, price/liquidity data.
- **Horizon:** 20–60 trading days.
- **Why useful:** distinct behavioral information not reducible to price momentum.
- **Risks:** disclosure delay, transaction classification, zero/missing values, clustering within issuers, post-2015 coverage.

### C. Promoter-pledge deterioration

- **Rationale:** rising promoter encumbrance can increase forced-selling and governance downside risk; the natural output may be an avoidance/risk edge rather than return alpha.
- **Data:** point-in-time shareholding filings with revision-aware pledge percentage, liquidity/returns.
- **Horizon:** 60–120 trading days.
- **Why useful:** potentially better suited to downside-risk scoring than directional trading.
- **Risks:** short history, backfilled filings, XBRL unit inconsistencies, sector/size confounding.

### D. Index-addition announcement-to-effective-date pressure

- **Rationale:** passive demand may create predictable positioning between public announcement and effective membership.
- **Data:** announcement and effective dates, historical identifiers, survivorship-safe prices/turnover.
- **Horizon:** announcement +1 through effective date and 5–20 days after.
- **Why useful:** precisely timed, falsifiable event edge with explicit counterparties.
- **Risks:** PDF coverage before 2010, ticker mapping, announcement-time precision, crowding/decay, confounding corporate events.

## Stop condition

Slice A stops here. No Slice B hypothesis, production score, Streamlit decision integration, or AI workflow has been implemented.
