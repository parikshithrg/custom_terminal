# Corporate-Action Contract Comparison

## Finding

`dtest.data.corporate_actions` contains a useful discontinuity detector, not an
authoritative corporate-action ledger. It compares exchange-published
`prev_close` with the previous traded close, rejects market-wide inconsistency,
and derives an isolated adjustment factor. Its reporting labels suggest common
split or bonus ratios, but it cannot prove action type, announced ratio,
dividend treatment, rights terms, merger continuity or the authoritative event
record.

`market_intel` has the stronger canonical evidence model: typed corporate
actions with publication/effective dates, action types, ratios or cash amounts,
old/new identifiers and predecessor/successor links. Its trust gate correctly
keeps corporate-action verification `UNKNOWN` where the authoritative ledger is
absent.

## Required semantic separation

| Stage | `dtest` evidence | Canonical meaning |
|---|---|---|
| Exchange `prev_close` observed | yes | a published reference field exists |
| Isolated discontinuity candidate | yes | a large symbol-level discrepancy survived local guards |
| Market-wide inconsistency rejected | yes | suspect whole-market dates are quarantined |
| Adjustment factor derived | yes | a numerical continuity factor can be produced |
| Corporate-action type verified | no | requires authoritative event evidence |
| Ratio verified authoritatively | no | derived factor is not announcement terms |
| Dividend-inclusive return available | no | module explicitly excludes ordinary cash dividends |
| Authoritative action record linked | no | no event ID/source payload link is attached |

The shared `CorporateActionEvidence` contract enforces these as separate stages.
It refuses a verified action/type claim without an authoritative evidence
reference and requires raw prices to remain preserved.

## Actual strategy use

The corporate-action module is tested and has a standalone verification script,
but the inspected hypothesis scripts simulate on raw OHLC panels. The
mean-reversion script calls `detect_actions` and prints counts, yet its signal,
ATR, fills and exits still use raw closes/highs/lows/opens. No hypothesis script
imports `adjusted_close`; `daily_returns` is not used in strategy P&L.

| Strategy group | Observed price treatment |
|---|---|
| Mean reversion, delivery/OI/participant/volatility/price-action | raw OHLC; inferred action report is diagnostic only where called |
| Momentum | raw close for 252/21-session ranking and raw open for 21-session execution |
| Pairs/same-sector pairing | raw cash closes for spread events; raw cash/futures execution prices |
| Earnings surprise, value, quality | fundamental trigger combined with raw OHLC execution |
| Existing `market_intel` momentum | raw local OHLC, explicit unresolved-action limitation; no inferred adjustment inside outcome |

Therefore existing results are neither verified total-return results nor
consistently corporate-action-adjusted price-return results. Long-horizon
momentum, value and fundamental holds are especially exposed to unadjusted
splits, bonuses, dividends and identity transitions.

## Canonical recommendation

- Preserve raw exchange observations unchanged.
- Materialize candidate factors separately and label them inferred.
- Join authoritative actions before marking action type or ratio verified.
- Version price-return and dividend-inclusive series independently.
- Require every experiment manifest to state which series it used.
- Do not silently replace existing strategy artifacts; compatibility adapters
  must retain their raw-price semantics.
