# Owner development sequence v1

Date recorded: 2026-09-08
Starting repository checkpoint: `d39df04`

## Purpose

This record preserves the project owner's agreed development sequence after the
R10K pre-access safety abort. It supplements the existing owner-review records;
it does not rewrite them or grant execution authority.

The project remains an analysis-only Indian-market decision-support system.
Its intended visible outputs include a market-sentiment score and individual
stock scores, supported by point-in-time data, reproducible evidence,
uncertainty and limitations. Unsupported scores remain hidden. The project must
never place, modify or cancel trades.

## Remaining synthetic-to-real transition

The current estimate is three bounded milestones before the first controlled
real-data inspection, provided each milestone succeeds:

1. Design the F&O production-boundary remediation and reauthorization plan.
2. Implement the selected read-only boundary and complete its synthetic and
   adversarial tests.
3. Complete owner review, pipeline-readiness confirmation and exact
   authorization for any proposed real-data attempt.

The count may increase if the driver, sidecar policy, read-budget enforcement,
provenance or database route cannot satisfy the safety contract.

## Mandatory product-skeleton gate

After synthetic infrastructure testing is complete and the pipeline is judged
ready to accept real market data, but before importing, inspecting or analysing
that data, build an interactive skeleton of the intended app or website.

The skeleton must use clearly labelled mock or synthetic values and must have
no live-data dependency, research conclusion, recommendation, broker action or
trade-execution capability.

The owner will use this skeleton to decide what information the final product
actually needs, including:

- pages and navigation;
- market-overview content;
- market-sentiment presentation;
- individual stock pages and score presentation;
- confidence, evidence, risks and limitations;
- charts and comparisons;
- portfolio-related views, if retained;
- data freshness and missing-data warnings;
- research status and methodology;
- information that must remain hidden;
- features to remove or defer.

## Product and data-requirements freeze

After the owner reviews the skeleton, record the accepted interface and map
every retained screen element to:

- exact data fields;
- proposed free source;
- required history;
- update frequency;
- point-in-time and quality requirements;
- fallback and missing-data behavior;
- licensing, access and retention constraints;
- evidence required before display;
- whether the element remains hidden until validation.

The project will then produce an updated owner-review document or PDF. The
owner must approve the product/data requirements and separately authorize the
next real-data milestone.

## Revised sequence

1. Complete the production-boundary remediation plan.
2. Implement and synthetically validate the selected safety boundary.
3. Confirm pipeline readiness and complete the required owner review.
4. Build the interactive app/website skeleton with mock data.
5. Review and freeze the interface and exact data requirements.
6. Produce and review the updated pre-real-data report or PDF.
7. Begin only the separately authorized controlled real-data qualification.
8. Remediate or qualify the data source.
9. Register a bounded research hypothesis under a current review gate.
10. Conduct the first controlled real-data analysis or backtest.

No step automatically authorizes the next one.

## Standing constraints

- Use free sources such as NSE, SEBI, BSE and AMFI where relevant.
- Kite Connect may supplement available current data but cannot replace a
  historically complete market population.
- `version2.0` remains a separate comparison project.
- The local F&O database remains unqualified after R10K.
- No paid market-data source is approved.
- No real-data research, simulation, backtesting, scoring or recommendation is
  currently authorized.
- Trade execution remains permanently outside the project.
