# Market System Development - Status and Pre-Research Review

**Version 4 - Research R.9G**

Summarized source: `custom_terminal` main commit `b658033f7acf0fdc206831cedc5ef374c043e27d`

Research-state fingerprint: `6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db` over 242 files

Review state: `PDF_V4_GENERATED_AWAITING_OWNER_REVIEW`

Proposed next scope: `EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY`

NO DATABASE CONNECTION, SQL, PRAGMA, SCHEMA INSPECTION, MARKET-ROW ACCESS, AUDIT, ANALYSIS, SCORING, SIMULATION, BACKTESTING, RECOMMENDATION, BROKER ACTION, OR TRADING IS AUTHORIZED BY THIS REPORT.

This document is a status report for the project owner. It records no approval and changes no production boundary.

[PAGE BREAK]

## Executive summary

This project is intended to become an analysis-only Indian market research system. Its eventual purpose is to produce a market-sentiment score, evidence-backed stock scores, transparent supporting evidence, reproducible research results, and clear warnings when evidence is insufficient. Untested scores must remain hidden.

The project must not execute trades. Broker connectivity may provide data only. The data policy is free-source-only: no paid data source is required or authorized. Preferred sources include NSE, SEBI, AMFI where relevant to mutual funds, other lawful free official sources, and Kite Connect where its current-market data is available and appropriate.

The central design rule is simple: a market conclusion is not trustworthy merely because code can calculate it. The underlying information must have been knowable at the historical decision time, the relevant security population must be reconstructible, calculations must be reproducible, and predictive evidence must be separated from executable-trade evidence.

The project has built and tested substantial infrastructure for those controls. It has not validated a tradable edge. The existing 12-1 momentum work remains research evidence, not an approved score or recommendation. The local F&O database has been located and sampled at the filesystem level, but it has not been connected to, inspected, audited, or qualified.

### Current decision point

The owner is being asked only to review this report and consider whether a later task may prepare a code-reviewable interlock-removal proposal. Even a positive answer would not change the interlock, connect to the database, authorize an audit, or permit analysis.

[PAGE BREAK]

## 1. What we are building

The intended system collects market evidence, preserves where it came from and when it became knowable, calculates deterministic features and outcomes, tests hypotheses out of sample, and reports uncertainty and limitations. If the evidence eventually supports it, the system may help with investment research, asset allocation, portfolio balancing, and downside-risk decisions.

The intended user-facing outputs are:

- a market-sentiment score supported by visible evidence;
- stock scores based on tested relationships rather than arbitrary weights;
- reproducible experiment results and historical score-bucket behavior;
- confidence and warning signals that are separate from the raw research score;
- explicit non-results when data quality or statistical evidence is insufficient.

The intended architecture keeps raw evidence, features, research definitions, validation, confidence, decisions, and portfolio risk separate. Deterministic and statistical code remains the quantitative source of truth. AI may explain evidence and help generate hypotheses, but it must not manufacture scores or replace reproducible calculations.

### Non-negotiable scope

- The project must not execute trades.
- Broker connections may be used for data only.
- No paid market-data source is required or authorized.
- Lawful free sources are preferred; AMFI applies to mutual-fund evidence, not equity survivorship or equity identity.
- Kite Connect current instruments are not a historical universe.
- Untested or unsupported scores remain hidden.

[PAGE BREAK]

## 2. Why development has been cautious

### Survivorship bias

If a historical study uses only companies that still exist today, failed, merged, suspended, or delisted securities disappear from the sample. The remaining group can look artificially successful. A trustworthy cross-sectional study needs the population that actually existed at each historical date.

### Look-ahead leakage

Leakage occurs when a calculation uses information that was published, revised, or otherwise available only after the decision time. Even one-day timing errors can turn unavailable knowledge into an apparently predictive signal.

### Incomplete historical populations and missing terminal outcomes

A daily price file proves that a security traded that day; it does not prove that it lists every security eligible to trade. Missing delisting proceeds, merger consideration, suspensions, and other terminal events can also exaggerate returns or silently drop losses.

### Ambiguous security identity

