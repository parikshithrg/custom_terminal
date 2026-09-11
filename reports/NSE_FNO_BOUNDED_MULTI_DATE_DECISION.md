# NSE F&O Bounded Multi-Date Owner Decision

## Decision

R.10N-D is ready to present a planning packet to the owner. It authorizes no
external access or acquisition. The adapter remains
`CANDIDATE_NOT_PRODUCTION_AUTHORIZED`, and its stale research fingerprint
remains unchanged and fail closed.

## Proposed evidence sample

The already qualified `2026-09-09` package is the anchor and must not be
reacquired. Two new date pairs are proposed offline:

- `2026-09-10`, the next completed weekday after the anchor, tests immediate
  adjacent-date stability.
- `2025-07-08`, a Tuesday one year after the repository-recorded UDiFF
  transition, tests temporal stability across roughly fourteen months.

Neither date is claimed to be an NSE trading day or to have files available.
The repository only establishes that each is a weekday and that no existing
evidence identifies it as a holiday. A separately authorized exact-pair check
must confirm one final UDiFF F&O bhavcopy and its NSE-exclusive MII contract
file before acquisition. Failure to confirm either file stops that date; it
does not permit a fallback.

## Evidence questions and acceptance

Each date must independently preserve all required UDiFF and MII columns,
types, date semantics, bounded archive structure, and exact filename/date
agreement. Additions are recorded and accepted only when non-colliding;
removal, duplication, type drift, or changed required semantics stops the
qualification. Column order is irrelevant only if normalized output remains
identical.

`FinInstrmId` must be unique in MII and join every UDiFF row exactly once.
Missing, duplicate, ambiguous, or unresolved identities have a zero tolerance.
Both futures and options must be represented to exercise classification.
Expiry and lot size must be valid and agree across paired sources; option
strike/type must be present while futures retain not-applicable semantics.
Required OHLC, settlement, volume, and open-interest values must parse with
zero distinct from missing, and every traded row must have valid OHLC bounds.

Population counts need not be equal between dates. Additions, removals, and
intersection are recorded because ordinary contract turnover is expected;
it cannot be treated as evidence of a corrected report. These thresholds
protect the required-field and identity contracts rather than being tuned to
reproduce the anchor's counts.

## Exact ceiling and stop protocol

The ceiling is two manual date invocations, four new payloads, four initial
HTTP GETs, four accepted direct responses, zero redirects, zero retries, zero
enumeration, and zero fallback dates. The anchor has a retrieval budget of
zero. A missing file, access-control response, redirect, unexpected response,
archive failure, schema drift, or incomplete approval stops the run without a
partial final package.

The current downloader can validate allowlisted redirects. The proposed
R10N-E protocol is stricter: it requires zero redirects. R10N-E must preflight
that behavior before any external access. Raw packages remain ignored and
uncommitted; the owner must approve an exact relative destination and deletion
deadline for each date. Only sanitized aggregate evidence and immutable hashes
may be committed.

## Correction limitation

For every approved retrieval, later evidence would record SHA-256, byte
length, sanitized ETag and Last-Modified values when supplied, exact filename,
and UTC retrieval time. Report finality is recorded from the approved `_F_`
variant. A later replacement can only be inferred by comparing the same date
and filename at a later, separately approved retrieval. Different-date hashes
or population changes are ordinary cross-date evidence.

This bounded plan authorizes only one retrieval per new date, so it cannot
establish correction behavior. It creates no monitor and permits no repeated
retrieval. Correction qualification would require its own owner decision.

## Exact owner decisions required

Before R10N-E, the owner must explicitly approve the two exact dates, four
filenames and proposed official URLs, exact relative destinations, bounded
pair-confirmation access, non-commercial internal technical purpose, an exact
retention deadline for each package, deletion policy, and the zero-retry,
zero-redirect, zero-fallback protocol. The owner must personally review the
current NSE policy pages and supply the acknowledgement flag only after the
whole decision is complete. Blank or partial approval authorizes zero requests.

## Remaining unauthorized actions

No NSE URL visit, availability check, download, crawling, archive enumeration,
legacy adapter, BSE or paid source, Kite, APSW, local F&O database, production
activation, scheduled monitoring, research, backtest, signal, score,
recommendation, portfolio logic, redistribution, or trading is authorized.
Adapter/source qualification and research authorization remain separate gates.

The recommended R10N-E scope is a separately approved, exact-date execution:
first close and test the zero-redirect downloader gap, then confirm and acquire
only the two approved pairs within the four-request/four-payload ceiling,
qualify each offline, retain hash-bound sanitized evidence, and stop on the
first deviation. It must not substitute dates or investigate corrections.

## Validation

All 12 new R10N-D governance tests passed. The R10N-C adapter and evidence set
passed 30 tests; the R10N-B, R10N-A, and downloader set passed 43; the combined
focused set passed 85; and the relevant governance set passed 63. Compilation,
strict JSON, manifest, historical hash, and privacy checks passed.

The complete root suite reported 871 passed, four skipped, and two failures.
Both reproduce the R10N-C classifications unchanged: the deliberately stale
fail-closed research-fingerprint assertion and the sealed R9K `job_timeout`
timing diagnostic at negative 0.003 seconds. Neither assertion or its evidence
was modified, and R10N-D introduced no functional test failure.
