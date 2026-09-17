# Kite Dashboard documentation review v1

Recorded 2026-09-17 at `758b84fc6938c08802fd851a4fd8e9332b221cc0`;
initial worktree clean. Owner “go ahead” followed the proposed provider-permission
and field-definition review. Public documentation only, through web search/open;
no authenticated requests, report payloads, market data or credentials.
Only paraphrases/links are tracked, not document copies. This is not legal advice
or acceptance of terms. Pages reviewed live; no revision/effective date verified.

## Official permission evidence

Zerodha's Terms §2 expressly contemplate an exclusively private personal interface.
§2(a) prohibits public live-data display and live-data use in mock-trading apps.
§4(b) restricts permanent API-content copies and redistribution-oriented caching.
§5 calls for compliance records for at least five years; §9 addresses ending use
and permitted cached content. §13 ranks individual agreements and specific
policies above general terms. These are conditional rights, not blanket personal
use permission. [Official Terms](https://kite.trade/terms/)

Project assessment: a single-owner local read-only display appears consistent
with the stated personal-interface purpose, subject to applicable account/API
agreements, entitlement and jurisdiction. This is an inference, not publisher
approval of this implementation. Public deployment with live values is excluded.
Existing synthetic fixtures are not live market data; never connect live data to
paper/mock trading. No trading functionality is proposed.

No automatic requirement to contact NSE is established by this review. Owner
must verify applicable account/product conditions and approve the exact new
consumer. Additional clarification is needed only if those conditions or the
proposed caching/logging policy cannot be reconciled. Compliance records are
not raw price retention; their proposed sanitized scope needs separate review.
The NSE package deadline is unchanged and cannot authorize Kite retention.

## Official field evidence

The v3 market-quotes page defines `timestamp` as exchange quote-packet time,
`last_trade_time` as last-trade time (nullable), and `last_price` as last traded
price. Full `/quote` exposes both clocks; missing instrument keys must be checked.
LTP/OHLC response attributes do not supply those clocks. Instrument-dump price
is not current; the dump is daily. Exchange plus symbol identifies quote requests;
tokens may be reused. Full-quote `ohlc.close` is previous trading-day close, not
today's close. [Official market-quotes documentation](https://kite.trade/docs/connect/v3/market-quotes/)

Project policy: use only the full-quote field definitions for a future watchlist;
no OHLC/change calculation is authorized. Keep last-trade and quote time distinct;
do not fill an absent quote time with trade/retrieval time. Null trade time is a
documented possible state, not proof of bad data; the offline v1 conservative
fixture gate remains unchanged and must not silently be loosened for a provider.

Unresolved here: an explicit timezone binding for naive REST timestamps, currency
and adjustment conventions for the exact cash-equity targets, account-specific
entitlement/conditions, and permitted cache/compliance-log policy. Documentation
does not verify today's operational coverage. These gaps keep real activation
pending, not the original NSE F&O source qualified.

## Separately proposed implementation, not executed

Smallest useful build: a pure offline full-quote parsing boundary using invented
JSON fixtures, with no provider calls or UI wiring. Decode numeric JSON tokens
directly to Decimal (including integer price tokens), preserving only transmitted
precision—not claiming exchange accuracy. Reject nonfinite/invalid prices,
duplicate JSON keys, identity mismatch and unexpected shapes; preserve missing
keys/null clocks as explicit unavailable states. Inject documented timezone policy
or leave naive clocks unresolved; inject response-completed retrieval and as-of.
Retain separate quote/trade clocks, original facts and sanitized provenance.

Freeze consumer fields, synthetic target namespace, payload/record limits and
failure states before implementation. Test parsing precision, response-completion
ordering, ambiguous/unknown clocks, malformed/oversized inputs, no I/O and no
activation. Do not change the existing connector or either contract to absorb
real data. A later provider-specific contract/policy and owner execution approval
are required before requests or Dashboard wiring.

Owner decision required: approve that synthetic offline parser build, or defer.
Real display also requires owner review of applicable Terms/account conditions
and a bounded credential, target, cache/log, request and retention scope. Do not
send credentials through chat or store them in Git.

## Validation and preservation

209 focused offline contract/current-market/UI/news/NSE governance tests passed.
Documentation-only change; staged diff and private-path/secret checks passed.
Existing UI, provider and historical evidence are unchanged. No root suite/live
test; known unrelated research-fingerprint/R9K failures remain untouched.
F&O stays last/unqualified; alternative corroboration deferred; approved NSE
retention stays 2026-12-31. No terms accepted, activation, research or deletion.
