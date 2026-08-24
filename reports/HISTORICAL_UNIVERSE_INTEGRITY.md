# Historical Universe Integrity Report

## Result

The implementation is point-in-time causal, but the materialized universe is not historically representative because its input columns are survivor selected.

Verified by code and tests:

- A rebalance at close T becomes eligible only after T.
- Liquidity uses trailing data only.
- Minimum history and staleness are calculated as of each decision.
- An instrument that disappears later remains eligible at earlier decisions.
- Exclusions and dataset/universe versions are persisted.

Unresolved data-level failures:

- Known historical symbols are missing from the panel.
- Delistings, mergers, and renamed listings cannot enter or terminate correctly.
- `close × volume` is not verified exchange turnover.
- Current ticker filenames do not prove historical listing identity.

Conclusion: `historical_universe_reconstructible = FAIL` for the audited snapshot, despite the universe algorithm passing its causal integrity tests.
