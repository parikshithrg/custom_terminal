# R10N-F offline OHLC semantic failure diagnosis

The retained 2026-09-09, 2026-09-10, and 2025-07-08 packages matched every tracked manifest size and SHA-256 binding before row access. Full ZIP CRC and GZIP decompression/CRC validation passed. No network request, download, archive extraction, or package deletion occurred.

The unchanged R10N-C adapter reproduced `OHLC_INCONSISTENT` at 2026-09-10 CSV row 4724. Predicate-level exact-decimal diagnosis shows that only `high_below_close` is true: high equals both open and low, while close is 3534.20 above high. The row has nonzero volume. A second nonzero-volume STF futures row on that date has the same sole predicate with a 28.80 gap. The differences rule out rounding or sub-paise precision.

Across the three dates, every other close-above-high occurrence belongs to a zero-volume row: 21,774 on 2026-09-09, 22,201 on 2026-09-10, and 19,662 on 2025-07-08. There are no high-below-open, high-below-low, low-above-open, or low-above-close cases. The two nonzero cases occur only on 2026-09-10 and are both STF futures. Matching MII identifiers resolve uniquely, with no duplicate, conflicting, or unresolved identifier contribution. The current cross-file expiry interpretation disagrees for both examples, but expiry is not an input to the OHLC predicate.

The adapter implements its declared rule correctly, so this is not an implementation-branch defect. The retained official-format evidence remains `PENDING_OFFICIAL_FORMAT_EVIDENCE`: it contains official report column names but no authoritative definitions establishing that close must lie inside high/low whenever total volume is nonzero, nor a definition of special trade states. The observed predicate violation is confirmed; its exchange-intended meaning is not. It would therefore be unsafe either to label the source corrupt or to relax the rule.

The rule's semantics require a separately reviewed R10N-G remediation decision with explicit field/trade-state semantics and regression tests. This milestone does not modify the adapter or qualify the source. `CANDIDATE_NOT_PRODUCTION_AUTHORIZED` and `MULTI_DATE_SOURCE_NOT_QUALIFIED` remain in force.

Decision: `ADAPTER_OHLC_RULE_SEMANTICS_REQUIRE_REMEDIATION`.
