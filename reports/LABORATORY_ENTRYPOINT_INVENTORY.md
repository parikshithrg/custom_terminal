# Laboratory Entry-point Inventory

## Method and totals

R.4 inspected every tracked Python `__main__` under `Data test`, `scripts`,
`tools`, `src` and `views`; project scripts; callable simulators/log writers;
Streamlit laboratory surfaces; subprocess references; notebooks; and shell,
batch and PowerShell launchers. No notebook or repository shell/batch/PowerShell
research launcher and no production subprocess research launcher was found.

The versioned inventory contains 68 entries:

| Classification | Count |
|---|---:|
| `CANONICAL_GOVERNED` | 2 |
| `DEVELOPMENT_ONLY_NONCANONICAL` | 64 |
| `DEPRECATED` | 2 |
| `UNSAFE_BYPASS` | 0 |

`scripts/preview_governed_run.py` is counted as governed administration but
cannot execute. `GovernedExecutionGateway.run` is the sole canonical execution
path.

## Canonical and deprecated paths

| Path / callable | Purpose; inputs → outputs | Gateway / canonical access | Classification and remediation |
|---|---|---|---|
| `src/research_contracts/governance.py::GovernedExecutionGateway.run` | Exact registered objects → temporary attempt, root manifest, atomic bundle, events | Yes; sole canonical execution path | `CANONICAL_GOVERNED`; exact approval is now mandatory |
| `scripts/preview_governed_run.py::main` | Paths, catalog and explicit evaluation time → stdout JSON only | Reads governance state; never executes/imports | `CANONICAL_GOVERNED`; side-effect-free preview |
| `src/market_intel/application/momentum_cli.py::main` | Former Slice A command | No; exits before parsing or loading | `DEPRECATED`; fail-closed warning |
| `tools/build_golden_fixture.py::main` | Former external-data fixture builder → committed fixture | No | `DEPRECATED`; raises before access/write |

## Direct callable surfaces

| Path / callable | Purpose and output | Gateway / canonical access | Classification and remediation |
|---|---|---|---|
| `src/market_intel/application/runner.py::run_momentum` | Slice A compatibility calculation → legacy-shaped run directory | No; cannot update a catalog | `DEVELOPMENT_ONLY_NONCANONICAL`; warning and marker added |
| `Data test/dtest/evaluate/hypothesis_log.py::append_entry` | Result row → ignored legacy CSV | No | `DEVELOPMENT_ONLY_NONCANONICAL`; warning/marker before write |
| `Data test/dtest/engine/simulate.py::simulate_trades` | Signals/prices/config → in-memory trades | No direct writer | `DEVELOPMENT_ONLY_NONCANONICAL`; callers remain marked/rejected |
| `Data test/dtest/engine/pairs_simulate.py::simulate_pairs_trades` | Pair signals/prices → in-memory pair trades | No direct writer | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/dtest/engine/portfolio.py::run_portfolio` | Trades/config → portfolio frames | No direct writer | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `views/mg_lab.py` | Streamlit stub metadata only | No controls or runner | `DEVELOPMENT_ONLY_NONCANONICAL`; no remediation needed |
| `views/research_backtest_framework.py` | Streamlit stub metadata only | No controls or runner | `DEVELOPMENT_ONLY_NONCANONICAL`; no remediation needed |

Low-level `dtest/features`, `dtest/signals` and remaining engine functions can
calculate values in memory but cannot create canonical evidence. The importer
requires a registered approval, consumed start event, final event and complete
governed root manifest; wrapping these callables or invoking them in a
subprocess does not manufacture those bindings.

## Data-test executable scripts

Every command below is `python "Data test/scripts/<name>.py"`. Each loads the
shared typed configuration before its research/data path. R.4 uses that shared
boundary to display a development-only warning and create
`UNGOVERNED_NONCANONICAL_OUTPUT` under
`artifacts/noncanonical_entrypoints/<script>`. Outputs remain in configured
`artifacts`, `runs` or data-cache paths, never the future canonical catalog.
The call-stack detection is a convenience marker and is not treated as a
security boundary: explicit log/run markers plus canonical-import rejection are
decisive. Shell and subprocess launches traverse the same configuration call.

### Research, backtest and diagnostic scripts

| Path | Purpose; principal output | Classification |
|---|---|---|
| `Data test/scripts/monte_carlo_hypotheses.py` | hypothesis simulations; artifact CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/sweep_exit_geometry.py` | exit-parameter sweep; diagnostic CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_delivery_breakout.py` | delivery-breakout backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_earnings_surprise.py` | earnings-surprise backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_mean_reversion.py` | mean-reversion backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_momentum.py` | legacy momentum backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_oi_momentum.py` | OI-momentum backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_pairs_reversion.py` | pairs backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_participant_tilt.py` | participant-tilt backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_participant_tilt_stress_gated.py` | stress-gated tilt backtest; artifacts/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_price_action.py` | price-action backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_quality.py` | quality backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_same_sector_pairing.py` | sector-pairing backtest; artifacts/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_sector_pairing_oilgas.py` | sector diagnostic backtest; artifacts/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_value.py` | value backtest; trades/placebos/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_vol_squeeze_breakout.py` | volatility-squeeze backtest; artifacts/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/test_vol_squeeze_breakout_delayed.py` | delayed-entry variant; artifacts/log | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_entry_delay.py` | entry-delay diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_execution_timing.py` | fill-timing diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_liquidity_momentum.py` | liquidity/momentum diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_pairs_reversion.py` | pairs diagnostic; CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_price_action_short.py` | short-side diagnostic; CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_regime_gate.py` | regime-gate diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_sector_pairing.py` | sector-pairing diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_stress_gate.py` | stress-gate diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_stress_gate_tercile.py` | stress-tercile diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_trend_gate.py` | trend-gate diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnostic_window_execution.py` | window/fill diagnostic; CSV | `DEVELOPMENT_ONLY_NONCANONICAL` |

