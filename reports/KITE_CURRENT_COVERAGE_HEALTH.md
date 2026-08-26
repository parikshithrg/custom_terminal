# Kite Ephemeral Current-Market Coverage Health

## Contract

`CurrentMarketHealth` is a typed, current-only operational summary containing:

- provider, session state and validation state;
- inventory and quote retrieval timestamps and local ages;
- freshness and provider-time availability;
- market-session label, calendar version and timezone;
- requested, returned and missing quote counts;
- inventory counts by exchange, segment and instrument type;
- incomplete rows, expired derivatives and duplicate keys;
- entitlement classification, stale-cache state and last sanitized error;
- immutable scope `CURRENT_TRADABLE_ONLY`.

Calling its historical-capability conversion fails explicitly.

## Inventory diagnostics

The current inventory is summarized in memory into total, equity, index,
futures and options counts plus exchange/segment/type maps. Row-level missing
or invalid identifiers are retained with quality flags and counted. The health
surface also counts expired derivative contracts and excess duplicate provider
keys or exchange-symbol pairs. It never persists or exports raw rows or
provider tokens.

## Quote and entitlement semantics

Local selection failures, provider no-value results, explicit Kite permission
errors, invalid sessions, temporary provider failures and unknown sanitized
errors remain distinct. A missing quote alone is
`PROVIDER_NO_VALUE_UNCERTAIN`; it is never labeled an entitlement failure
without an explicit provider `PermissionException`.

## Freshness

- `FRESH_NETWORK`: retrieved from the network and at least one provider
  timestamp is available.
- `FRESH_CACHE`: served within the declared 15-second in-memory cache lifetime.
- `STALE_CACHE`: an older cached result was used after a sanitized provider
  failure.
- `NO_DATA`: no quote snapshot exists.
- `UNKNOWN_PROVIDER_TIME`: freshly retrieved locally but provider timestamps
  are absent.

Snapshot age always uses local retrieval time. When valid provider timestamps
exist, their independently calculated age is also shown; a naive Kite timestamp
is interpreted in the explicitly declared Asia/Kolkata timezone. Provider-time
absence or malformed values are shown explicitly. No classification claims
streaming or exchange real-time delivery.

## Market session

The classifier supports `PRE_OPEN`, `OPEN`, `POST_CLOSE`,
`NON_TRADING_DAY` and `UNKNOWN` in Asia/Kolkata. It requires an explicit,
versioned calendar containing both known trading and non-trading dates. The
repository has no adequately maintained current official holiday calendar, so
the application passes no calendar and reports `UNKNOWN` instead of guessing.

## Manual refresh and export

Session validation, inventory and quote refreshes are manual and independently
limited by a five-second cooldown. There is no polling, keepalive, automatic
retry or refresh loop. Provider rejection clears invalid session material.

The user may download an in-memory JSON health summary. It contains only the
typed aggregate contract. It excludes API credentials, tokens, authorization
headers, user/account details, raw instruments, raw quotes and full responses.
No download is created automatically.

## Boundaries

The endpoint allowlist remains unchanged. No order, WebSocket, persistence,
signal, score or recommendation functionality exists. This health surface does
not modify `AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`, historical population
trust, momentum status, experiment readiness or Slice B readiness.
