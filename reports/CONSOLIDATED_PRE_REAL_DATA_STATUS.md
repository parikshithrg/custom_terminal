# Consolidated Pre-Real-Data Owner Status

## Document control

| Field | Value |
|---|---|
| Milestone | R.10J |
| Document version | 1.0 |
| Generation date | 2026-09-08 |
| Repository / branch | custom_terminal / main |
| Exact source commit | b7c6124c6e6a353b61078a950652b763db3467bf |
| Remote synchronization | VERIFIED_SYNCHRONIZED |
| Evidence classification | OWNER_STATUS_REPORT_NON_EXECUTION_EVIDENCE |
| Owner-review status | NOT_RECORDED |
| Next-task approval | NOT_RECORDED |

NO ANALYSIS, BACKTESTING, SCORING, RECOMMENDATION OR TRADING AUTHORIZED

This is an owner-status document. It records evidence and asks for decisions;
it does not grant permission to perform the next task.

[PAGE BREAK]

# Table of contents

| Section | Page |
|---|---:|
| Executive summary | 3 |
| What we are trying to build | 4 |
| What has been completed: foundation | 5 |
| What has been completed: synthetic platform and governance | 6 |
| Data sources: access and coverage I | 7 |
| Data sources: access and coverage II | 8 |
| Data sources: qualification and allowed use I | 9 |
| Data sources: qualification and allowed use II | 10 |
| What remains blocked or unknown | 11 |
| Test and evidence status | 12 |
| Safety and authority boundaries | 13 |
| Proposed next development stage | 14 |
| Owner review and separate decisions | 15 |

Status vocabulary: **PASS** means directly demonstrated for the stated scope;
**BLOCKED** means a required gate prevents progression; **NOT QUALIFIED** means
available evidence has not passed the trust contract; **NOT APPLICABLE** means
the source or capability does not address that question.

[PAGE BREAK]

# Executive summary

The project is building an analysis-only decision-support system for Indian
markets. Its eventual visible outputs may include a market-sentiment score and
individual stock scores, but only when those values can be traced to clean,
point-in-time data and genuinely out-of-sample evidence.

The engineering machinery is substantially proven on fictional data. It can
preserve source vintages, calculate deterministic features and outcomes, run
walk-forward validation, separate predictive/economic/portfolio evidence, and
publish immutable noncanonical artifacts. This does **not** prove that any
market edge exists.

Current market-data readiness remains blocked. The broad equity directory is
survivor-selected; the official NSE population sample qualified only 3 of 12
dated security/bhavcopy pairs; terminal outcomes, stable identity, corporate
actions, benchmarks and historical costs remain incomplete. Momentum v1 is not
validated or actionable.

| Readiness area | Current state |
|---|---|
| Architecture | DEFINED |
| Synthetic Infrastructure | MECHANICALLY_VALIDATED_NONCANONICAL |
| Historical Market Data | NOT_QUALIFIED |
| Historical Population | FAIL_3_OF_12_PAIRS |
| Real Data Research | NOT_AUTHORIZED |
| Economic Edges | NONE_VALIDATED |
| Market Sentiment Score | PLANNING_ONLY_HIDDEN |
| Stock Scores | PLANNING_ONLY_HIDDEN |
| Trade Execution | PERMANENTLY_PROHIBITED |

The single proposed next stage is `LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1`. It is a bounded
qualification task for an already-local candidate source, not a backtest. It
requires a separate owner decision after this report is reviewed.

[PAGE BREAK]

# What we are trying to build

The target is a trustworthy research and capital-allocation support system,
not a trading bot. Deterministic code remains the numerical source of truth;
AI may explain evidence and propose hypotheses but may not invent scores or
override validation.

| Layer | Responsibility | Required evidence |
|---|---|---|
| Data ingestion | Acquire immutable source objects through replaceable providers. | Source identity, retrieval time, hashes, terms and parser version. |
| Data qualification | Normalize typed facts and test completeness, identity and timing. | PASS/FAIL/UNKNOWN capabilities with evidence. |
| Research | Declare hypotheses, universes, features and executable outcomes. | Pre-registration and point-in-time inputs. |
| Validation | Use walk-forward folds, purge/embargo, costs and untouched holdouts. | Out-of-sample prediction, economic and portfolio diagnostics. |
| Scoring | Calibrate validated predictions and keep confidence separate. | Comparable historical buckets, uncertainty, decay and lifecycle. |
| Presentation | Expose approved evidence and limitations without recalculation. | Immutable read models and provenance. |
| Trading | Outside project scope. | No order placement, modification or cancellation. |

