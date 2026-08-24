# Local Terminal architecture audit

Date: 2026-08-24  
Scope: the complete contents of the supplied `Local Terminal.zip`, including the Streamlit scaffold, the nested `Data test` research harness, committed datasets, results, scripts, and tests. No product rewrite was performed.

> **Review note:** The audit's main conclusion remains valid. The refined design, including corrected storage roles, simpler bounded contexts, explicit score semantics, and the first two vertical slices, is in `ARCHITECTURE_REFINEMENT.md`. Where the two documents differ, the refinement supersedes the original target-design detail.

## Executive conclusion

This repository is not one system yet. It is two adjacent systems:

1. **`Local Terminal`** is an 18-route Streamlit product map. Four routes contain meaningful behavior; most routes are deliberately shared stubs.
2. **`Data test`** is a serious, narrow Indian cash-equity research harness with valuable safeguards, but it is organized around one-off hypothesis scripts rather than reusable edge, score, confidence, and decision services.

The right migration is to make the deterministic research harness the seed of a new domain core, not to wire each page independently and not to discard the harness. Preserve its next-open execution, explicit costs, point-in-time liquidity universe, deterministic hashing, placebo tests, split discipline, portfolio accounting, and append-only hypothesis history. Refactor its data contracts and experiment orchestration; replace CSV-as-state, machine-specific paths, page-owned calculations, live analytical scoring, and the current informal notion of a “signal” with versioned feature/edge/validation/score records.

The first deliverable should be one vertical slice—prices/universe → feature snapshot → one edge → walk-forward validation → calibrated score + confidence → decision evidence—served to a thin Streamlit page. Do not implement the remaining page inventory until that slice proves the contracts.

## 1. Repository inventory

| Area | What exists | Assessment |
|---|---|---|
| `app.py`, `views/_registry.py` | Hidden Streamlit navigation and centralized page metadata | Keep the thin navigation concept; update stale counts and domain naming |
| `views/` | 18 registered routes, common top bar/stub renderer; news, event risk, trade management, and reports have substantive code | Keep as a prototype/spec; prevent views from owning data acquisition or quantitative logic |
| `Data test/dtest/data` | NSE bhavcopy, corporate actions, F&O, financial filings, shareholding, insider activity, index reconstitution parsers/loaders | Keep parsers and their tests; put them behind provider/ingestion contracts and a common temporal envelope |
| `Data test/dtest/features` | Technical, fundamental, regime, stress, pairs, and price-action transforms | Refactor into registered, versioned, point-in-time feature definitions |
| `Data test/dtest/signals` | Eleven hypothesis-specific signal modules | Recast as edge definitions that emit continuous predictions/exposures where possible, not only Boolean trade triggers |
| `Data test/dtest/engine` | Cash/futures costs, fills, single-leg and pairs simulation, portfolio accounting | Keep and generalize behind execution and portfolio protocols |
| `Data test/dtest/evaluate` | Metrics, placebo testing, append-only hypothesis log | Keep ideas; expand into a validation service and durable edge registry |
| `Data test/scripts` | 49 acquisition, hypothesis, report, and diagnostic scripts | Consolidate repeated experiment runners into a declarative runner plus small CLIs |
| `Data test/tests` | 36 test files and fixtures | Keep; add temporal-contract, walk-forward, calibration, and end-to-end golden tests |
| `Data test/data`, `Data test/runs` | 2,783 data files (~54 MB) and 158 result files (~33 MB), mostly CSV | Migrate metadata to a catalog and large immutable tables to partitioned Parquet/object storage; do not keep Git as the primary data/result database |

The root README says 17 pages and six Data Library pages, while the registry currently contains 18 routes and seven Data Library entries (the later `Reports` route causes the drift). The README also calls the project pages-only even though four routes now do real work. Treat the registry as product taxonomy, not an architectural boundary.

## 2. Current architecture and data flow

### Streamlit surface

`app.py` constructs every route from `views/_registry.py`. Stub pages read their metadata and call one of two shared renderers. The substantive pages break that pattern:

- News and calendar fetch remote feeds/APIs during a Streamlit session and use TTL caches.
- Event risk fetches Yahoo/breadth/news inputs, maps current percentiles through hard-coded transformations, writes sentiment history to a tracked CSV, and renders a composite.
- Trade management is an isolated calculator/form, not connected to portfolio state.
- Reports read committed research result CSVs and recreate a narrative in the UI.

There is no application/service boundary between UI and analytics, no common data access layer, and no score/confidence/decision API.

### Research harness

The typical hypothesis path is:

```text
config.toml + external machine paths + local CSV/SQLite
  -> source-specific loader / bhavcopy panel builder
  -> monthly liquidity-rule universe
  -> feature function
  -> signal function
  -> next-open fill + costed trade simulation
  -> placebo + metrics + portfolio simulation
  -> hypothesis_log.csv + several run CSVs
  -> reports page / generated PDF
```

This is deterministic in its core calculations and explicitly guards next-open fills. Train/validation/test windows are fixed, but the current runner pattern usually invokes one selected window at a time; it is not a general walk-forward engine. Only the audit path actually constructs and writes a `RunManifest`; the hypothesis runners write result CSVs without consistently attaching manifests, despite the stated “a result without a manifest is not a result” rule.

### Data model

Each source has its own CSV schema and date conventions. Financial/shareholding data correctly recognizes filing/broadcast time as the causal key; index changes carry announcement and effective dates; bhavcopy acquisition stores raw bytes and a fetch log. These are strong source-specific choices, but there is no enforced common record containing observation time, publication time, effective interval, retrieval time, revision/vintage, provider, source identifier, parser version, and payload hash.

## 3. What to keep, refactor, consolidate, or replace

### Keep

- Next-session fills, participation limits, explicit cash and futures cost schedules.
- Point-in-time liquidity-rule universe rather than today's index membership.
- Raw-source preservation, stable hashing, explicit `as_of`, seeded randomness, and deterministic tie-breaking.
- Fixed holdout discipline, embargo concept, placebo comparisons, non-overlapping significance checks, and hypothesis counting.
- Separation between trade-level diagnostics and capital-constrained portfolio accounting.
- Source parsers, fixtures, and the extensive domain commentary documenting real NSE quirks.
- Central page registry and thin Streamlit routing.

### Refactor

- Rename `Data test/dtest` to a real package (for example `market_intel`) and split source adapters, temporal storage, features, research, scoring, decisioning, and portfolio risk into explicit packages.
- Move all numeric strategy parameters out of signal module constants into versioned edge specifications. The configuration claim that every number lives in TOML is not currently true.
- Replace per-script loading, benchmark, simulation, placebo, logging, and output code with one `ExperimentRunner` driven by an immutable `ExperimentSpec`.
- Turn signals into registered edge definitions with prediction direction, target outcome, horizon, universe, rebalance rule, feature versions, execution model, and validation policy.
- Make every run produce a manifest automatically, not optionally.
- Put news/event acquisition behind the same ingestion boundary as market data. Streamlit must only read published snapshots.
- Convert the reports page from manually duplicated narrative logic to views over validation artifacts.

### Consolidate

- **Lab and Backtesting Framework:** one Research Workbench backed by the same experiment runner. “Lab” is exploratory configuration; “Backtests” is saved/approved runs, not a second engine.
- **Market Gate score, regime, sector context, allocation, and decision helper:** shared score/regime/decision services with different projections, not page-specific computations.
- **Risk Dashboard, Capital Protection, Event Risk, and Portfolio Impact:** one portfolio/risk engine with stress scenarios and policy outputs.
- **Data Coverage and pipeline Status:** one data catalog/observability service.
- **Correlation and Seasonality:** feature/research tools backed by the common feature and validation stores.
- Nineteen near-identical `_load_price_panels` implementations, twelve benchmark loaders, and repeated placebo/portfolio/logging blocks in experiment scripts.

### Replace

- CSV files as mutable application state (notably `data/sentiment_history.csv`) and Git as the main run database.
- Machine-specific absolute source paths in tracked configuration.
- Hard-coded live “stress score” mappings presented as quantitative evidence. Until validated, label these as descriptive indicators, not scores or edges.
- Page-owned remote calls and calculations.
- Arbitrary composite weights. A composite must use predeclared, empirically fitted/validated combination logic or remain a transparent vector of component evidence.
- The flat hypothesis log as the only edge catalog; it cannot represent versions, horizons, target definitions, regimes, lifecycle, validation folds, provenance, or decay.

## 4. Material weaknesses and risks

### Point-in-time correctness

1. **Revision handling defect in fundamental features.** `point_in_time_series` sorts by period and filing date, then keeps only the latest filing for each period. That removes the original value entirely. A later restatement therefore does not create a new vintage; it erases what was actually known between the original and revised filings. Store both vintages and perform an as-of join at each decision timestamp.
2. **No common temporal contract.** Source-specific date fields are useful but not uniformly required or validated. `effective_date` in index reconstitution is even typed as a string.
3. **Current UI analytics are not reproducible.** News/stress code reads the wall clock, fetches live sources, caches transiently, and mutates sentiment CSV state. This is acceptable for a monitor, not for a backtestable score.
4. **Corporate-action and symbol identity are not yet a full security master.** Ticker reuse, mergers, renames, delistings, instrument identifiers, listing intervals, and adjustment vintages need first-class representation.

