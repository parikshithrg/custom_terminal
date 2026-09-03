# Market System Development — Status and Pre-Research Review

**Version 2 - Research R.9C**

Generated from: `custom_terminal` main commit `a87cedc7ad5db14adaba0661bf44fd3346e399ab`
Research-state fingerprint: `9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31`
External reference: `version2.0` master commit `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`, tree `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f`
Review state: `REPORT_GENERATED_PENDING_REVIEW`

Covered next scope: `FNO_PRODUCTION_ENABLEMENT_DESIGN_AND_SYNTHETIC_TESTING`

NO DATABASE ACCESS, MARKET ANALYSIS, SIMULATION, BACKTESTING, SCORING, RECOMMENDATION, BROKER ACTION, OR TRADING IS AUTHORIZED BY THIS REPORT.

[PAGE BREAK]

## Executive summary

This project is building a personal Indian-market research and capital-allocation support system whose conclusions can be reconstructed from point-in-time evidence. The system is intended to collect and preserve data, calculate deterministic features and outcomes, test hypotheses out of sample, measure uncertainty and costs, and eventually support portfolio and downside-risk decisions. It is not a trade-execution system, and it currently has no approved investment edge, production score, or recommendation.

The strongest completed work is infrastructure. `custom_terminal` now contains provider-neutral data contracts, immutable evidence patterns, point-in-time controls, governed research approvals, a one-use execution gateway, and an independently audited synthetic canary. Vertical Slice A proved a reproducible momentum experiment workflow, but the underlying local equity panel failed the trust gates needed for cross-sectional market claims. Momentum remains non-actionable.

The current data position remains cautious. Only 3 of 12 locked historical security/bhavcopy pairs qualified. Historical population, stable identity, inactive listings, economic terminal outcomes, authoritative corporate actions, benchmark PRI/TRI coverage, dated statutory costs, and retention rights remain incomplete or unresolved. Kite is useful only for bounded current-market display and does not repair historical-universe gaps.

R.8 separated ambiguous market-sentiment and stock-score concepts instead of inventing weights. R.9A specified a tightly bounded local F&O database audit. R.9B implemented that auditor with aggressive safety controls, but tested it only against tiny synthetic SQLite fixtures. The production locator is deliberately rejected. The real F&O database has never been located, opened, hashed, inspected, or queried.

This PDF prepares the next owner decision. If the owner accepts it, the next milestone may design and synthetically test production enablement. It may not access the real database. A later implementation review, exact database binding, and separate one-use audit approval would still be required before a real Stage 1-3 audit.

### Current status at a glance

| Area | Status | Meaning |
|---|---|---|
| Architecture | ESTABLISHED | Canonical trust, research, evidence, and application boundaries are defined. |
| Historical equity data | NOT TRUSTED | Survivor selection and population gaps prevent trustworthy cross-sectional claims. |
| Research governance | PROVEN ON SYNTHETIC CANARY | Infrastructure behavior passed; no investment hypothesis was validated. |
| Momentum 12-1 | NON-ACTIONABLE | Reproducible workflow exists; data and evidence gates remain closed. |
| Sentiment definition | SENTIMENT_DEFINITION_AMBIGUOUS | Distinct concepts remain separate; no combined score exists. |
| Stock score definition | STOCK_SCORE_DEFINITION_AMBIGUOUS | No validated weighting, ranking, or decision mapping exists. |
| F&O audit plan | FNO_AUDIT_PLAN_READY | Bounded Stages 1-3 are specified. |
| F&O auditor | SYNTHETIC ONLY | Safety implementation passes synthetic tests; production access is blocked. |
| PDF review gate | PENDING OWNER REVIEW | This exact v2 must be reviewed before the next covered design phase. |

[PAGE BREAK]

## 1. What are we trying to build?