Intended scores remain richer than a number: raw prediction, confidence,
regime, horizon, contributors, risks and behavior of comparable historical
scores must remain visible. Missing evidence cannot be converted into a neutral
score.

Standing owner decisions include: no paid market-data providers; preference
for relevant free official sources; version2.0 remains separate; scores remain
hidden until supported; the local F&O database may be audited later; portfolio
and some presentation choices remain deferred; and the project must never
execute trades.

[PAGE BREAK]

# What has been completed - foundation

| Milestone | Status | Evidence-backed result |
|---|---|---|
| Architecture | DEFINED | Local-first modular monolith with typed Parquet facts, DuckDB analytics, SQLite workflow state and immutable evidence manifests. |
| Vertical Slice A | INFRASTRUCTURE_PROOF | Momentum v1 mechanics reproduced on a golden fixture and walk-forward machinery implemented; no actionable score. |
| A.5 | DATASET_NOT_TRUSTED | Broad local equity directory is survivor-selected and insufficient for cross-sectional edge approval. |
| A.6-A.10 | PUBLIC_ROUTE_INCOMPLETE | Provider-neutral ingestion exists; official sample produced 12 bhavcopies but only 3 dated population pairs; NSE permission response remains absent. |
| A.11-A.12 | CURRENT_ONLY_READY | Kite supports bounded read-only current instruments, quotes and ephemeral health; no historical use or order endpoints. |
| R.1-R.9 | GOVERNANCE_FOUNDATION | Shared research contracts, promotion gates, evidence manifests, split access, owner-review gates and F&O audit safety plans were established. |

## Momentum v1 status

The legacy experiment was rejected in its original archive. The new Slice A
reproduced mechanics on a controlled fixture, but the available broad dataset
failed survivorship and provenance gates. Apparent results on that directory
cannot confirm the hypothesis. Momentum is neither `VALIDATED` nor `ACTIVE`,
and it emits no BUY/HOLD/REDUCE recommendation.

## Evidence categories

- **Mechanically validated infrastructure:** deterministic contracts and tests.
- **Synthetic-only evidence:** fictional known-answer fixtures, noncanonical.
- **Historically trustworthy market evidence:** not yet sufficient.
- **Economically validated edges:** none.

[PAGE BREAK]

# What has been completed - synthetic platform and governance

All items on this page are engineering evidence from fictional inputs, not market findings.

| Milestone | Status | Evidence-backed result |
|---|---|---|
| R.10A | SYNTHETIC_NONCANONICAL | Point-in-time pipeline, feature, outcome, walk-forward, economic and portfolio evidence mechanics validated on fictional data; holdout left unconsumed. |
| R.10B | SYNTHETIC_NONCANONICAL | Incremental ingestion, schema drift, dependency rebuilding, immutable reuse and recovery validated. |
| R.10C | SYNTHETIC_NONCANONICAL | Security events, causal identity, non-destructive adjustments and terminal-economics mechanics validated. |
| R.10D | SYNTHETIC_NONCANONICAL | Exchange-calendar, decision-clock, execution-session, purge and embargo mechanics validated. |
| R.10E | SYNTHETIC_NONCANONICAL | Multi-feature evidence, calibration, confidence, multiplicity and lifecycle semantics validated; no external decision. |
| R.10F | SYNTHETIC_NONCANONICAL | Immutable evidence publication, freshness, supersession and read-only facade validated; outputs remain NO_DECISION. |
| R.10G | SYNTHETIC_NONCANONICAL | Mandate, portfolio accounting and internal decision-policy mechanics validated; external result remains NO_DECISION. |
| R.10H | REMEDIATION_REQUIRED_THEN_COMPLETED | Readiness audit found stale fingerprint assumptions and 14 missing executable entries; no engine defect or economic readiness. |
| R.10I | GOVERNANCE_REMEDIATED | Historical review semantics and cumulative 77-entrypoint inventory corrected forward-only. |
| R.10I.1 | COHERENCE_CONFIRMED | Conflicting working-tree hashes reconciled; authoritative 280-file Git-object fingerprint is 19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6. |

