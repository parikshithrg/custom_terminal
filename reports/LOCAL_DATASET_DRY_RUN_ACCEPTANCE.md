# Local Dataset Dry-Run Acceptance

Provider: `local_audited_files_v1`

Canonical dataset: `local_audited_equity_history`

Dataset version: `sha256:e88d52a3cdada96a`

Raw objects manifested: 296

Canonical daily-equity rows: 1,166,839

## Capability result

| Capability | Status | Evidence |
|---|---|---|
| `price_history_complete` | FAIL | No complete independent historical listing population supplied. |
| `survivorship_safe` | FAIL | Multi-year panel contains no terminated listings. |
| `historical_universe_reconstructible` | FAIL | Population, turnover and identity prerequisites fail. |
| `corporate_actions_verified` | UNKNOWN | No authoritative action ledger supplied. |
| `delisting_outcomes_available` | FAIL | No authoritative terminal-outcome dataset supplied. |
| `exchange_turnover_available` | FAIL | 1,166,839 rows lack exchange turnover. |
| `publication_timing_known` | UNKNOWN | 1,166,839 rows lack provider publication timestamps. |
| `stable_security_identity_verified` | FAIL | 294 security identities remain unresolved. |

## Reconciliation findings

- Duplicate listing/trade dates: 0.
- Impossible OHLC rows: 5.
- Non-positive OHLC rows: 609.
- Zero or missing volume rows: 2,962.
- Missing benchmark sessions within observed listing periods: 14,606.
- Historical cost-schedule coverage gaps: 1.
- Benchmark classification: explicit local PRI classification; TRI absent.

## Decision

**REJECTED FOR EDGE RESEARCH.**

The dry run proves the adapter → immutable raw manifest → typed normalization → reconciliation → trust-contract path. It does not improve or supersede the Slice A.5 trust verdict.

Full generated outputs are stored locally under `artifacts/acceptance/local_audited_files_v1/`; content-addressed raw objects are under `artifacts/raw/local_audited_files_v1/`.
