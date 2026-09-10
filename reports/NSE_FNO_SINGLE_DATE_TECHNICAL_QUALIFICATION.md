# NSE F&O Single-Date Technical Qualification

## Decision

`SINGLE_DATE_PACKAGE_TECHNICALLY_QUALIFIED`

The retained `2026-09-09` package is technically usable for the bounded,
non-commercial internal qualification approved by the owner. This decision
does not authorize another date, bulk acquisition, redistribution, research,
production activation, recommendations, or trading.

## Owner gate and acquisition outcome

The owner explicitly confirmed personal review of the NSE Terms of Use,
Copyright page, and Data Sharing & Usage Policy, and approved exactly the two
R.10N-A files and the stated local destination for technical qualification.

The package already existed when that confirmation was supplied. After the
gate passed, the exact R.10N-A command was run once. The hardened downloader
refused to overwrite the destination before making a network request. No
automatic retry, alternative URL, alternative date, or replacement download
was attempted. Qualification therefore used the pre-existing package after
reconciling its manifest, official URLs, byte lengths, and SHA-256 hashes.

## Package and archive integrity

- UDiFF ZIP: `BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip`, 1,028,737
  bytes, SHA-256
  `50826bed50da889b90b208c9b6368d3768c0eabb416178b176f064d3f93de3f5`.
  It contains exactly the expected CSV member: 6,034,961 expanded bytes,
  CRC32 `24cbaf4b`.
- MII GZIP: `NSE_FO_contract_09092026.csv.gz`, 1,725,381 bytes, SHA-256
  `a58c75d36a5100506c005961af181cd6ca8ed597289ffc5fdc3107920e4850cf`.
  Its validated CSV stream is 28,581,969 expanded bytes.

Both archives passed bounded structural, CRC/decompression, expected-member,
path, and expansion checks. The parser streamed only the validated CSV
members; it did not use general-purpose extraction or persist extracted rows.
No partial staging directory was found or created.

## Observed schemas and normalization

UDiFF and MII were parsed as separate schema families. Legacy bhavcopy fields
are rejected by the UDiFF parser. MII epoch-second expiries and its `CE`, `PE`,
and futures `XX` option-type convention are validated explicitly.

- UDiFF source and normalized rows: 33,250 / 33,250.
- MII source and normalized rows: 78,603 / 78,603.
- UDiFF instruments: 647 futures and 32,603 options.
- Trading date: all 33,250 facts rows report `2026-09-09`.
- Malformed facts or contract rows: 0 / 0.
- Invalid traded-row OHLC ranges: 0.

Missing and not-applicable values remain distinct. Futures account for the
647 UDiFF and 665 MII rows where strike and option type are not applicable;
these values were not treated as missing or malformed.

## Contract identity and field coverage

The only join key is `FinInstrmId`. All 33,250 facts rows matched exactly one
of 78,603 unique MII identities, for a 100% join rate. Missing keys,
unresolved identities, ambiguous identities, and duplicate MII keys were all
zero. The implementation fails closed for any of those cases and has offline
tests for duplicate and ambiguous identities.

All facts rows had parseable expiry, lot size, price, settlement price,
volume, and open-interest fields. Coverage observations were:

- Volume: 11,476 non-zero; 21,774 zero.
- Settlement price: 33,161 non-zero; 89 zero.
- Open interest: 16,659 non-zero; 16,591 zero.
- Option strike/type: present for all 32,603 options and explicitly not
  applicable for all 647 futures.
- MII option strike/type: present for 77,938 options and explicitly not
  applicable for 665 futures; expiry and lot size were valid on all rows.

## Limits and reproducibility

The `_F_` UDiFF filename identifies this sample as the final report variant,
but one retained observation cannot establish whether later corrections occur
or whether schemas are stable across dates. Raw archives remain ignored under
`artifacts/` and are intentionally absent from Git, so another machine cannot
reproduce the measurements from the commit alone without separately permitted
access to the exact hash-bound payloads.

Tracked evidence is aggregate and sanitized: it contains source provenance,
archive/schema metadata, counts, coverage, decisions, and cryptographic
bindings, but no raw exchange rows, full contract inventory, credentials,
headers, response bodies, or absolute private paths.

## Validation

The combined R.10N-B, downloader, and R.10N-A focused suites passed 46/46;
relevant F&O governance tests passed 41/41. The final root suite reported 833
passed, four skipped, and one failure. That failure is the pre-existing sealed
R9K native-sleep `job_close` timing diagnostic at negative 0.003 seconds. An
earlier full run reproduced both known R9K timing cases at the same value; it
also identified two new-entrypoint inventory diagnostics, which were resolved
by keeping this offline qualification module out of the production entrypoint
inventory. No historical inventory or R9K assertion was changed.