The R10A holdout remains `UNCONSUMED_SYNTHETIC_HOLDOUT`. Synthetic successes
prove that the engines respond correctly to declared known answers and failure
challenges. They do not estimate a real return, validate a market relationship,
or justify a score.

[PAGE BREAK]

# What data we currently have - access and coverage I

Availability describes what is present or identified; it does not establish research fitness.

| Source | Cost/access | Current availability | Historical depth | Primary purpose |
|---|---|---|---|---|
| Existing equity price directory | Existing local/free files | 430 symbol files; nominal 2000-2026 history | Long but survivor-selected | Historical cash-equity prices |
| Local F&O database | Already local; source cost unverified | Located and sampled, not qualified | Not yet audited | Potential futures/options history |
| NSE official public | Free public surfaces; paid routes prohibited | 12/12 sampled bhavcopies; only 3/12 dated security snapshots | Price files partial; population history incomplete | Bhavcopy, security snapshots, corporate filings |
| SEBI official | Free official publications | Selected repositories identified | Varies by document series | Regulations, orders, event and cost evidence |
| BSE official | Free official public surfaces | Interfaces identified; sample incomplete | Unqualified | Independent listing and lifecycle reconciliation |

The existing broad equity directory is **not sufficient** to approve a
cross-sectional edge. Long date coverage and many files do not compensate for
omitted historical securities, unresolved identities or missing terminal
economics.

[PAGE BREAK]

# What data we currently have - access and coverage II

These sources supplement specific current, benchmark or cost questions; none closes historical equity-population gaps.

| Source | Cost/access | Current availability | Historical depth | Primary purpose |
|---|---|---|---|---|
| AMFI | Free official mutual-fund source | Not evaluated for this equity scope | NOT APPLICABLE | Possible future mutual-fund research only |
| Kite Connect | User account/API application required; not an archive source | Read-only live smoke test passed | CURRENT_TRADABLE_ONLY | Current instrument discovery and bounded quotes |
| NSE Indices | Official public reports | Separate PRI/TRI surfaces identified; no qualified object | UNKNOWN | NIFTY 50 PRI/TRI benchmark evidence |
| Government/SEBI/NSE cost circulars | Free official publications | Source categories identified | Incomplete | Dated statutory trading-cost schedules |

Kite current instruments are not a historical universe and cannot validate
historical cross-sectional research. AMFI is relevant to mutual funds, not to
equity population or security identity. The local F&O database is not trusted
merely because it exists.

[PAGE BREAK]

# Data qualification and allowed use I

Qualification remains source- and purpose-specific. Missing capabilities stay explicit.

| Source | Survivorship / terminal | Corporate actions | Qualification | Allowed vs prohibited |
|---|---|---|---|---|
| Existing equity price directory | FAIL; terminal: FAIL | UNKNOWN | NOT QUALIFIED | Allowed: Compatibility and bounded diagnostics only. Prohibited/unproven: Cross-sectional edge approval, complete historical universe. |
| Local F&O database | NOT APPLICABLE/UNKNOWN contract coverage; terminal: Contract expiry handling unqualified | Underlying continuity unqualified | LOCATED_AND_SAMPLED_NOT_QUALIFIED | Allowed: Future separately authorized read-only qualification. Prohibited/unproven: Research, strategy, scores, unrestricted scans, writes. |
| NSE official public | UNKNOWN/FAIL reconstruction; terminal: Economic outcomes incomplete | Selected case evidence only | PUBLIC ROUTE INCOMPLETE | Allowed: Retained qualified evidence and planning only. Prohibited/unproven: New acquisition, full historical population, production research. |
| SEBI official | Not a population source; terminal: Case evidence possible, not complete | Supplementary event evidence | PARTIAL/SUPPLEMENTARY | Allowed: Source evaluation and retained qualified documents. Prohibited/unproven: Substitute for exchange population. |
| BSE official | UNKNOWN; terminal: UNKNOWN | UNKNOWN | NOT QUALIFIED | Allowed: Planning; keep BSE listings distinct. Prohibited/unproven: Ticker/name-based stitching to NSE. |

