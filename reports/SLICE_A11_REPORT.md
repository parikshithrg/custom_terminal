# Vertical Slice A.11 — Secure Read-Only Kite Current-Market Data

## Outcome

Baseline commit `8080529` was clean. A separate, ephemeral current-market path
now supports daily user login, protected in-memory session state, explicit
session validation, current instrument discovery, and bounded quote snapshots.
No live credentials were supplied or used and no live provider request was
made during implementation.

## Implementation

- Hardened session representation and sanitized provider errors.
- Added deterministic login cleanup and full disconnect cleanup.
- Added six explicit session lifecycle states and provider-rejection handling.
- Added `CurrentMarketDataProvider`, `CurrentInstrumentSnapshot`, and
  `CurrentQuoteSnapshot` contracts separate from historical provider contracts.
- Added an endpoint/method allowlist with only profile, instruments, LTP, quote,
  and OHLC GET operations. Token exchange remains a separate POST.
- Added typed current-instrument CSV normalization with retrieval provenance and
  the mandatory `CURRENT_TRADABLE_ONLY` scope.
- Added inventory-validated quote requests, a 25-symbol limit, 15-second
  in-memory cache, missing-result representation, and stale-cache labeling.
- Replaced the Data Coverage stub with connection health, manual validation,
  inventory counts, bounded quote lookup, scope warnings, and disconnect.
- No order controls or trading methods exist.

## Storage and scope

API secrets and one-time tokens are removed from application state after every
exchange attempt. Access tokens, clients, inventory, and quote cache are
memory-only. Disconnect or provider rejection removes their application
references; this does not claim secure erasure from Python process memory.

The connector cannot be converted to a historical universe and does not touch
research, historical universe, outcome, acceptance, momentum, or promotion
packages. Earlier trust specifications, golden fixtures, and manifests remain
protected by final hash comparison.

## Verification

- Root: `.\.venv\Scripts\python.exe -m pytest -q` — **80 passed**.
- Legacy: with `PYTHONPATH` set to `Data test`, pytest with
  `--basetemp=.pytest_tmp\a11-data-test-final` — **289 passed**, with existing
  SWIG deprecation warnings only.
- JSON validation — **23 specifications parsed**.
- Python compilation and `git diff --check` — passed.
- Tracked-file sensitive-name scan — only code identifiers, redacted display
  text, endpoint field names, and documentation were found; no credential-like
  literal was found.
- Baseline comparison — protected momentum specifications, golden fixtures,
  historical trust specifications, and earlier manifests are unchanged.

All tests are offline; live validation requires credentials entered by the
user through Streamlit.

## Historical status

This current-data milestone does not alter
`AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`, historical-population capability,
experiment readiness, or Slice B readiness.

## Final current-data decision

`KITE_CURRENT_DATA_READ_ONLY_READY`

## Recommended next milestone

Perform one user-driven, read-only smoke test through the Streamlit page with a
fresh daily Kite login, recording only sanitized health/count results and no
credentials or raw inventory.
