# Market System Development - Status and Pre-Research Review

**Version 3 - Research R.9E**

Generated from: `custom_terminal` main commit `450e976ae472fa440a704c74ad959b60f1113219`
Research-state fingerprint: `f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38`
External reference: `version2.0` master commit `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`, tree `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f`
Review state: `REPORT_GENERATED_PENDING_REVIEW`

Covered next scope: `EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION`

NO SQLITE CONNECTION, SQL, PRAGMA, AUDIT EXECUTION, MARKET-ROW ACCESS, MARKET ANALYSIS, SIMULATION, BACKTESTING, SCORING, RECOMMENDATION, BROKER ACTION, OR TRADING IS AUTHORIZED BY THIS REPORT.

[PAGE BREAK]

## Executive summary

This project is building a personal Indian-market research and capital-allocation support system whose conclusions can be reconstructed from point-in-time evidence. The intended system preserves data provenance, calculates deterministic features and outcomes, tests hypotheses out of sample, measures uncertainty and costs, and may eventually support portfolio and downside-risk decisions. It is analysis-only. It has no approved investment edge, production score, recommendation, or trading capability.

Research governance comes before strategy testing because a plausible backtest can be invalidated by survivor selection, unstable identity, revised data, incorrect event timing, ambiguous execution, or arbitrary score weights. The system therefore separates raw evidence, deterministic calculations, validation, confidence, decisions, and portfolio risk. AI may interpret evidence and generate hypotheses, but it is not the quantitative source of truth.

Infrastructure is the strongest completed result. Through R.9D, the repository has provider-neutral data contracts, immutable evidence patterns, a governed research lifecycle, an independently audited synthetic canary, a synthetic-only bounded F&O auditor, and a durable production-enablement boundary. The boundary includes atomic one-use approval consumption, append-only hash-chained events, crash-detectable attempts, bounded evidence retention, secret and path redaction, and network and broker isolation.

Production access is still impossible. The production locator remains disabled, the actual configuration value has not been read, the real database path has not been resolved, the database has not been located or opened, and its identity is unknown. No production registry, real approval, or audit attempt exists. Synthetic safety tests do not establish the trustworthiness of the real database.

This report asks the owner to approve only `EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION`. If explicitly approved later, that phase may perform one bounded filesystem-only identity ceremony and prepare a sanitized binding proposal. It may not connect to SQLite, execute SQL or pragmas, inspect schema or market rows, create or consume an audit approval, or execute the audit.

### Current status at a glance

| Area | Status | Meaning |
|---|---|---|
| Architecture | ESTABLISHED | Trust, research, evidence, and application responsibilities are separated. |
| Historical equity data | NOT TRUSTED | Population, identity, inactive listing, and terminal-outcome evidence remains incomplete. |
| Momentum 12-1 | NON-ACTIONABLE | Reproducible infrastructure exists; evidence gates remain closed. |
| Research governance | SYNTHETICALLY PROVEN | A synthetic canary completed and was independently audited. |
| F&O auditor | SYNTHETIC ONLY | Bounded Stages 1-3 work on temporary synthetic fixtures only. |
| Durable production boundary | IMPLEMENTED BUT DISABLED | Governance exists; exact production binding and approvals do not. |
| PDF v3 | PENDING OWNER REVIEW | This report cannot authorize its own covered next phase. |

[PAGE BREAK]

## 1. What are we building?

The objective is a trustworthy research machine first and a decision-support product later. Every important score should represent one or more declared relationships between information knowable at decision time and a later outcome. A credible score should disclose historical bucket behavior, out-of-sample and walk-forward performance, sample size, transaction-cost sensitivity, drawdown, predictive strength, regime dependence, decay, confidence, and provenance.

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

Prediction quality, economic quality, and portfolio quality remain separate. A statistically interesting relationship is not automatically executable. A profitable historical result is not trustworthy if the eligible population was reconstructed from survivors, identifiers were guessed, delistings were omitted, corporate actions were destructively adjusted, or costs used the wrong effective date.

The AI layer is an interpreter and research assistant. It may explain results, propose hypotheses, and suggest falsification tests. Deterministic and statistical code must own data transformations, features, outcomes, backtests, scores, confidence, and portfolio risk.

The system remains analysis-only. Broker actions and trading are prohibited.

## 2. Why governance precedes strategy testing