Ticker symbols can change and can later be reused. Company names are not stable identifiers. Without dated aliases, ISIN continuity, listing identifiers, and explicit successor relationships, observations can be joined to the wrong security.

### Silent data mutation

Providers can correct files or revise data. If old bytes are overwritten without hashes and retrieval records, a past result cannot be reconstructed exactly.

### Why a profitable-looking backtest can mislead

A backtest may appear profitable because of survivor selection, future information, inaccurate costs, untradeable prices, repeated tuning, or a benchmark mismatch. Profit alone is not validation. This project is therefore building evidence and governance controls before trusting market conclusions.

[PAGE BREAK]

## 3. Work completed to date

### Research architecture and Vertical Slice A

- The architecture was refined around point-in-time data, stable identity, feature and outcome definitions, reusable experiment execution, evidence, confidence, decisions, and portfolio risk.
- Vertical Slice A migrated the existing 12-1 momentum experiment into versioned temporal data, universe, feature, outcome, cost, experiment, manifest, and walk-forward contracts.
- Predictive quality, economic quality, and portfolio behavior were separated so a statistical relationship cannot be confused with an executable trade.
- Golden fixtures and deterministic manifests were added to show exactly where old and new behavior agree or differ.

### Historical-data trust work

- Provider-neutral ingestion, immutable raw manifests, typed normalization, identity reconciliation, corporate-action handling, and dataset acceptance were implemented.
- Public official-source access and historical-population reconstruction were tested conservatively.
- The broad local equity history was found to be survivor-selected and therefore unsafe for trustworthy historical cross-sectional conclusions.
- Current Kite instruments and quotes were isolated as current-market data and explicitly prevented from becoming a historical security master.

### Research governance

- Research families, preregistration, declared inputs, split access, one-use approvals, execution events, immutable manifests, and lifecycle controls were introduced.
- A synthetic governance canary demonstrated that the machinery can enforce a bounded, non-market run.
- Pre-research PDF gates require the owner to review the current state before later authority can be considered.
- Reconciliation contracts distinguish exploratory or legacy evidence from canonical evidence.

### F&O preparation

- A bounded synthetic F&O audit infrastructure was built and tested without production access.
- A disabled production boundary was added deliberately. Production activation remains impossible.
- After exact owner approval, R.9F performed one filesystem-only locator-binding ceremony.
- R.9F created a sanitized database alias and sampled identity without connecting to SQLite, executing SQL, reading schema, or reading market rows.

[PAGE BREAK]

## 4. What has and has not been validated

| Category | Current status | What is known | What remains missing | May influence a user-facing score? |
| --- | --- | --- | --- | --- |
| Infrastructure mechanics | MECHANICALLY_TESTED | Deterministic fixtures, hashing, manifests, temporal contracts, and bounded controls pass offline tests. | Real datasets still require separate qualification. | No |
| Governance and reproducibility | MECHANICALLY_TESTED | Review gates, one-use concepts, evidence binding, and fail-closed controls are implemented and tested. | Each real run still needs exact current evidence and approval. | No |
| Equity historical population | NOT_TRUSTED | Public-source work identified important coverage limits; broad local history is survivor-selected. | Complete dated population, inactive securities, identity, and terminal outcomes. | No |
| 12-1 momentum evidence | RESEARCHED_NOT_VALIDATED | The hypothesis was reproduced under explicit contracts and examined out of sample. | Trustworthy historical population and further independent confirmation. | No |
| Kite data | CURRENT_ONLY | Read-only current instruments and bounded current snapshots can be obtained after user login. | Historical population, delisted securities, and long-term point-in-time coverage. | No |
| Free-source reference data | PARTIALLY_QUALIFIED | Several official and lawful sources have been catalogued and sampled. | Complete, repeatable coverage and clear retention rights across the required history. | No |
| Local F&O database | LOCATED_AND_SAMPLED_NOT_QUALIFIED | A stable filesystem target with SQLite magic was sampled once under a bounded ceremony. | Connection, schema audit, row-level data-quality audit, provenance, completeness, and research fitness. | No |
| Market-sentiment scoring | NOT_BUILT_OR_VALIDATED | Component planning is documented. | Qualified inputs, registered hypotheses, out-of-sample evidence, and approval. | No |
| Stock scoring | NOT_BUILT_OR_VALIDATED | Component planning is documented. | Validated edge library, confidence rules, and qualified data. | No |
| Backtesting authority | PROHIBITED | Infrastructure tests and prior bounded research artifacts exist. | A current report, exact scope, and separate approvals for any future production-data work. | No |
| Trading capability | PROHIBITED | No trading authority exists. | Trading is outside the project boundary. | No |