The intended product is a trustworthy research machine first and a decision-support product later. Every important score should be based on a declared relationship between information knowable at decision time and a later outcome. A credible score should disclose historical bucket behavior, out-of-sample and walk-forward performance, sample size, transaction-cost sensitivity, drawdown, predictive strength, regime dependence, decay, confidence, and provenance.

The target evidence chain is:

```text
Data sources
  -> immutable raw and point-in-time normalized evidence
  -> deterministic features and declared outcomes
  -> preregistered experiments
  -> walk-forward validation
  -> evidence and confidence
  -> decision policy
  -> portfolio and risk support
```

Prediction quality, economic quality, and portfolio quality must stay separate. A statistically interesting feature is not automatically tradable. A profitable backtest is not trustworthy if the historical population is survivor-selected, identifiers are unstable, delistings are omitted, corporate actions are guessed, or costs use the wrong date.

The AI layer is an interpreter and research assistant, not the quantitative source of truth. Deterministic code must own data, features, outcomes, backtests, scores, and risk. AI may explain evidence, suggest falsification tests, and investigate why an edge might work or decay.

The system remains analysis-only. No project surface is authorized to place, modify, or cancel an order.

## 2. Repository authority

`custom_terminal` remains the canonical governance, provenance, trust, evidence, approval, lifecycle, and promotion authority. `version2.0` remains a separate product and reference repository containing dashboard patterns, current displays, and exploratory ideas. Its outputs are not canonical research evidence.

| Responsibility | Authoritative location | Current rule |
|---|---|---|
| Point-in-time data and trust | custom_terminal | Fail closed when evidence is missing or ambiguous. |
| Research approvals and execution | custom_terminal | Exact preregistration, immutable inputs, and one-use approval. |
| Evidence and lifecycle | custom_terminal | Only governed artifacts may become canonical. |
| UI and exploratory ideas | version2.0 reference | May inform later design; cannot promote evidence. |
| Market sentiment and stock-score ideas | version2.0 reference | Priority candidates for later definition review only. |
| Broker code | isolated reference | Must remain disconnected from research and product actions. |

The public `version2.0` master branch was rechecked read-only for R.9C. It remains at commit `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`, so its tree remains `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f`. It has not changed from the previously reviewed binding. It was not cloned, executed, copied, or integrated.

[PAGE BREAK]

## 3. What has been completed?

### Foundation and Vertical Slice A

- The original Streamlit scaffold was audited and reorganized around shared engines rather than page-by-page calculations.
- Typed temporal and provenance contracts preserve observation, publication, effective, retrieval, revision, source, parser, and quality information where available.
- Stable instrument identity and dated aliases were introduced as contracts; ticker strings are not treated as permanent identity.
- The 12-1 momentum feature, explicit outcome, versioned universe, experiment specification, walk-forward runner, costs, manifests, and evidence layers were implemented.
- A deterministic golden fixture records old/new compatibility. It is debugging evidence, not proof of an edge.
- The experiment remained non-actionable and did not become a production score.

### Data qualification and current-market work

- Provider-neutral ingestion, immutable raw manifests, typed normalization, identity reconciliation, corporate-action handling, and dataset acceptance were implemented.
- Public official sources were qualified conservatively. Bhavcopy availability did not get misrepresented as historical population completeness.
- The 12-date population study qualified only 3 pairs; historical population reconstruction remains incomplete.
- Official-response handling preserves ambiguity rather than converting silence into permission.
- Kite supports memory-only daily authentication and bounded read-only current instruments and quotes. It is explicitly current-only and cannot validate historical cross-sectional research.

### Research governance

- Legacy evidence was preserved and labeled noncanonical rather than rewritten.
- Research-family, preregistration, input declaration, split-access, approval, execution, artifact, and lifecycle contracts were introduced.
- A three-row synthetic governance canary ran once under exact one-use approval and passed independent evidence audit.
- A permanent pre-research PDF gate requires a current owner-reviewed status report before future market research can proceed to its separate run approval.

### R.8 through R.9B