Research iteration creates incentives to change a hypothesis after seeing its result. A governed system counters that risk with explicit definitions, immutable inputs, locked specifications, out-of-sample evaluation, one-use approvals, manifests, and separate lifecycle decisions. This does not guarantee a valid edge, but it makes hidden changes and unsupported promotion easier to detect.

Infrastructure evidence and market evidence are different. Passing concurrency, hashing, or manifest tests shows that the machinery behaves as specified on tested fixtures. It does not prove that historical prices, security populations, corporate actions, costs, benchmarks, or F&O rows are complete and point-in-time correct.

[PAGE BREAK]

## 3. Milestones through R.9C

### Architecture and Vertical Slice A

- The original Streamlit scaffold was audited and reorganized conceptually around shared engines instead of duplicated page calculations.
- Vertical Slice A migrated the 12-1 momentum experiment into typed temporal data, feature, outcome, universe, cost, experiment, manifest, and walk-forward contracts.
- A deterministic golden fixture preserved compatibility evidence. It is a debugging anchor, not statistical proof.
- The experiment remained non-actionable and was not converted into a production score.

### Historical-data qualification

- Slice A.5 found that the local equity panel was not trustworthy for cross-sectional research because the security population and inactive listings were incomplete.
- A.6 introduced provider-neutral ingestion, immutable raw manifests, typed normalization, identity reconciliation, corporate-action handling, and dataset acceptance.
- A.7 and A.8 qualified public official evidence conservatively. Bhavcopy availability was not treated as a historical security population.
- Only 3 of 12 locked historical security/bhavcopy pairs qualified. Historical population reconstruction remains incomplete.
- A.9 and A.10 preserved official-response ambiguity instead of inferring permission.
- A.11 and A.12 established bounded read-only current Kite coverage. Current instruments are not a historical universe.

### Governed execution and independent evidence

- R.1 and R.2 preserved legacy evidence as noncanonical rather than rewriting it.
- R.3 and R.4 introduced research families, preregistration, declared inputs, split access, exact approvals, execution events, manifests, evidence import, and lifecycle controls.
- R.5 executed one tiny synthetic infrastructure canary under an exact one-use approval.
- R.6 independently audited that canary and confirmed the governance chain, not a market edge.
- R.7 established the pre-research PDF review gate and reconciled the external `version2.0` repository as separate and reference-only.

### Planning and the synthetic F&O auditor

- R.8 kept market sentiment and stock-score concepts separate because their economic meanings, clocks, populations, and missingness differ. No combined score or arbitrary weights were created.
- R.9A defined a tightly bounded, hashed F&O audit proposal limited to file identity, SQLite catalog safety, and local provenance inventory.
- R.9B implemented the auditor with synthetic fixtures only. It prohibited market-table reads and rejected the production locator.
- R.9C generated PDF v2. The owner later approved only production-enablement design and synthetic testing. That approval is preserved historically and became stale when R.9D changed the governed source state.

[PAGE BREAK]

## 4. Repository authority and current assets

`custom_terminal` is the canonical authority for provenance, point-in-time trust, research definitions, approvals, execution evidence, lifecycle, and promotion. `version2.0` remains a separate product and reference repository. Its dashboards and ideas may inform later design, but its calculations are not canonical evidence.

The public `version2.0` master branch was rechecked read-only for R.9E on 2026-09-03. It remains at commit `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`; therefore its bound tree remains `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f`. It has not changed from the previously reviewed binding and was not cloned, copied, or executed.

| Capability | What exists | Evidence boundary |
|---|---|---|
| Temporal and provenance contracts | Observation, publication, effective, retrieval, revision, source, parser, and quality concepts | Can express point-in-time state when source evidence exists. |
| Immutable evidence patterns | Raw hashes, manifests, content-addressed objects, and artifact inventories | Detects mismatch against preserved anchors. |
| Research governance | Families, preregistration, split controls, exact approvals, and lifecycle | Prevents informal promotion into canonical evidence. |
| Synthetic canary | One completed, independently audited run | Proves a narrow infrastructure path on non-market data. |
| Kite current data | Memory-only login and bounded read-only snapshots | Current display only; not historical research evidence. |
| Synthetic F&O auditor | Bounded identity, catalog, and provenance inspection | Tested only on temporary synthetic SQLite fixtures. |
| R.9D production boundary | Durable approval and evidence governance with fail-closed locator | Production remains deliberately unreachable. |