### Validation and statistical research

1. Fixed train/validation/test splits are not walk-forward validation.
2. The framework lacks score-bucket forward outcomes, cross-sectional IC/rank IC, turnover, capacity, regime-conditioned results, stability tests, and formal decay monitors.
3. Thirty placebo seeds give a coarse empirical tail probability floor; multiple-testing control is counted but not formally applied by research family/version.
4. Benchmark excess is computed for trades, but the implementation notes that benchmark prices use close-to-close while the strategy uses executable next-open fills; comparison conventions should be declared per target and made symmetric where appropriate.
5. No purge logic is generalized by label horizon. A fixed 60-trading-day embargo can be safe or wasteful depending on the outcome horizon.
6. Hypothesis runners can touch `test` repeatedly by CLI choice; there is no policy/permission state that seals a test set after one use.

### Reproducibility and operations

1. Manifests are optional and rarely used by actual hypothesis scripts.
2. The root requirements omit research/test dependencies used in the nested project (`numpy`, `scipy`, `pytest`, `PyMuPDF`, `reportlab`, `beautifulsoup4`, Parquet support). There is no lockfile or build metadata.
3. Absolute local paths couple results to one workstation and to a separate `Dashboard` project.
4. Raw, normalized, derived, and published artifacts are mixed between tracked CSVs, ignored caches, an external SQLite database, and committed run directories.
5. The test suite could not be executed in the supplied environment because `pytest` is absent; therefore no passing-test claim is made in this audit.

### Domain/API abstractions missing

- Provider interface and source dataset registry.
- Security master and point-in-time universe membership store.
- Feature definition/version registry and materialization metadata.
- Outcome/label specification.
- Edge specification, version, lifecycle, owner, rationale, and validation policy.
- Score calibration artifact and confidence model.
- Decision policy separate from score.
- Portfolio holdings/transactions/constraints and scenario model.
- Published snapshot API for UI and AI tools.

## 5. Target architecture

Start as a **modular monolith with offline jobs**, not microservices. Use clear package boundaries and typed contracts; split deployment only when scale requires it.

```text
Providers (NSE, SEBI, RBI, AMFI, vendor adapters)
  -> Ingestion jobs + immutable raw payload store
  -> Normalization + security master + bitemporal/PIT catalog
  -> Feature registry + point-in-time materializations
  -> Outcome/label registry
  -> Edge registry + experiment runner
  -> Walk-forward/purged validation + execution/cost/portfolio simulation
  -> Score calibration + confidence + lifecycle monitoring
  -> Decision policies
  -> Portfolio/risk/scenario engine
  -> Published evidence snapshots / query API
  -> Streamlit views and constrained AI research tools
```

### Suggested package boundaries

```text
src/market_intel/
  domain/          identifiers, temporal types, enums, specs
  providers/       swappable source interfaces and implementations
  ingestion/       acquisition, raw hashing, parsing, normalization, quality
  storage/         catalog, as-of queries, repositories, migrations
  universe/        security master and PIT eligibility/membership
  features/        definitions, registry, computation, materialization
  outcomes/        forward-return/risk label definitions
  research/        edge specs, runner, folds, multiple-testing ledger
  backtest/        fills, costs, simulator, portfolio accounting
  validation/      IC, buckets, OOS/walk-forward, regimes, capacity, decay
  scoring/         calibration and score snapshots
  confidence/      evidence-quality and stability model
  decisions/       policy rules mapping evidence to implications
  portfolio/       holdings, allocation, constraints, risk, stress
  publishing/      immutable snapshots and read models
  ai/              read-only evidence tools, hypothesis drafts, explanations
apps/streamlit/    presentation only
tests/             unit, temporal-contract, integration, golden-run
```

### Storage model

For a personal system, begin with:

- Immutable raw payloads on disk/object storage, addressed by SHA-256.
- Partitioned Parquet for normalized observations, feature values, labels, and simulation events.
- DuckDB for local analytical queries.
- A small transactional catalog (DuckDB initially; PostgreSQL when concurrent writers/users justify it) for dataset versions, security identity, experiments, edges, validation runs, calibrations, lifecycle events, and published snapshots.

Every normalized observation should carry, where applicable:

```text
instrument_id, field, value,
observation_time, publication_time,
effective_from, effective_to,
retrieved_at, source_id, source_record_id,
revision_id, supersedes_revision_id,
raw_payload_hash, parser_version, quality_flags
```