- R.8 clarified candidate component boundaries without running empirical work.
- R.9A produced an exact, hashed, bounded Stage 1-3 F&O audit proposal.
- R.9B implemented and adversarially tested the auditor using synthetic fixtures only.

[PAGE BREAK]

## 4. What do we currently have?

### Useful and trustworthy infrastructure

| Capability | What exists | What it proves |
|---|---|---|
| Temporal contracts | Publication/effective/retrieval and revision concepts | The architecture can express what was knowable at time T. |
| Immutable evidence patterns | Raw hashes, manifests, artifact inventories | Mutations and mismatches can be detected against anchors. |
| Research governance | Preregistration, split controls, exact one-use approval | A run cannot become canonical through an informal shortcut. |
| Synthetic canary | One completed and independently audited run | The governance machinery worked on non-market synthetic input. |
| Current Kite data | Read-only instruments and bounded snapshots | Current display flow works; historical claims remain prohibited. |
| Synthetic F&O auditor | Bounded identity, catalog, and provenance inspection | Safety behavior works on small synthetic SQLite fixtures. |

### Evidence that remains noncanonical or incomplete

The local equity panel contains useful observations but not a defensible complete historical market population. The historical F&O database has not been audited. `version2.0` calculations and old Data-test results remain exploratory and noncanonical. No displayed score or recommendation has passed the required research lifecycle.

### The current research boundary

The reviewed PDF v1 authorized bounded planning only. It did not authorize the R.9A audit proposal to run. R.9B created a synthetic-only implementation without using the real database. This v2 begins pending review and cannot itself authorize any audit or research execution.

[PAGE BREAK]

## 5. What remains untrusted or incomplete?

| Capability | Status | Consequence |
|---|---|---|
| Historical listed population | FAIL / INCOMPLETE | Traded rows cannot stand in for all eligible securities. |
| Survivorship safety | FAIL | Missing inactive or failed listings can bias cross-sectional results. |
| Stable identity history | INCOMPLETE | Symbol, series, ISIN, merger, and listing transitions remain unresolved. |
| Economic terminal outcomes | FAIL | Final quote is not authoritative delisting or merger consideration. |
| Corporate actions | UNKNOWN / PARTIAL | Raw price discontinuities do not prove action type or total return. |
| Benchmark PRI/TRI | PARTIAL / UNKNOWN | Price-return data cannot be silently labeled total return. |
| Historical statutory costs | INCOMPLETE | Unknown intervals must fail rather than inherit current rates. |
| Publication and revision timing | PARTIAL | Some inputs cannot yet be reconstructed as-of decision time. |
| Rights and retention | REQUIRES REVIEW | Technical access is not permission to retain or reuse an archive. |
| F&O database identity | UNKNOWN | No production path or database byte has been inspected. |
| F&O provenance/retention | UNKNOWN | A large database or long date span is not evidence of provenance. |
| F&O market-row integrity | NOT EVALUATED | R.9A and R.9B exclude market-table reads. |
| Full SQLite integrity | NOT EVALUATED | `quick_check` and `integrity_check` are excluded. |

The governance system also has genuine limitations. The local filesystem owner can modify files; hashes detect change only against separately preserved anchors. Some process limits are declared rather than OS-enforced. The canonical catalog has limited history. These matters should not be confused with the more fundamental data-completeness blockers.

[PAGE BREAK]

## 6. Owner decisions already recorded

The owner reviewed PDF v1 after generation. That approval covered planning only. The decisions are preserved below; none authorized audit execution or empirical market research.

1. The project objective was approved: build trustworthy research and capital-allocation support, not a fast signal generator.
2. The development order was approved: governance and data qualification before strategy testing and scoring.
3. Paid market-data providers are prohibited.
4. Free official sources are preferred.
5. Kite Connect may supplement data only where available and governed.
6. The current milestone order was retained.
7. Optional governance hardening was deferred rather than made the immediate priority.
8. `version2.0` remains separate and reference-only.
9. Market sentiment and stock scores are priority candidate ideas for later review.
10. Untested recommendations and live scans remain hidden.
11. Live broker code may remain only if isolated.
12. No trade execution is permitted; the system remains analysis-only.
13. A local F&O trust audit is permitted only subject to exact controls and later approvals.
14. Display-only provider selection remains deferred.
15. Renaming legacy validation labels remains deferred, while bounded planning work was approved.

