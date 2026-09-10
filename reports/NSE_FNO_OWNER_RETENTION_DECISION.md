# NSE F&O Owner Retention Decision

## Decision state

`READY_FOR_OWNER_RETENTION_DECISION`

R.10N-A hardens and preflights an acquisition utility. It does not authorize
access, retention, reuse, analysis, redistribution, or any later milestone.
The repository cannot accept NSE terms or resolve legal permission for its
owner.

## Official-page review

Reviewed on 2026-09-10:

- [NSE Terms of Use](https://www.nseindia.com/static/nse-terms-of-use) — access
  is stated to bind the user to the terms and policies. The page restricts
  copying, storage and automated collection, while distinguishing information
  made available for download. It also contains restrictions concerning
  gaming, virtual trading and simulation. Updated 2025-10-29.
- [NSE Copyright](https://www.nseindia.com/static/nse-copyright) — permits
  viewing, printing and downloading content for personal, non-commercial or
  educational purposes subject to accurate reproduction, no modification and
  acknowledgement, but excludes identified third-party content. Updated
  2025-10-21.
- [NSE Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy)
  — defines market data broadly enough to include end-of-day and historical
  derivatives prices, identifiers, volume and trade data. Its research route
  describes requests through NSE's Economic Policy Research Department,
  pricing/waivers, underlying documentation and confidentiality declarations.
  Updated 2025-12-11.
- [NSE derivatives reports](https://www.nseindia.com/all-reports-derivatives)
  — publicly presents date-selected downloads for the F&O UDiFF Common
  Bhavcopy Final ZIP and both NSE-exclusive and cross-exchange MII contract
  files. It states that older common/bhavcopy reports were discontinued from
  2024-07-08 in favor of UDiFF.
- [NSE forms and formats](https://www.nseindia.com/static/resources/forms-formats-members)
  — documents UDiFF standardization, catalogues and FO bhavcopy file formats.
  It is technical schema evidence, not a grant of retention or reuse rights.
  Updated 2026-06-30.

## Availability is not permission

A report being selectable and downloadable from a public NSE page establishes
technical availability. It does not by itself settle which terms govern local
retention, automated retrieval, later parsing, research use, derived outputs,
or redistribution. The copyright page's personal/non-commercial download
language, the Terms' storage and automation restrictions, and the data
policy's agreement-based research route are not reconciled clearly enough for
this repository to infer permission.

This is an unresolved policy ambiguity, not a technical access failure. The
owner may seek written clarification from NSE or qualified legal advice before
proceeding.

## Precise proposed qualification

The only proposed acquisition is one manually initiated internal package for
trading date `2026-09-09`, containing exactly:

1. `BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip`
2. `NSE_FO_contract_09092026.csv.gz`

The package would be fetched from the two exact official URLs recorded in
`docs/investigations/r10n_a/hardening_v1/dry_run_plan.json`. It would be used
only for a later, separately scoped technical qualification of provenance,
archive integrity, schema versions, contract identity and field coverage. It
would not authorize another date, enumeration, retries, bulk acquisition,
research, scoring, recommendations, trading, redistribution, or production
activation.

## Owner approval required

Before personally supplying `--acknowledge-nse-terms`, the owner must:

1. Review the five official pages above in their current form.
2. Decide that the owner's identity, purpose, access method, local retention,
   and proposed technical reuse are permitted, or obtain clarification.
3. Explicitly approve only the date, two filenames, two official URLs, local
   destination, and non-commercial internal qualification described above.
4. Accept responsibility for required attribution, restrictions, security,
   deletion and any applicable agreement or undertaking.
5. Understand that the flag records the operator's acknowledgement; it is not
   a license, legal opinion, or repository-generated approval.

Only after that decision, the exact later command would be:

```powershell
python -c "from tools.download_nse_fno_reports import main; raise SystemExit(main())" --date 2026-09-09 --report both --acknowledge-nse-terms
```

Do not execute it merely because it appears in this report.
