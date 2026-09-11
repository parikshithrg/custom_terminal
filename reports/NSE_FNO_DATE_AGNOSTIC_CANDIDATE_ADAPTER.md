# NSE F&O Date-Agnostic Candidate Adapter

## Decision

R.10N-C implements an offline, date-agnostic paired-report adapter with the
lifecycle state `CANDIDATE_NOT_PRODUCTION_AUTHORIZED`. It is not registered as
a provider and is unreachable from UI, scheduled jobs, production runners,
and research pipelines.

## Architecture

The reusable implementation lives in
`market_intel.foundation.nse_fno_candidate`. Its caller must supply an explicit
package directory, canonical ISO trading date, and sanitized acquisition
manifest. Descriptor construction verifies the date-derived filenames, exact
official HTTPS URLs, byte lengths, and SHA-256 hashes. Adaptation then applies
bounded ZIP/GZIP validation, parses UDiFF and MII independently, joins only by
`FinInstrmId`, and returns immutable normalized records plus deterministic
quality results.

Acquisition remains in `tools/download_nse_fno_reports.py` and was not coupled
to parsing. The R10N-B qualification command now delegates reusable parsing
and verification to the candidate, then translates the result into the sealed
R10N-B evidence shape. It is still independent from application and research
entrypoints.

## Normalized contract

The record contract covers trading date, financial instrument ID, instrument
type, ticker, available underlying identifier, expiry, strike, option type,
lot size, OHLC, settlement price, volume, open interest, source family/version,
and a two-file manifest provenance binding. Prices and strikes use exact
decimal values; lot size, volume, and open interest use integers. No binary
floating point is introduced.

UDiFF ISO dates are exchange-calendar dates without a timezone. MII expiry
seconds are interpreted in UTC before taking the calendar date. Missing,
not-applicable, malformed, and present are distinct states. Futures strike and
option type are explicitly not applicable rather than missing.

## Failure behavior

The adapter returns no partial normalized result when the manifest, hash,
archive, schema, value, date, OHLC, or identity boundary fails. Missing,
duplicate, unresolved, and conflicting identities fail with distinct error
codes. Legacy bhavcopy input is rejected explicitly. Added columns and column
reordering are accepted; missing or duplicate required columns are rejected.
No archive or manifest is discovered implicitly.

## Validation and reconciliation

Fully synthetic ZIP/GZIP fixtures cover two different dates, futures/options,
zero values, state distinctions, malformed fields, identity failures, legacy
input, filename/date and hash mismatches, unsafe/corrupt archives, and schema
addition/reordering. These fixtures prove adapter behavior only; they do not
show that NSE's real schema is stable across dates.

The refactored R10N-B qualifier was also run offline against its retained,
owner-approved package. All five evidence files reproduced byte-for-byte,
including the root manifest. No sealed R10N-B evidence was rewritten.

The candidate-only suite passed 20 tests; the complete R10N-C focused and
evidence set passed 73, and the relevant governance set passed 51. The full
root suite reported 858 passed, four skipped, and two failures. One is the
unchanged sealed R9K native-sleep timing diagnostic at negative 0.003 seconds.
The other is the intended fail-closed research-state fingerprint signal: the
current review fingerprint is stale because policy v2 includes every
`src/**/*.py` byte and this milestone adds a foundation source file. The old
fingerprint policy, assertion, and evidence remain unchanged. A fresh review
would be required before any separately proposed research scope could advance.

## Limits and next milestone

The only real NSE evidence remains the single `2026-09-09` package. This
milestone does not authorize another download, URL access, enumeration, local
F&O database access, Kite, APSW, holdouts, production activation, research,
backtests, signals, scores, recommendations, portfolio logic, redistribution,
or trading.

The recommended next milestone is a separately owner-approved, bounded
multi-date schema-stability and correction-behavior decision. Synthetic dates
cannot substitute for that permission or real-source evidence.
