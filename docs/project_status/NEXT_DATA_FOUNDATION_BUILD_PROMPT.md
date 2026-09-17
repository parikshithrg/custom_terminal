# Prioritized next-build prompt — offline watchlist contract

PROPOSED ONLY. This audit is not implementation authorization. Owner must
explicitly approve the scope below before build work. Real-source activation,
consumer wiring and subsequent research each remain separately gated.

## Ready-to-use implementation prompt

Continue from the committed data-readiness audit and preserve the approved UI.
Implement `dashboard_watchlist_read_model_v1`, a pure, read-only Python contract
for **one consumer: Dashboard's illustrative watchlist table**. Use only bounded
synthetic in-memory fixtures. Do not wire it into Streamlit in this milestone.

Read `reports/DATA_FOUNDATION_READINESS_AUDIT.md`, existing current snapshot/PIT
contracts and relevant tests. Verify the current baseline and preserve unrelated
changes. Reuse concepts, not real provider sessions or local market data.

Freeze these exact fields before implementation:

- Envelope: `schema_version`, `consumer_id`, `mode`, `as_of`, `fixture_version`,
  `fixture_hash`, `records`, `readiness_state`, `reason_codes`.
- Record: `instrument_id`, `exchange`, `instrument_class`, `display_symbol`,
  `currency`, `last_price`, `source_id`, `source_record_id`, `event_time`,
  `published_at`, `retrieved_at`, `provider_timestamp`, `value_state`,
  `quality_flags`.
- `last_price` is a finite positive Decimal or null with explicit missing reason;
  never coerce absent values to zero. No OHLC, change %, scores, settlement,
  quantity, positions or indicators in this v1. Those need separate semantics
  and requirements approval. Do not alter existing UI fixtures/columns.

Identity: synthetic namespace mandatory (`SYNTHETIC:`); exchange is explicitly
`SIMULATED`, class is `DEMO_EQUITY` or `DEMO_FUTURE`, labels are not real
contracts. Uniqueness is scoped to fixture version and synthetic instrument;
reject duplicates. Do not reuse provider tokens as permanent identity. Retain
the future requirement for effective-dated listing/contract crosswalks without
inventing one or accepting real records in v1.

Time: caller injects timezone-aware `as_of`; no wall-clock calls. Fixture event,
publication and retrieval times are declared **synthetic metadata**, ordered
event <= publication <= retrieval <= as_of; reject naive/future/invalid times.
`provider_timestamp` must be null in synthetic mode; never manufacture exchange
time. No market-session inference or current-calendar claim.

Provenance/freshness: fixture source/version, stable record identifiers and
deterministic content hash; changing identity/value/time changes the binding.
No credentials, response bodies or private paths. Readiness is always
`SYNTHETIC_NOT_MARKET_READY`, even for complete values. Preserve explicit
unavailable/quality reasons. Synthetic age is not real-source freshness. No
real-data age threshold, holiday calendar, entitlement or licence is inferred.

Source gates: v1 accepts synthetic mode only. Reject real/current-provider,
historical NSE, quarantined and unclassified inputs before evaluation. Future
real-source mode needs separately approved consumer scope/fields, authoritative
identity/field basis, reuse/retention permission, session/entitlement validation,
publication/provider time policy, freshness/calendar policy, provenance and
quality eligibility. Owner approval alone is not authoritative semantics.

Tests/completion: deterministic bytes/hash with injected clock, Decimal exactness,
immutable inputs, duplicate and malformed identities, missing/nonfinite/invalid
prices, naive/future/unordered timestamps, explicit missingness, synthetic status
never promoting, and refusal of every non-synthetic input. At most 25 fixture
records; reject larger inputs. Prove no HTTP, file/database access, provider
imports, Streamlit rendering, source qualification, research, fingerprint refresh
or persistent outputs. Only new contract/fixture/test/docs files may change;
approved UI files and sealed evidence must remain byte-exact. Run focused
contract/UI/governance tests and document checks actually performed; do not
repair unrelated failures. Commit validated scoped changes; do not push unless
explicitly requested.

Stop with the tested offline contract and a separately proposed next decision.
Do not connect a provider, run backtests, compute recommendations, execute legacy
news/risk/report consumers, reacquire evidence, amend retention or delete data.