Do not overwrite revisions. An as-of query selects records with `publication_time <= decision_time` and the appropriate effective interval/vintage.

### Core contracts

- `DataProvider.fetch(request) -> RawBatch`
- `Normalizer.normalize(raw_batch) -> ObservationBatch`
- `PointInTimeRepository.as_of(dataset, decision_time, universe) -> frame`
- `FeatureDefinition.compute(context, as_of) -> FeatureBatch`
- `OutcomeSpec.compute(entry_time, horizon, benchmark, risk_definition) -> LabelBatch`
- `EdgeSpec` = immutable economic hypothesis + feature versions + target + horizon + universe + execution + validation policy
- `ExperimentRunner.run(edge_version, data_snapshot, fold_plan) -> ValidationArtifact`
- `ScoreCalibrator.fit(oos_predictions, outcomes) -> CalibrationArtifact`
- `ConfidenceModel.evaluate(validation, data_quality, stability, decay) -> ConfidenceSnapshot`
- `DecisionPolicy.evaluate(score, confidence, regime, portfolio_constraints) -> DecisionSnapshot`

### Edge and score lifecycle

Use distinct objects:

1. **Raw edge prediction:** continuous signed forecast/exposure in natural units or model output.
2. **Validated score:** monotonic calibration of prediction to historical OOS outcome distribution. A 0–100 score is a percentile/probability-like presentation backed by a named calibration version, not a weighted opinion.
3. **Confidence:** separate evidence reliability measure based on OOS sample/effective sample size, uncertainty, data quality/coverage, stability across folds/regimes, cost sensitivity, multiple-testing burden, and recent decay.
4. **Decision:** policy result combining score, confidence, regime, holdings, constraints, expected horizon, and downside risk.

Edge states should be event-sourced: `DRAFT -> RESEARCHING -> VALIDATED -> ACTIVE -> WEAKENING -> SUSPENDED -> RETIRED`. Promotion/demotion rules must be declared before monitoring. Every published score references edge version, feature snapshot, calibration version, validation artifact, data snapshot, and code commit.

### Minimum validation artifact

For every edge version/horizon:

- Fold definitions, train/validation/test chronology, purge/embargo, and untouched holdout status.
- OOS predictions and outcomes.
- Score-bucket count, mean/median forward return, hit rate, excess return, drawdown/adverse excursion, turnover, and costs.
- Pearson IC where meaningful and Spearman rank IC, with effective sample size and confidence intervals.
- Walk-forward aggregate and per-fold results.
- Regime/sector/size/liquidity breakdowns with minimum sample gates.
- Portfolio simulation, benchmark, max drawdown, exposure and capacity.
- Parameter/cost sensitivity and placebo/null comparison.
- Multiple-testing family and adjusted evidence threshold.
- Recent rolling metrics, change-point/decay indicators, and lifecycle recommendation.

### AI boundary

The AI receives read-only tools over published evidence: dataset catalog, feature definitions, edge cards, validation artifacts, score explanations, portfolio exposures, and source documents. It may draft hypotheses and experiment specs, but deterministic validation must approve them; it cannot write production scores, alter edge lifecycle, or invent missing values/weights. AI output must cite artifact IDs and distinguish fact, inference, and hypothesis.

## 6. Product-page consolidation

Retain the user jobs, but make pages projections of shared engines:

| Product surface | Backing read model |
|---|---|
| Decision Center (trade/invest views) | score + confidence + regime + decision + comparable bucket history |
| Opportunity Explorer | edge/score snapshots and universe filters |
| Market & Sector Regimes | regime feature and validation snapshots |
| Portfolio & Allocation | holdings, constraints, optimizer proposals, attribution |
| Risk & Stress | factor exposure, drawdown, scenarios, event impact, protection policy |
| Research Workbench | hypothesis/edge specs, experiment runs, comparisons |
| Edge Library | lifecycle, validation cards, decay, versions |
| Data Catalog & Health | providers, coverage, vintages, quality, ingestion status |
| News & Events | normalized documents/events, entity links, publication chronology |
| Reports / AI Research | evidence-grounded narratives over immutable artifacts |

Goal tracking and tradebook can remain workflow modules, but they should consume portfolio/decision records rather than implement analytics. Options stays deferred until the instrument/security master and execution models support contracts, expiries, rolls, surfaces, and option-specific costs.

## 7. Migration plan

### Phase 0 — freeze claims and establish a baseline (1–2 days)

- Mark all current UI composites as prototype/descriptive, not validated scores.
- Inventory datasets, schemas, date semantics, file hashes, existing experiments, and known caveats into a machine-readable catalog.
- Add a reproducible `pyproject.toml`/lockfile and CI command; run the existing suite unchanged.
- Capture golden outputs for a small price/universe/signal/backtest fixture.
- Fix documentation drift (18 routes) without redesigning pages.

