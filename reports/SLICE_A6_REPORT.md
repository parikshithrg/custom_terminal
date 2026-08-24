# Vertical Slice A.6 — Historical Data Acquisition & Ingestion Readiness

## Outcome

The system is ready to plug in and objectively evaluate an approved historical-data source without coupling research code to a provider. No external source was contacted, scraped, purchased or downloaded.

The local-file dry run remains **REJECTED FOR EDGE RESEARCH**, preserving the Slice A.5 verdict and non-promotable state.

## Relevant code tree

```text
src/market_intel/foundation/
  providers.py                    provider-neutral protocols and dataset kinds
  raw_ingestion.py                immutable payloads and raw manifests
  canonical_schemas.py            six typed canonical table schemas
  local_file_provider.py          dry-run adapter only
  identity_resolution.py          deterministic listing/ISIN/alias workflow
  corporate_action_integrity.py   non-destructive classification/factors
  reconciliation.py               reusable integrity and population checks
  acceptance.py                   trust-capability acceptance harness
tools/
  run_dataset_acceptance.py       end-to-end acceptance command
tests/
  test_ingestion_readiness.py     A.6 failure-mode tests
```

Existing research, simulation and evidence packages were not given provider dependencies.

## Provider-neutral flow

```text
HistoricalDataProvider.discover
  -> ProviderObject
  -> acquire_immutable
  -> RawObjectManifest + content-addressed payload
  -> provider normalizer
  -> typed canonical Parquet
  -> reconciliation checks
  -> DatasetTrustContract + evidence
```

Research continues to consume only canonical datasets/snapshots. Replacing a provider requires a new adapter/parser, not changes to momentum, universe, outcome or experiment code.

## Canonical datasets

- `daily_equity_v1`: date, stable references, symbol/series, raw OHLC/previous close, volume, exchange turnover, trade count and provenance.
- `security_master_v1`: issuer/instrument/listing, exchange/series, symbol, ISIN, validity/listing/end dates and status.
- `corporate_actions_v1`: typed action and PIT/effective dates, ratio/cash terms, old/new and predecessor/successor references.
- `terminal_outcomes_v1`: suspension/termination, reason, authoritative final price/consideration, successor and resolution state.
- `benchmark_history_v1`: index, PRI/TRI, OHLC, methodology and source.
- `cost_schedules_v1`: component, effective interval, rate/base, citation and version.

These remain separate typed tables rather than generic field/value storage.

## Dry-run result

- Provider: `local_audited_files_v1`.
- Raw objects: 296 (294 equity files, one current industry/security list, one NIFTY 50 file).
- Canonical price rows: 1,166,839.
- Dataset version: `sha256:e88d52a3cdada96a`.
- Decision: rejected for edge research.

Capabilities remain:

| Capability | Result |
|---|---|
| Price history complete | FAIL |
| Survivorship safe | FAIL |
| Historical universe reconstructible | FAIL |
| Corporate actions verified | UNKNOWN |
| Delisting outcomes available | FAIL |
| Exchange turnover available | FAIL |
| Publication timing known | UNKNOWN |
| Stable security identity verified | FAIL |

Additional reconciliation evidence includes 5 impossible OHLC rows, 609 non-positive-price rows, 2,962 zero/missing-volume rows, 14,606 missing benchmark sessions inside observed listing spans, 294 unresolved identities and an uncovered historical cost interval.

## Exact external fields still required

1. Daily equity: exchange security/listing ID, ISIN where published, series, raw OHLC, previous close, volume, exchange turnover, trade count, source publication timestamp and correction/revision identity.
2. Security identity: stable issuer/instrument/listing IDs, ISIN, exchange/segment/series, dated symbols, listing/end dates, status and predecessor/successor relationships.
3. Corporate actions: typed action, announcement/publication/ex/record/effective dates, ratios/cash amounts, old/new identifiers, predecessor/successor and authoritative source record.
4. Terminal outcomes: suspension/termination dates, reason, authoritative final tradable price, cash/security consideration, successor and explicit unresolved treatment.
5. Benchmarks: stable index ID, explicit PRI and TRI series, open/close where available, methodology version, effective/publication metadata and revisions.
6. Costs: each statutory component, effective interval, rate/base/buy-sell applicability, primary-source citation and schedule version.
7. Population reference: independent listed/new/terminated counts and security identifiers by date or year.
8. Licensing: local raw retention, correction retention, derived research use, display/redistribution limits and post-termination export rights.

## Preservation

- `momentum_12_1_v1` and its specification were not changed.
- Golden fixtures and Slice A manifests were not changed.
- Slice A.5 trust specifications and verdict were not changed.
- No momentum rerun, optimization, Slice B research, production score or Streamlit decision integration occurred.

## Stop decision

Slice A.6 is complete. The next permitted activity is evaluation of candidate sources with the template and, only after explicit approval, a bounded sample or acquisition. Slice B remains blocked by the existing trust contract.
