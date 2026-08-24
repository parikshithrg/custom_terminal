# Official Public Data Feasibility

## Scope

This review evaluates legally accessible official public sources for a historically reconstructible Indian-equity research dataset. It does not authorize bulk acquisition, scraping, authentication bypass, or redistribution. The machine-readable registry is `specs/official_public_sources_v1.json`.

## Source findings

| Required evidence | Official source | Feasibility | Principal limitation |
|---|---|---|---|
| Daily cash-equity observations | [NSE All Reports](https://www.nseindia.com/all-reports/) and [historical reports](https://www.nseindia.com/static/resources/historical-reports-capital-market-daily-monthly-archives) | Partial | Dated bhavcopies are accessible in multiple schemas, but a complete date-by-date archive, correction-vintage policy, and automated-use permission are not established. |
| Historical security/listing master | NSE dated MII security file via All Reports | Unknown | Current dated security files are advertised; complete historical snapshots and issuer/successor continuity are unproved. |
| Corporate actions | [NSE corporate filings](https://www.nseindia.com/companies-listing/corporate-filings-application?id=equity) | Partial | Ex-date actions and broadcast-timestamped issuer announcements exist, but a complete historical action ledger and uniform identifier continuity are unproved. |
| Name/symbol changes | NSE listing circulars | Sample feasible | Official dated circulars can state old/new symbols and effective dates. No complete machine-readable historical registry was established. |
| Suspension/delisting | [NSE delisting page](https://www.nseindia.com/static/list/list-of-companies-proposed-to-be-delisted) and [compliance page](https://www.nseindia.com/static/regulations/listing-compliance) | Partial | Official lists/orders exist, but final tradable value, consideration, and historical list vintages are not uniformly available. |
| Delisting regulation/orders | [SEBI legal archive](https://www.sebi.gov.in/legal/regulations/) | Supplementary | Authoritative legal/event evidence, not a complete listed-security population or standardized terminal-value table. |
| Independent reconciliation | [BSE listed securities](https://www.bseindia.com/corporates/List_Scrips.html) and BSE corporate records | Unknown | Bounded cross-exchange sample and historical population archive still require manual qualification and terms review. |
| NIFTY 50 PRI/TRI | [NSE Indices historical data](https://www.niftyindices.com/reports) | Partial | Interactive PRI and TRI outputs are advertised, but retrieval permission, downloadable date floor, publication timing and revisions remain unqualified. NSE Indices explicitly distinguishes price returns from dividend-inclusive total returns. |
| Statutory costs | Government/SEBI/NSE gazettes and circulars | Feasible with manual compilation | Primary documents are distributed across issuers and must be assembled into a dated schedule with supersession links. Slippage remains an assumption. |
| Merger/demerger consideration | Issuer filings and [NSE scheme documents](https://www.nseindia.com/companies-listing/corporate-filings-scheme-document) | Case-feasible | Large, case-specific documents; no uniform historical table or proven complete index. |
| Mutual funds | [AMFI](https://www.amfiindia.com/) | Not applicable | AMFI is relevant to future mutual-fund research, not equity survivorship or equity security identity. |

## Access and format evidence

- NSE publishes full bhavcopy/security-deliverable reports, CM-UDiFF bhavcopy, and dated MII security files. Its page also documents the 2024 transition away from older common-bhavcopy formats.
- A bounded request succeeded for 2016 legacy ZIP and 2020/2024 full CSV formats. A 2012 legacy request returned access-control HTML and was quarantined; no bypass was attempted.
- NSE’s official delisting page exposes downloadable proposed/delisted lists and committee material.
- NSE Indices exposes separate historical index and total-return sections. Its total-return methodology explains that the price index excludes dividend receipts and the TRI includes reinvested dividends.
- NSE issuer announcements expose broadcast timestamps, but the exchange disclaimer states issuer-uploaded information is disseminated without verification of adequacy or accuracy; cross-evidence remains necessary.

## Capability implications

The public official ecosystem contains many required components, but accessibility of individual files is not equivalent to a complete historical population. The following remain blockers:

1. Proven day-by-day historical listing/security snapshots, including inactive securities.
2. Complete symbol/ISIN/listing validity history.
3. A complete action ledger with publication and effective timing.
4. Terminal consideration/final-price treatment for every terminated listing.
5. Independent yearly population reconciliation against BSE or another official reference.
6. Confirmed retention/automation/licensing permission for systematic historical acquisition.
7. Complete PRI/TRI and historical statutory-cost histories with version metadata.

## Proposed trustworthy start date

None. Three successful price dates and several lifecycle documents cannot establish that the listed population, identities, actions, and terminal outcomes are reconstructible from any continuous start date.
