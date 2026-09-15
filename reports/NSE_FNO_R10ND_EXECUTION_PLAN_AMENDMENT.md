# NSE F&O R10N-D Execution Plan Amendment

## Offline preflight finding

R10N-E stopped before external access because the governing request budget is
internally inconsistent. The R10N-D plan allows four requests total and also
requires all four payload GETs. That leaves zero requests to confirm both
files in each pair before acquiring either one. Using a payload GET as the
confirmation would acquire the first file before its mate was confirmed and
would violate the explicit gate.

No NSE URL was checked, no acknowledgement flag was used, and no payload was
downloaded. The existing `2026-09-09` anchor was not accessed or reacquired.

## Proposed smallest amendment

Amend the ceiling to eight direct requests and eight direct HTTP 200 responses:

- Four no-body `HEAD` requests, one to each exact proposed URL.
- Four payload `GET` requests, only after all four HEAD confirmations succeed.
- Zero redirects, retries, landing-page requests, enumeration, fallback dates,
  substitutions, or anchor requests.

If any HEAD is unsupported, ambiguous, redirected, or not HTTP 200, execution
stops with zero GETs. HEAD confirms only direct endpoint availability; it does
not validate payload bytes. Content, archive, schema, and identity validation
remain fail-closed after an authorized transactional GET.

The dates, destinations, filenames, and URLs are unchanged:

1. `2026-09-10` → `artifacts/nse_fno_reports/2026-09-10/`
   - `BhavCopy_NSE_FO_0_0_0_20260910_F_0000.csv.zip`
   - `NSE_FO_contract_10092026.csv.gz`
2. `2025-07-08` → `artifacts/nse_fno_reports/2025-07-08/`
   - `BhavCopy_NSE_FO_0_0_0_20250708_F_0000.csv.zip`
   - `NSE_FO_contract_08072025.csv.gz`

The four exact URLs remain those in the sealed R10N-D plan. Their availability
has not been checked or asserted.

## Offline downloader hardening

The downloader subsystem now has an explicit, non-entrypoint R10N-E companion
API named `download_package_zero_redirects`. It sends requests with
`allow_redirects=False`, rejects every HTTP status from 300 through 399 without
interpreting `Location`, rejects hidden redirect history and a changed final
URL, makes no retry, and keeps transactional cleanup and HTTP-session ownership
behavior. The historical CLI downloader remains byte-identical, preserving its
sealed entrypoint inventory and allowlisted-redirect contract. R10N-E would
require the strict companion API.

## Owner amendment decision required

Before any later external request, the owner must explicitly approve or reject
the four HEAD plus four GET structure and eight-request/eight-response ceiling.
Approval must also cover the unchanged two dates, four filenames and URLs,
destinations, non-commercial internal technical purpose, exact retention
deadline for each package, deletion at those deadlines, zero redirects,
retries, fallbacks and enumeration, current NSE policy review, and personal
authorization to supply the acknowledgement flag.

Blank, partial, assumed, or indirect approval authorizes zero requests. This
report itself is not approval. Source qualification still authorizes neither
production nor research, and the adapter remains
`CANDIDATE_NOT_PRODUCTION_AUTHORIZED` with the research fingerprint stale and
fail closed.

## Validation

The strict downloader suite passed 71 tests, the R10N-E preflight suite passed
10, the unchanged R10N-D governance suite passed 12, the combined focused set
passed 139, and relevant governance passed 73. The historical downloader is
byte-identical and its sealed entrypoint-inventory check passes. Compilation,
strict JSON, manifest, privacy, historical-evidence, and raw-payload checks
also pass.

The complete root suite reported 924 passed, four skipped, and three failures.
They are the already classified fail-closed research-fingerprint assertion and
both sealed R9K `job_timeout` and `job_close` timing diagnostics, each at the
unchanged negative 0.003 seconds. No assertion or sealed evidence was changed,
and R10N-E introduced no functional failure.
