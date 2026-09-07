# R.10F — Synthetic evidence publication and read-model boundary

## Result

R.10F validates immutable synthetic publication and read-only query mechanics.
It does not authorize or publish real evidence, a market score, a probability
forecast, an expected return, a recommendation or production integration.

Authoritative clean implementation checkpoint:
`42a938c50ea013dcb1d3971e4f61162fc5148ac9`.

## Contracts and reused components

The published `asset_evidence_publication_r10f_v1` contract contains identity,
calendar/knowledge timing, horizon/outcome, raw prediction, percentile score and
definition, calibration binding, expected outcome and interval, probability and
definition, confidence and limiting factors, component versions, lifecycle,
sample sizes, freshness, data quality, risks, decision, provenance hashes, run
identity and supersession.

It reuses R.10E's score and evidence values without recalculation, the existing
canonical serialization/hash helpers, R.10B dependency machinery, and prior
lifecycle/holdout boundaries. No second scoring, fold or outcome engine exists.

Cross-field validation rejects ambiguous score language, invalid ranges,
missing uncertainty/reasons, invalid sample sizes, temporal leakage, component
version mismatch, missing or mutated artifacts, synthetic canonical/promotion
claims, active synthetic lifecycle and any synthetic decision other than
`NO_DECISION`.

## Publication eligibility

Synthetic evidence may be exposed only for internal engineering display and
diagnostic inspection. It is always noncanonical, nonpromotable and ineligible
for decision support. Strong oracle metrics cannot override classification,
freshness, provenance, lifecycle, data-quality, terminal-accounting or
confirmatory-status gates.

## Immutable bundles and history

Six content-addressed bundles were atomically published. Each contains snapshot,
component references, lifecycle, freshness and policy objects, followed by a
root manifest binding their hashes. Repeating identical publication returns the
same hash. Different content under one identity is rejected, and interrupted
publication leaves no partial valid bundle.

The pointer-only index stores no copied scores. History remains, in newest-first
order, `SYN-PUB-006` through `SYN-PUB-001`. Stale, suspended and retired bundles
remain historically retrievable, while latest-valid selection remains
`SYN-PUB-003`. Rejected cycles or invalid hashes cannot alter the latest pointer.

## Freshness and supersession

Freshness uses an explicitly supplied evaluation instant—never wall-clock now.
Exactly 60 minutes after the knowledge cutoff is `CURRENT`; one second later is
`AGING`. Explicit supersession is `SUPERSEDED`; later corrections are `STALE`;
missing calendar state is `CALENDAR_UNKNOWN`; blocked quality is `DATA_BLOCKED`;
and a clock before availability is `NOT_YET_AVAILABLE`.

Filesystem modification times are not used. Historical stale evidence remains
queryable but cannot become a current decision.

## `NO_DECISION` gate

Every synthetic snapshot returns exactly:

`NO_DECISION — SYNTHETIC_NONCANONICAL_EVIDENCE`.

The gate also retains named reasons for stale evidence, blocked quality,
inactive lifecycle, low confidence, unresolved terminal economics, unavailable
calibration, provenance mismatch and multiple-testing failure. No
ACCUMULATE/HOLD/REDUCE/AVOID rules were added; a score alone cannot decide.

## Read-only facade

The bounded application facade can list summaries, retrieve exact history or
the latest valid snapshot, and expose stored score definition, expected outcome
and interval, probability, confidence limits, lifecycle, freshness, component
evidence, provenance IDs and the `NO_DECISION` explanation.

It imports no scoring/fitting functions and cannot recompute values, change
lifecycle, write artifacts, execute SQL, open arbitrary paths, access providers
or brokers, or return raw payloads/private paths. Identifiers and pagination are
bounded. Returned objects are frozen and component maps are read-only.

No Streamlit or version2.0 code was changed.

## Adversarial and incremental results

Nineteen named publication/read failures close safely, covering source and
published-object mutation, manifest/component loss, schema/semantic errors,
synthetic misclassification, range/type errors, recomputation, stale display,
cycles, partial bundles, traversal, SQL/write attempts and secret leakage.

Seven incremental changes—source observation, calibration, confidence,
lifecycle, calendar, publication policy and presentation schema—equal clean
rebuilds. The ledger records 52 causal rebuilds and 214 hash-verified reuses;
all unaffected bundle hashes remain unchanged.

## Verification

- Direct R.10F tests: 34 passed.
- Static R.10F evidence tests: eight passed (42 combined R.10F tests).
- Focused R.10A–R.10F regression: 210 passed.
- Separate `Data test` regression: 289 passed using a repository-local pytest
  temporary directory; an initial attempt using the Windows user-temp directory
  was blocked by host filesystem permissions before 35 fixture setups.
- Evidence package: 49 JSON files, approximately 126 KB; 48 manifest-bound
  artifact hashes and six complete bundles.
- Strict JSON, nested bundle manifests and all hashes reconcile.
- R.10A holdout remains `UNCONSUMED_SYNTHETIC_HOLDOUT`.
- R.10A–R.10E roots, momentum definition and golden fixture remain unchanged.
- No real/private data, network, broker, APSW production adoption, interlock
  change, UI integration, score publication or recommendation was added.
- An additional unrestricted root-suite diagnostic completed with 654 passed,
  four skipped and nine legacy governance failures. Eight failures deliberately
  detect that the last owner-reviewed research-state fingerprint predates the
  R.10 synthetic work; the remaining entrypoint-inventory failure also lists
  earlier R.9J–R.10E tools, so it was already broader than R.10F. These records
  were not rewritten and no replacement PDF was authorized by this task.

## Limitations

- The index is an intentionally small in-memory pointer model; durable workflow
  storage can later use the approved SQLite catalog without storing quantitative
  truth.
- Synthetic dates, scores and freshness are engineering fixtures, not market
  facts.
- The read facade is not connected to any UI or production application.
- Canonical import, real-data quality and decision policy remain separately
  blocked by existing governance.

## Next task

Proceed to `SYNTHETIC_MANDATE_AND_PORTFOLIO_DECISION_POLICIES`: holdings,
mandates, deterministic accounting, risk constraints and continued
`NO_DECISION`, without optimization or real recommendations.

Before any real/private-data transition, genuine analysis, score publication,
UI integration, APSW adoption or interlock change, stop for the consolidated
PDF and explicit owner authorization.

`SYNTHETIC_EVIDENCE_PUBLICATION_VALIDATED_NONCANONICAL`
