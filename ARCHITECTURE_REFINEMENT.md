# Architecture refinement

Date: 2026-08-24  
Status: proposed design following review of `ARCHITECTURE_AUDIT.md`

## Two-repository boundary (R.7 amendment)

The reviewed system spans two repositories. `version2.0` is the product-facing
Streamlit dashboard, current-state display and exploratory-tool repository.
`custom_terminal` is the authoritative governance, provenance, historical-data
trust, preregistration, approval, canonical evidence and lifecycle repository.

No version2.0 analysis, backtest, validation, live-scan, recommendation or
broker output is canonical. Product components may be selectively proposed for
integration only through published read models and the custom_terminal gates;
the repositories are not merged by this architecture decision. Exact reviewed
bindings and execution paths are versioned in
`specs/cross_repository_reconciliation_v1.json`.

## Review verdict

The audit's main recommendation stands: preserve the honest research kernel, stop building page-specific engines, and prove one deterministic vertical slice before expanding the product surface.

Five refinements are necessary:

1. The original package proposal had too many top-level modules for a personal system. It risked replacing script duplication with architectural ceremony.
2. DuckDB should be the analytical query engine, not implicitly the transactional workflow database. Use SQLite for the local catalog and Parquet queried through DuckDB for analytical facts.
3. A universal field/value temporal table would become an EAV bottleneck. Keep dataset-specific typed tables and require a shared temporal/provenance envelope.
4. A 0–100 score needs an explicit semantic contract. Percentile rank, probability of a positive outcome, and expected excess return are different outputs and must never share an unlabeled number.
5. The first vertical slice must distinguish infrastructure proof from edge approval. Reproducing a rejected momentum result can validate plumbing, but must not generate an actionable production score.

## 1. Architectural principles

The system is a local-first, batch-oriented modular monolith:

- One Python codebase and one dependency graph.
- Offline acquisition, normalization, feature, research, and publishing jobs.
- Immutable analytical artifacts.
- A small workflow/catalog database.
- Streamlit reads published snapshots and submits research jobs; it does not calculate quantitative truth.
- No microservices, event bus, separate feature-store product, or model-serving platform until measured scale requires them.

The most important boundary is not UI versus backend. It is:

```text
historically reconstructible evidence | current workflow and presentation
```

Anything left of that boundary must be replayable with an explicit knowledge cutoff. Anything right of it may use current time, but cannot silently become historical evidence.

## 2. Six bounded contexts

### A. Data foundation

Owns providers, acquisition, immutable raw payloads, normalization, security identity, data quality, temporal semantics, and as-of queries.

It answers: **What was knowable about this instrument at decision time T, and from which source bytes?**

### B. Research foundation

Owns universes, feature definitions, outcomes/labels, edge definitions, experiment plans, folds, simulation, statistical validation, and the multiple-testing ledger.

It answers: **Did information available at T predict a predeclared outcome after T under executable assumptions?**

### C. Evidence and scoring

Owns validated edge versions, calibration artifacts, comparable-score histories, uncertainty/confidence, decay monitoring, lifecycle state, and published asset/regime evidence.

It answers: **What does the current prediction mean in terms of genuinely out-of-sample historical evidence, and how reliable is that evidence now?**

### D. Portfolio and decisions

Owns holdings, transactions, mandates, constraints, benchmark policy, allocation proposals, portfolio simulation, exposure, drawdown, stress scenarios, and decision policies.

It answers: **Given evidence plus this portfolio and mandate, what action—if any—is justified?**

### E. Application and publishing

Owns immutable read models, job submission/status, Streamlit routes, reports, exports, and data-health views.

It answers: **How is approved evidence safely exposed without reimplementing calculations?**

### F. AI research assistant

Owns read-only evidence tools, source-document retrieval, explanation, comparison, research-question decomposition, and draft hypothesis/experiment specifications.

It answers: **How can evidence be interpreted and new tests proposed without making the AI the numerical authority?**

These are code ownership boundaries, not processes or deployable services.

## 3. Refined runtime and storage design

```text
Provider jobs
  -> raw/{provider}/{dataset}/{retrieval_id}/payload + manifest
  -> normalized typed Parquet + dataset-version manifest
  -> PIT feature/outcome Parquet + materialization manifest
  -> experiment artifacts (OOS predictions, trades, folds, metrics)
  -> approved evidence snapshots
  -> Streamlit / reports / AI read tools

SQLite catalog
  datasets, instruments, aliases, jobs, experiment specs/runs,
  edge versions, lifecycle events, artifact pointers, publication state

DuckDB
  read/query/join Parquet analytical facts; generate validation read models
```

### File roles

