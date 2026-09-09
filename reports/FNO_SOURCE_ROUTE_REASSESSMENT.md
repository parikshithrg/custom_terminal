# F&O Source Route Reassessment

## Decision

`HYBRID_FNO_ROUTE_RECOMMENDED`

Use free official NSE reports as the primary candidate for daily contract facts and contract identity; SEBI publications for participant/regulatory context; and the already-scoped Kite connector for current instruments, current quotes and limited continuous daily futures. Treat BSE as a distinct supplementary market. Defer or abandon the existing local F&O database unless a later, separately approved immutable snapshot and material unique capability are demonstrated.

This report qualifies documentation, not downloaded history. It does not authorize acquisition, research, backtesting, scoring, recommendations, broker actions or trading.

## Official-source findings

NSE's [derivatives reports page](https://www.nseindia.com/all-reports-derivatives) lists UDiFF and legacy bhavcopies, MII contract files, settlement prices, OI, participant files, ban files and market-activity reports. NSE's [UDiFF formats page](https://www.nseindia.com/static/resources/forms-formats-members) supplies schema evidence. These are strong candidates for daily futures/options facts, but exact historical ranges, corrections, unattended retrieval and retention remain unqualified. Legacy and UDiFF are separate versions.

The [NSE research-data list](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20list%20under%20NSE%20Data%20Sharing%20Policy%20for%20Research%20and%20Analysis_20250728.pdf) confirms that archive products exist; it is not interpreted as blanket permission. Paid EOD/order/trade products are excluded.

BSE's [equity-derivatives format](https://www.bseindia.com/downloads1/File_Format_Equity_Derivatives.pdf) documents price, settlement, volume and OI fields, while its [UDiFF guidance](https://www.bseindia.com/downloads1/Annexure_A_SEBI_guidance_document_having_the_UDiFF_Standards_for_Generation_and_Implementation.pdf) supports schema planning. Neither proves archive depth or substantial useful liquidity. NSE and BSE contracts stay separate.

SEBI's [FPI derivative-trades statistics](https://www.sebi.gov.in/statistics/fpi-investment/derivative-trades.html) are suitable for aggregate participant and regulatory context, not contract-level prices.

Kite's [historical-candle documentation](https://kite.trade/docs/connect/v3/historical/) supports OHLCV, optional OI and limited continuous daily futures. The current instrument dump is not a historical contract master, and expired-option coverage is not established. Kite remains supplemental and account/API dependent.

## Local-database decision

The route fails two mandatory time-box conditions and has no evidence for a third: no current stable-snapshot mechanism, no calibration applicable to useful real-schema queries, and no proven unique capability. APSW itself is conditionally reviewable, but that does not rescue the data route. R9P's largest synthetic catalog read was 36,484 bytes; it cannot justify R10L's 256 MiB cap for an unopened approximately 45 GB database.

Exclusive sharing on only the main file does not prove producer quiescence or directory/sidecar consistency. Before/after hashes are insufficient. A separately supplied immutable snapshot could change this conclusion, but none exists and R10M was forbidden to create one.

Decision: `DEFER_OR_ABANDON_LOCAL_FNO_DATABASE_ROUTE`. No additional synthetic boundary implementation is justified now.

## Product implication

Current option chain and current futures curve are supportable through Kite within session/entitlement limits. Daily futures history, OI changes and participant positioning are only partially supportable until official files are sampled and accepted. Daily expired options, rollover, implied volatility and put-call measures remain hidden pending evidence. Intraday derivative history and historical option-chain replay are deferred. Breadth/sentiment remains mock-only until its definitions are researched later.

The interactive website skeleton remains mock-first. Missing chains remain visible; no source is treated as complete by convenience.

## Next milestone

Run one bounded, manual-first official NSE F&O paired-date qualification: acquire one permitted UDiFF/legacy daily facts file with its matching MII contract file, preserve immutable provenance, normalize the two schema versions separately, and test identity/OHLCV/OI/expiry coverage. Stop before bulk acquisition or research.

Owner decision required: approve or reject that single official-file qualification scope. No approval is inferred here.
