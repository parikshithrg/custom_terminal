# Kite Current-Market Data Scope

## Purpose

This connector uses the user's own Zerodha account and Kite Connect API
application for a narrow, current-market display. It is independent of the
historical research qualification system.

## Allowed network surface

| Operation | Method | Endpoint | Purpose |
|---|---:|---|---|
| Token exchange | POST | `/session/token` | One-time daily authentication only |
| Profile | GET | `/user/profile` | User-requested session validation |
| Instruments | GET | `/instruments` | Current tradable inventory |
| LTP | GET | `/quote/ltp` | Bounded current snapshot |
| Quote | GET | `/quote` | Bounded current snapshot |
| OHLC | GET | `/quote/ohlc` | Bounded current snapshot |

All other endpoint names and every market-data method other than GET are
rejected locally before a request. Order placement, modification and
cancellation; baskets; GTT; order margins; holdings mutation; funds transfer;
publisher buttons; and WebSocket order updates are not implemented.

This describes application behavior, not the full permissions of the user's
Kite access token.

## Credentials and lifecycle

- API key: treated as an application identifier and optionally retained during
  the Streamlit session until disconnect.
- API secret and one-time request token: masked and removed from application
  state after either a successful or failed exchange.
- Access token and authorization header: held only by in-memory session/client
  objects; object representations redact them.
- Disconnect and provider token rejection remove relevant application
  references. Python memory is not claimed to be securely erased.
- Nothing is intentionally persisted to files, databases, caches, artifacts,
  manifests, browser query parameters, or Git.
- Validation is user-triggered. There is no login automation or keepalive poll.
- Provider rejection is authoritative; no expiry is inferred solely from the
  local clock and no one-time token is retried.

States are `UNAUTHENTICATED`, `AUTHENTICATING`, `AUTHENTICATED`, `EXPIRED`,
`INVALID`, and `DISCONNECTED`.

## Current inventory and quotes

The CSV inventory is normalized into `CurrentInstrumentSnapshot` with provider
tokens, symbol, exchange, segment, instrument type, expiry, strike, tick size,
lot size, retrieval timestamp, session date, endpoint, parser version, and
scope `CURRENT_TRADABLE_ONLY`. It is retained only in the current application
session.

Quote requests accept at most 25 keys, all validated against that inventory.
Results identify provider, retrieval time, missing values, and cache state.
The in-memory cache lifetime is 15 seconds; a cached value served after a
network failure is explicitly `STALE_CACHE`. Snapshots are not called streaming
or real-time. Entitlements and provider availability may restrict coverage.

## Research prohibition

Kite current instruments are not a historical universe and cannot validate
historical cross-sectional research. Inactive and delisted securities may be
absent. The current inventory cannot enter historical security-master tables,
universe construction, outcomes, momentum specifications, acceptance gates, or
experiment promotion. `CurrentInstrumentSnapshot.as_historical_universe()`
fails explicitly.

The NSE official-response gate remains
`AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`. A.8–A.10 trust verdicts are unchanged.
