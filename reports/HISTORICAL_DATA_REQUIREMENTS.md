# Historical Data Requirements

## Mandatory before publishable equity-edge research

| Dataset | Fields required | Frequency | Minimum history | Point-in-time requirements | Corporate-action requirements | Delisting requirements | Identifier requirements | Preferred authoritative source type | Fallback source type | Licensing concern |
|---|---|---|---|---|---|---|---|---|---|---|
| NSE cash-equity bhavcopy archive | trade date, symbol, series, OHLC, last/previous close, volume, exchange turnover, trade count where available | Daily | 2003 onward, preferably full archive | Immutable dated raw files; retrieval and parser version recorded | Exchange previous-close/action markers retained; raw and adjusted facts separated | Must retain every historically listed EQ-series security through its final session | ISIN/security code where published, plus exchange/listing key | NSE official historical archive or licensed exchange feed | Regulated vendor delivering raw exchange history | Redistribution, retention, and derived-data rights |
| Historical listed-security master | issuer, instrument/listing, exchange, segment/series, symbol, ISIN, validity intervals, listing/end status | Event/daily snapshot | Same span as prices | Effective and publication dates; all vintages retained | Predecessor/successor and demerger relationships | Reason and effective date for delisting, merger, suspension and relisting | Stable issuer, instrument, listing and ISIN identifiers | NSE/SEBI official security and corporate-action archives | Established India-market reference-data vendor | Symbol/ISIN history may be licensed reference data |
| Corporate-action ledger | action type, announcement/ex/record/pay dates, ratio/cash amount, old/new identifiers | Event | Same span as prices | Announcement/publication and effective dates separated | Splits, bonuses, dividends, rights, mergers, demergers, symbol/ISIN changes | Merger consideration and successor entitlement | ISIN and listing IDs before/after event | NSE/BSE issuer action files plus regulatory filings | Licensed adjusted-price vendor with auditable factors | Corporate-action redistribution limits |
| Terminal outcomes | last trade, suspension date, delisting effective date, reason, cash/security consideration, recovery where applicable | Event | Same span as prices | Only information known by each historical cutoff | Merger/demerger consideration linked to actions | Explicit delisting return or unresolved state | Stable listing/ISIN plus successor IDs | Exchange delisting notices and issuer/regulatory filings | Specialist vendor | Event-document retention and reuse |
| NIFTY 50 PRI and TRI | date, index identifier, official close/open where available, PRI/TRI classification, methodology version | Daily | Match research span | Vintage/methodology changes recorded | Index-provider treatment documented | Not applicable | Stable index ID | NSE Indices official history/license | Reputable index-data vendor | Index history often has contractual use limits |
| Historical statutory cost schedule | effective dates and rates for STT, exchange, SEBI, stamp duty, service tax/GST; broker schedule | Event-effective | Match research span | Date-effective versions immutable | Not applicable | Not applicable | Schedule/version ID | Government, exchange, SEBI and broker circulars | Audited secondary compilation | Usually public documents; preserve citations |

Required acceptance checks after acquisition:

- Reconcile daily listed population counts against exchange records.
- Sample terminated securities and reproduce their complete lifecycle.
- Verify symbol/ISIN transitions and avoid accidental series stitching.
- Reconcile turnover and price fields to raw archive files.
- Validate adjustment factors independently; retain unadjusted evidence.
- Confirm publication and retrieval assumptions for each dataset.
- Re-run the categorical trust contract; every experiment-required capability must be `PASS`.

## Useful later

| Dataset | Fields required | Frequency/history | Purpose | Main licensing concern |
|---|---|---|---|---|
| Point-in-time sector/industry classifications | dated classification and methodology | Event, full research span | Sector-neutral diagnostics and exposure attribution | Vendor taxonomy redistribution |
| Historical free float and shares outstanding | effective shares/free float and announcement dates | Event/monthly | Capacity, investability and corporate-action validation | Vendor/reference-data rights |
| Bid/ask or intraday bars | quotes/trades, auction flags | Tick or 1–5 minute, shorter recent span acceptable | Slippage and fill realism | Storage and exchange entitlement costs |
| Trading-status calendar | halts, suspensions, auctions, circuit states | Event/daily | Distinguish ordinary missing data from untradeability | Exchange archive access |
| Dividend/tax treatment reference | dividend dates/amounts and applicable tax assumptions | Event | Total shareholder return and after-tax variants | Corporate-action licensing |

No purchase, subscription, scraping, or bulk download is authorized by this document. It is an acquisition specification only.
