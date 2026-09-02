# Market Sentiment Component Plan

## Definition before formula

"Market sentiment" is not yet one coherent measurable object. The candidate
inputs in version2.0 span different economic concepts, clocks and populations.
They must remain separate until each concept has a causal definition and its
relationship to a declared future outcome is independently evaluated under the
governed research process.

Potential concepts are:

- **Market stress:** observable price, volatility, liquidity or correlation
  conditions. This may describe risk state without measuring opinion.
- **Investor positioning:** derivatives OI, participant positioning, fund flow
  or ownership changes. Position and intent are not interchangeable.
- **Corporate-management tone:** language in earnings transcripts and filings,
  available only after a verified publication timestamp.
- **Breadth:** participation across a historically valid security population;
  a current NIFTY 500 list cannot reconstruct it historically.
- **Derivatives positioning:** futures/options measures whose contract identity,
  roll, expiry, availability and correction history must be qualified.
- **Macro conditions:** official release-vintage variables whose revision and
  publication clocks differ from market-session clocks.

## version2.0 reference inventory

| Input idea | Current finding | Planning disposition |
|---|---|---|
| Earnings-transcript sentiment | Useful display concept; corpus coverage, rights, timestamps and revisions unqualified | Qualify original filing lineage first |
| Macro context | Mixed sources and clocks | Define one series at a time with release vintages |
| Ownership | Partial coverage; revisions may be collapsed | Current display only until vintages are preserved |
| Insider disclosures | Filing evidence may be official; identity and broadcast clocks incomplete | Candidate for source qualification |
| Market regime inputs | Current diagnostic contains arbitrary composite semantics and action-oriented language | Separate observable state variables; remove action language |
| Existing composite score | Multiple unlike concepts combined without governed calibration | Do not import formula or thresholds |

The detailed source/capability matrix is
`docs/research_r8/source_capability_matrix_v1.json`.

## Alternative conceptual models

1. A **stress dashboard** could publish several current state measurements with
   no aggregate score.
2. A **positioning evidence vector** could keep participant, ownership and
   derivatives observations separate by horizon and population.
3. A **management-tone research component** could later define document-level
   features after publication timing and corpus missingness pass.
4. A **breadth research component** could proceed only after the relevant
   historical population is reconstructible.

R.8 does not choose among these models, combine them, assign numerical weights,
fit thresholds or inspect backtest performance.

## Data qualification gates

Every input needs: lawful free/permitted access; immutable raw evidence;
retention status; publication and availability timestamp; revision vintages;
stable identity; historical population where cross-sectional; explicit
missingness; parser version; and current-versus-historical scope.

## Output and decision semantics

Any future prototype begins as `EXPLORATORY_NONACTIONABLE`. It may not emit
buy, sell, deploy, avoid, aggressive or defensive actions. The permitted
readiness decisions are:

- `SENTIMENT_COMPONENT_READY_FOR_DATA_QUALIFICATION`
- `SENTIMENT_DEFINITION_AMBIGUOUS`
- `SENTIMENT_INPUTS_NOT_POINT_IN_TIME`
- `SENTIMENT_COMPONENT_BLOCKED`

Current planning assessment: the concepts are separable and inventory-ready,
but the definition remains ambiguous and inputs are not yet qualified.
