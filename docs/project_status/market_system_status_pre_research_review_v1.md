# Market System Development - Status and Pre-Research Review

Report version: R.7 / v1
Generation date: 1 September 2026
Summarized source commit: bc3f11f
Research-state fingerprint: f40ba4e841fdc8839a039e29ed7deff03cf57b21b9ae303bbc03ac8ac0176c70
PDF review status: PENDING USER REVIEW

NO MARKET ANALYSIS, SIMULATION, BACKTEST, DATA ACQUISITION, OR RESEARCH EXECUTION IS AUTHORIZED BY THIS REPORT.

[PAGE BREAK]

## Executive summary

This project is building a personal Indian-market research system that can explain what it knows, reproduce how it knew it, test ideas honestly, and keep investment decisions separate from unverified calculations. Its eventual purpose is decision support for trading, investing, asset allocation, portfolio balance, and downside risk. It is not yet an automated trading system, and it does not currently have an approved investment edge or production score.

The development order deliberately puts trust before strategy testing. A statistically attractive result is not useful if the historical population excludes failed companies, if ticker identities are wrong, if corporate actions are missing, or if today's transaction costs are applied to old trades. The project therefore stopped momentum research when the local data was shown to be survivor-selected and incomplete.

What is working now is the research machinery: versioned contracts, immutable evidence, point-in-time concepts, deterministic tests, one-use approvals, a governed execution gateway, and an independently audited three-row synthetic canary. The canary proved infrastructure behavior only. It did not test an investment idea.

The main blocker is data trust. The local panel contains useful price history, but it is not a complete historical market population. Only three of twelve dated security-snapshot and bhavcopy pairs qualified. Stable identity, inactive securities, economic terminal outcomes, authoritative corporate actions, NIFTY PRI/TRI history, complete dated statutory costs, and access/retention rights remain incomplete.

The proposed direction is cautious: review this report first, define one bounded free-source capability question, qualify access and retention, run a small data pilot only if permitted, and only later preregister a descriptive or falsification study. A separate exact run approval would still be required.

### Current overall status

| Area | Status | Meaning |
|---|---|---|
| Architecture | ESTABLISHED | A modular local research architecture and dependency direction are defined. |
| Research governance | PROVEN FOR SYNTHETIC CANARY | One bounded non-market canary completed and was independently audited. |
| Historical equity data | NOT TRUSTED | The current panel is survivor-selected and cannot support complete-market claims. |
| Historical population | FAIL | Only 3 of 12 locked security/bhavcopy pairs qualified. |
| Market research execution | BLOCKED | This PDF is pending review; data and run-specific gates also remain closed. |
| Production score or recommendation | NOT AVAILABLE | No edge has passed the required validation and evidence chain. |

[PAGE BREAK]

## What are we trying to build?

The intended system is a trustworthy Indian-market research foundation. It should collect point-in-time evidence, preserve revisions, calculate features deterministically, define future outcomes before looking at them, validate hypotheses out of sample, and publish evidence that can be independently reconstructed.

The core chain is:

Data sources -> immutable raw evidence -> typed normalized data -> point-in-time features -> declared outcomes -> governed experiments -> validation -> scores and confidence -> decision policy -> portfolio and risk support.

Three kinds of evidence must remain separate:

- Prediction evidence asks whether a feature ranks or forecasts later outcomes.
- Economic evidence asks whether the relationship survives execution assumptions, costs, turnover, capacity, and adverse excursions.
- Portfolio evidence asks what happens when positions interact through concentration, exposure, drawdown, cash, and constraints.

A research idea should move through exploration, validation, one-time test, independent replication, and only then production consideration. A result can be rejected at any stage. A 0-100 score, if eventually built, must be a calibrated representation of validated out-of-sample evidence. Confidence must be separate from the raw score, and the final decision must also consider regime, holdings, horizon, risk, and mandate.