The prior approval scope was `BOUNDED_FREE_SOURCE_CAPABILITY_PLANNING`. It did not authorize data acquisition, database access, market analysis, simulation, backtesting, scoring, recommendations, broker actions, trading, or a governed research run.

[PAGE BREAK]

## 7. R.8 component decisions

### Market sentiment

The inherited idea called "sentiment" combines economically different concepts: market stress, participant positioning, management tone, breadth, derivatives conditions, and macro context. These signals have different clocks, sources, horizons, missingness, and causal stories. R.8 therefore preserved them as separate candidate components.

No combined sentiment score exists. No weights, thresholds, action mapping, training result, or production recommendation exists. The current decision is:

```text
SENTIMENT_DEFINITION_AMBIGUOUS
```

### Stock scores

Data quality, liquidity, market behavior, disclosures, ownership, sentiment, and derivatives context also remain separate. Missing evidence cannot be converted to a neutral midpoint, and convenient weights cannot replace empirical validation.

No final 0-100 score, cross-sectional ranking, confidence mapping, or actionable recommendation exists. The current decision is:

```text
STOCK_SCORE_DEFINITION_AMBIGUOUS
```

### Local F&O database

A bounded trust-audit plan exists, but the production database has not been audited. File size and apparent historical span are not evidence of identity, provenance, completeness, correction handling, or research fitness. The R.8 planning decision is:

```text
FNO_AUDIT_PLAN_READY
```

[PAGE BREAK]

## 8. R.9A bounded audit proposal

R.9A proposed only three stages.

| Stage | Permitted purpose | Explicit boundary |
|---|---|---|
| 1 | Locate an approved target and freeze bounded file identity | Regular file, header, size/time, sampled chunks, sidecars; not a full hash. |
| 2 | Verify SQLite read-only safety and inventory schema/catalog | No market rows, aggregates, coverage, outcomes, or integrity scan. |
| 3 | Inventory already-local provenance and retention evidence | No network, acquisition, parser execution, or market-data content reads. |

Stages 4-6 remain excluded. They would cover later questions such as market-row coverage and integrity, but they have not even been approved for proposal execution. `quick_check`, `integrity_check`, exports, outcomes, features, signals, ranks, scores, strategies, recommendations, broker activity, and trading are excluded.

### Exact proposal bindings

| Object | SHA-256 |
|---|---|
| Proposal package content | `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd` |
| Proposal manifest | `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8` |
| Audit scope | `86af643f9c88a1162ecaecf76d22e4e74b5d39816f6e6117eb6105b726588d8d` |
| Resource envelope | `1aec4f54a6e3cf88cfa1ecde91b5b8c1579886d38a5282e5131471b2694436b5` |
| Expected outputs | `b1d05cfba2de056156d07c4f93512372af9eafd6f2de7d682404050e742f0d8a` |

### Resource envelope

- Identity: at most 64 deterministic 4 MiB chunks plus the first 100 bytes per pass, with five checkpoint passes.
- SQLite: at most 50 attempted statements, each with a 5-second progress deadline.
- Provenance: at most 500 files and 512 MiB of reads.
- Output: at most 25 MiB; temporary storage declaration 128 MiB.
- Whole audit: 20-minute and 512 MiB declarations.

The sampled identity detects changes in selected bytes, size, time, header, and sidecars. It is weaker than a complete file hash. Statement cancellation and output/read counts are code-enforced in R.9B. Total wall time and process memory remain declared, not OS-enforced.

[PAGE BREAK]

## 9. R.9B synthetic-only auditor

R.9B added a dedicated local-data-audit contract separate from market-research approvals. Its default mode is a proposal dry run that resolves no path, creates no attempt, opens no connection, and executes no SQL.

Explicit execution requires an exact, registered, unexpired, one-use approval of type `LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1`. The approval binds the proposal hashes, stages, resources, outputs, synthetic locator declaration, and sampled fixture identity. It is atomically consumed before the first SQLite connection and cannot be reused after completion, abort, or failure.

### Independent SQLite protections

- SQLite URI `mode=ro`.
- Verified `PRAGMA query_only=ON`.
- One connection and disabled extension loading.
- Strict statement allowlist and operation denylist.
- SQLite authorizer rejecting DDL, DML, attach/detach, maintenance, writable pragmas, and user-table reads.
- Maximum 50 attempted statements.
- Monotonic 5-second progress-handler cancellation.
- Sanitized statement events with literal and path redaction.

### Filesystem, provenance, and output protections

- Caller-supplied path must remain inside a marked synthetic fixture root.
- Symlink and path indirection rejection.
- Bounded sampled identity with deterministic small-file offset deduplication.
- Mutation detection after every stage and before publication.
- Database-associated journal, WAL, SHM, and other sidecar detection.
- Stage 3 deterministic traversal with file and byte limits and no symlink following.
- Secret and personal-path non-disclosure.
- Exact output allowlist, deterministic JSON, aggregate output-byte enforcement, and atomic finalization.
- Every result is `canonical=false` and `promotion_eligible=false`.

The auditor has only been tested on small synthetic SQLite fixtures.
The real F&O database has never been located, opened, hashed, inspected, or queried.

[PAGE BREAK]

## 10. R.9B verification and limitations

The complete root suite passed 294 tests. Two Windows symlink tests were skipped because the current environment lacks unprivileged symlink creation. Direct path-escape tests and production symlink guards passed. The separate Data-test suite passed 289 tests. Proposal hashes, 498 JSON objects, Python compilation, entry-point reconciliation, protected evidence, secret scans, network-dependency scans, and Git whitespace checks passed.

### Remaining limitations

- The two Windows symlink execution cases remain unobserved in this environment.
- Approval storage is process-local and synthetic-only.
- Production locator resolution does not exist and `paths.fno_db` is explicitly rejected.
- The real database identity is unknown.
- Source provenance, retention rights, correction vintages, and backup metadata remain unresolved.
- Historical completeness and point-in-time fitness are not evaluated.
- Market-row coverage and integrity are not evaluated.
- Full SQLite integrity is not evaluated; `quick_check` and `integrity_check` remain excluded.
- Sampled identity is not a complete file hash.
- Total runtime and process memory are declarations rather than OS-enforced quotas.
- No backup, restore, retention, or redistribution conclusion exists.
- Contract-level immutability rejects an existing attempt ID; it does not make local storage physically tamper-proof.

These are intentional stop points, not evidence that the real database is safe or fit for research.

[PAGE BREAK]

## 11. What should happen next?

After owner review, the next milestone should design and synthetically test production enablement. It should not run the database audit.

A bounded production-enablement design milestone may propose:

- durable local audit-approval registration and one-use consumption;
- production locator resolution without committed personal paths;
- exact locator and database identity binding;
- path, error, SQL, and artifact redaction;
- safe pre-connection identity capture;
- a read-only production adapter that preserves the R.9A boundaries;
- task-scoped local audit evidence storage outside the source directory;
- restart, crash, and partial-finalization handling;
- a documented final execution ceremony.

Every implementation test must still use synthetic fixtures. Production locator rejection may be removed only in a separately reviewed commit with a replacement fail-closed binding. No real database may be accessed during that design milestone.

Only after the implementation is reviewed, the PDF remains current or is regenerated, the exact production database is safely bound, and the owner issues a separate exact one-use audit approval may the real Stage 1-3 audit run. The result would still need independent review before Stages 4-6 could even be proposed.

