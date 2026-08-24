# Historical Data Source Evaluation Template

Use one copy per candidate source. Complete it from contractual documentation, sample files, and a bounded technical evaluation. Ease of API access is not an acceptance criterion.

## Candidate identity

| Item | Answer | Evidence/reference |
|---|---|---|
| Provider/source |  |  |
| Product/version |  |  |
| Authoritative, vendor, or aggregator |  |  |
| Evaluation date and evaluator |  |  |
| Sales/technical contact |  |  |
| Expected cost and billing model |  |  |

## Dataset coverage

| Requirement | Available? | Earliest date | Fields/format | PIT/vintage behavior | Gaps/limitations | Evidence |
|---|---|---|---|---|---|---|
| NSE cash-equity daily OHLC/previous close/volume/exchange turnover/trade count |  |  |  |  |  |  |
| Historical listed-security master |  |  |  |  |  |  |
| Symbol and ISIN validity history |  |  |  |  |  |  |
| Corporate actions |  |  |  |  |  |  |
| Delisting/merger terminal outcomes |  |  |  |  |  |  |
| NIFTY 50 PRI |  |  |  |  |  |  |
| NIFTY 50 TRI |  |  |  |  |  |  |
| Historical transaction-cost schedules |  |  |  |  |  |  |

## Trust and operational review

| Criterion | PASS / FAIL / UNKNOWN | Required evidence |
|---|---|---|
| Point-in-time fidelity: publication/effective/revision timestamps |  | Sample vintages and documentation |
| Historical population includes inactive, merged and delisted securities |  | Counts by year and terminated-name samples |
| Stable listing/security ID quality |  | Identifier dictionary and lifecycle examples |
| ISIN continuity and changes |  | Dated mappings |
| Corporate-action completeness |  | Action taxonomy, announcement/ex/effective dates, factors |
| Delisting treatment |  | Cash/security consideration and unresolved policy |
| Exchange turnover is supplied, not derived |  | Field definition and raw sample |
| Benchmark explicitly distinguishes PRI and TRI |  | Index metadata/methodology |
| Retrieval method |  | API/SFTP/files/media and authentication |
| Raw data format and schema stability |  | Schemas, versioning and change policy |
| Update frequency and correction policy |  | SLA and revision behavior |
| Historical backfill availability |  | Full-universe sample/counts |
| Licensing permits local retention |  | Contract clause |
| Licensing permits derived research artifacts |  | Contract clause |
| Redistribution/display limitations |  | Contract clause |
| Exit/termination and support |  | Export rights and notice period |

## Required sample evaluation

- Ingest a bounded sample through the provider-neutral adapter.
- Verify raw hash and immutable manifest replay.
- Reconcile at least three normal listings, three symbol/ISIN changes, three splits/bonuses, three cash dividends, three mergers/demergers, and three delistings/suspensions.
- Compare yearly listed/new/terminated counts with an independent reference.
- Reconcile OHLCV and exchange turnover for randomly selected sessions.
- Confirm raw and adjusted prices are separate and adjustment factors are auditable.
- Run the dataset acceptance command and attach JSON/Markdown results.

## Capability conclusion

| Capability | PASS / FAIL / UNKNOWN | Evidence and limitation |
|---|---|---|
| `price_history_complete` |  |  |
| `survivorship_safe` |  |  |
| `historical_universe_reconstructible` |  |  |
| `corporate_actions_verified` |  |  |
| `delisting_outcomes_available` |  |  |
| `exchange_turnover_available` |  |  |
| `publication_timing_known` |  |  |
| `stable_security_identity_verified` |  |  |

Final decision: **ACCEPT / ACCEPT FOR LIMITED DECLARED CAPABILITIES / REJECT / MORE EVIDENCE REQUIRED**

Approved use, if any:

Prohibited use:

Open contractual questions:

Open technical questions:
