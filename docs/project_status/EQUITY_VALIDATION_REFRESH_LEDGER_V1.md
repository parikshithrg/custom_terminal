# Offline equity validation/refresh ledger v1

Implemented 2026-09-19 from baseline `141e1ba` after the owner directed work to
continue to the next recorded milestone. This is a pure, in-memory contract for
the future `dashboard_daily_equity_health` consumer. It is not wired into the UI.

## Contract

The ledger binds the exact health-contract version, code version, configuration
version, policy version, source input/content hashes and an immutable allowlist of
permitted input hashes. It carries aggregate requested, returned, missing,
unavailable and stale counts. A contract mismatch or unpermitted hash is recorded
with deterministic sanitized rejection codes.

Every record is explicitly `SYNTHETIC_FIXTURE` and
`NOT_EXTERNALLY_VERIFIED`. Owner-reported, manually supplied, provider, historical,
quarantined, derivative and claimed verified modes fail closed. Numerical or hash
agreement cannot promote evidence classification.

The caller supplies the timezone-aware ledger time. Serialization and content
hashing are deterministic. Instrument identities, symbols, tokens, prices,
credentials, raw quotes, inventories and private paths are absent.

## Boundaries

The ledger grants no refresh, persistence, provider access, source activation,
real-data display, research or production authority. It performs no HTTP, file or
database access, wall-clock call, provider import, UI rendering, output write or
background work. Aggregate/hash persistence still requires a separate
provider-specific record and retention policy.

F&O remains deferred, hidden and unqualified. Existing exact-price live-test
approval and target-binding prerequisites remain independent and pending.

## Next separately scoped milestone

Add read-only equity quality diagnostics and stronger synthetic anomaly fixtures,
extending the existing readiness and health contracts. Preserve original facts;
do not interpolate prices, substitute zero, silently remove duplicates, infer
sessions/holidays or select providers by observed volume.