### Analysis and report builders

| Path | Purpose; principal output | Classification |
|---|---|---|
| `Data test/scripts/analyze_stock_performance.py` | full-period outcome analysis; CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/analyze_stock_performance_post2021.py` | later-period analysis; CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/build_holding_period_analysis.py` | holding-period evidence; CSVs/figures | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/build_holding_period_analysis_val_only.py` | validation-only holding analysis | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/build_hypothesis_report_data.py` | legacy log/artifacts → report tables | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/build_hypothesis_report_pdf.py` | report tables → legacy PDF | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnose_top_performers.py` | top-performer diagnostics; CSVs | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/diagnose_top_performers_post2021.py` | later-period top-performer diagnostics | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/dig_delivery_breakout_holding_period.py` | delivery holding-period diagnostic | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/price_precision.py` | source-price precision diagnostic | `DEVELOPMENT_ONLY_NONCANONICAL` |

### Acquisition, coverage and data-audit scripts

These are not canonical research execution. They were still inventoried because
they can create inputs or diagnostic artifacts. R.4 did not run or contact any
source.

| Path | Purpose; principal output | Classification |
|---|---|---|
| `Data test/scripts/audit_data.py` | local coverage audit; CSV/text | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/fetch_financial_results.py` | remote financial-result cache | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/fetch_index_reconstitution.py` | remote index-event cache | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/fetch_insider_trading.py` | remote insider-event cache | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/fetch_macro_stress_series.py` | remote macro cache | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/fetch_shareholding.py` | remote shareholding cache | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/ingest_bhavcopy.py` | local bhavcopy ingestion | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/probe_financial_results_coverage.py` | coverage probe artifact | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/probe_insider_trading_coverage.py` | coverage probe artifact | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/probe_shareholding_coverage.py` | coverage probe artifact | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `Data test/scripts/verify_corporate_actions.py` | inferred-action diagnostic | `DEVELOPMENT_ONLY_NONCANONICAL` |

## Evidence and data-administration commands

| Path | Purpose; outputs | Gateway / canonical access | Classification |
|---|---|---|---|
| `scripts/check_legacy_log_divergence.py` | read two logs → sanitized versioned result | No research/import | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `scripts/export_legacy_ledger.py` | frozen snapshot → neutral R.2 ledger | Legacy-only, nonpromotable | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `scripts/import_legacy_evidence.py` | validated R.2 ledger → legacy catalog | Cannot enter future catalog | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `scripts/preserve_legacy_snapshot.py` | exact designated bytes → frozen package | Legacy preservation only | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `tools/audit_historical_data.py` | local dataset → audit report | No research run | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `tools/qualify_historical_population_a8.py` | official objects → qualification | No research run | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `tools/qualify_official_public_sample.py` | bounded objects → qualification | No research run | `DEVELOPMENT_ONLY_NONCANONICAL` |
| `tools/run_dataset_acceptance.py` | local normalized data → trust report | No research run | `DEVELOPMENT_ONLY_NONCANONICAL` |

## Remaining limitations

The filesystem owner can always write arbitrary files or invoke low-level
Python outside these paths. R.4 does not claim process sandboxing. Such output
lacks the exact registered approval, consumed start event, final event and root
manifest, so it cannot enter the canonical catalog. No material repository
entry point remains classified `UNSAFE_BYPASS`.
