# Offline equity-only Dashboard watchlist contract v1

## Authorization and completion scope

Baseline verified: `f9a10273d77694ae000e4019f87b4174ba0b1a37`; initial worktree
clean. Owner explicitly approved implementation in this task:

> i approve implementing the equity-only, synthetic, offline Dashboard watchlist
> contract described in NEXT_DATA_FOUNDATION_BUILD_PROMPT.md, without UI wiring,
> provider access, or research

The approved committed prompt's SHA-256 is
`3f8419b87b06989c4e3aa075db6f9196c995abb20e198d760165304587c2d6b8`.
This is permission for synthetic contract implementation only, not source
semantics, external access, UI wiring or research authorization. Earlier
proposed/pending records are preserved, not rewritten.

## Frozen fields and API

`market_intel.dashboard_watchlist_read_model_v1` supplies frozen/slotted
`WatchlistRecord`, `WatchlistEnvelope` and `build_watchlist`. Its import uses
only the standard library and the minimal top-level package; it does not import
foundation providers or the UI. Independent fixtures live in
`dashboard_watchlist_fixtures_v1`, not the approved preview module.

Exact envelope fields, unchanged from the approved prompt:
`schema_version`, `consumer_id`, `mode`, `as_of`, `fixture_version`,
`fixture_hash`, `records`, `readiness_state`, `reason_codes`.

Exact record fields:
`instrument_id`, `exchange`, `instrument_class`, `display_symbol`, `currency`,
`last_price`, `source_id`, `source_record_id`, `event_time`, `published_at`,
`retrieved_at`, `provider_timestamp`, `value_state`, `quality_flags`.

Consumer is `dashboard_illustrative_watchlist`; schema is
`dashboard_watchlist_read_model_v1`. Mode is strictly `SYNTHETIC`. Readiness is
always `SYNTHETIC_NOT_MARKET_READY`, with `SYNTHETIC_ONLY` and
`NOT_MARKET_EVIDENCE` reasons, including for empty/fully populated fixtures.
No extra OHLC/change/score/settlement/quantity/indicator/portfolio fields exist.

Call `build_watchlist(mode="SYNTHETIC", as_of=<aware datetime>,
fixture_version=<fixture version>, records=<tuple of WatchlistRecord>)`.
The mode gate executes first, before touching records. Only a tuple of at most
25 exact record objects is accepted; no iterators, provider objects or mappings
are evaluated. Constructors and serialization recheck invariants.

## Guarantees and limitations

- Exchange must be `SIMULATED`, class `DEMO_EQUITY`; identities, source and
  record IDs use bounded `SYNTHETIC:` codes. Display labels begin `DEMO EQUITY`.
  Currency uses a three-letter code. Duplicate instruments or source-record IDs
  within the fixture are rejected. This is not a security/contract crosswalk.
- Prices must already be finite positive `Decimal` objects; floats, integers,
  strings, zero and nonfinite/negative values are rejected, never repaired.
  Null requires `MISSING` plus `MISSING_PRICE`; available price requires
  `AVAILABLE` without that missing flag. Reasons are bounded immutable code
  tuples, not arbitrary text/private paths; quarantine/derivative/historical/
  unclassified input flags are ineligible. Other synthetic quality flags remain
  visible. No provider eligibility is inferred from a price or label.
- All four times require aware `datetime` objects; event <= publication <=
  retrieval <= caller-injected as-of. No wall clock or market calendar is read.
  Provider timestamp must remain null. Fixture dates are invented metadata,
  not observed exchange/publication times or market freshness.
- Records/envelope are frozen and deeply immutable for permitted types; inputs
  remain unchanged. Canonical UTF-8 JSON has sorted keys, compact separators,
  UTC ISO timestamps, exact Decimal **strings** and explicit nulls. No precision
  rounding occurs, including under altered Decimal contexts. Record order is
  significant and is preserved, not silently sorted/deduplicated.
- `fixture_hash` is SHA-256 of the canonical envelope excluding only
  `fixture_hash` itself; it binds schema/consumer/mode/as-of/version/records/
  readiness/reasons, not merely prices. Changing identity, values or synthetic
  times changes the binding. Equivalent timezone representations serialize
  identically. Decimal scale is preserved and therefore binding-significant.
  `to_bytes()` returns memory bytes only; there is no file output or loader.
- The API cannot authenticate the origin of deliberately mislabeled values.
  It enforces explicit synthetic input declarations and refuses non-synthetic
  modes/types; it is not evidence that a real source is valid or permitted.

## Validation and preserved boundaries

Focused contract, UI, cash-scope, temporal and NSE protocol/policy/adapter
governance tests passed: **148 tests**, zero failures/skips, using isolated
synthetic test outputs. Compilation, staged diff checks and scoped private-path/
credential-pattern checks passed. Existing tracked files were unchanged; only
the four new scoped implementation/fixture/test/documentation files were added.
Full root suite and known unrelated stale research-fingerprint/R9K timing
failures were not rerun, changed or refreshed.
Tests cover exact fields, deterministic bytes/hash reconstruction and changes,
Decimal precision, immutability, missingness/flags, identity/size/type refusal,
all non-synthetic modes, time validity/order/cutoff, scope tampering and refusal
to promote. Runtime open/socket guards and an AST import/call allowlist check
the contract/fixtures for network, database/file, wall-clock, UI and provider
execution. Existing UI files, approved columns and sealed evidence are unchanged.

No external requests, provider activation, Streamlit wiring, legacy page execution,
research, backtest, recommendations, fingerprint refresh, evidence reacquisition,
retention amendment or deletion. F&O remains deferred/unqualified; dependent
features remain hidden. Existing 2026-12-31 retention is unchanged.

## Proposed next milestone — not executed

Following `EQUITY_FIRST_PRIORITY_V1.md`, separately authorize **legacy-news
execution/readiness gating and non-F&O consumer requirements**. Proposed scope:
prevent automatic legacy news fetch/sentiment execution without an explicit
approved source/consumer gate; show an unavailable state by default; freeze
publisher attribution, event/identity fields, publication/retrieval timestamps,
freshness, provenance, reuse/retention and missingness requirements using offline
fixtures. Keep hidden risk/report paths hidden and preserve manual Data Coverage
scope. Test zero requests/writes on page load and fail-closed missing approval.
No news source activation, API probing, scoring research or real acquisition is
included. Exact UI-behavior change and requirements need separate owner approval;
none is authorized or implemented by this completion.
