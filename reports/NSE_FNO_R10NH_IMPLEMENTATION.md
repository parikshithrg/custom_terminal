# R.10N-H — Versioned OHLC Semantics and MII Expiry Encoding

R.10N-H implemented `nse_fno_ohlc_semantics_v1` in the isolated candidate adapter. It does not qualify or activate the source.

The parser still fails closed on malformed required numerics, negative volume, `high < low`, package-integrity failures, identity failures, invalid MII expiry encodings, and any MII/UDiFF expiry mismatch. With qualifying-trade coverage still unresolved, open and close outside the published daily range are now deterministic qualification-blocking diagnostics rather than parse failures. Settlement-range observations are informational and separate. Every zero-volume row produces a visible state diagnostic and is not treated as a traded range. Source prices are never changed or imputed.

The prior Unix-time assumption was removed. NSE's current Master Data Specification v1.6 defines the F&O Contract Expiry Date as integer seconds elapsed from midnight 01-Jan-1980. NSE circulars identify the standardized `NSE_FO_contract_ddmmyyyy.csv.gz` as the FO MII contract file. The named decoder therefore uses exact timezone-free arithmetic from that origin. Empty, zero, signed, noninteger, overflowing, and out-of-bounds values fail closed because the reviewed F&O specification supplies no nullable expiry rule.

Offline regression revalidated the retained 2026-09-09, 2026-09-10, and 2025-07-08 packages without network access. All 99,026 joined fact rows had matching decoded MII and UDiFF expiries. Exact source and normalized price-tuple digests matched on every date. The two prior 2026-09-10 close-range observations are now explicit blocking diagnostics; zero-volume state counts remain visible. No raw rows, identifiers, archives, or official-document review copies were added to Git.

The adapter remains `CANDIDATE_NOT_PRODUCTION_AUTHORIZED`. The research fingerprint remains stale and fail closed. R.10N-I requires separate owner approval before offline source requalification.