- **Raw store:** immutable source response and request metadata. Never parsed in place or overwritten.
- **Normalized store:** typed, dataset-specific Parquet tables.
- **Derived store:** universe, feature, label, prediction, trade, portfolio, and validation facts.
- **Published store:** immutable JSON/Parquet snapshots safe for application and AI consumption.
- **SQLite catalog:** mutable workflow state and pointers to immutable artifacts.

SQLite must not hold large price/feature matrices. Git may keep code, schemas, compact manifests, experiment specifications, and small golden fixtures; it should not be the primary raw-data or run-artifact store.

### Temporal contract

Do not force every dataset into a generic field/value table. Each typed normalized table must include the applicable subset of this envelope:

```text
instrument_id           stable internal identifier
event_time              when the observed event economically occurred
period_start/end        period described by the observation, if any
published_at            first source timestamp at which it became public
effective_from/to       interval where a rule/membership/status applies
retrieved_at            when this system obtained the payload
source_id               provider + dataset
source_record_id        provider's record key, when available
revision_number         source or system vintage sequence
supersedes_record_id    prior published vintage, never destructive overwrite
raw_payload_hash        exact source evidence
parser_version          code/schema version
quality_flags           structured flags, not free-text only
```

The causal availability timestamp is dataset-specific but explicit:

```text
available_at = availability_policy(record)
```

Examples:

- Daily bhavcopy close: exchange session close plus a declared processing lag.
- Filing: broadcast timestamp; if time zone/intraday precision is absent, conservatively available after that session.
- Index change: announcement is knowable at `published_at`; membership applies at `effective_from`. These support different features.
- Revised filing: original and revised records both remain; an as-of query returns the latest vintage published by T, not the final vintage known today.

Every as-of query requires both `knowledge_cutoff` and `decision_clock` (for example, `NSE_CLOSE` or `NEXT_OPEN`). Date-only comparison is insufficient when publication times exist.

## 4. Security master and universe model

Ticker strings cannot be primary keys. Introduce:

- `instrument_id`: listed tradable instrument.
- `issuer_id`: economic company/entity.
- `listing_id`: exchange/listing identity if distinct from instrument.
- Identifier aliases with validity intervals: NSE symbol, ISIN, vendor ticker.
- Corporate-action/event links: split, bonus, merger, demerger, rename, delisting, relisting.

Universe definitions are versioned rules, not stored lists alone. A materialization records:

```text
universe_definition_version
decision_time
eligible instrument_ids
membership reason / exclusion reason
input dataset versions
```

Keep the existing liquidity-rule universe as the first definition. Historical index membership can later be another definition; it should not replace the liquidity universe or be retroactively inferred.

## 5. Research objects and artifact graph

### Feature definition

```text
feature_id + version
economic meaning
input datasets and versions
availability lag
lookback and minimum history
cross-sectional or time-series scope
null/staleness policy
calculation code hash
parameters
```

Feature values are keyed by `(feature_version, instrument_id, decision_time)` and carry an input snapshot ID.

### Outcome definition

An outcome is not merely “future return.” It declares:

```text
entry clock and executable price convention
horizon / exit clock
absolute or benchmark-relative target
corporate-action handling
cost inclusion
risk outcomes (MAE, MFE, drawdown) where relevant
missing/delisting treatment
```

Delisting and unavailable exit prices must produce explicit economic handling, not dropped samples.

### Edge definition

An edge version binds:

```text
predeclared economic hypothesis
prediction function
feature versions
outcome version and horizon
universe version
direction and monotonicity expectation
execution/cost version
fold plan
primary metric and acceptance gates
secondary diagnostics
research family / multiple-testing ledger
```

An edge emits a continuous prediction when the hypothesis supports one. Boolean triggers remain valid for genuine event edges but should not be imposed on ranking/factor research.

### Experiment artifact graph

Every run has one root manifest linking:

```text
code commit + dirty-worktree fingerprint
environment lock hash
experiment spec hash
input dataset snapshot hashes
feature/outcome/universe versions
fold plan and seeds
execution/cost/portfolio versions
output artifact hashes
parent run / superseded run
```

Manifests are constructed by the runner and cannot be opted out of. Diagnostics are runs too, but are labeled `DIAGNOSTIC` and cannot promote an edge.

## 6. Validation protocol

### Research phases

1. **Draft:** hypothesis and primary test specified before outcome inspection.
2. **Development:** expanding/rolling training folds; parameters selected only here.
3. **Confirmation:** locked candidate evaluated on later walk-forward folds.
4. **Holdout:** one sealed final interval, consumed once per edge family/version under an explicit approval event.
5. **Monitoring:** forward results after activation; never folded back into the original OOS claim.

“Sealed” is workflow governance, not pretend cryptographic secrecy from the owner. The catalog records every access and prevents accidental reuse by normal commands.

### Fold construction

