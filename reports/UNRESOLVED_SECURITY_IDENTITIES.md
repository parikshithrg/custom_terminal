# Unresolved Security Identity Report

All 294 current-map equity filenames remain unresolved as stable historical identities.

Available evidence proves only a current symbol string and a local file date span. It does not prove issuer continuity, NSE listing identity, ISIN, listing/delisting date, or predecessor/successor relationships. The implementation therefore creates provisional `instrument_id` values with an explicit unknown-listing component and leaves every identity relationship unresolved.

Machine-readable records:

- `artifacts/data_audit/local_430_v1/security_master_provisional.parquet`
- `artifacts/data_audit/local_430_v1/symbol_aliases_provisional.parquet`
- `artifacts/data_audit/local_430_v1/historical_reference_symbols_absent.parquet`

Resolution requires an authoritative dated security master with ISIN and symbol-change history. Company-name similarity or filename similarity must not auto-merge instruments.
