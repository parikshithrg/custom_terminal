# Offline equity quote parser v1

Baseline: `a6e7256`. Initial worktree clean. Owner “i approve” answers the
synthetic offline parser build question. No provider requests or UI wiring.

## Frozen scope before implementation

One Dashboard equity-watchlist parsing boundary, synthetic fixtures only.
Inputs: mode, immutable UTF-8 payload bytes <=65536 bytes, immutable tuple of
1..25 unique synthetic targets, response-completed retrieval time, caller as-of,
and optional explicit synthetic timezone policy. JSON nesting <=8; no arrays.
Targets require the SYNTHETIC:EQUITY_ namespace, not arbitrary synthetic classes.
Envelope exactly `status: success` and `data` object. Response keys must be
selected SYNTHETIC: targets; no unrelated instruments. Minimal fixture record
fields only: instrument_token, last_price, timestamp, last_trade_time.
Token required, integer and exactly crosswalk-matched; last_price required,
positive finite JSON numeric or null. Prices decode directly to Decimal;
never pass through float. Strings/bools/invalid/nonfinite prices are refused.

Timezone policy fields: version, zone, evidence_hash. Allowed fixture zones UTC
or Asia/Kolkata only (fixed-offset, no DST ambiguity). A valid hash is a metadata
claim, not verified authoritative timezone evidence. No policy means naive clocks
stay naive and unavailable. Both provider clocks remain separate; no fallback.
Null, absent, malformed, naive-unresolved, future and unordered clocks have
explicit reason codes. Unknown last-trade time is documented as possible but
conservatively unavailable here; neither existing readiness contract is relaxed.
Retrieval/as-of must be aware and retrieval <= as-of. Parser does not evaluate
freshness ages, permission, currency/adjustment eligibility or market session.

Results retain original Decimal and timestamp strings, parsed clocks,
synthetic target/token, value state and reasons; missing response rows produce
MISSING_ROW rather than disappear. Display price is null for unavailable rows.
Envelope binds schema, fixture version, target/policy/time inputs, payload hash
and parsed records; canonical JSON/hash remain memory-only. Permission always
NOT_VERIFIED, readiness SYNTHETIC_NOT_MARKET_READY, execution flags false.
No response bodies, credentials, real IDs or private paths are tracked.

Malformed UTF-8/JSON, duplicate keys, excessive nesting/size, arrays, unexpected
fields, token/target mismatch and invalid prices fail the whole parsing boundary
with sanitized errors, not partial/fallback results. There are no HTTP or
provider imports, retries, persistence or downstream contract/UI integration.

## Completion and next gate

244 focused tests passed: parser plus all 209 existing current-equity/current-
market/watchlist/UI/cash/news/NSE governance checks. Canonical JSON/hash checks,
compilation, privacy scan and staged diff checks passed. The first run encountered
Windows setup errors from oversized generated fixture labels; bounded explicit
test labels resolved these without changing parser behavior. No full root suite
or live test was run; known unrelated research-fingerprint/R9K failures remain
untouched. Only four new contract/fixture/test/documentation files changed.
Existing UI, providers,
contracts and historical evidence remain unchanged. F&O is deferred/unqualified;
NSE retention stays 2026-12-31. No research, fingerprint refresh or deletion.

Next separately scoped decision: establish provider-specific timezone,
currency/adjustment, display/cache/compliance-log permissions and target bindings,
then approve an offline provider-specific contract and connector remediation
before any live test. This parser does not establish those prerequisites.