The system is not yet able to claim complete-market historical results, survivorship-safe portfolio performance, delisting-aware returns, verified total-return comparisons, production-grade momentum, actionable asset scores, or live portfolio recommendations. It implements no production research approval from this PDF and no automated trade execution.

[PAGE BREAK]

## What has been completed?

### Architecture review and refinement

Purpose: replace a page-by-page Streamlit scaffold and a separate script-heavy research laboratory with one modular system.
Result: a local modular monolith was selected, using typed contracts, Parquet for analytical facts, DuckDB for queries, SQLite for workflow state, immutable artifacts, and a thin Streamlit layer.
Significance: shared engines should serve multiple pages rather than duplicate calculations.
Evidence type: architecture and infrastructure only.

### Momentum Vertical Slice A

Purpose: migrate the existing 12-1 momentum experiment through reproducible data, feature, outcome, experiment, manifest, cost, and walk-forward contracts.
Result: deterministic infrastructure, a golden compatibility fixture, explicit execution assumptions, manifests, and validation layers were created. The result remained non-actionable.
Significance: the slice exposed trust problems instead of manufacturing a favorable edge.
Evidence type: compatibility and research-process evidence; not production investment evidence.

### Dataset trust and survivorship audit - Slice A.5

Purpose: determine whether the local historical panel represented the historical market.
Result: NOT TRUSTED for cross-sectional equity-edge research. The 294 mapped equities behave like present-day survivors with attached back history. A separate historical reference contains 1,699 symbols absent from the panel.
Significance: causal calculations inside the panel do not make the population complete.
Evidence type: data-quality evidence.

### Provider-neutral ingestion - Slice A.6

Purpose: prepare replaceable ingestion, typed schemas, immutable raw manifests, identity resolution, reconciliation, and dataset acceptance.
Result: an end-to-end local dry run produced 1,166,839 price rows but failed the required trust capabilities.
Significance: future sources can be judged by the same contract rather than trusted by reputation.
Evidence type: infrastructure and data-quality evidence.

[PAGE BREAK]

### Official public-source qualification - Slices A.7 to A.10

Purpose: determine whether legally accessible official public sources can reconstruct population, identity, lifecycle, benchmarks, and costs.
Result: the 12-date sample retrieved every bhavcopy but only three dated security snapshots. Direct population reconstruction failed at 3/12; event reconstruction also failed because no complete event ledger was proved. Automated NSE collection was classified as prohibited by the reviewed terms, and retention/derived-use questions require review. No substantive written NSE response was available.
Significance: a public file existing on a webpage is not proof of permission, continuity, completeness, or research suitability.
Evidence type: bounded source-access and sample-qualification evidence.

### Security identity, corporate actions, terminal outcomes, benchmarks, and costs

Purpose: prevent ticker stitching, invented delisting values, destructive price adjustment, PRI/TRI confusion, and current-cost backfilling.
Result: typed models and fail-closed checks exist, but authoritative historical evidence is incomplete. All 294 local equity identities remain unresolved. Three sampled delistings have no proven economic consideration. One symbol transition qualified; split, bonus, dividend, rights, demerger, and complete terminal quotas did not. The local NIFTY file is PRI-like only, and the historical statutory-cost schedule is incomplete.
Significance: the system now says UNKNOWN or FAIL rather than guessing.
Evidence type: contract and gap evidence.

### Current-market Kite path - Slices A.11 and A.12

Purpose: provide a separate, read-only, in-memory current-market health path.
Result: daily login, current inventory, bounded quotes, sanitization, explicit endpoint allowlist, and current-only coverage health were implemented.
Significance: this helps present-time monitoring but cannot reconstruct historical populations or validate research.
Evidence type: current operational infrastructure only.

[PAGE BREAK]

### Research evidence reconciliation - R.1 and R.2

