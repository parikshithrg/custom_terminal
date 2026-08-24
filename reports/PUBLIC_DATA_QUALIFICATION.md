# Official Public Data Qualification

## Reproducible sample

Specification: `specs/public_qualification_sample_v1.json`

Source registry: `specs/official_public_sources_v1.json`

Runner: `tools/qualify_official_public_sample.py`

The bounded run requested six official NSE objects and performed no bulk acquisition:

- Four fixed bhavcopy dates: 2012-01-03, 2016-01-04, 2020-01-02, and 2024-01-02.
- Current official NSE delisted-company workbook.
- NSE/CML/58016 symbol-change circular.

Every response retains URL, retrieval timestamp, request parameters, HTTP status/selected headers, exact bytes, SHA-256, parser version, retry history, and outcome. Quarantined bytes remain immutable and are never normalized.

## Retrieval results

| Object | Result |
|---|---|
| 2012 legacy bhavcopy | QUARANTINED — access-control/CAPTCHA-class HTML response; no bypass attempted |
| 2016 legacy bhavcopy ZIP | PASS |
| 2020 full bhavdata CSV | PASS |
| 2024 full bhavdata CSV | PASS |
| NSE delisted-company XLSX | PASS |
| NSE symbol-change PDF | PASS |

## Sample quotas

| Category | Required | Qualified | Result |
|---|---:|---:|---|
| Continuously observed equities | 3 | 3: INFY, RELIANCE, TCS on three qualified dates | PASS at sample level |
| Delisted securities | 3 | 3 official rows with symbol and ISIN | PASS at sample level; economic terminal treatment remains unresolved |
| Merger/ticker/ISIN transitions | 3 | 1: ADANITRANS → ADANIENSOL, effective 2023-08-24 | FAIL |
| Split | 1 | 0 | UNKNOWN |
| Bonus | 1 | 0 | UNKNOWN |
| Dividend | 1 | 0 | UNKNOWN |
| Rights | 1 | 0 | UNKNOWN |
| Demerger | 1 | 0 | UNKNOWN |
| Historical trading dates | 4 | 3 | FAIL |

No action or identity was guessed to fill a quota.

## Normalized evidence

The run emits versioned sample tables for daily observations, security identities, alias transitions, listing/status events, terminal outcomes, corporate actions, benchmark observations and statutory costs. Empty tables are explicit when no qualified object exists.

- Nine daily rows reproduce official raw OHLC, previous close, volume and exchange turnover for three symbols and three dates.
- Three delisted rows retain official symbol/ISIN/date/type evidence but use `UNRESOLVED` for final tradable price, consideration and successor.
- The symbol transition is tied to the exact official circular hash and effective date.
- Bhavcopy-only current-symbol observations remain unresolved stable identities because those files alone do not prove ISIN/listing continuity.
- Raw prices are never adjusted or overwritten.

Every populated normalized row carries `source_id`, `raw_payload_hash`, and `parser_version`.

## Three distinct conclusions

### Source feasibility

Partial. Official public files can provide exact dated prices, exchange turnover, selected delistings, and individual identity/action circulars.

### Sample qualification

Partial and insufficient. Some price and lifecycle cases pass, but most action quotas, identity continuity, benchmark, cost schedule, and an older price date remain unqualified.

### Production historical coverage

Fail. The sample does not prove a complete historical security population or continuous terminal/action coverage. No capability is promoted from sample success.

## Updated capability assessment

| Capability | Result |
|---|---|
| `price_history_complete` | FAIL |
| `survivorship_safe` | UNKNOWN |
| `historical_universe_reconstructible` | FAIL |
| `corporate_actions_verified` | UNKNOWN |
| `delisting_outcomes_available` | FAIL |
| `exchange_turnover_available` | UNKNOWN at production scale; PASS only for sampled bhavcopy rows |
| `publication_timing_known` | UNKNOWN |
| `stable_security_identity_verified` | FAIL |

Machine-readable assessment: `specs/public_official_feasibility_trust_v1.json`.

## Unresolved blockers

- Complete historical security snapshots and population counts.
- Two additional authoritative symbol/ISIN/merger transitions.
- Qualified split, bonus, dividend, rights and demerger cases with PIT timestamps.
- Terminal final-price/consideration evidence for delistings.
- BSE independent reconciliation sample.
- NIFTY 50 PRI/TRI bounded sample and usage permission.
- Complete historical statutory schedule.
- Documented automated retrieval and local-retention rights.

## Readiness decision

**public sources remain insufficient without manual evidence collection**
