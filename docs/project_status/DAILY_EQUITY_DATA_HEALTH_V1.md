# Offline Daily Equity Data Health contract v1

Implemented 2026-09-19 from baseline `141e1ba` after explicit owner approval.
This milestone adds a pure, aggregate read model for one future consumer,
`dashboard_daily_equity_health`. It is not wired into Streamlit.

## Contract

The contract accepts one or two existing immutable synthetic readiness batches,
for a total of 1–50 records, a synthetic session fixture, caller-injected aware
`as_of`, and an optional caller-injected last-successful-refresh clock. It emits
requested, returned, missing, fixture-valid, unavailable and stale counts; batch
count; bounded session state; separate provider-quote, retrieval-completion and
inventory clock ranges; sanitized aggregate reason counts; and deterministic
bytes/content hashes.

Record identities, symbols, tokens, prices and account details are absent from
the output. No last-success clock is inferred. Unknown clocks remain null. Counts
reconcile explicitly; cross-batch duplicate identities and mismatched as-of clocks
fail closed. Only invented synthetic inputs are accepted.

`SYNTHETIC_VALID` describes a fixture session only. Output is always
`SYNTHETIC_NOT_MARKET_READY`; fetching, real-data exposure and persistence are
always false. Permission remains unverified and market session remains unknown.
The contract performs no HTTP, database/file access, wall-clock calls, provider
imports, UI rendering, output persistence or background work.

## Boundaries

No Kite request, credentials/session inspection, target binding, live-test
implementation/execution, Dashboard wiring, provider activation, quote retention,
research, scheduling, recommendation or trading is authorized. Existing exact-price
live-test prerequisites remain pending and independent. F&O remains deferred,
hidden and unqualified; historical evidence and retention rules are unchanged.

## Next separately scoped milestone

Prepare and implement the sanitized in-memory validation/refresh ledger contract
described in `MILESTONE_CHECKLIST_V2.md`, using synthetic fixtures only. It must
bind contract/code/policy versions, permitted input hashes, aggregate counts and
rejection reasons without identities, prices, credentials or private paths.
Persistence and provider-specific retention remain separately gated.