Purpose: reconcile the older laboratory with the newer trust system without rewriting history.
Result: 32 legacy rows were preserved: 26 rejected and 6 accepted under the old vocabulary, across 13 reviewed families. None has a verified run manifest; every row is production-ineligible. The one legacy validation-confirmed momentum row remains exploratory because it lacks the new preregistration, population, identity, terminal, cost, and test/replication chain.
Significance: preservation is not retroactive validation.
Evidence type: quarantined legacy evidence.

### Future governance contracts - R.3 and R.4

Purpose: close canonical research execution behind complete preregistration, immutable inputs, split access, manifests, approval, and import validation.
Result: the governance catalog is hash-linked; every attempt must produce an atomic bundle and root manifest; direct laboratory scripts are marked noncanonical. Exact one-use approval is mandatory, while wall-time and memory declarations remain unenforced.
Significance: future evidence has a controlled lineage and cannot become canonical merely because a script produced a result.
Evidence type: governance infrastructure.

### Synthetic canary - R.5 and R.6

Purpose: prove the governance mechanism on three synthetic rows without market data.
Result: one canary was proposed, separately approved, executed once, consumed its approval, produced three declared artifacts, created one canonical record, and passed an independent byte-level audit with zero mismatches. Its lifecycle is `INFRASTRUCTURE_CANARY_COMPLETED` and promotion eligibility is permanently false.
Significance: the governance machine works for a bounded non-market case.
Evidence type: infrastructure evidence only.

[PAGE BREAK]

## What do we currently have?

### Application and package architecture

- A Streamlit product scaffold organized by user job.
- A provider-neutral market-intelligence package with foundation, research, simulation, evidence, portfolio, and application boundaries.
- A separate legacy `Data test` laboratory whose direct outputs are explicitly noncanonical.
- Versioned temporal, identity, feature, outcome, universe, cost, benchmark, experiment, manifest, approval, and governance contracts.

### Data and fixtures

- A local 430-file price directory, including 294 currently mapped equities, benchmarks, and unresolved instruments.
- A normalized dry-run panel with 1,166,839 price rows.
- Twelve official bhavcopies in the locked population sample, but only three corresponding historical security snapshots.
- Small deterministic fixtures for point-in-time, identity, lifecycle, cost, benchmark, governance, and canary tests.
- A three-row synthetic canary fixture that contains no market observations.

The local historical price panel must be described as a point-in-time liquidity rule over the observed historically traded panel. It must not be described as the complete historical NSE listed population.

### Governance and evidence

- A hash-linked governance event catalog.
- One independently audited, nonpromotable canonical canary record.
- A tracked sanitized canary anchor containing exact hashes.
- A preserved neutral legacy ledger and separate legacy evidence catalog.
- An entry-point inventory with zero known unsafe canonical bypasses.
- A permanent pre-research PDF policy introduced by this milestone.

### Current verification baseline

- Main project suite: 230 passed, with two known deprecated-runner warnings.
- Separate Data-test suite: 289 passed, with existing third-party SWIG and noncanonical-log warnings.
- Focused R.7 gate and PDF suite: 17 passed.
- Combined R.3-R.7 governance suite: 94 passed.

[PAGE BREAK]

## What remains unresolved?

### Research blockers

| Blocker | Current finding | Why it matters |
|---|---|---|
| Historical listed population | FAIL | Missing inactive and terminated listings can create survivorship bias. |
| Historically traded population | UNKNOWN | Twelve sample files do not prove continuous coverage or retained revisions. |
| Stable security identity | FAIL | Ticker strings cannot safely join names through symbol, ISIN, merger, or listing changes. |
| Suspension and delisting history | UNKNOWN / FAIL | Missing states can distort eligibility, fills, marks, and returns. |
| Economic terminal outcomes | FAIL | Last quoted price is not delisting or merger consideration. |
| Corporate actions | UNKNOWN | Raw discontinuities do not prove action type, ratio, or total return. |
| Benchmark PRI/TRI | PARTIAL / UNKNOWN | PRI cannot be silently presented as dividend-inclusive TRI. |
| Historical statutory costs | INCOMPLETE | Current rates cannot be carried backward into historical trades. |
| Access, retention, licensing | REQUIRES REVIEW | Technical accessibility is not permission to automate or retain an archive. |