Infrastructure tests demonstrate that machinery behaves as designed on tested inputs. They do not prove that a market dataset is complete or that a hypothesis predicts returns.

[PAGE BREAK]

## 5. Exact R.9F binding result

R.9F used the sanitized alias `PRIVATE_FNO_DATABASE_V1`. The private configured and resolved paths are intentionally absent from tracked evidence and from this report.

| Measurement | Recorded result |
| --- | --- |
| File size | 48,345,137,152 bytes |
| Header inspection | SQLite magic present in the first 100 bytes |
| Deterministic sample positions | 64 |
| Sampled chunk bytes | 268,435,456 |
| Total raw bytes read | 268,435,556 |
| Sample passes | 1 |
| Before/after stability | Passed during the single bounded pass |
| Database connection | Did not occur |
| SQL or PRAGMA | Not executed |
| Schema or market rows | Not inspected |
| Audit, analysis, or backtest | Not started |

**The sampled identity is not a full-file hash and does not prove that every unsampled byte remained identical.**

The method sampled 64 deterministic positions and checked file metadata and the first 100 bytes before and after the pass. A passed stability check means the sampled observations and checked metadata were stable during that bounded pass. It does not establish complete byte identity for a 48.3 GB file.

Modification time is metadata, not complete identity. It can help detect change, but it is not a substitute for a full-file cryptographic hash. R.9F therefore proves only that a specific safely resolved filesystem object was present and stable under the declared bounded checks. It does not prove data quality, completeness, provenance, point-in-time correctness, or suitability for research.

[PAGE BREAK]

## 6. Current safety boundary

The following states remain false:

```
database_connected: false
sql_executed: false
schema_inspected: false
market_rows_read: false
audit_started: false
analysis_started: false
backtest_started: false
trading_enabled: false
production_activation_eligible: false
```

The deliberate production interlock remains active:

```
R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE
```

The binding ceremony did not qualify the database and did not authorize it for research. The current software boundary still rejects production activation even if all modeled evidence inputs are set to true.

This report also creates no authority. Its authority state is:

```
owner_review_recorded: false
interlock_change_authorized: false
database_connection_authorized: false
audit_authorized: false
market_row_access_authorized: false
analysis_authorized: false
scoring_authorized: false
backtesting_authorized: false
trading_authorized: false
```

[PAGE BREAK]

## 7. Proposed development sequence

1. The owner reviews PDF v4.
2. If acceptable, record an exact and narrow owner decision covering only `EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY`.
3. Prepare a code-reviewable proposal explaining how the deliberate production interlock could later be replaced by an exact one-use authorization mechanism.
4. Review that proposal separately.
5. Only after another explicit owner authorization, implement the narrowly approved boundary change.
6. Generate another current pre-research report if the research state changes.
7. Obtain an exact one-use approval before the first database connection.
8. Conduct only the bounded F&O data-quality audit.
9. Review the audit results.
10. Decide whether the database is trustworthy enough for any analysis.
11. Only after another current PDF and owner approval may analysis, scoring, simulation, or backtesting begin.

Several separate approvals remain. Review of PDF v4 must not be interpreted as approval to change the interlock, connect to the database, execute an audit, inspect market rows, analyze data, score securities, simulate, backtest, recommend trades, or trade.

The next proposal, if authorized, would be a design and review artifact only. It would explain possible safeguards and the exact authority still required. It would not itself alter executable code or create access.

[PAGE BREAK]

## 8. Decisions requested from the owner

Please answer each question in order. Silence, a generic instruction to continue, or answers given before this PDF was generated do not count as review of version 4.

