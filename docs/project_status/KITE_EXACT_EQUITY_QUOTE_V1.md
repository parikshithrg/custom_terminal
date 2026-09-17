# Kite exact equity quote boundary v1

Baseline `ea41aac`; initial worktree clean. Owner approved the Kite quote contract
and connector update, offline testing only, no live requests or Dashboard wiring,
and requested two decimal places. Two decimals are a presentation rule only:
original source Decimal remains exact and immutable. Display uses explicit
ROUND_HALF_UP (1.005 becomes 1.01), including trailing zeros. A positive sub-cent
price may display 0.00 due to rounding; the original is never replaced with zero.

## Frozen implementation scope

The new opt-in `KiteCurrentMarketClient.decode_exact_equity_response` consumes a
caller-supplied response and immutable tuple of 1..25 exact cash-equity keys.
It performs no HTTP call, credential access, login, retry or cache mutation.
The caller owns the injected response, including closure. Current inventory must
be Kite current-only, aware/not future, uniquely match keys and contain unflagged
NSE/BSE EQ entries in matching cash segments, without expiry. Numeric tokens and
keys must be unique and match each response record. This is a current operational
crosswalk, not a permanent/PIT security master. Freshness is not inferred.

Supplied response must be HTTP 200, exact HTTPS api.kite.trade/quote URL and JSON
content type. Stream consumption is bounded to 64 KiB; empty/oversized content,
plain-content length mismatch, malformed JSON/UTF-8, duplicate JSON keys, nesting
above eight, unknown targets, token mismatch or invalid prices fail closed with
sanitized errors. Encoded content length is not compared to decoded bytes.
This validates a supplied final response, not a redirect chain or transport;
future live acquisition needs separately approved transport rules and budgets.

Completion clock is captured only after stream exhaustion. Caller supplies aware
as-of; inventory <= completion <= as-of is mandatory. No request-start timestamp
is substituted. The parser decodes numeric price lexemes directly to Decimal,
rejecting float/string/bool, nonfinite/nonpositive values, more than 64 digits or
absolute exponent above 64. It retains original quote/trade strings separately.
Missing rows/prices or malformed/missing/future/unordered clocks remain explicit
UNAVAILABLE, with null display price. Unknown trade time is not filled from quote
time. Existing conservative trade-clock behavior is unchanged.

Naive REST timestamps use IST under the already recorded official Kite response
semantics, not local workstation timezone. Aware timestamps retain their offsets.
The official documentation reference previously reviewed is
[Kite response structure](https://kite.trade/docs/connect/v3/response-structure/).
No fresh documentation access occurred in this milestone. Provider quote time
is not asserted to be event/publication time or evidence of an active session.

Full quote JSON may include provider extras such as OHLC/depth; these are bounded
but not retained, interpreted or exposed by this contract. Only identity/token,
last price and the two clocks enter records. This does not authorize new fields.
Deterministic memory-only JSON/hash binds payload hash, exact source values,
original clocks, target tokens, completion/as-of and diagnostic outcomes.
No response body, real inventory, credentials or private paths are tracked.

Results are PARSED_NOT_MARKET_READY; permission, currency and adjustment remain
NOT_VERIFIED, freshness NOT_EVALUATED, fetch/exposure flags false. Parsed display
strings are candidates, not permission to expose real data. The existing float
manual quote path remains unchanged and is not silently promoted or rerouted.
Synthetic Dashboard contracts/UI and sealed NSE evidence remain unchanged.
F&O stays deferred/unqualified; retention remains 2026-12-31.

## Next decision, not executed

Approve a separate live transport integration/manual test with exact cash targets,
endpoint and transaction/byte/redirect/time budgets, raw-response retention scope,
personal display/cache permission evidence, INR/adjustment basis and explicit
quote/retrieval/inventory freshness and session handling. Existing login or 50/50
manual coverage does not supply these prerequisites. Only then can a separately
scoped Dashboard integration be considered. No provider activation, UI wiring,
research, backtests, recommendations, fingerprint refresh or deletion occurred.

## Validation performed

331 focused offline tests passed: 41 new exact-equity cases plus 290 existing
pipeline/parser/readiness, authentication/current-market, synthetic UI/cash and
news/NSE governance checks. Tests cover exact values, two-decimal half-up display,
immutability/deterministic hashes, separate IST clocks, completion after bytes,
no HTTP/files/cache mutation, caller response ownership, malformed/unsafe payloads,
identity/token/derivative refusal, truncation, missingness, budgets and activation
refusal. Compilation, scoped credential/private-path scan and staged diff checks
passed. The initial run had two Windows test-setup failures from oversized fixture
labels; explicit short labels fixed these without changing acceptance behavior.
No live/root-suite result is claimed. Known unrelated fingerprint/R9K timing
failures were not rerun or changed. Local server was not restarted.