No displayed score or recommendation has passed the required evidence lifecycle. Sentiment and stock scores remain future candidates, not approved calculations.

## 5. What remains untrusted?

| Capability | Status | Consequence |
|---|---|---|
| Historical listed population | FAIL / INCOMPLETE | Traded rows cannot stand in for all eligible securities. |
| Survivorship safety | FAIL | Missing inactive or failed listings can bias results. |
| Stable identity history | INCOMPLETE | Symbol, series, ISIN, merger, and listing transitions remain unresolved. |
| Economic terminal outcomes | FAIL | A final quote is not authoritative delisting consideration. |
| Corporate actions | UNKNOWN / PARTIAL | Price discontinuities do not establish action type or total return. |
| Benchmark PRI/TRI | PARTIAL / UNKNOWN | Price-return evidence cannot be silently labeled total return. |
| Historical statutory costs | INCOMPLETE | Unknown intervals must fail rather than inherit current rates. |
| F&O database identity | UNKNOWN | No production database byte or path has been inspected. |
| F&O provenance and retention | UNKNOWN | File size and apparent span do not prove source lineage or rights. |
| F&O market-row quality | NOT EVALUATED | Coverage, values, and point-in-time fitness remain outside Stages 1-3. |

[PAGE BREAK]

## 6. The R.9A and R.9B audit boundary

R.9A permits only three future audit stages, subject to later exact authorization.

| Stage | Permitted purpose | Explicit exclusions |
|---|---|---|
| 1 | Bounded target identity | No full hash, copy, export, or market interpretation. |
| 2 | SQLite read-only safety and catalog metadata | No user-table rows, aggregates, coverage, or integrity scan. |
| 3 | Already-local provenance and retention inventory | No network, acquisition, parser execution, or market-data reads. |

Stages 4-6 remain excluded. `quick_check`, `integrity_check`, market-table row reads, dates, symbols, expiries, strikes, prices, volume, open interest, returns, features, scores, strategies, recommendations, and trading remain prohibited.

### Exact R.9A bindings

| Object | SHA-256 |
|---|---|
| Proposal package content | `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd` |
| Proposal manifest | `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8` |
| Audit scope | `86af643f9c88a1162ecaecf76d22e4e74b5d39816f6e6117eb6105b726588d8d` |
| Resource envelope | `1aec4f54a6e3cf88cfa1ecde91b5b8c1579886d38a5282e5131471b2694436b5` |
| Expected outputs | `b1d05cfba2de056156d07c4f93512372af9eafd6f2de7d682404050e742f0d8a` |

R.9B uses SQLite URI `mode=ro`, verifies `query_only`, disables extension loading, enforces a statement allowlist and authorizer denylist, limits statements, applies a monotonic progress deadline, redacts statements, detects sidecars and mutation, bounds provenance traversal, restricts outputs, and finalizes artifacts atomically. It consumes its exact approval before the first target connection.

The auditor has only been executed against small temporary synthetic fixtures. No result from R.9B qualifies the real database.

[PAGE BREAK]

## 7. R.9D durable production boundary

R.9D replaced the process-local production-enablement concept with durable synthetic-tested governance while keeping the real target unreachable.

### Durable approval and event model

- A separate local-data-audit approval type prevents substitution of a market-research approval.
- Approval registration preserves the exact canonical payload hash and rejects duplicate IDs or payloads.
- Events are append-only and linked by SHA-256, making reordering or mutation detectable against the event head.
- Approval consumption uses a SQLite `BEGIN IMMEDIATE` transaction and unique constraints.
- Two spawned processes raced for one approval; exactly one succeeded and the other failed before target connection.
- A consumed approval remains consumed after process restart.
- A crash before committed consumption leaves the approval unused.
- A crash after committed consumption leaves a durable incomplete attempt for later inspection.
- Completed, aborted, and failed terminal events reconcile against the attempt projection.
- Approval consumption occurs before any target connection.

### Sanitization and retention

- Private absolute paths and secret-like values are rejected or redacted from durable governance events.
- Runtime dependency injection is rejected at the production boundary.
- The module has no network, broker, Streamlit, scoring, portfolio, recommendation, or trading call path.
- Synthetic audit outputs are written under a task-scoped store separate from source data.
- Output names and total bytes are bounded, hashes are exact, publication is atomic, and finalized attempt directories are immutable by contract.
- Retention metadata states that restore was not tested and no backup is claimed.
- Synthetic artifacts remain noncanonical and ineligible for promotion.

