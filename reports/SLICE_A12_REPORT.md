# Vertical Slice A.12 — Ephemeral Current-Market Coverage Health

## Outcome

Baseline commit `dc7d708` was clean. The working Kite connector now exposes a
typed, sanitized and entirely in-session operational health surface. No live
Kite session was run for this milestone.

## Added

- Separate `CurrentMarketHealth`, inventory-diagnostic, freshness,
  entitlement, declared-calendar and cooldown contracts.
- Aggregate current inventory counts and integrity diagnostics.
- Explicit retrieval/provider-time freshness classifications.
- Honest `UNKNOWN` market-session state when no maintained calendar exists.
- Manual five-second cooldown for session, inventory and quote requests.
- Missing-versus-explicit-entitlement distinction.
- Compact Coverage Health UI and optional sanitized in-memory JSON download.
- Row-level inventory quality flags without persistence or historical joins.

## Preserved

- The exact read-only endpoint allowlist.
- Fifteen-second quote cache and bounded 25-instrument request limit.
- Memory-only credentials, inventory and quotes.
- No orders, WebSockets, automatic refresh, persistence, scores, signals or
  recommendations.
- All historical trust and research boundaries.

## Verification

- Focused current-market suite:
  `.\.venv\Scripts\python.exe -m pytest tests/test_current_market_health.py tests/test_kite_current_market.py tests/test_kite_connect.py -q`
  — **35 passed**.
- Root suite: `.\.venv\Scripts\python.exe -m pytest -q` — **96 passed**.
- Separate legacy suite, with `PYTHONPATH` set to the absolute `Data test`
  directory and a separate temporary test path — **289 passed**; only its
  existing SWIG deprecation warnings remain.
- JSON validation — **23 specifications valid, 0 invalid**.
- Python compilation — **passed** for `src`, `views` and `tests`.
- Git diff whitespace/error check — **passed** (Git emitted only expected
  Windows line-ending notices).
- Credential-pattern scan across source, UI, reports, specifications, tests
  and README — **0 matches**.
- Protected momentum specifications, fixtures, experiment manifests,
  historical trust specifications, and research/simulation packages compared
  with `dc7d708` — **unchanged**.

No credentials or live provider requests were used during verification. No
raw current instrument or quote data was persisted or committed.

## Historical state

`AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE` remains unchanged. Current health
cannot promote historical capabilities, momentum, experiments or Slice B.

## Decision

`KITE_CURRENT_COVERAGE_HEALTH_READY`

## Recommended next milestone

Qualify and version an official current NSE trading calendar before enabling
non-`UNKNOWN` live session labels; keep that work independent of signals and
historical-universe research.
