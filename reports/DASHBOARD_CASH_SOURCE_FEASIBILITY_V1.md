# Dashboard cash-equity source feasibility v1

Recorded 2026-09-17 against `c1e6d7b7d07b86094a88bedcac55af4a3f83a9da`.
Initial worktree clean. Owner “go ahead with next step” authorizes the previously
proposed offline source feasibility/permission decision, not provider activation.
Repository documentation and code only; no source request or market-file access.

## Recommendation

Use the existing Kite current-market implementation as the **candidate** for one
future consumer, Dashboard's equity watchlist. It is not yet consumer-eligible.
Build a separate offline current-equity readiness contract before changing the
connector or UI. Keep the synthetic v1 contract unchanged; real identities cannot
be relabeled synthetic to pass its gate. No source is activated by this report.

| Route | Existing evidence | Decision for this consumer |
|---|---|---|
| Kite current snapshots | `KITE_LIVE_SMOKE_TEST.md` records 2026-08-26 user-triggered quote success: 3 requested, 3 returned, 0 missing; inventory counts not recorded. Current client, manual controls and fake-HTTP tests exist. | Best implementation candidate, not verified today or licensed for this new consumer by that test. Current selected instruments only; no history claim. |
| Existing local audited historical files | `DATASET_TRUST_REPORT.md` records survivor selection, unresolved identity, permissions and timing. No files reopened here. | Not eligible; historical files are neither today's quote service nor qualified research data. |
| Yahoo/other alternatives | Legacy code/proposal references do not bind this consumer's identity, field semantics, availability, lineage or reuse rights. | Unverified, not selected. No new proposal or external capability claim. |
| NSE F&O / quarantine | Previously sealed blocking diagnostics remain; alternative corroboration deferred. | Excluded, last priority. Cannot feed Dashboard or research. |

## What the existing implementation guarantees—and does not

- `foundation/kite_current_market.py`: GET endpoint allowlist, at most 25
  inventory-matched keys, 20-second timeout and 15-second in-memory quote cache.
  Invalid sessions and explicit entitlement failures do not fall back to stale
  quotes. Temporary request failures can return explicitly stale cache.
- `foundation/current_market.py`: provider key is exchange plus current symbol,
  accompanied by provider token. It is not a permanent security or historical
  identity; current snapshots refuse historical-universe conversion.
- Inventory quality flags and duplicate counts are diagnostic, not fail-closed
  rejection. `views/_cash_scope.py` filters EQ/INDICES on NSE/BSE for existing
  Data Coverage; a watchlist must additionally require EQ only, unambiguous
  identity and valid metadata. Filtering alone is not source qualification.
- Quote parsing uses float, including `float(last_price)`. Converting that float
  to Decimal later cannot recover original lexical precision. Missing price can
  coexist with AVAILABLE status; finite/positive prices are not comprehensively
  enforced. Existing snapshots are therefore insufficient for exact-price v2.
- `/quote` keeps `timestamp` or `last_trade_time` in one string; those clocks may
  have different meanings. LTP mode does not guarantee a provider timestamp.
  Retrieval time is captured before the request; it is not response completion
  time, exchange event time or publication time. None should be invented.
- `current_market_health.py` uses the latest parseable timestamp across quotes;
  it can hide older/unknown records. It assumes IST for naive provider strings
  and clamps negative ages to zero. FRESH_CACHE uses cache age, not per-record
  event freshness. These existing operational labels cannot certify Dashboard.
- Data Coverage passes no maintained calendar: session remains UNKNOWN.
  Entitlement CLEAR means no classified error, not licensing permission.
  The August smoke test is historical operational evidence, not a current test.

## Exact consumer target and outstanding prerequisites

One current cash-equity watchlist, at most 25 explicitly selected keys; no
indices, derivatives, historical series or reference-close/change calculation.
Target fields: provider, endpoint/parser version, current provider token/key,
exchange, instrument class, display symbol, declared currency, exact Decimal
last price or null/reason, provider quote time and last-trade time separately,
response-completed retrieval time, caller-aware as-of, content binding,
cache state, value state, readiness and reason codes. Publication/event times
remain unknown unless authoritative field definitions establish them. Do not
claim a provider quote timestamp is exchange event time.

Before real use, bind applicable provider/exchange permission evidence for this
specific local display, entitlement, credential lifecycle, and permitted
in-memory caching/retention. Prior Data Coverage authorization is not transferred;
personal use and owner approval are not themselves publisher permission evidence.
No current permission conclusion is made offline. No secret belongs in chat/git.

Bind provider field definitions, timezone, currency/units and adjustment basis;
freeze maximum provider/retrieval ages and inventory validity policy before
observing live results. A TTL is not that policy. Unknown, malformed, naive
without documented timezone, future, stale or incompatible clocks fail closed.
Missing rows/prices, ambiguous identities, explicit access failure and transport
failure stay distinct. No zero fill, old-price fallback or silent repair.
Unknown market session stays UNKNOWN; do not claim market-open or streaming data.
Only an explicitly approved unknown-session display policy could permit display
without a maintained calendar, separately from freshness and permission checks.

## Next-build scope for separate approval

Implement a pure `dashboard_current_equity_readiness_v1` contract with invented
provider-shaped in-memory fixtures only. No connector imports, HTTP, credentials,
file/database access, UI wiring or persistence. Accept explicit caller as-of and
versioned freshness/identity/semantic policies; reject missing policies rather
than choose production thresholds. Bound 25 records, immutable inputs, exact
Decimals and deterministic content hashing. Return per-record unavailable
states for failed prerequisites. Fixture provenance must remain conspicuously
synthetic; readiness can never authorize a real source or activate execution.

Tests: duplicates/non-EQ identities, nonfinite/zero/negative/null prices,
float rejection, independent quote/trade clocks, unknown/naive/future times,
stale cache and per-record ages, missing/invalid policies, permission metadata
versus verified rights, immutable deterministic serialization, and no I/O or
promotion. No amendments to the existing provider, synthetic v1, UI or history.
Completion: all focused tests pass, existing 118 integration/governance checks
stay passing, only new contract/fixture/test/documentation files change.

Owner decision: approve that offline build scope, or defer. Real activation is a
later decision requiring actual permission/semantics evidence, exact target and
request/retention budgets, connector precision/time remediation, and bounded
operational validation. Do not ask for credentials or execute that later scope.

## Validation and unchanged boundaries

153 existing current-market, Kite, health, watchlist, UI/cash, news and NSE
governance tests passed offline with fake HTTP.
No full root suite or live smoke test; known unrelated stale research-fingerprint
and R9K timing failures remain untouched. Diff and private-path/secret checks
cover this report. Application and sealed evidence are unchanged; F&O remains
`MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`, alternative corroboration stays
deferred, and retention remains 2026-12-31. No activation, research or deletion.
