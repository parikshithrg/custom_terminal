# Permanent Pre-Research Owner-Review Gate

## Boundary

Every future market-research family must bind a current owner-reviewed project
status PDF before its preregistration can lock. The gate is checked again in
side-effect-free preflight and immediately inside the governed gateway before
any attempt directory or runner invocation.

The gate applies to market analysis, hypothesis evaluation, simulation,
backtesting, parameter sweeps, placebo tests and empirical research. Explicit
`INFRASTRUCTURE_CANARY` and `SYNTHETIC_TEST` families are exempt because they
contain no market evidence and remain nonpromotable. The completed R.6 canary
is therefore not retroactively invalidated.

## Required evidence

- Exact PDF and source paths and SHA-256 values.
- Summarized source commit and PDF generation timestamp.
- Deterministic research-state fingerprint.
- Complete rendered-page verification.
- Explicit post-generation owner approval identifying the report and scope.
- Exact covered scope repeated in the preregistration.
- Current, non-superseded review status.
- The same review binding repeated in the separate run approval.

Missing, pending, changed, stale, superseded, predated, scope-mismatched,
generic conversational or synthetic approval fails closed.

## Fingerprint and self-reference

The fingerprint uses canonical path, byte-size and SHA-256 rows for 229 current
research-relevant files. Included categories are research/simulation source,
contracts, specifications, data-trust declarations, proposals, governance
policies, tracked evidence anchors, the architecture source of truth and the
milestone reports that define scientific scope.

The PDF, its maintainable presentation source, review record, R.7 completion
report, mechanical PDF artifacts, tests, caches and README are excluded. This
prevents unavoidable self-reference and ensures an ordinary documentation-only
change does not stale the report. Any included substantive change changes the
fingerprint and requires a new PDF and review.

## Separation of approvals

The successful report-gate state is named
`RESEARCH_EXECUTION_PERMITTED_BY_REPORT_GATE`, but its returned contract states
`research_execution_authorized=false` and
`separate_run_approval_required=true`. It means only that a separately reviewed
proposal may proceed through the existing governance process. It does not
authorize acquisition, analysis, backtesting or execution.

The current v1 record remains `REPORT_GENERATED_PENDING_REVIEW`; all research
remains blocked.
