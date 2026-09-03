# Research R.9C - Pre-Research Status PDF Version 2

## Baseline and boundary

R.9C began from clean, synchronized commit
`a87cedc7ad5db14adaba0661bf44fd3346e399ab`. The research-state fingerprint
was and remains
`9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31`
across 231 research-relevant files.

The public `version2.0` reference repository was checked read-only. Its
`master` branch remains at commit
`f9a6eaec2cab1dd9e85d284e48b9863cae0b1298`, tree
`ad3c21fb2244f0acd7680bd0bdc4958d2516b16f`. It was not cloned, executed,
copied, or integrated.

No production F&O locator was enabled or resolved. The real database was not
located, opened, hashed, inspected, or queried. No audit approval was created,
registered, sealed, or consumed. No audit or market research was executed.

## Generated evidence

- Source: `docs/project_status/market_system_status_pre_research_review_v2.md`
- Source SHA-256: `dc47a7e51b821711987cafba66b403d787d58841c9e79d48b09031abd0890284`
- PDF: `output/pdf/market_system_status_pre_research_review_v2.pdf`
- PDF SHA-256: `765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf`
- Generation timestamp: `2026-09-03T02:28:47.0007235Z`
- Page count: 17 A4 pages
- Visual result: `PASS_17_PAGES_NO_MATERIAL_DEFECTS`

All 17 rendered pages were inspected. There are no material clipping,
overlap, blank-page, broken-glyph, table, pagination, or margin defects. PDF
text and geometry checks confirmed that apparent cropping in one image preview
was a preview-display artifact rather than a PDF defect.

## Review lifecycle

The reviewed v1 PDF remains byte-identical at SHA-256
`cbd1b504a5526f294d359b3949822bb30f313a5a18305270e8761b7868372b6c`.
Its record preserves the historical owner approval and later staleness, and now
identifies v2 as its successor.

The v2 record begins in `REPORT_GENERATED_PENDING_REVIEW`. All seven reviewer
answers and every approval field are null. Its only covered future scope is
`FNO_PRODUCTION_ENABLEMENT_DESIGN_AND_SYNTHETIC_TESTING`. The normal review
validator rejects the record while it is pending. Even an eventual PDF review
could approve only the covered design phase; it cannot authorize an audit run.
A separate exact, registered, one-use local-data-audit approval remains
mandatory for any later execution.

## Verification

R.9C adds focused offline tests for v1 preservation and supersession, v2 hash
and fingerprint bindings, pending-review rejection, unanswered reviewer fields,
scope boundaries, production-locator rejection, audit-approval separation, PDF
content and structure, and protected evidence.

The completion verification includes the focused R.9C suite, combined R.7-R.9C
governance tests, complete root and Data-test suites, JSON parsing, PDF
structural and visual checks, Python compilation, research-state fingerprint,
entry-point reconciliation, secret scan, protected-evidence comparison, and
Git whitespace validation.

Final results:

- Focused R.9C: 10 passed.
- Combined R.7-R.9C: 91 passed, 2 skipped because Windows symlink creation is unavailable.
- Complete root suite: 304 passed, 2 skipped, 2 expected development-only warnings.
- Separate Data-test suite: 289 passed; only pre-existing dependency and development-only warnings.
- JSON parse validation: 79 valid, 0 invalid outside ignored runtime/artifact directories.
- PDF structure: 17 nonblank A4 pages; bounds passed; no encryption, forms, or JavaScript.
- Python compilation: passed.
- Entry-point inventory: passed.
- Secret-pattern scan: 0 credential-pattern hits.
- Protected research/evidence diff: 0 changed paths.
- Research fingerprint: exact, 231 files.
- `git diff --check`: passed (line-ending notices only).

## Stop state

R.9C prepares review evidence only. Production enablement, real database access,
audit approval, audit execution, market-row inspection, analysis, simulation,
backtesting, scoring, recommendations, broker actions, and trading remain
prohibited.

PRE_RESEARCH_PDF_V2_READY_FOR_OWNER_REVIEW
