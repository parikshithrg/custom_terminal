# Dataset Trust Report — Vertical Slice A.5

## Verdict

**NOT TRUSTED** for cross-sectional equity-edge research.

The directory behaves like a survivor-selected collection derived from a current security list, not a historically complete exchange population. This is a data verdict, not a verdict on momentum profitability.

## Scope and evidence

- Audit cutoff: 2026-08-13.
- Local directory: 430 `*_DAILY.csv` files.
- Classification using the local industry map: 294 current-map equities, 131 benchmarks/indices, and 5 other or unresolved instruments.
- Independent local reference: 10,417 index inclusion/exclusion event rows covering 1,993 distinct historical symbols.
- Historical reference symbols absent from the current equity directory: 1,699.
- No provider was purchased, scraped, queried, or downloaded during this audit.

The complete machine-readable inventory, annual coverage, discontinuities, absent-reference symbols, provisional security master and audit manifest are under `artifacts/data_audit/local_430_v1/`.

## Coverage and survivorship diagnostics

The current-map equity population grows almost monotonically from 4 names in 2000, 128 in 2004, 180 in 2010, 257 in 2021, to 294 in 2025. No current-map equity disappears in any annual transition, and 100% of the equities observed in every historical year continue to the local dataset end.

That pattern is incompatible with a complete history of the Indian listed-equity population over 26 years. It is consistent with taking a present-day list and attaching whatever back history remains available for those survivors.

Additional findings:

- 125 of 294 equity files start in 2010 or later.
- 127 contain at least one gap longer than five benchmark trading sessions.
- No equity file contains exchange turnover; Slice A derived a proxy as close × volume.
- Four equity files contain zero or negative OHLC values.
- No duplicate dates were detected after parsing.
- All 294 current-map equities reach the dataset end, so delisted and merged names are structurally absent rather than properly represented with terminal outcomes.
- Large close-to-close discontinuities were detected as candidates only. Without authoritative corporate-action records, they cannot be classified reliably as splits, bonuses, transformations, or bad data.

## Independent local-reference comparison

The index-event archive is not a complete exchange security master, but it is independent evidence that the price directory omits historically relevant securities. It contains 1,699 distinct event symbols absent from the 294-file current-map equity population. The missing-event table retains every relevant event row rather than guessing identity links.

The workspace also contains 926 symbol-named fundamental files, including historical aliases and failed/merged entities. These names are useful leads but cannot establish price coverage, ISIN continuity, listing intervals, or successor relationships on their own.

## Dataset capability contract

| Capability | Status | Reason |
|---|---|---|
| `price_history_complete` | FAIL | Present-day mapped population omits known historical symbols and terminal histories. |
| `survivorship_safe` | FAIL | Every current-map equity continues to the dataset end; historical exits are absent. |
| `historical_universe_reconstructible` | FAIL | Liquidity can be recomputed only within the survivor-selected population, not the historical market population. |
| `corporate_actions_verified` | UNKNOWN | Discontinuities exist, but no authoritative action ledger is joined. |
| `delisting_outcomes_available` | FAIL | No resolved delisting/merger terminal values are available. |
| `exchange_turnover_available` | FAIL | All equity files lack turnover; close × volume is only an approximation. |
| `publication_timing_known` | UNKNOWN | Files contain event dates but no publication/retrieval history from the upstream source. |
| `stable_security_identity_verified` | FAIL | Identity is filename-based; ISINs, listing IDs and alias intervals are unavailable. |

The versioned contract is `specs/local_equity_daily_trust_v1.json`. Experiments requiring any failed or unknown capability are automatically non-promotable.

## Security identity and terminal outcomes

A provisional security master now separates issuer, instrument, listing, ISIN, aliases, validity dates and predecessor/successor relationships. None of those relationships is silently inferred. All 294 equity mappings remain `UNRESOLVED` because the local filename and current industry map do not prove stable identity.

The terminal-state contract distinguishes ordinary missing data, temporary suspension, permanent delisting, merger/acquisition, demerger, ticker change, source failure, and unresolved terminal state. Missing exits remain unresolved unless an authoritative event determines the cause; terminal values are never invented.

## Historical-universe integrity

The liquidity algorithm itself is causal within the supplied panel:

- selection uses trailing 63-session liquidity and information through the decision close;
- membership becomes active on the following session;
- later disappearance does not erase earlier eligibility;
- staleness and history rules are evaluated at each decision time;
- the minimum-history rule is a declared eligibility constraint, not a future-survival check.

However, causal calculation within an incomplete panel does not make the universe historically complete. The universe capability therefore fails.

## Benchmark audit

`NIFTY50_DAILY.csv` contains OHLC index levels from 2000-01-03 through 2026-08-13 and no dividend or TRI field. It is classified as a **price return index**, not a total return index. Its upstream provider and adjustment methodology are not recorded locally.

Stock outcomes use raw local OHLC and are not proven dividend-inclusive. The current comparison is therefore price-like versus price-index, but neither side has sufficient corporate-action/dividend provenance for publication-quality inference. Benchmark metadata is explicit in `market_intel.foundation.benchmarks`.

## Cost-model audit

The Slice A compatibility model is preserved unchanged as `india_delivery_2026_08_13_slippage_5bps_v1`. Its 2026 statutory rates are not valid as a verified historical schedule back to 2004.

- Brokerage: broker/product dependent; zero is a current delivery assumption, not universally historical.
- STT, exchange charges, SEBI charges, stamp duty and GST: potentially date-varying statutory components.
- Slippage: approximate and unknowable from daily OHLCV alone.
- Market impact and bid/ask spread: unknown.

A date-effective schedule wrapper has been added. Dates outside a registered schedule fail explicitly. The golden fixture still uses the original compatibility version.

## Statistical dependence and baselines

Inference no longer uses row-level IID errors for approval. A moving decision-date block bootstrap resamples whole monthly cross-sections, preserving contemporaneous dependence and short serial dependence from overlapping holding windows. Fixed seed, block length and replication count are reported.

The baseline framework supports benchmark return, equal-weight eligible-universe return, matched-size random portfolios, and a within-decision-date rank placebo. Random/placebo results are distributions over recorded seeds, not a single favorable draw. These tools were implemented but not used to tune momentum.

## Rerun decision

State **C — dataset remains unsuitable**.

`momentum_12_1_v1` was not rerun for edge approval. Restricting to an apparent interval would not solve the missing historical population, identity, corporate-action or delisting problems. Slice B should not begin until the mandatory data requirements are satisfied and re-audited.
