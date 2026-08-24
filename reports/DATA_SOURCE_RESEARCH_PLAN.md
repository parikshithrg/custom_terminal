# Historical Data Source Research Plan

No acquisition is authorized by this plan. Research should start with product documentation, licensing terms, sample schemas and bounded samples supplied with permission.

## Priority 1 — NSE official/historical data products

Investigate official cash-market bhavcopy/history products and official security/listing reference files.

Expected capabilities:

- `price_history_complete`: daily historical EQ-series population and fields.
- `survivorship_safe`: inclusion of inactive and delisted historical listings.
- `historical_universe_reconstructible`: volume and exchange turnover across the full population.
- `publication_timing_known`: archive publication/revision policy.
- Partial `stable_security_identity_verified`: exchange security/listing identifiers and ISIN where supplied.

Questions: full-history availability, inactive symbol coverage, previous-close semantics, corrections/vintages, raw retention, derived research rights, delivery mechanism and pricing.

## Priority 2 — BSE/SEBI official reference and corporate-action sources

Investigate official issuer/listing, corporate-action, suspension, delisting, merger/demerger and regulatory records. BSE material may corroborate issuer identity and cross-listing events; SEBI/exchange notices may provide authoritative terminal reasons.

Expected capabilities:

- `corporate_actions_verified`.
- `delisting_outcomes_available`.
- `stable_security_identity_verified` through dated ISIN/listing/symbol relationships.
- Supporting evidence for `survivorship_safe` and `publication_timing_known`.

Questions: downloadable historical depth, event timestamps, old/new identifiers, merger consideration, authoritative final price, unresolved cases, licensing and document retention.

## Priority 3 — NSE Indices official PRI/TRI history

Investigate official NIFTY 50 price-return and total-return histories plus methodology/version records.

Expected capabilities/support:

- Removes benchmark PRI/TRI ambiguity.
- Supports point-in-time benchmark methodology/version evidence.
- Enables return target selection consistent with dividend/corporate-action treatment.

Questions: open levels for execution-aligned comparisons, earliest PRI/TRI date, methodology changes, revisions, licensing for stored/published derived results.

## Priority 4 — Government, exchange and SEBI transaction-cost circulars

Build an authoritative, date-effective history for STT, exchange transaction charges, SEBI charges, stamp duty and service-tax/GST regimes. Broker schedules remain separately versioned assumptions.

Expected support:

- Closes `dated_cost_schedule_gaps` for the research interval.
- Makes transaction-cost-adjusted evidence historically defensible.

Questions: effective versus announcement dates, taxable base, buy/sell applicability, state-level stamp-duty history, superseding circulars and machine-verifiable citations.

## Priority 5 — Commercial Indian-market vendors

Evaluate only as fallback or supplementation when official sources cannot provide usable completeness, identity continuity or delivery mechanics. Compare every candidate with `DATA_SOURCE_EVALUATION_TEMPLATE.md`.

Expected capabilities depend on product:

- Backfilled survivorship-complete daily equity history.
- Normalized security master and alias/ISIN history.
- Audited corporate actions and terminal consideration.
- Provider-supported PIT/revision history.

Reject convenience-only feeds that expose current tickers with backfilled prices, silently adjusted series, undocumented delisting omissions, or licenses that prevent durable raw retention and reproducibility.

## Evaluation sequence

1. Obtain documentation, field dictionaries, coverage counts, license/retention terms and price quotation.
2. Complete the evaluation template without committing to purchase.
3. Request an explicitly permitted bounded sample containing difficult lifecycle cases.
4. Implement a provider adapter outside research modules.
5. Run immutable acquisition, normalization, reconciliation and acceptance.
6. Compare provider population counts with an independent reference.
7. Record each capability as PASS/FAIL/UNKNOWN with evidence.
8. Seek user approval before subscription, bulk acquisition or scraping.