## 12. Authorization ladder

```text
R.9C PDF generation
  -> owner reviews PDF v2
  -> owner approves bounded next design phase
  -> production-enablement implementation
  -> implementation review
  -> exact database binding
  -> exact one-use audit approval
  -> Stage 1-3 read-only audit
  -> independent audit-result review
  -> later decision on whether Stages 4-6 may even be proposed
```

Each arrow is a separate decision. Passing one step does not imply or authorize the next.

[PAGE BREAK]

## 13. What remains prohibited?

- Enabling or resolving the production F&O locator during R.9C.
- Locating, opening, hashing, inspecting, copying, querying, repairing, vacuuming, or otherwise touching the real F&O database.
- Creating, registering, sealing, or consuming a real audit approval.
- Running the synthetic auditor against any non-synthetic target.
- Reading F&O market rows, computing row counts, dates, symbols, expiries, strikes, coverage, or integrity statistics.
- Acquiring external market data or using paid data.
- Treating current Kite instruments as a historical universe.
- Running market analysis, simulation, backtesting, parameter search, scoring, ranking, recommendation, portfolio action, broker action, or trading.
- Promoting momentum, sentiment, stock scores, version2.0 output, or audit output to canonical actionable evidence.
- Treating PDF approval as audit execution authority.

### Approval separations

| Approval or decision | What it may permit | What it cannot permit |
|---|---|---|
| PDF v2 owner review | Confirms summary and covered next design scope | Database access or audit execution |
| Next design-phase approval | Synthetic production-enablement design work | Real locator resolution or database access |
| Implementation review | Confirms code is ready for binding | Execution by itself |
| Exact one-use audit approval | One precisely bound Stage 1-3 run | Stages 4-6, market research, or trading |
| Independent audit-result review | Interprets Stage 1-3 evidence | Automatic data trust or research readiness |

[PAGE BREAK]

## 14. Decisions requiring owner review

Please answer each question explicitly after reading this exact PDF:

1. Do you approve PDF v2 as an accurate summary of the project through R.9B?
2. Do you confirm that `version2.0` should remain separate and reference-only?
3. Do you approve proceeding only to a production-enablement design and synthetic-testing milestone?
4. Do you agree that this approval must not access the real F&O database?
5. Do you confirm that no market-row analysis, simulation, backtesting, scoring, recommendation, broker action, or trading is authorized?
6. Do you want any correction before the next phase?
7. Do you want the two Windows symlink tests to remain a documented limitation, or should they be rerun later in an environment with symlink privileges?

Reviewer answers: **UNANSWERED**
Reviewer identity: **UNANSWERED**
Review timestamp: **UNANSWERED**
Review decision: `REPORT_GENERATED_PENDING_REVIEW`

An acceptable review must identify this report as Version 2, occur after its generation, and answer the seven questions. A prior approval, a generic instruction to continue, or approval of planning does not satisfy this gate.

[PAGE BREAK]

## Appendix A - Milestone timeline

| Milestone | Result | Evidence class |
|---|---|---|
| Architecture and Slice A | Reproducible momentum infrastructure; non-actionable | Research process |
| Slice A.5 | Local equity dataset NOT TRUSTED | Data quality |
| Slice A.6 | Provider-neutral ingestion ready; local dry run rejected | Infrastructure/data quality |
| Slices A.7-A.8 | Public samples incomplete; historical population failed | Source qualification |
| Slices A.9-A.10 | Official-response gate remained closed | Access governance |
| Slices A.11-A.12 | Read-only current Kite coverage ready | Current-market infrastructure |
| R.1-R.2 | Legacy evidence preserved and quarantined | Legacy evidence |
| R.3-R.4 | Governed execution and one-use research approvals | Governance infrastructure |
| R.5-R.6 | Synthetic canary executed once and independently audited | Infrastructure evidence |
| R.7 | PDF v1 reviewed for bounded planning only | Owner review |
| R.8 | Component definitions and bounded F&O audit plan | Planning |
| R.9A | Exact Stage 1-3 proposal ready | Data-audit proposal |
| R.9B | Synthetic-only auditor implemented and adversarially tested | Safety infrastructure |
| R.9C | PDF v2 generated pending owner review | Documentation/review preparation |

