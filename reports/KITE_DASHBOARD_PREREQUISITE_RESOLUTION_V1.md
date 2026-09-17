# Kite Dashboard prerequisite resolution v1

Recorded 2026-09-17 against `7e55f00c6cff300de543e5ce8245103669a46004`.
Initial worktree clean. Owner “continue on next step” authorizes further public
documentation prerequisite review, not account access or live activation.
This supplements the earlier review; historical reports/contracts are unchanged.

## Newly resolved: REST timezone

Kite's v3 Response structure, Data types section explicitly specifies response
datetime strings in IST, UTC+05:30. This supplies the missing authoritative
timezone binding for the documented REST string format. Reviewed 2026-09-17;
no effective date or revision identifier was verified.
[Official response structure](https://kite.trade/docs/connect/v3/response-structure/)

Future provider-specific parsing can bind this rule to documented naive strings
and normalize to UTC while retaining the original lexical values. It must reject
malformed/nonconforming timestamps, not infer arbitrary clock meaning. This does
not retrospectively validate actual responses, authorize execution or change the
synthetic parser's caller-injected policy. No document copy was retained.

The full quote's `timestamp` identifies exchange quote-packet time and
`last_trade_time` identifies nullable last-trade time; `last_price` is last traded
market price. These remain different facts. This is not an adjusted historical
series specification or proof of a case-specific price basis.
[Official quote attributes](https://kite.trade/docs/connect/v3/market-quotes/#response-attributes)

## Permission and account boundary still pending

The Terms contemplate private personal interfaces, restrict public display and
live-data mock trading, limit permanent content copies/redistribution caches,
and require compliance records. Individual/product agreements can supersede
general terms. Public documentation cannot verify the owner's applicable
conditions, current entitlement or permission for a specific cache/log design.
[Official Terms, §§2, 4, 5, 13](https://kite.trade/terms/)

Owner confirmation needed: active data-entitled account/application, reviewed
applicable agreements and permission for exclusively private local cash-equity
display. Do not supply credentials, user IDs or account documents through chat.
This is a prerequisite declaration, not provider-issued evidence or approval of
any public deployment, historical retention, strategy research or trading.

Proposed scope for a future rights review: prices/raw responses memory-only,
bounded short cache with no redistribution; sanitized compliance records handled
separately from payloads. No new log/caching policy is approved or implemented.
The documented audit-record obligation is not authorization to retain raw quotes.
NSE package retention remains unrelated and unchanged.

## Next implementation proposal—separate approval required

Build an offline provider-specific full-quote boundary with invented responses,
documented IST binding, 25-target/64-KiB bounds and lexical Decimal decoding.
Do not pass real-provider inputs into either synthetic contract. Bind target
exchange, EQ classification, token/key, currency and price units explicitly;
unverified currency/adjustment policy stays unavailable, not assumed from a symbol.
Keep immutable original facts, separate nullable trade/quote clocks and response-
completed retrieval. Define how unused full-quote fields are safely bounded;
the existing minimal synthetic parser must not silently accept full responses.

Required tests: timezone mapping, missing/null clocks, exact prices, effective
crosswalk mismatch, unverified semantics/permission, payload limits, immutable
provenance, unavailable states and no I/O/activation. No existing connector,
manual controls or UI changes in that proposed offline scope. Connector
remediation and bounded live validation each remain separately gated.

Stop before implementation or live access. No further generic source proposal
is needed; the immediate missing input is owner account/permission confirmation
and approval of the explicitly offline provider-specific build scope above.

## Validation

244 focused offline parser, readiness, current-market, UI/cash/news and NSE
governance tests passed. Privacy and staged diff checks passed. Only this report
changed; historical evidence and application/provider files remain byte-exact.
No API requests, payload downloads, credentials, unrelated database access,
research, fingerprint refresh, retention changes or deletion. No root-suite or
live-test claim; known unrelated fingerprint/R9K failures untouched. F&O remains
deferred/unqualified and its experimental outputs unavailable to UI/research.
