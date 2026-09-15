# R10N-G authoritative NSE OHLC semantics and remediation decision

## Outcome

Official NSE UDiFF material defines `OpnPric`, `HghPric`, `LwPric`, and `ClsPric` as opening, daily high, daily low, and daily closing price; it defines `TtlTradgVol` separately as total traded quantity and `SttlmPric` as a conditional settlement price. The reviewed documents do **not** state that `ClsPric` must lie within `LwPric` and `HghPric` whenever total volume is nonzero, and they do not establish that every trade state contributes identically to aggregate volume and OHLC.

NSE's equity-derivatives settlement methodology says a liquid futures closing price is a last-half-hour weighted average, while an unexpired illiquid futures contract can receive a theoretical settlement price. This establishes that settlement must remain separate from traded OHLC, but it does not prove the exact exception responsible for the two retained STF rows. No value may be replaced or manufactured.

Decision: propose `nse_fno_ohlc_semantics_v1` for a separately approved R10N-H implementation. This decision does not modify the adapter or qualify the source.

## Owner decision packet

- **Current rule:** for every nonzero-volume row, the candidate requires high to be at least open, close, and low, and low to be at most open, close, and high. Any breach is `OHLC_INCONSISTENT`.
- **Why unsupported:** the UDiFF definitions name distinct fields, but contain no close-within-range contract and no common trade-universe rule. NSE separately documents calculated closing and settlement bases.
- **Proposed rule:** always fail malformed required values, negative volume, source/identity failures, and `high < low`. Enforce open containment as fatal only when qualifying-trade coverage is authoritatively established. Treat observable open/close range departures with unresolved basis as deterministic, qualification-blocking diagnostics. Keep settlement and zero-volume states separate.
- **Cases remaining fatal:** malformed/missing required values, negative volume, `HIGH_BELOW_LOW`, an open-range violation under an authoritatively established qualifying-trade contract, source/identity failure, and the unresolved MII expiry encoding.
- **Explicit diagnostics:** `OPEN_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS`, `CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS`, `SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS`, `ZERO_VOLUME_PRICE_STATE`, and `TRADE_STATE_ATTRIBUTION_UNAVAILABLE`.
- **Three-date impact:** 2026-09-09 and 2025-07-08 have no nonzero-volume range diagnostic; 2026-09-10 has two sanitized STF `high_below_close_only` diagnostics. The zero-volume states remain visible at 21,774, 22,201, and 19,662 rows respectively. All three dates remain unqualified.
- **False-rejection risk:** the current combined rule rejects rows based on a relationship the reviewed authority does not prescribe.
- **False-acceptance risk:** parsing an anomaly could conceal bad source data unless its code and exact value relationship remain deterministic and block qualification. The proposal preserves that block.
- **Unresolved expiry issue:** both trigger identities resolve uniquely, but interpreting MII `XpryDt` as Unix seconds produces the same month/day exactly ten years earlier than UDiFF. UTC-to-IST conversion does not change either date. The official evidence reviewed does not define the MII numeric epoch, so expiry remains a separate fail-closed gate.
- **Tests required before implementation:** split-invariant, status-code/count, zero/nonzero state, settlement separation, no-mutation, qualification-blocking, expiry fail-closed, and bounded three-package offline regression tests.

The owner decision for a later milestone is: authorize or decline a separately scoped R10N-H implementation of `nse_fno_ohlc_semantics_v1`. R10N-G itself grants no implementation authority.

## Official evidence

The bounded review used only the official NSE [Forms & Formats page](https://www.nseindia.com/static/resources/forms-formats-members), its linked UDiFF Guidance Note, current UDiFF Catalogue Version 4.0, current Trade and Bhavcopy File Formats, the official [equity-derivatives settlement-price page](https://www.nseindia.com/static/products-services/equity-derivatives-settlement-price), and NSE circular MSD60315 identifying the daily MII contract file. Hashes and exact document metadata are recorded in the sanitized evidence inventory; no full document is committed.

No market-report URL was requested, no new payload or date was acquired, and the candidate adapter remained byte-identical.