**Exit:** current behavior can be installed, tested, and reproduced from documented inputs.

### Phase 1 — carve out the trustworthy kernel (3–7 days)

- Create the new package skeleton and move code without behavioral changes.
- Introduce typed IDs, time fields, `DataSnapshot`, `ExperimentSpec`, and mandatory `RunManifest`.
- Relocate machine paths to environment/profile configuration.
- Wrap existing price/NSE loaders in provider/repository interfaces.
- Fix fundamental revision semantics with temporal regression tests.

**Exit:** one legacy hypothesis produces byte-equivalent outputs through the new runner and every run has provenance.

### Phase 2 — temporal data foundation (1–3 weeks)

- Build security master and alias/listing history.
- Define the common temporal observation envelope and source registry.
- Migrate bhavcopy, filings, shareholding, insider, index, and macro data incrementally to raw + normalized Parquet/catalog storage.
- Add quality contracts: uniqueness, chronology, revision behavior, coverage, stale data, unit scale, and quarantine.
- Implement true as-of query tests using adversarial late/revised records.

**Exit:** a query at historical T returns exactly the records knowable at T, with traceable source bytes.

### Phase 3 — feature/outcome registry and experiment runner (1–2 weeks)

- Register existing features with code/config/data versions, lookback, availability lag, universe, and null policy.
- Add outcome specs for 1/5/20/60-day forward return, benchmark-relative return, drawdown/adverse excursion, and risk-adjusted outcomes.
- Replace repeated test scripts with a declarative runner.
- Add purged walk-forward folds, embargo derived from horizon, cost sweeps, IC/buckets, regime slices, and multiple-testing families.
- Enforce test-set sealing through catalog state.

**Exit:** the same edge spec runs research, validation, and report generation without page/script-specific logic.

### Phase 4 — first validated score vertical slice (1–2 weeks)

- Select one edge only after data/temporal gates pass; a simple price edge is preferable for infrastructure validation even if economically rejected.
- Store OOS predictions and fit a monotonic calibration using training folds only.
- Publish raw prediction, calibrated score, confidence components, regime, horizon, bucket history, contributors, risks, and provenance.
- Implement lifecycle thresholds and rolling decay monitoring.
- Serve the snapshot to one Decision Center page.

**Exit:** one displayed score is historically reconstructible and links to its validation artifact and exact input/code versions.

### Phase 5 — portfolio and decision layer (2–4 weeks)

- Introduce holdings/transactions, tax lots if needed, benchmarks, constraints, factor/sector exposures, covariance versions, stress scenarios, and allocation policies.
- Define decision policies (`ACCUMULATE/HOLD/REDUCE/AVOID`) separately by horizon and mandate.
- Backtest decisions and rebalancing rules including turnover/costs; do not infer decisions directly from asset score thresholds.
- Add portfolio confidence and risk overrides.

**Exit:** asset evidence and portfolio context jointly produce a reproducible recommendation.

### Phase 6 — expand data and edges, then AI (ongoing)

- Add providers according to research value and temporal quality, not page demand.
- Promote only edges meeting predeclared OOS/walk-forward/economic gates.
- Add news/event entity linking and event studies before any event score.
- Add the AI assistant last, over read-only published evidence and hypothesis-drafting workflows.
- Defer options until contract-level PIT data and option execution/cost models are ready.

## 8. Immediate backlog, in order

1. Reproducible environment and full green baseline suite.
2. Temporal regression test and fix for fundamental revisions.
3. Mandatory run manifests on all experiment paths.
4. `ExperimentSpec` + common runner to remove copied scripts.
5. Dataset/source/security catalogs and common temporal schema.
6. Walk-forward/purged validation artifact with score buckets and IC.
7. Edge registry/lifecycle and score/confidence separation.
8. One thin UI vertical slice.
9. Portfolio/risk contracts.
10. Only then expand pages and AI.

## 9. Decisions to make before implementation

- Canonical instrument identifier strategy for Indian securities and historical ticker changes.
- Initial local storage choice: DuckDB catalog + Parquet is recommended; choose PostgreSQL only if concurrent writers are already required.
- First decision mandate and horizon (short-horizon trading versus long-horizon allocation) for the initial vertical slice; do not combine their labels or policies.
- Formal edge promotion/demotion thresholds and multiple-testing policy.
- Whether historical raw vendor files may be redistributed/committed; this determines artifact storage and backup design.

These decisions affect contracts. The exact future page layout does not, and should not block the foundational migration.