1. Is the stated project objective accurate: an analysis-only Indian market research system with evidence-backed sentiment and stock scores, reproducible research, visible uncertainty, no trade execution, and untested scores hidden?
2. Is the completed-work summary accurate enough, including the distinction between tested infrastructure, partially qualified data, researched hypotheses, validated hypotheses, and disabled production capabilities?
3. Is the free-source-only policy correctly represented, including lawful official sources, Kite Connect where appropriate, and AMFI only for mutual-fund evidence?
4. Is the description of R.9F accurate: one filesystem-only binding ceremony, a sanitized alias, bounded raw-byte sampling, stability checks, and no database connection, SQL, schema inspection, market-row access, audit, analysis, or backtest?
5. Do you understand and accept that the sampled identity is not a full-file hash, does not cover every byte, and that modification time is metadata rather than complete identity?
6. Should any risks, factual corrections, missing work, or additional constraints be added before development proceeds?
7. Do you authorize the next task to prepare an interlock-removal proposal only, without changing the interlock, connecting to the database, executing an audit, reading market rows, analyzing data, scoring, simulating, backtesting, recommending trades or trading?

Do not treat an answer to question 7 as database-access or audit authority. Any proposal produced later must be reviewed separately, and further explicit approvals remain mandatory.

[PAGE BREAK]

## Appendix A - Exact evidence bindings

| Evidence | SHA-256 or value |
| --- | --- |
| R.9F anchor | `115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc` |
| R.9F binding proposal | `995524b670dc95b717fa7d4b27935c788d661bcf75b8f7f4400d76831a8f434f` |
| Sampled-identity root | `b1b8c0ca1338d477987da28e6d9647b151c120a0eac7bb17c9e9293edfd4bc47` |
| Header SHA-256 | `9d708fa6ca29946338e85c37c74cfd058312013721a348278981756067faedc2` |
| Configuration file SHA-256 | `cb68999f6e0dd16796d017f1104cc630483ada44ed1959143b99c9e9d11d29a2` |
| R.9F source commit | `816333959097519297b3095da9c81a1677f50bf8` |
| R.9F completion commit | `b658033f7acf0fdc206831cedc5ef374c043e27d` |
| Current research fingerprint | `6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db` |
| Research-state file count | 242 |
| PDF v3 SHA-256 | `75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2` |
| Production interlock | `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` |

### Evidence inputs used

- `evidence/fno_locator_binding_v1/anchor.json` - tracked, sanitized R.9F result.
- `proposals/fno_locator_binding_v1/binding_proposal.json` - tracked, non-activating proposal state.
- `reports/RESEARCH_R9F_REPORT.md` - completed milestone explanation and verification results.
- `docs/project_status/pre_research_review_record_v3.json` - historical owner review and post-R.9F staleness record.
- Earlier architecture, data-trust, research-governance, and milestone reports summarized by the version 3 report and current fingerprint.

The private runtime binding artifact was not read for this report. Only the tracked sanitized evidence was used.

[PAGE BREAK]

## Appendix B - Evidence vocabulary

| Term | Meaning in this report |
| --- | --- |
| Mechanically tested | The implementation behaved as specified in deterministic tests. It is not a claim about real market-data quality. |
| Historically qualified | Point-in-time population, identity, events, and outcomes have sufficient evidence for the declared interval. Broad equity history has not reached this state. |
| Researched | A declared hypothesis was executed under research controls. This does not mean the result is validated or actionable. |
| Validated hypothesis | A hypothesis has met declared out-of-sample, economic, robustness, and data-trust gates. No current hypothesis is approved in this report. |
| Located and sampled | A filesystem object was found and bounded bytes were inspected. It is not database or data qualification. |
| Canonical evidence | Evidence admitted through declared hashes, provenance, approval, execution, manifest, and import controls. |
| User-facing score | A score displayed as evidence-backed decision support. No current evidence in this report may drive one. |

### Lifecycle result

```
PDF_V4_GENERATED_AWAITING_OWNER_REVIEW
```

This is the end of R.9G. No owner approval is recorded by this document. The production interlock remains active, and all database, audit, research, scoring, backtesting, broker, recommendation, and trading authority remains prohibited.