### Important hardening, but not the primary data blocker

- The filesystem owner can rewrite local files. Hash chains detect changes only relative to separately preserved anchors.
- Ignored raw canary evidence lacks a documented backup, retention, restore-test, and access policy.
- The declared five-second wall time and 64 MiB memory limit were not process-enforced during the canary.
- The canonical evidence catalog has one exact anchored record but no record-to-record hash chain.

These items matter before serious governed research, but fixing them would not make incomplete historical data trustworthy.

[PAGE BREAK]

## Free-source constraint and opportunities

Paid market-data providers are unavailable for this project. Free-source work must therefore separate six different questions: Is the object public? Is access lawful? Is automation permitted? Is local retention permitted? Is the history complete? Is it point-in-time correct and fit for the intended claim?

| Source | Potential role | Current caution |
|---|---|---|
| NSE | Bhavcopies, security files, corporate filings, listing and delisting notices | Pre-February-2024 security snapshots and retention rights remain unresolved; systematic collection was not authorized. |
| BSE | Independent listing codes, security references, corporate actions, lifecycle evidence | BSE listings must remain distinct from NSE listings; no complete historical reconciliation is qualified. |
| SEBI | Regulations, orders, delisting and scheme evidence | Strong event/legal evidence, but not a complete daily exchange population. |
| AMFI | Mutual-fund NAVs and fund-industry information | Relevant only to future mutual-fund questions; not equity identity or survivorship evidence. |
| RBI | Rates, liquidity, currency, credit, and macro publications | Potential macro context; each series still needs release-vintage and revision treatment. |
| Government publications | Taxes, stamp duty, GST/service-tax history, official calendars | Useful for date-effective costs; documents must be assembled with supersession links. |
| Issuer filings | Action terms, merger/demerger schemes, consideration, dates | Case-specific supplements; conflicts cannot silently override exchange evidence. |

No source is qualified merely because a webpage, download button, PDF, or current file exists. A useful future source must pass access, immutable provenance, identity, population, correction, and intended-use checks.

[PAGE BREAK]

## What should happen next?

### Staged program

1. The owner reads this PDF and records corrections or explicit approval of the covered planning scope.
2. Define one bounded free-source capability question, not an alpha hypothesis.
3. Identify official evidence and qualify manual access, automation, retention, correction, and derived-use conditions.
4. Define a small acquisition pilot with a fixed object list, request budget, cache, abort rules, and no outcome selection.
5. Verify identity, lifecycle, population, benchmark, and cost coverage before any empirical claim.
6. Regenerate and re-review this PDF if an included research-state byte changes.
7. Preregister one bounded descriptive or falsification study only if its required capabilities pass.
8. Obtain a separate exact one-use run approval after preregistration and input binding.
9. Only then allow the governed gateway to conduct that exact analysis.

### Go criteria

- Owner explicitly approves the exact current report and covered scope after PDF generation.
- The proposed source has documented access and retention conditions compatible with personal non-commercial research.
- The pilot question is answerable without pretending observed traded rows are the complete listed market.
- Required identities, event timing, benchmark class, cost intervals, and missing-data treatment are declared.
- Research-relevant state fingerprint still matches this report.
- A complete preregistration and separate run-specific approval exist.

### Stop criteria

- CAPTCHA, authentication bypass, prohibited automation, persistent rate limiting, or unclear retention rights.
- Missing required official objects, unrecognized schema, mutable content without preserved vintages, or unresolved identity keys.
- A proposed claim requires complete historical population, delisting economics, or TRI/cost evidence that is not available.
- Any request to choose parameters, periods, or hypotheses because preliminary outcomes look favorable.
- Any attempt to treat PDF approval as run authorization.

