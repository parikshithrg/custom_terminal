# Offline equity validation pipeline v1

Baseline: `e012d71474387df132cae04ddce21b4344cbed59`; initial worktree clean.
Owner requested the next bounded equity validation milestone. Scope is composition
of existing synthetic parser/readiness components only: no live access, connector
remediation or Dashboard wiring. Owner reported two manual batches returning
25 quotes each with zero missing; this is owner-reported operational evidence,
not independent precision, freshness or licensing qualification.

## Frozen boundary

`offline_equity_validation_v1.validate` accepts synthetic mode, version, immutable
JSON bytes, 1..25 immutable explicit target/metadata pairs, aware response-completed
retrieval/as-of, explicit fixture freshness policy and optional fixture timezone
policy. Existing parser limits remain 64 KiB, eight levels, no arrays, strict
selected identities and token matching. No transport, wall clock or persistence.

Each pair binds one numeric synthetic parser token to one synthetic metadata
token, by explicit association, not inferred symbol similarity. Keys must match;
tokens and identities must be unique. Metadata is SIMULATED/EQ/INR only, with empty
price/provider clocks/retrieval and INPUT_NOT_PARSED missing reason. Its explicit
inventory timestamp, cache state and invented provenance remain subject to the
unchanged readiness checks. These bindings are fixture declarations, not a
verified real security master or currency/adjustment evidence.

The parser preserves exact Decimal lexical values and original clock strings.
The pipeline builds separate immutable readiness records, retaining quote and
trade clocks individually and injecting the supplied completion timestamp.
Missing rows never disappear or become zero. Parser reasons are merged with
readiness reasons; either component's blocking finding makes display price null.
Original parser facts and caller metadata remain unchanged. No age defaults or
relaxed missing-trade policy are introduced. Fixture limits are not live policy.

Deterministic JSON includes both component envelopes and hashes, original facts,
policy-bound input hash and combined diagnostics. Output hash covers those bytes.
Permission remains unverified/metadata-only, market session UNKNOWN and readiness
SYNTHETIC_NOT_MARKET_READY. Fetch/display activation flags remain false. Results
are returned in memory only; UI and provider code are unchanged.

## Next separately scoped milestone

Before real quotes can feed Dashboard: approve a consumer-specific provider
contract and connector remediation, binding authoritative identity, INR and
adjustment semantics, distinct quote/trade clocks, lexical Decimal parsing and
response-completion retrieval, applicable personal display/cache permission,
explicit quote/retrieval/inventory freshness and session/unavailable behavior.
Supply missing evidence or separately approve its bounded review; this task
does not authorize browsing. A subsequent manual live test needs exact targets,
request budgets and retention permission. No float-to-Decimal conversion can
recover already lost source precision. No activation follows from 50/50 coverage.

F&O remains deferred/unqualified; experimental outputs cannot feed UI or research.
Sealed historical evidence, existing acceptance decisions and the 2026-12-31 NSE
retention deadline remain unchanged. No research, fingerprint refresh or deletion.

## Validation

290 focused tests passed: 17 pipeline cases plus the existing 273 parser/readiness,
watchlist/UI/cash, login/current-provider and news/NSE governance cases. Coverage
includes precise deterministic output, immutable metadata, mode refusal before
evaluation, incompatible/prepopulated bindings, missing rows/prices, parser reason
preservation, separate clocks, stale ages, bounded/duplicate bindings and no-I/O
dependencies. Compilation, scoped private-path/credential scan and staged diff
checks passed. Only these three new pipeline/test/documentation files changed;
existing UI, provider and historical evidence remain byte-exact. No live requests,
full root-suite or real-source qualification are claimed. Known unrelated stale
research-fingerprint/R9K timing failures were not rerun or repaired.
