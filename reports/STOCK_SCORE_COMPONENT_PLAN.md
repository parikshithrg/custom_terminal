# Stock Score Component Plan

## Boundary

R.8 does not define a final stock score. It inventories candidate evidence
categories and the contracts required before any stock-level feature could be
calculated historically. No security is ranked and no recommendation is
produced.

## Candidate categories

| Category | Candidate inputs | Primary blockers | Possible initial use |
|---|---|---|---|
| Data quality | coverage, freshness, identity resolution, source status | calibration and display semantics | Current evidence-quality label |
| Liquidity | price, volume, exchange turnover, delivery | survivor-selected history, missing daily population | Current display; historical only after qualification |
| Market behavior | returns, volatility, breadth relationship | action treatment, benchmark class, outcome governance | Research candidate only |
| Corporate disclosure | filings, actions, ratings | publication timestamps, corrections, issuer/listing identity | Current display or later PIT research |
| Ownership | shareholding and changes | incomplete coverage, collapsed revisions, filing clocks | Current display only today |
| Sentiment | transcript language and disclosed events | corpus rights, document timing, selection/missingness | Separate exploratory component |
| Derivatives context | delivery, futures, OI and options | F&O provenance, contracts, rolls, publication and revisions | Blocked pending database audit |

## Input-specific requirements

- **Price and liquidity:** stable listing identity, raw/adjusted separation,
  corrections, corporate actions, inactive securities and daily availability.
- **Ownership:** exact filing timestamp, original and revised filings, issuer and
  listing relationship, missing filers and reporting-period semantics.
- **Insider disclosures:** transaction/filing/broadcast clocks, security identity,
  amendment history and explicit handling of estimated values.
- **Earnings transcripts:** original document hash, publication time, language,
  issuer identity, corpus selection and missing documents.
- **Ratings:** rating instrument versus equity issuer identity, agency source,
  action timestamp, withdrawn ratings and coverage gaps.
- **Delivery statistics:** report provenance, publication clock, symbol/series
  keys, missing sessions and revision handling.
- **Options/futures:** instrument token, underlying, option type, strike, expiry,
  contract transition, settlement, OI and roll semantics.
- **Corporate filings/actions:** event, publication and effective dates; original
  and corrected evidence; predecessor/successor identity.

## Missing data and scope

Missingness must remain explicit and must not be converted to a neutral score.
Current display availability is not evidence of historical availability. A
stock absent from a dataset cannot be assumed to have no event, no insider
activity or neutral sentiment. Inactive securities remain necessary for any
historical cross-sectional claim even though they are not current trade ideas.

## Publication boundary

A future UI may render approved category-level read models. It must display the
knowledge cutoff, horizon, source state, missingness and qualification status.
It may not aggregate categories into an opaque number until a separately
preregistered and validated combination exists.

Any future prototype begins as `EXPLORATORY_NONACTIONABLE`. Permitted planning
decisions are:

- `STOCK_SCORE_COMPONENT_READY_FOR_DATA_QUALIFICATION`
- `STOCK_SCORE_DEFINITION_AMBIGUOUS`
- `STOCK_SCORE_INPUTS_NOT_POINT_IN_TIME`
- `STOCK_SCORE_COMPONENT_BLOCKED`

Current planning assessment: category boundaries are ready for owner review;
the combined score remains undefined and the historical inputs remain
unqualified.