Technical accessibility is not permission, and permission is not completeness.
Every source must pass both evidence-quality and lawful-retention gates before
canonical research can use it.

[PAGE BREAK]

# Data qualification and allowed use II

Current access or conceptual methodology does not imply qualified historical research evidence.

| Source | Survivorship / terminal | Corporate actions | Qualification | Allowed vs prohibited |
|---|---|---|---|---|
| AMFI | NOT APPLICABLE TO EQUITIES; terminal: NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | Allowed: Mutual-fund planning only. Prohibited/unproven: Equity identity or survivorship evidence. |
| Kite Connect | FAIL as historical solution; terminal: Inactive/delisted instruments may be absent | Not qualified | CURRENT READ-ONLY READY | Allowed: Manual current health and quotes. Prohibited/unproven: Historical universe, canonical research, orders. |
| NSE Indices | Benchmark methodology only; terminal: NOT APPLICABLE | Dividend treatment documented conceptually | NOT QUALIFIED | Allowed: Methodology planning. Prohibited/unproven: TRI claims from PRI, benchmark publication. |
| Government/SEBI/NSE cost circulars | NOT APPLICABLE; terminal: NOT APPLICABLE | NOT APPLICABLE | NOT QUALIFIED | Allowed: Planning and existing citations. Prohibited/unproven: Backfilling old periods with current rates. |

NSE and BSE listings remain distinct. Issuer-name or ticker similarity cannot
merge them. Current rates cannot be carried backward into historical cost
schedules. PRI cannot be silently substituted for TRI.

[PAGE BREAK]

# What remains blocked or unknown

- Complete historical NSE listed population, including non-trading and later inactive securities.
- Complete suspension, delisting and authoritative economic terminal outcomes.
- Stable instrument/listing/ISIN/dated-alias identity across the research interval.
- Complete point-in-time corporate-action ledger and adjustment evidence.
- Historical exchange turnover at production scale where the universe requires it.
- Local F&O database schema, coverage, provenance, corrections, retention and point-in-time fitness.
- Provider permission for immutable retention and reproducible normalized research tables.
- Real-data research authorization and any defensible historical research start date.
- Economic validity of Momentum v1 or any other edge.
- Validated market-sentiment and individual-stock scores.
- Portfolio construction rules and final presentation choices.

No defensible continuous historical start date has been promoted. Missing
delisting consideration remains unresolved; a last quoted price is not an
economic terminal value. A selected set of circulars is not a complete event
ledger.

Scores are planning concepts only. Market-sentiment inputs represent different
economic objects and clocks; stock-score categories have distinct data and
leakage risks. No aggregation weights, calibration or recommendation semantics
have been approved.

[PAGE BREAK]

# Test and evidence status

The latest completed suites and evidence checks establish engineering integrity within their declared scopes.

| Check | Latest verified status |
|---|---|
| Root Suite | 742 passed, 4 expected Windows symlink skips, 2 established development warnings, 0 failed |
| Data Test Suite | 289 passed, 0 failed |
| Artifact Hashes | R10A-R10G 208 of 208 validated at R10I; chained roots unchanged |
| Parquet | 34 of 34 synthetic evidence objects readable at R10I |
| Momentum Spec Sha256 | 1eed7fd7960c177af8ef90972ea9c4409827a81ab3af8387d69273e9c0ce90d5 |
| Momentum Golden Sha256 | d3f72849464c176c81da036e01db7242672d0c7504ce817400242fd228a0779f |
| R10A Holdout | UNCONSUMED_SYNTHETIC_HOLDOUT |
| Entrypoint Inventory | 77 |
| R10I Fingerprint File Count | 280 |
| Fingerprint Contradiction | RESOLVED_BY_R10I_1_FORWARD_AMENDMENT |

Authoritative R10I Git-object fingerprint (280 policy-v2 files):

```
19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6
```