These controls are application-level and tamper-evident. They are not physical protection against the machine owner, and they do not establish real database quality.

[PAGE BREAK]

## 8. The deliberate production interlock

### Production access is still impossible.

The locator state is:

```text
PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING
```

The deliberately impossible R.9D interlock is:

```text
R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE
```

Current facts:

- The configuration value has not been read.
- The real path has not been resolved.
- The database has not been located.
- The database has not been opened.
- The database identity is unknown.
- No production registry exists.
- No real audit approval exists.
- No real audit attempt exists.
- The activation template is unsealed, unregistered, unusable, and contains missing binding fields.
- The production entry point fails before configuration reading, path resolution, filesystem identity reads, attempt creation, or SQLite access.

Synthetic tests demonstrate behavior for constructed inputs under the tested runtime. They do not show that the real file is SQLite, that it is stable, that its schema is safe, that its provenance is adequate, that its rows are complete, or that its market data is suitable for research.

PDF v2 remains byte-exact historical evidence of the owner's earlier limited approval. It is now `PDF_V2_STALE_AFTER_R9D_IMPLEMENTATION` because R.9D changed the research-state fingerprint.

[PAGE BREAK]

## 9. Exact proposed next action

The only proposed next phase is:

```text
EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION
```

Only after explicit owner review and approval of this exact PDF may that phase perform the following bounded filesystem operations:

1. Read the approved configuration file.
2. Resolve only `paths.fno_db`.
3. Verify that the resolved target is a regular file.
4. Reject symlinks and path escapes.
5. Assign a sanitized alias; keep the absolute path private.
6. Record file size and modification time.
7. Read the 100-byte SQLite header without opening SQLite.
8. Calculate one bounded, deterministic 64-position sampled identity pass.
9. Record the position/chunk hashes and aggregate sampled-identity root.
10. Verify that size, modification time, header, and relevant sidecar state did not change during the pass.
11. Prepare an exact sanitized binding proposal for later owner review.

That phase must not:

- Call `sqlite3.connect`.
- Execute a pragma or SQL statement.
- Create the production audit registry.
- Create, register, or consume an audit approval.
- Inspect schemas, tables, indexes, or foreign keys.
- Read any market row or calculate market statistics.
- Execute audit Stages 1-3.

Approval of locator-binding preparation is not approval of the later audit.

[PAGE BREAK]

## 10. Identity cost and limitations

The proposed identity pass is bounded and deliberately weaker than a full-file hash.

| Item | Bound or meaning |
|---|---|
| Deterministic positions | 64 |
| Chunk size | 4 MiB |
| SQLite header | 100 bytes |
| Maximum expected read for one pass | 268,435,556 bytes |
| Expected elapsed estimate | Proposal estimate only; depends on local storage and file size |
| Output | Chunk hashes plus one aggregate sampled-identity root |

Sampled identity is not a full SHA-256. Modification time is metadata, not identity. Unchanged sampled chunks do not prove that unsampled bytes are unchanged. The pass does not prove SQLite structural integrity, schema safety, market-row quality, provenance, completeness, or point-in-time fitness.

The absolute path remains private. Committed evidence may contain only a sanitized database alias and non-identifying bounded metadata. No full database copy or export is proposed.

The locator-binding phase should perform one identity pass. It must not quietly consume the five-checkpoint identity budget reserved for a later approved audit. A second bounded comparison may occur only if mutation detection is expressly covered by the same later approved scope.

## 11. Standing constraints

- Paid data is prohibited; free official sources are preferred.
- Kite Connect may supplement data only where governed and does not solve historical population gaps.
- `version2.0` remains separate and reference-only.
- Sentiment and stock scores remain future candidates.
- Recommendations and live scans remain hidden.
- No trade execution is permitted; the project remains analysis-only.
- Broker actions and trading remain prohibited.
- Display-only provider decisions and legacy-label cleanup remain deferred.

[PAGE BREAK]

## 12. Future authorization ladder

```text
PDF v3 generation
  -> owner reviews PDF v3
  -> owner approves locator-binding preparation only
  -> bounded filesystem identity ceremony
  -> exact sanitized binding report
  -> owner reviews exact database identity
  -> production interlock removal proposal
  -> implementation review
  -> exact one-use audit approval
  -> approval consumption
  -> first SQLite connection
  -> Stage 1-3 audit
  -> independent audit review
  -> decision whether later stages may be proposed
```

