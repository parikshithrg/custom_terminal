# A.11.1 — Kite Read-Only Live Smoke Test

## Test identity

- Test date: 2026-08-26
- Timezone: Asia/Calcutta
- Baseline commit: `129e4f8`
- Application version: `0.1.0`
- Connector scope: `CURRENT_TRADABLE_ONLY`
- Execution: user entered all credentials through masked Streamlit fields;
  no credential was supplied through chat, terminal, source code or a file.

## Sanitized results

| Check | Result | Sanitized evidence |
|---|---|---|
| Initial application state | PASS | App started locally as unauthenticated; historical-universe warning visible; no order controls visible. |
| Daily token exchange | PASS | Authenticated after adding the required API-version header and running the local app with outbound Kite access. |
| Secret/request-token cleanup | PASS | Sensitive input widgets were absent after authentication. |
| Session validation | PASS | User confirmed the UI displayed `Session is valid.` |
| Current instrument discovery | PASS | Current inventory loaded in memory and was labeled current-only. |
| Inventory counts | NOT_RECORDED | Aggregate counts were not copied before disconnect. No raw inventory was retained for reconstruction. |
| Bounded instrument search | PASS | Full-dump multiselect hang was replaced with filtered, maximum-100-result search. |
| LTP endpoint | PASS | User exercised the snapshot type; aggregate requested/returned counts were not separately recorded. |
| OHLC endpoint | PASS | User exercised the snapshot type; aggregate requested/returned counts were not separately recorded. |
| Quote endpoint | PASS | Requested 3, returned 3, missing 0. |
| Mode-specific display | PASS | LTP, OHLC and Quote now render distinct declared fields and endpoint labels. |
| In-session cache | PASS | User confirmed `FRESH_CACHE` for a repeated request within 15 seconds. |
| Disconnect cleanup | PASS | User confirmed disconnect; UI confirmed application references were removed and credential fields were empty. |
| Invalid/expired token | NOT_OBSERVED | No natural provider rejection occurred after authentication; offline tests cover the path. |
| Trading behavior | PASS | No order or trading endpoint/control was implemented or exercised. |

## Compatibility fixes made during the smoke test

1. Added the officially required `X-Kite-Version: 3` token-exchange header.
2. Added sanitized provider and network error categories without response-body
   or credential disclosure.
3. Identified that the first Streamlit process had sandbox-blocked outbound
   sockets; restarted it with explicit outbound permission. A credential-free
   request then confirmed official Kite API reachability.
4. Replaced the full-inventory multiselect with exchange/type filters, a
   two-character minimum query and a maximum of 100 rendered matches.
5. Added distinct LTP, OHLC and Quote tables. Quote displays only explicitly
   normalized fields rather than raw payloads.
6. Added backward-compatible rendering and in-memory client upgrade behavior
   for Streamlit hot reloads, avoiding a forced re-login.
7. Replaced Streamlit's deprecated dataframe width argument with the supported
   `width="stretch"` form observed in the live application logs.

Every code compatibility change has an offline regression test. The endpoint
allowlist was not broadened.

## Data handling confirmation

- API key, API secret, request token, redirect token, access token and
  authorization header are absent from this report.
- Full user ID, profile, instrument dump and raw quote responses were not
  recorded or committed.
- User-supplied screenshots are not repository artifacts and are not committed.
- Only aggregate quote counts and categorical outcomes are retained.
- Inventory count evidence is explicitly `NOT_RECORDED`; it is not inferred.
- Disconnect removes application references and does not claim secure erasure
  of Python process memory.

## Scope invariants

Kite current instruments remain prohibited as a historical universe. This test
does not change `AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE`, historical population
capability, momentum status, experiment promotion or Slice B readiness.

## Verification

- Root suite: `.\.venv\Scripts\python.exe -m pytest -q` — **86 passed**.
- Kite suite: `.\.venv\Scripts\python.exe -m pytest tests\test_kite_connect.py tests\test_kite_current_market.py -q` — **25 passed**.
- Legacy suite: with `PYTHONPATH` set to `Data test`, pytest with
  `--basetemp=.pytest_tmp\a111-data-test` — **289 passed**, with existing SWIG
  deprecation warnings only.
- JSON validation — **23 specifications parsed**.
- Python compilation — passed.
- Credential-pattern scan — passed.
- `git diff --check` — passed.
- Protected momentum specifications, golden fixtures, historical trust
  specifications and earlier manifests — unchanged from `129e4f8`.

## Decision

`KITE_LIVE_SMOKE_TEST_PASSED`

The limited missing inventory aggregates are a reporting omission, not a data
claim. A.12 may begin only after this report and its code diff are reviewed.
