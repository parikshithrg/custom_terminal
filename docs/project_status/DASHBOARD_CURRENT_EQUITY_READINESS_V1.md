# Offline current-equity readiness contract v1

Baseline: `7419e6e` (cash-source feasibility decision); initial worktree clean.
Owner approval: “i approve building the offline equity-readiness contract using
synthetic fixtures only, without provider access or UI changes”. This approves
the new contract, fixture, tests and documentation—not a real source or consumer.

## Frozen API and semantics

`dashboard_current_equity_readiness_v1.evaluate` is pure: keyword-only `mode`,
`fixture_version`, caller-aware `as_of`, `policy`, immutable tuple `records`.
Mode must be SYNTHETIC before records are evaluated. At most 25 exact
`EquityFixtureRecord` instances; no generators, provider objects or source imports.

`EquityPolicy` fields, in order: version, identity_version, semantics_version,
max_quote_age_seconds, max_retrieval_age_seconds, max_inventory_age_seconds,
permission_metadata_hash. All versions and explicit integer age limits required;
0..86400 seconds bounds prevent unbounded fixture policies. These are structural
limits, not approved market-freshness thresholds. No policy defaults are selected.
The fixture's 30/15/300-second values are invented test values only.

Fixture record fields, in order: instrument_key, provider_token, exchange,
instrument_class, display_symbol, currency, last_price, missing_reason,
provider_quote_time, last_trade_time, retrieval_completed_at, inventory_as_of,
cache_state, source_state, event_time, published_at, provider, source_endpoint,
parser_version. All provider/key/token/endpoint identifiers use SYNTHETIC:
namespaces; labels use DEMO EQUITY. Eligible fixtures use SIMULATED/EQ/INR.
Non-equity/unknown classes or incompatible currency remain unavailable.
Provider and parser provenance are invented, not assertions about Kite.

Prices accept exact Decimal or null, never float/int/string/bool. Nonfinite,
zero/negative, missing or inconsistent prices are unavailable without repair.
Null has MISSING_PRICE and an explicit supplied reason, or
MISSING_REASON_UNSPECIFIED. Missing row, access failure and transport failure
retain different reasons, even if a record also lacks price.

Quote time and last-trade time remain separate. No time substitution: unknown,
naive and future clocks block fixture availability. Quote <= retrieval <= as-of;
inventory <= retrieval, trade <= quote. A trade can legitimately precede a recent
quote by more than the quote-age limit; the contract does not certify trade
recency. Quote/retrieval/inventory ages are assessed independently per record,
with equality at the explicitly injected boundary permitted. FRESH_CACHE never
overrides age failures; STALE_CACHE/UNKNOWN cache always blocks. No maintained
calendar is inferred: market_session remains UNKNOWN. Event/publication remain
null and cannot be supplied as if field semantics were established.

Duplicate keys or tokens block every implicated record. Original frozen fixture
objects remain intact in each result; `display_price` is null for unavailable
records. This separation prevents loss of failed evidence or price substitution.

`RecordReadiness` fields: instrument_key, fixture, value_state, display_price,
reason_codes. Value state is FIXTURE_VALID_ONLY or UNAVAILABLE.
`EquityReadiness` fields: schema_version, consumer_id, fixture_version, as_of,
input_hash, records, permission_state, readiness_state, market_session,
can_fetch, can_expose_real_data. Consumer is dashboard_illustrative_watchlist;
readiness always SYNTHETIC_NOT_MARKET_READY; both execution flags always false.

Input SHA-256 binds schema/mode/version/as-of/policy and complete original fixture
records, including failed observations. Canonical compact sorted UTF-8 JSON
preserves Decimal strings and UTC-aware times; naive invalid input times remain
naive in original evidence. `to_bytes()` returns memory-only result JSON;
`content_hash` binds those bytes. No disk/cache/database output exists.

Permission state is NO_PERMISSION_EVIDENCE or METADATA_ONLY_NOT_VERIFIED.
A syntactically valid SHA-256 claim is never authenticated rights, even when
all fixture quality checks pass. The contract has no activation path.

## Validation and preservation

209 focused tests passed: new contract checks plus all 153 prior cash-source,
watchlist integration/contract, UI/cash, news and alternative/quarantine checks.
Tests cover precise decimals, deterministic bindings, immutability, duplicates,
scope/size limits, price/missingness failures, separate clocks, per-row ages,
cache states, explicit policy requirements, permission non-authorization,
mode/provenance refusal and no network/file access or UI imports.
Compilation, privacy and diff checks passed. Only four new scoped files changed.
Existing UI, provider, synthetic watchlist v1 and sealed evidence are byte-exact.
No full root suite or live test; known stale research-fingerprint/R9K timing
failures were not rerun or repaired. No external access, ingestion, research,
fingerprint refresh, credential access, evidence access or deletion occurred.
F&O remains deferred/unqualified and hidden dependencies remain hidden;
retention remains 2026-12-31.

## Next separately authorized decision

For real cash-equity use, supply or authorize a bounded review of applicable
provider/exchange display/caching rights and authoritative quote/trade timestamp,
currency and price semantics. Existing manual Data Coverage permission does not
extend to Dashboard. Before remediation or activation, separately approve exact
targets, freshness/calendar policy, lexical Decimal/response-completion parsing,
request budgets, retention controls and operational tests. No current connector
snapshot is promoted or made exact by this offline contract. UI remains synthetic.