No step automatically authorizes the next. In particular:

- This PDF is not self-authorizing.
- Locator-binding approval cannot authorize SQLite access.
- A binding report cannot remove the production interlock.
- Interlock-removal implementation cannot create audit authority.
- A one-use approval authorizes only its exact target, stages, envelope, outputs, issue/expiry interval, and attempt.
- Completion of Stages 1-3 cannot authorize market-row reads or Stages 4-6.
- Audit evidence cannot become a market score or recommendation without a separate research lifecycle.

### Approval separations

| Decision | May permit | Cannot permit |
|---|---|---|
| PDF v3 owner review | Confirms summary and exact covered preparation scope | Any operation by itself |
| Locator-binding approval | Bounded filesystem-only identity preparation | SQLite connection or audit execution |
| Exact binding review | Confirms the sanitized target identity | Automatic interlock removal |
| Interlock implementation review | Confirms reviewed code and bindings | Audit execution by itself |
| Exact one-use audit approval | One bound Stage 1-3 attempt | Market rows, later stages, or research |
| Independent audit review | Interprets bounded audit evidence | Automatic database trust or strategy approval |

[PAGE BREAK]

## 13. Current verification evidence

R.9D verification results are infrastructure evidence only:

| Verification | Result |
|---|---|
| Focused R.9D tests | 19 passed |
| Focused R.9C/R.9D boundary tests | 30 passed |
| Combined R.7-R.9D governance | 111 passed, 2 skipped |
| Complete root suite | 324 passed, 2 skipped |
| Complete separate Data-test suite | 289 passed |
| Concurrent consumption | Exactly one of two contenders consumed approval |
| Production locator non-resolution | Passed |
| Network and broker isolation | Passed |
| Protected evidence | Unchanged |
| JSON validation | 84 valid, 0 invalid |
| Secret-pattern scan | 0 credential-pattern hits |

The two skipped tests exercise Windows symlink behavior in an environment without unprivileged symlink creation. Direct path-escape and production symlink guards passed, but the platform-specific execution cases remain a documented limitation.

The research-state fingerprint changed during R.9D from `9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31` over 231 files to `f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38` over 237 files. PDF v3 binds the latter state and source commit `450e976ae472fa440a704c74ad959b60f1113219`.

Passing these tests does not prove the real database's identity, provenance, completeness, SQLite integrity, schema, row quality, or suitability for any market hypothesis.

[PAGE BREAK]

## 14. What remains prohibited?

- Reading the F&O configuration value before later explicit owner approval.
- Resolving or disclosing the real absolute database path.
- Locating, opening, connecting to, copying, exporting, repairing, or querying the real database during R.9E.
- Calling SQLite, executing SQL or pragmas, or inspecting schemas and tables during locator-binding preparation.
- Creating a production registry, real activation, real audit approval, or audit attempt.
- Consuming any approval or executing audit Stages 1-3 under this PDF alone.
- Reading F&O market rows or calculating dates, symbols, expiries, strikes, prices, volume, open interest, returns, coverage, or integrity metrics.
- Running market analysis, simulation, backtesting, parameter search, ranking, scoring, recommendations, portfolio actions, broker actions, or trading.
- Treating current Kite instruments as a historical universe.
- Treating `version2.0` output, momentum, sentiment, stock scores, or audit output as actionable evidence.
- Acquiring paid data or silently broadening external-source rights.

This report is a review artifact. It does not authorize execution, and none of its pending questions has an answer at generation time.

[PAGE BREAK]

## 15. Owner-review questions

Please answer every question explicitly after reading this exact PDF.

1. Is PDF v3 an accurate summary of the project through R.9D?
2. Do you confirm that `version2.0` remains separate and reference-only?
3. Do you authorize only `EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION`?
4. Do you authorize reading the configured locator value and performing the bounded filesystem identity pass described in the report?
5. Do you confirm that SQLite connection, SQL, pragmas, schema inspection, and market-row access remain prohibited during that phase?
6. Do you confirm that the resolved absolute path must remain private and only a sanitized alias may appear in committed evidence?
7. Do you accept that the sampled identity is not a full-file hash?
8. Do you confirm that a later exact approval is still required before the first database connection?
9. Do you request any correction before locator-binding preparation?

