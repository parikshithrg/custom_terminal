# Dashboard equity prerequisite documentation review v1

Completed 2026-09-19 after the owner confirmed applicable Kite account/application
permission for exclusively private local cash-equity display and transient
in-memory processing, and authorized this documentation-only review. No credentials,
authenticated endpoints or market-data payloads were accessed.

## Result

The review **partially resolves** the eligibility prerequisites. Current LTP
meaning and authoritative session sources are established. REST currency labelling,
a maintained calendar implementation and a compliance-record design remain open.
Dashboard wiring is therefore still blocked.

### Price and adjustment semantics

Kite defines full-quote `last_price` as the last traded market price, `timestamp`
as the exchange quote-packet time, `last_trade_time` separately, and `ohlc.close`
as the prior trading day's close. The consumer may therefore treat `last_price`
only as a current trade observation. It must not call it an adjusted historical
price, settlement value or valuation close. No corporate-action adjustment is
performed or required for this current-only display because no history/change
comparison is authorized.

The WebSocket specification states non-currency packet prices use paise scaling,
but the REST full-quote response has no explicit currency field. That supports a
unit inference but does not authoritatively bind each REST NSE-EQ value to INR.
The currency/unit gate remains unresolved rather than relying on symbol similarity.

### Exchange session policy

NSE's official timings/holidays page supplies the authoritative source for normal
equity hours, annual holidays and special-session notices. It records regular
equity trading from 09:15 to 15:30 IST and a pre-open period beginning 09:00,
with declared holidays and exceptional sessions handled separately.

A future calendar must be versioned, timezone-aware and date-explicit. Weekends
plus a stale holiday list are insufficient; Muhurat, Budget, contingency and
other special sessions require explicit NSE entries. Unknown or expired calendar
coverage blocks current-market display. No calendar was downloaded or implemented.

### Cache, retention and compliance

Kite's terms contemplate an exclusively private personal interface and prohibit
public live-data display and redistribution. They restrict permanent content
copies/caches absent permission, refer to permitted cache headers, and require
complete compliance trails for at least five years or applicable law.

No quote response or cache header was accessed, so no cache duration is inferred.
The conservative proposal keeps raw quote bytes and parsed prices only in transient
session memory. A separate durable compliance ledger would retain only aggregate
request timing, endpoint category, counts, sanitized outcome, byte/duration and
policy/code versions—never credentials, account/instrument identifiers, prices,
bodies, sensitive headers or private paths. This proposed schema is not yet
implemented and is not represented as a legal conclusion that every obligation is
satisfied.

## Remaining gates

- Authoritative REST NSE-EQ currency/unit binding.
- Implemented, maintained NSE cash-session calendar with special-session updates.
- Owner-reviewed sanitized compliance-record policy and retention implementation.
- Exact live target binding and separately approved bounded operational test.
- Separate consumer/display approval after all gates pass.

The earlier owner confirmation satisfies a project prerequisite but is not
publisher-issued evidence. Synthetic tests and manual 50/50 coverage cannot
promote the source. The Dashboard remains synthetic; no UI/provider code changed.
F&O remains hidden, deferred and unqualified.

## Proposed next scope—not executed

Implement offline-only session-policy and sanitized compliance-ledger contracts
using invented fixtures and caller-injected dates/times. The calendar contract
would accept versioned declared sessions/holidays/special sessions rather than
performing network access. The ledger would implement the proposed aggregate
schema without credentials, identities, prices or payloads. Neither contract
would authorize live requests, persistence, Dashboard wiring, research or trading.

Official sources reviewed:

- [Kite market quotes](https://kite.trade/docs/connect/v3/market-quotes/)
- [Kite WebSocket price units](https://kite.trade/docs/connect/v3/websocket/)
- [Kite API terms](https://kite.trade/terms/)
- [Kite errors and rate limits](https://kite.trade/docs/connect/v3/exceptions/)
- [NSE market timings and holidays](https://www.nseindia.com/resources/exchange-communication-holidays)
