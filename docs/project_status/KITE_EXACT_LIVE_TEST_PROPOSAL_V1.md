# Exact-price NIFTY 50 operational test — preparation only

Baseline `f1f97b37e6c7013630032098d82b1ccaa712c02d`; initial worktree clean.
Owner approved preparing execution scope and readiness rules offline, not
implementation, API requests or Dashboard wiring. Scope is frozen in adjacent
`KITE_EXACT_LIVE_TEST_SCOPE_V1.json`. No existing application behavior changes.

## Proposed smallest live test

Use the owner's already authenticated session, today's validated owner-supplied
official constituent CSV and same-day current Kite cash inventory. Freeze exactly
50 sorted NSE EQ keys/tokens into two batches of 25, in isolated session memory.
Before any request, bind CSV hash, inventory retrieval/parser provenance, selected
key/token crosswalk, scope hash and batch order into a local target hash; owner
must confirm that binding in the private interface. No identifiers or actual
prices enter Git. Current target hash is **pending**, not invented from the prior
owner-reported result. CSV source remains owner-declared, not authenticated.

Proposed acquisition: two GETs to the fixed HTTPS api.kite.trade/quote endpoint,
one per batch, no redirects/retries/cache/fallback. Maximum 64 KiB decoded bytes
per response, 128 KiB combined; 20-second connect/read timeout, 60-second total
acquisition deadline and ten-minute owner session. A future implementation must
enforce the total deadline during streaming, not treat Requests' read timeout as
an overall deadline. Identity encoding only; encoded responses stop, not silently
expand limits. No profile/inventory/CSV acquisition belongs to these two requests;
their existing manual controls remain separate. Missing prerequisite inventory
or session requires stopping, not automatic setup requests.

The offline injected-response decoder exists; the bounded live transport and
the operational test UI **do not yet exist**. Those require separate approval
and offline enforcement tests before any owner-triggered request. The legacy
float manual test is not this exact-price test and remains unchanged.

## Proposed readiness rules and permitted conclusions

Exact source Decimal is immutable; two-decimal ROUND_HALF_UP is display only.
Retain separate quote/trade clocks and original strings; documented naive REST
strings use IST under the previously recorded official semantics. Completion
time follows the last response byte. Future/unordered/unknown clocks block;
nullable last-trade time is possible, but this conservative scope does not waive
its current unavailable behavior. Old last-trade time is not proof of stale quote
time or certified trade recency. No clock or price substitution.

At one common as-of after both batches, proposed per-row age ceilings are quote
30 seconds, retrieval 15 seconds, inventory 86,400 seconds plus same IST date.
Equality passes. Quote/retrieval thresholds are conservative application-policy
proposals, not authoritative feed guarantees; inventory's age/day rule reflects
the existing daily-current constraint, not permanent identity validity. A slow
second batch can make the first stale: report that, do not tune thresholds after
viewing results. No calendar exists; session remains UNKNOWN, blocking current
market-ready display. Unverified currency/units, adjustment or permission also
blocks such display. Complete coverage alone cannot override these gates.

Report requested/decoded/missing/unavailable/stale counts per batch, separate
per-row ages in private memory, and sanitized aggregate reasons. Both responses
must complete before combined reporting; structural failure stops without partial
publication. Missing validly encoded rows remain explicit, not structural failure.
Test success means bounded execution and truthful decoding/diagnostics, not that
all rows pass freshness or that provider prices match exchange ground truth.
Never call the two batches simultaneous or qualify a source from their agreement.

## Permission and retention still pending

Existing repository reviews record Kite's private-personal-interface terms and
constraints on public display, permanent content copies/caching, plus compliance
records and agreement precedence. No fresh terms review or publisher permission
was obtained here. Owner must confirm the applicable entitled account/application
conditions permit this isolated private test and transient processing, and that
its proposed no-new-log scope is compatible with compliance-record obligations.
If not reconciled, stop for a separately scoped record-policy amendment.
Do not send credentials, account documents or IDs through chat. Owner confirmation
is a prerequisite declaration, not authoritative currency/adjustment evidence.

Proposed quotes/raw bytes remain transient memory only, with no files, exports,
shared caches or public UI. Parsed results expire after 60 seconds; failure,
disconnect/reconnect or expiry removes application references. This is not secure
RAM erasure. No existing files/packages are deleted. The NSE package deadline
2026-12-31 is unchanged and does not grant Kite quote-retention rights.

## Separate owner decision required

Confirm applicable entitlement, private-test/transient-processing permission and
compliance compatibility; approve the proposed budgets, thresholds and retention.
Then separately approve implementing the bounded transport/manual test and its
owner-triggered execution **only after local target-hash confirmation**. Execution
is not currently authorized, and the proposal is not a fully bound request yet.
Currency/adjustment evidence and a maintained session policy remain prerequisites
for any later Dashboard display, even if this operational test runs successfully.

Proposed approval question (not answered by preparation approval):
“Having reviewed my applicable Kite agreements, I confirm this isolated private
test and memory-only processing comply with my entitlement and record obligations.
I approve implementing and owner-triggering the two-request scope in
KITE_EXACT_LIVE_TEST_SCOPE_V1.json, including its freshness and retention rules,
after confirming the exact local target binding. No Dashboard wiring, public
display, research or trading is authorized.”

No real-source promotion, F&O work, fingerprint refresh, research or deletion.
Dashboard remains synthetic and the original NSE F&O route remains unqualified.

## Validation performed

335 focused offline tests passed: four proposal governance checks plus all 331
existing exact-equity/pipeline/authentication/UI/cash/news/NSE checks. JSON parsing,
scope budgets, pending authorization/bindings, unavailable-state restrictions,
privacy/retention separation and compilation passed. Staged diff checks passed.
Only this report, its scope JSON and new governance tests changed; application,
UI, provider and historical evidence remain unchanged. No network, credentials,
session/database inspection or live execution occurred. Known unrelated root
research-fingerprint/R9K timing failures were not rerun or repaired. No push or
server restart is part of this preparation.