### Current decisive states

- Historical equity data: `NOT_TRUSTED_FOR_CROSS_SECTIONAL_RESEARCH`.
- Historical population: `HISTORICAL_POPULATION_RECONSTRUCTION_INCOMPLETE`.
- Official NSE response: `AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`.
- Kite: `CURRENT_MARKET_DATA_ONLY`.
- Momentum: non-actionable and not promoted.
- F&O audit proposal: bounded Stages 1-3 only.
- F&O auditor: `SYNTHETIC_ONLY_FNO_AUDITOR_IMPLEMENTED`.
- Production locator: rejected.
- PDF v2: `REPORT_GENERATED_PENDING_REVIEW`.

[PAGE BREAK]

## Appendix B - Evidence and hash index

| Evidence | Binding |
|---|---|
| custom_terminal source commit | `a87cedc7ad5db14adaba0661bf44fd3346e399ab` |
| Research-state fingerprint | `9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31` |
| Previous PDF v1 | `cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c` |
| version2.0 commit | `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298` |
| version2.0 tree | `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f` |
| R.9A proposal package | `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd` |
| R.9A proposal manifest | `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8` |
| Frozen legacy log | `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d` |
| Neutral legacy ledger | `79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392` |

### Core source index

- `ARCHITECTURE_REFINEMENT.md`
- Slice A through A.12 reports and trust assessments
- `reports/RESEARCH_R7_REPORT.md` through `reports/RESEARCH_R9B_REPORT.md`
- `reports/FNO_STAGE_1_3_AUTHORIZATION_PROPOSAL.md`
- `reports/FNO_AUDITOR_IMPLEMENTATION_REVIEW.md`
- `reports/FNO_AUDITOR_ADVERSARIAL_TESTS.md`
- `reports/FNO_AUDITOR_APPROVAL_LIFECYCLE.md`
- `docs/quarantined_proposals/local_fno_audit_stage_1_3/`
- `src/market_intel/foundation/local_fno_audit.py`
- `specs/pre_research_review_policy_v1.json`

[PAGE BREAK]

## Appendix C - Plain-language glossary

| Term | Meaning |
|---|---|
| Point-in-time | Uses only information knowable at the declared historical decision time. |
| Survivorship bias | Results are distorted because securities that later failed or disappeared are missing. |
| Stable identity | A durable security/listing identifier that survives symbol and name changes. |
| Terminal outcome | Economic treatment when a listing ends, delists, merges, or becomes untradeable. |
| PRI / TRI | Price-return index versus dividend-inclusive total-return index. |
| Preregistration | A locked question, data, method, metric, and decision rule written before outcome access. |
| One-use approval | Exact authorization consumed by one attempt and never reusable. |
| Catalog-only audit | Reads SQLite schema metadata without reading user-table market rows. |
| Sampled identity | Hashes deterministic selected byte ranges; detects bounded change but is not a full hash. |
| Canonical evidence | Evidence admitted through the governed approval, manifest, event, and import chain. |
| Nonpromotable | Permanently barred from becoming production or actionable evidence. |
| Report gate | Owner review prerequisite; never execution authority by itself. |

### Staleness policy

The research-state fingerprint includes the declared research, simulation, contract, specification, governance, evidence, architecture, and scientific-scope files. Established PDF mechanics, source presentation, review records, tests, caches, and README remain excluded to prevent self-reference. Any included substantive byte change makes this report stale and requires a new PDF plus post-generation owner review.

Current status: `REPORT_GENERATED_PENDING_REVIEW`.

PRE_RESEARCH_PDF_V2_READY_FOR_OWNER_REVIEW
