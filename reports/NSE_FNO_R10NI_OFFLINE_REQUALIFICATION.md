# R.10N-I — Offline Requalification of Three Retained NSE F&O Dates

All three retained, hash-bound packages passed the integrity preflight and were evaluated offline under the unchanged `nse_fno_ohlc_semantics_v1` and `nse_fo_elapsed_seconds_from_1980_01_01_v1` contracts. No network request, adapter change, new date, ingestion, research, production activation, or deletion occurred.

The UDiFF and MII schemas are stable: every date has the same 34 UDiFF and 150 MII columns, no required or non-required additions/removals, strict type parsing succeeds, and observed price/strike precision remains two decimal places. All 99,026 fact identities join uniquely, all decoded MII expiries agree with UDiFF, required fields remain explicit, and exact price digests are unchanged.

The 2026-09-09 and 2025-07-08 dates pass independently. The 2026-09-10 date does not pass because two `CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS` diagnostics and one `TRADE_STATE_ATTRIBUTION_UNAVAILABLE` diagnostic remain qualification-blocking. Settlement-range and zero-volume diagnostics remain visible and nonblocking. Ordinary contract additions/removals are recorded only as expected population turnover, not correction evidence.

Because every approved date must pass, the overall source route remains unqualified despite stable schemas. The appropriate next step is a separately authorized source-policy decision, not bounded historical-ingestion design. Existing 2026-12-31 retention deadlines remain unchanged; no package may be deleted without explicit owner authorization and exact path verification.