- Use expanding-window walk-forward by default for Indian equities.
- Purge training labels whose outcome windows overlap validation.
- Derive embargo from the maximum outcome/execution horizon, rather than one global 60-day constant.
- Fit all transforms, winsorization, imputation, ranking cutoffs, regimes, combination weights, and calibrators inside each training fold.
- Apply universe eligibility and source availability independently at each historical decision time.

### Required reports

Report three layers separately:

1. **Prediction quality:** IC/rank IC, calibration, bucket monotonicity, effective sample size, uncertainty intervals.
2. **Economic quality:** gross/net forward outcomes, turnover, slippage/cost sensitivity, capacity/liquidity, adverse excursion, regime/sector robustness.
3. **Portfolio quality:** realizable capital curve, benchmark-relative return, drawdown, concentration, exposure, skipped orders, and stress behavior.

Avoid a universal acceptance formula. Each edge version declares a primary metric appropriate to its prediction type, plus minimum universal gates:

- Point-in-time and leakage checks pass.
- Minimum effective OOS sample size passes.
- Net economics survive the declared cost range.
- Results are not dependent on one fold, sector, or tiny subgroup.
- Multiple-testing policy for its research family passes.
- Prediction-to-outcome relationship has the declared direction and adequate stability.

### Multiple testing

The current hypothesis count is valuable but insufficient. Add:

- Research-family identifier.
- All attempted versions, including diagnostics that informed later choices.
- False-discovery control or family-wise threshold chosen before confirmation.
- Deflated/probabilistic Sharpe diagnostics where portfolio Sharpe is selected.
- A clear distinction between exploratory findings and confirmatory claims.

## 7. Score semantics

The system may display `82/100`, but the stored evidence must remain richer.

### Required score outputs

```text
raw_prediction          e.g. 0.73 z-score or model output
score_0_100             display-oriented calibrated ordering
score_definition        e.g. OOS conditional-outcome percentile
expected_outcome        e.g. +1.4% 20-day excess return
expected_outcome_band   uncertainty interval
positive_outcome_prob   when statistically supported
horizon
calibration_version
comparable_bucket_id
```

Recommended initial definition:

> `score_0_100` is the percentile of the current raw prediction within the calibration population, oriented so higher predicts a better declared outcome.

This is interpretable and monotonic, but it does **not** mean an 82% chance of profit. Expected outcome and probability remain separately labeled empirical estimates from OOS neighbors/buckets or a validated calibrator.

### Edge combinations

Do not average edge scores. Combine edges only when a combination model is itself an edge version with:

- Training-fold-only fitting.
- Correlation/redundancy control.
- OOS validation against a declared outcome.
- Comparison against every component and a simple baseline.
- Turnover and stability analysis.

Until then, show an evidence vector: momentum evidence, value evidence, regime evidence, event risk, and so on.

## 8. Confidence and lifecycle

Confidence must not become another arbitrary weighted score. Store transparent components:

```text
statistical_uncertainty
effective_sample_size
fold_stability
regime_coverage
data_quality_and_freshness
cost_and_parameter_robustness
multiple_testing_burden
recent_decay
```

The default user-facing representation should be `LOW / MODERATE / HIGH` plus the main limiting factors and intervals. If a 0–100 confidence number is required, its mapping must be versioned and calibrated against subsequent reliability; until that history exists, label it an evidence-completeness index rather than probability/confidence.

Lifecycle rules are deterministic and event-recorded:

```text
DRAFT -> RESEARCHING -> VALIDATED -> ACTIVE
ACTIVE -> WEAKENING -> SUSPENDED -> RETIRED
```

- `WEAKENING`: monitoring breach but insufficient evidence for suspension.
- `SUSPENDED`: do not use in new decisions; retain historical output.
- `RETIRED`: structural rationale/data/execution no longer applies or repeated confirmation fails.

Monitoring thresholds, evaluation frequency, minimum new observations, and hysteresis are specified at activation so a noisy bad month does not churn lifecycle state.

## 9. Decision and portfolio semantics

There is no universal asset recommendation. A decision is scoped to:

```text
mandate_id
portfolio_snapshot_id
instrument_id
decision_time
horizon
score/evidence snapshot
confidence assessment
regime snapshot
constraints and current holdings
decision-policy version
```

`ACCUMULATE`, `HOLD`, `REDUCE`, and `AVOID` must mean different things for a 20-day trading mandate and a five-year allocation mandate. Policies need their own backtests, including rebalance cadence, turnover, tax assumptions where material, and risk overrides.

The portfolio engine should initially be deterministic accounting and rule evaluation, not an optimizer. Add optimization only after expected returns, covariance, constraints, estimation error, and turnover penalties are versioned and validated. A fragile optimizer fed weak scores creates false precision.

## 10. Application and AI read models

Publish a single `AssetEvidenceSnapshot` shape for the Decision Center:

```text
instrument, decision_time, horizon
raw prediction and score definition
expected outcome + interval
confidence band + limiting factors
regime
edge lifecycle state
comparable OOS bucket history and sample size
main deterministic contributors
portfolio-aware implication, if a mandate is selected
risks / invalidation conditions
artifact and provenance links
freshness/status flags
```

If evidence is stale, missing, suspended, or below a confidence gate, publish `NO_DECISION` rather than filling fields heuristically.

The AI can:

- Explain a published snapshot.
- Compare edge versions and regimes.
- Retrieve source records and validation artifacts.
- Draft hypotheses and experiment specs.
- Summarize failure/decay evidence.

The AI cannot:

- Calculate or overwrite quantitative outputs.
- promote lifecycle state;
- choose undeclared weights;
- treat exploratory diagnostics as confirmed evidence;
- give a decision when deterministic policy returned `NO_DECISION`.

## 11. Refined code layout

Use fewer top-level packages initially:

```text
pyproject.toml
src/market_intel/
  foundation/       providers, ingestion, temporal storage, security master
  research/         universe, features, outcomes, edges, folds, runner
  simulation/       fills, costs, trade and portfolio simulation
  evidence/         validation, calibration, confidence, lifecycle, publishing
  portfolio/        holdings, risk, stress, mandate-specific decisions
  application/      queries, job commands, read models, AI tool boundary
apps/streamlit/
tests/
  unit/
  temporal/
  integration/
  golden/
```

Internal modules may split as they grow. Dependencies flow downward:

```text
application -> portfolio/evidence -> research/simulation -> foundation
```

`foundation` never imports research or Streamlit. Research definitions never fetch live data. Application code never imports source-specific parsers directly.

## 12. First two vertical slices

### Slice A — infrastructure proof, explicitly non-actionable

Reproduce the existing 12–1 momentum experiment through the new contracts:

1. Ingest/version bhavcopy and benchmark inputs.
2. Materialize the existing liquidity universe.
3. Register momentum feature, outcome, edge, costs, and experiment spec.
4. Run existing fixed-window behavior as a golden compatibility test.
5. Run new purged expanding walk-forward validation.
6. Publish a research artifact with its actual lifecycle result—likely `REJECTED`/`RETIRED`, not an asset recommendation.

This slice proves parity, manifests, temporal joins, artifact lineage, and the runner without pretending an edge exists.

### Slice B — first publishable evidence

Choose a candidate only after preregistration and data-quality review. It must:

- Produce continuous predictions across a useful cross-section.
- Have adequate historical coverage for walk-forward folds.
- Use a clear 20- or 60-day outcome and executable convention.
- Survive net costs and simple baselines.
- Pass the promotion gates above.

Only then fit a calibration, publish an `AssetEvidenceSnapshot`, and connect one Streamlit Decision Center route. If no candidate passes, the correct product output is an Edge Library showing zero active edges and their rejection evidence.

## 13. Revised implementation sequence

1. Package/environment lock and executable test baseline.
2. Golden compatibility fixture for one existing hypothesis.
3. SQLite catalog schema, artifact store paths, and mandatory manifest writer.
4. Security identifiers plus dataset-specific temporal contracts.
5. Fix and test revision-vintage semantics.
6. Common runner and immutable experiment specification.
7. Outcome registry and horizon-derived purge/embargo.
8. Walk-forward OOS prediction store and validation reports.
9. Edge version/lifecycle and multiple-testing ledger.
10. Score calibration and transparent confidence assessment.
11. Published evidence snapshot and one thin Streamlit page.
12. Holdings/mandates, risk, and backtested decision policies.
13. News/event studies, broader datasets, and read-only AI tools.

## 14. Architecture decisions now resolved

- **Deployment:** local modular monolith and batch jobs.
- **Analytics storage:** typed partitioned Parquet queried with DuckDB.
- **Workflow catalog:** SQLite initially.
- **UI:** Streamlit remains, as a thin client/read-model renderer.
- **Backtesting:** one experiment runner; Lab and Backtesting become modes of one Research Workbench.
- **Scores:** calibrated, explicitly defined, and never arbitrary averages.
- **Confidence:** transparent evidence assessment first; calibrated numeric confidence only after reliability history exists.
- **AI:** read-only over approved artifacts plus draft-spec creation.
- **Options:** deferred until instrument, expiry, surface, execution, and cost contracts exist.
- **Pre-research owner review:** every future market analysis requires a
  current rendered status PDF, deterministic research-state fingerprint and
  explicit post-generation owner review before preregistration; this report
  gate never replaces the separate run-specific approval.

Open choices should now be limited to instrument identifier sourcing, raw-data retention/licensing, the exact first publishable edge candidate, and mandate-specific decision policy—not the broad architecture.