Reviewer answers: **UNRESOLVED**
Reviewer identity: **UNRESOLVED**
Review timestamp: **UNRESOLVED**
Review decision: `REPORT_GENERATED_PENDING_REVIEW`

An acceptable review must identify this report as Version 3, occur after its generation, and answer all nine questions. A prior approval, silence, or a generic instruction to continue does not satisfy the gate.

[PAGE BREAK]

## Appendix A - Milestone timeline and decisive states

| Milestone | Result | Evidence class |
|---|---|---|
| Architecture and Slice A | Reproducible momentum infrastructure; non-actionable | Research process |
| Slice A.5 | Local equity dataset not trusted | Data quality |
| A.6-A.8 | Provider-neutral ingestion; public population sample incomplete | Infrastructure and source qualification |
| A.9-A.10 | Official-response gate remained closed | Access governance |
| A.11-A.12 | Read-only current Kite coverage ready | Current-market infrastructure |
| R.1-R.4 | Legacy preservation and governed execution controls | Governance infrastructure |
| R.5-R.6 | Synthetic canary and independent audit | Infrastructure evidence |
| R.7 | PDF v1 reviewed for planning only | Owner review |
| R.8 | Sentiment/score ambiguity and F&O audit planning | Definition and planning |
| R.9A | Exact bounded Stage 1-3 proposal | Data-audit proposal |
| R.9B | Synthetic-only auditor | Safety infrastructure |
| R.9C | PDF v2 reviewed for R.9D design/testing only | Owner review |
| R.9D | Durable production boundary implemented but disabled | Safety infrastructure |
| R.9E | PDF v3 generated pending review | Documentation/review preparation |

### Current decisive states

- Historical equity data: `NOT_TRUSTED_FOR_CROSS_SECTIONAL_RESEARCH`.
- Historical population: `HISTORICAL_POPULATION_RECONSTRUCTION_INCOMPLETE`.
- Official NSE response: `AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`.
- Kite: `CURRENT_MARKET_DATA_ONLY`.
- Momentum: non-actionable and not promoted.
- Sentiment definition: `SENTIMENT_DEFINITION_AMBIGUOUS`.
- Stock-score definition: `STOCK_SCORE_DEFINITION_AMBIGUOUS`.
- F&O auditor: synthetic only.
- Production locator: `PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING`.
- PDF v2: stale historical reviewed evidence.
- PDF v3: `REPORT_GENERATED_PENDING_REVIEW`.

[PAGE BREAK]

## Appendix B - Evidence and hash index

| Evidence | Binding |
|---|---|
| custom_terminal summarized source commit | `450e976ae472fa440a704c74ad959b60f1113219` |
| Research-state fingerprint | `f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38` |
| PDF v2 | `765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf` |
| version2.0 commit | `f9a6eaec2cab1dd9e85d284e48b9863cae0b1298` |
| version2.0 tree | `ad3c21fb2244f0acd7680bd0bdc4958d2516b16f` |
| R.9A proposal package | `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd` |
| R.9A proposal manifest | `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8` |
| R.9A audit scope | `86af643f9c88a1162ecaecf76d22e4e74b5d39816f6e6117eb6105b726588d8d` |
| R.9A resource envelope | `1aec4f54a6e3cf88cfa1ecde91b5b8c1579886d38a5282e5131471b2694436b5` |
| R.9A expected outputs | `b1d05cfba2de056156d07c4f93512372af9eafd6f2de7d682404050e742f0d8a` |
| R.9D locator state | `PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING` |
| R.9D deliberate interlock | `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` |

### Plain-language glossary

| Term | Meaning |
|---|---|
| Point-in-time | Uses only information knowable at the declared historical decision time. |
| Survivorship bias | Results are distorted because later failures or disappearances are omitted. |
| Stable identity | A durable security/listing identifier that survives symbol and name changes. |
| Preregistration | A locked question, data, method, metric, and decision rule written before outcome access. |
| One-use approval | Exact authorization consumed by one attempt and never reusable. |
| Catalog-only audit | Reads SQLite metadata without reading user-table market rows. |
| Sampled identity | Hashes deterministic byte ranges; bounded change detection, not a full hash. |
| Canonical evidence | Evidence admitted through the governed approval, manifest, event, and import chain. |
| Report gate | Owner-review prerequisite; never execution authority by itself. |

Current status: `REPORT_GENERATED_PENDING_REVIEW`.

PRE_RESEARCH_PDF_V3_READY_FOR_OWNER_REVIEW