[PAGE BREAK]

## Proposed future analysis boundary

This report covers only `BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING`. After explicit review, that scope would permit planning and preregistration preparation, not analysis or acquisition by itself.

Questions that might eventually be supportable, subject to source-specific gates, include:

- Descriptive properties of securities actually observed trading on a session.
- Liquidity and exchange-turnover distributions within a clearly stated observed-traded population.
- Coverage, missingness, schema-transition, and identifier-quality studies.
- Signal behavior conditional on continuous observed history, clearly censored and nonpromotable.
- Infrastructure falsification tests designed to expose leakage, identity, cost, or universe failures.
- Macro descriptive studies using official release-vintage data, if revisions and publication timing are preserved.

Claims that remain prohibited include:

- Complete-market cross-sectional alpha.
- Survivorship-safe historical portfolio performance.
- Delisting-aware or merger-aware total returns.
- Production-grade 12-1 momentum.
- Actionable 0-100 scores or edge lifecycle promotion.
- Live portfolio allocation, accumulation, reduction, or avoidance recommendations.
- Automated or manual trading actions based on research output.

R.7 selects no investment hypothesis, parameters, period, security, or favorable-looking strategy.

[PAGE BREAK]

## Decisions requested from the owner

Please review and answer each question explicitly:

1. Is the project objective correct: a trustworthy research and capital-allocation support system rather than a fast signal generator?
2. Is the development order acceptable: governance and data qualification before strategy testing and scoring?
3. Is the no-paid-data constraint represented accurately and expected to remain in force?
4. Should any milestone or priority be changed before more data work?
5. Should optional governance hardening - raw-evidence backup, enforced process limits, or canonical-catalog chaining - happen before source planning?
6. Do you approve proceeding only to a bounded free-source capability-planning phase under scope `BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING`?
7. What corrections or clarifications must be incorporated into a revised PDF before approval?

An acceptable approval must identify this report/version and occur after PDF creation. A reply such as "continue," earlier approval, or approval of the synthetic canary does not satisfy this report gate. Even explicit PDF approval does not authorize data acquisition, analysis, simulation, backtesting, or a research run.

[PAGE BREAK]

## Appendix A - Milestone timeline and decision status

| Milestone | Result | Evidence class |
|---|---|---|
| Architecture audit/refinement | Modular target approved | Architecture |
| Slice A | Reproducible momentum infrastructure; non-actionable | Research-process |
| Slice A.5 | Local equity dataset NOT TRUSTED | Data quality |
| Slice A.6 | Provider-neutral ingestion ready; local dry run rejected | Infrastructure/data quality |
| Slices A.7-A.8 | Public samples incomplete; population reconstruction failed | Source/sample qualification |
| Slices A.9-A.10 | Official-response gate remains closed | Access governance |
| Slices A.11-A.12 | Read-only current Kite coverage ready | Current-market infrastructure |
| R.1-R.2 | Legacy evidence preserved and quarantined | Legacy evidence |
| R.3-R.4 | Governed execution and one-use approval contracts | Governance infrastructure |
| R.5 | Synthetic canary proposal | Infrastructure proposal |
| R.6 | Canary executed once and independently audited PASS | Infrastructure evidence |
| R.7 | Status PDF generated; owner review pending | Governance/documentation |

Important current decisions:

- Dataset: NOT TRUSTED for cross-sectional equity-edge research.
- Historical population: reconstruction incomplete.
- Official response: AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE.
- Canary: GOVERNED_CANARY_AUDIT_PASSED.
- Research report gate: REPORT_GENERATED_PENDING_REVIEW.
- Market research, acquisition, simulation, backtesting, and scoring: BLOCKED.

[PAGE BREAK]

## Appendix B - Evidence and report index

Key sources used to reconcile this report:

- `ARCHITECTURE_AUDIT.md` and `ARCHITECTURE_REFINEMENT.md`.
- `reports/SLICE_A_REPORT.md` and Slice A.5 through A.12 reports.
- `reports/DATASET_TRUST_REPORT.md` and `reports/HISTORICAL_DATA_REQUIREMENTS.md`.
- `reports/HISTORICAL_POPULATION_QUALIFICATION.md`.
- `reports/OFFICIAL_LIFECYCLE_QUALIFICATION.md`.
- `reports/BENCHMARK_AUDIT.md` and benchmark public-data qualification.
- `reports/COST_MODEL_AUDIT.md` and historical cost qualification.
- `reports/RESEARCH_SYSTEM_RECONCILIATION.md` and R.2 through R.6 reports.
- `reports/FUTURE_RUN_GOVERNANCE.md` and `reports/GOVERNED_EXECUTION_OPERATIONS.md`.
- `evidence/governance/canary_execution_anchor_v1.json`.
- `specs/pre_research_review_policy_v1.json`.

Key hashes:

| Object | SHA-256 |
|---|---|
| Canary approval file | 326afafdee722925c3fafbdbe3dc6b33ee61e0f2b7aaa48f564e8b6e993378e5 |
| Canary root manifest | bdb3ee240ce2939dff6c523c305d5affdf9cd6b4deaf1fd0995efe675a9c40fb |
| Canary governance terminal event | 9ddfaedf8fb0dd113417645b127c7dd3c021c478ae89b1648cf5e5d3caa5a0bb |
| Canary canonical record | 63f9fa81774313355033841960a34c2f1ef6ef5c1ffdc69c34c0a652e6fa0c6e |
| Frozen legacy log | 124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d |
| Neutral legacy ledger | 79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392 |
| Research-state fingerprint | f40ba4e841fdc8839a039e29ed7deff03cf57b21b9ae303bbc03ac8ac0176c70 |

[PAGE BREAK]

## Appendix C - Glossary

| Term | Plain-language meaning |
|---|---|
| Point-in-time | Uses only information that was knowable at the historical decision time. |
| Survivorship bias | Results look better because securities that later failed or disappeared are absent. |
| Stable identity | An internal security/listing ID that remains meaningful when symbols or names change. |
| Corporate action | Split, bonus, dividend, rights, merger, demerger, or identity change affecting price or ownership. |
| Terminal outcome | Economic treatment when a listing ends, merges, delists, or cannot be traded. |
| PRI | Price return index; ordinarily excludes reinvested cash dividends. |
| TRI | Total return index; includes defined dividend reinvestment. |
| Preregistration | A locked statement of the question, data, method, metric, and decision rule before outcome access. |
| Walk-forward | Repeated chronological training and later evaluation without using future information. |
| Canonical evidence | Evidence admitted through the governed manifest, approval, event, and import contracts. |
| Nonpromotable | Permanently barred from becoming production or actionable evidence. |
| Research-state fingerprint | One hash over every declared research-relevant file, used to detect staleness. |
| Report gate | Owner review prerequisite; it does not authorize a research run. |

### Known limitations and staleness policy

The fingerprint includes research and simulation code, contracts, specifications, data-trust declarations, proposals, governance policies, tracked evidence anchors, architecture decisions, and milestone reports that determine scientific scope. It excludes the generated PDF, its presentation source, the review record, mechanical PDF inventories, the R.7 completion report, tests, caches, and README. These exclusions prevent self-reference and allow documentation-only commits without automatic staleness.

Any substantive change to included code, contracts, data declarations, assumptions, universe, outcomes, costs, benchmarks, governance policy, proposal definition, or scientific-scope report changes the fingerprint and makes this PDF stale. A new PDF and post-generation owner review are then required.

### Final owner reminder

Current review status: PENDING USER REVIEW.
Research remains blocked.
This document is ready to be read and corrected; it is not permission to analyze markets.