R10I.1 proved that `e0870bd...` was a stale pre-refresh working-tree value and
`236fddae...` was a post-refresh working-tree value. Neither is presented as a
commit fingerprint. The immutable implementation and evidence commits both
reproduce the full hash above.

These tests prove deterministic mechanics, preservation, contracts and
fail-closed boundaries. They do **not** prove market-data completeness,
representative distributions, scalable production performance, profitability,
or an economically valid edge.

[PAGE BREAK]

# Safety and authority boundaries

NO ANALYSIS, BACKTESTING, SCORING, RECOMMENDATION OR TRADING AUTHORIZED

| Boundary | Authorized? |
|---|---|
| Analysis Only Product | YES |
| Trade Execution Authorized | NO |
| Broker Orders Authorized | NO |
| Unsupported Score Publication Authorized | NO |
| Private Or Paid Data Authorized | NO |
| R10A Holdout Consumption Authorized | NO |
| Real Data Research Authorized | NO |
| Status Report Approval Grants Research Authority | NO |

- Analysis-only product; no trade execution and no broker orders.
- No promotion or display of unsupported scores.
- No silent use of private or paid data.
- No R10A holdout consumption without separate exact authorization.
- No live-broker code change in this milestone.
- No real-data research authority arises from generating or approving this status report.

The application implements a narrow Kite read-only allowlist, but an account
token may possess broader provider permissions. The claim is about application
behavior, not about the theoretical capabilities of the token.

[PAGE BREAK]

# Proposed next development stage

This proposal is presented for a separate owner decision and is not active work.

## LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1

Recommendation: **RECOMMENDED_SEPARATE_OWNER_DECISION**

It is the narrowest bounded step that can replace assumptions about an already-local candidate source with evidence, without running a strategy or acquiring external data.

### Preliminary scope

- Bind the exact owner-approved local database through the existing private locator without publishing its path.
- Prove read-only opening and preserve a versioned database identity.
- Inspect schema, tables, columns, indexes and metadata under bounded timeouts.
- Measure bounded date, symbol, contract, expiry and field coverage.
- Check bounded duplicates, missingness, OHLC/volume/OI validity and continuity patterns.
- Assess provenance, raw-source lineage, corrections, retained vintages and permitted use.
- Produce a qualification verdict for possible later futures/options research.

### Explicit exclusions and abort boundary

- No strategy, feature, return, backtest, simulation, score or recommendation.
- No database write, repair, export, sidecar, unrestricted scan or external acquisition.
- No trading or broker action.
- Abort if read-only safety, bounded queries, provenance or access conditions cannot be established.

Status: `NOT_AUTHORIZED_UNTIL_SEPARATELY_APPROVED_AFTER_REPORT_REVIEW`

This is the narrowest useful next qualification step because it can determine
whether an already-local candidate source deserves any later research use. It
does not require a new external download and does not test a trading idea. If
read-only safety or bounded inspection cannot be established, the stage stops
and reports that blocker.

[PAGE BREAK]

# Owner review - separate decisions required

NO ANALYSIS, BACKTESTING, SCORING, RECOMMENDATION OR TRADING AUTHORIZED

## Facts to confirm

- The report accurately separates synthetic machinery readiness from real-data and economic readiness.
- No market edge or score is currently validated or actionable.
- Paid market-data providers remain prohibited.
- Kite remains current-only; AMFI is not equity-population evidence.
- The local F&O database remains unqualified.
- The project remains analysis-only and must never execute trades.

## Material risks

Historical population, identity, terminal outcomes, corporate actions,
benchmarks, cost schedules, provider rights and real-data reproducibility remain
materially incomplete. A readable database may still fail qualification.

## Decision A - report accuracy

[ ] Approve this report as an accurate status summary.  [ ] Request corrections.

Corrections / affected section: ____________________________________________

## Decision B - proposed next milestone

[ ] Separately approve `LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1`.  [ ] Do not approve it yet.

[ ] Pause development.

Owner name/signature: ____________________  Date: ____________________

Initial machine state: report approval `UNRECORDED`;
next-task approval `UNRECORDED`. Approval of Decision A
does not imply approval of Decision B. Neither choice authorizes research,
backtesting, scoring, recommendations or trading.
