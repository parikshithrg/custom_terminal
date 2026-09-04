# R.9I - Pre-Research Status PDF v5

## Outcome and scope

`PDF_V5_GENERATED_AWAITING_OWNER_REVIEW`

Generated a 10-page owner-readable report through R.9H. This is
`NON_APPROVAL_REPORT_GENERATION`, not implementation, an owner-review record,
approval issuance or audit execution. All implementation and execution authority
remains false. The PDF skill guided deterministic generation and visual
inspection of every page using the existing generator without modifying it.

## Baseline verified before authoring

- HEAD and origin/main: `d1f1995d92acd55318310812fa24889a30367f51`.
- Working tree: clean.
- Proposal manifest SHA-256:
  `a6529ec14520d163e327e2dcc7a7f469ea473d14b8d39e3ede345bc3d49dcdc1`.
- Package-content SHA-256:
  `628be5879d34a0a2f7c53ca493279c0a797f4ad45575988083d58e7b27f2945f`.
- Research fingerprint:
  `1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`
  over 252 files, unchanged after report generation.
- PDF v4 remains byte-exact and correctly historical/stale after R.9H.
- R.9F anchor and binding proposal, previous PDFs and protected research
  artifacts reconciled with existing checks; no baseline mismatch.
- `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` remains active.

Read the complete ten-object R.9H package, its report, canonical Stage 1-3
scope, v4 Markdown, generation manifest and owner-review record. Only tracked
sanitized evidence was used. The current stale v4 record hash differs from the
pre-R.9H historical hash referenced inside the proposal by design. Both are
preserved; the v5 manifest binds the current record bytes without rewriting
the historical reference.

## Added files

- `docs/project_status/market_system_status_pre_research_review_v5.md`
- `docs/project_status/pre_research_generation_manifest_v5.json`
- `output/pdf/market_system_status_pre_research_review_v5.pdf`
- `tests/test_research_r9i_pdf_v5.py`
- `reports/RESEARCH_R9I_REPORT.md`

Changed `.gitattributes` only to preserve exact v5 Markdown and manifest bytes
across Windows checkouts. No broader line-ending rule was changed.

No v5 owner-review record was created. No source, specification, proposal,
previous PDF, approval template or fingerprint exclusion was changed.

## Exact generated output

- Page count: 10.
- PDF SHA-256:
  `44502aa44d45ac666d4c849de00a62bae6d6fb5864014fa0214e92621fef46dd`.
- Markdown SHA-256:
  `35aade76d7560abe849404772857478e0a36ecd93c3cdbf1c2776092bc33dedf`.
- Unchanged generator SHA-256:
  `fa3f68a85d0a6a2f8548492d4df387b50937e0f621f05cec8c3a1d43bb3ecb83`.

The generation manifest binds exact source, generator, prior PDFs, R.9F,
R.9H, scope, fingerprint-policy and production-interlock evidence hashes.
It is not a permission object. Current report-only additions fall outside the
existing research fingerprint rules; those rules were not altered.

## Six decisions remain unresolved

1. Quiescent/no-sidecar target versus a fully reviewed sidecar set. Proposed:
   prefer the simplest no-sidecar policy only if synthetic engineering evidence
   can establish and maintain quiescence. Do not repair/checkpoint the target.
2. Real database-byte cap versus explicitly weaker measurable budgets.
   Proposed: retain the blocker and investigate exact semantics/enforcement on
   synthetic inputs. Bytes, pages, statements and rows are not interchangeable.
3. Explicit versus derived attempt ID. Proposed: explicit sealed ID plus
   durable uniqueness, subject to synthetic replay/concurrency/crash tests.
4. Exact EXPLAIN QUERY PLAN necessity. Proposed: none unless a Stage 1-3 need
   is shown; any formal scope narrowing needs separate specification review.
5. Declared versus enforced process-resource limits. Proposed: do not accept
   unspecified unenforced limits; investigate enforcement and residual risk.
6. Future one-use audit permission. Proposed: defer until after separately
   approved implementation, review and a current report. No immediate audit
   approval is requested.

Every recommendation is explicitly `PROPOSED_NOT_APPROVED`. Questions 1-5
affect the implementation contract; question 6 is a later issuance/execution
gate, not an authorization being solicited now. The PDF supplies options,
trade-offs, evidence requirements and blockers, plus nine numbered owner
questions separating summary confirmation, policy, technical evidence and a
specific future-task request. Answers are not pre-filled.

## Newly observed verification

Commands below ran in the root unless noted. Root Python is the existing
`.venv`; the PDF tools use the bundled Python with ReportLab and pypdf, not
new project dependencies.

| Command / check | Observed result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests/test_research_r9h_boundary_proposal.py -q` before authoring | 9 passed; baseline hashes, fingerprint, templates and interlock reconciled |
| `.\.venv\Scripts\python.exe -m pytest tests/test_research_r9i_pdf_v5.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9g_owner_review.py -q` | 22 passed |
| `.\.venv\Scripts\python.exe -m pytest -q` after focused tests added | 390 passed, 3 skipped, 2 warnings |
| From `Data test`: `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --basetemp '..\.pytest_tmp\data_test_r9i' --junitxml '..\.pytest_tmp\data_test_r9i.xml'` | 289 tests, 0 failures/errors/skips, verified from JUnit XML |
| JSON parse of `git ls-files -- *.json` plus new v5 manifest | 102 valid, 0 invalid |
| `.\.venv\Scripts\python.exe -m compileall -q src tools tests` | Passed |
| `git diff --check` and staged whitespace check | Passed |

The three skips are the established Windows symlink-creation limitations in
R.9B/R.9F tests, not exclusions added here. The two root warnings are established
development-only noncanonical-output warnings from the fixture manifest tests.
Data test also prints a SWIG deprecation warning. No live market research was
performed; the requested suites exercise synthetic/offline fixtures only.

Historical comparison only: R.9H recorded root 382 passed / 3 skips, Data test
289 passed, and 101 valid JSON files. These are distinguished from the new
R.9I results above.

### PDF QA

Used bundled Python to run `tools/generate_project_status_pdf.py --source
docs/project_status/market_system_status_pre_research_review_v5.md --output
output/pdf/market_system_status_pre_research_review_v5.pdf`. Repeated with
output `tmp/pdfs/r9i/repeat.pdf`; both SHA-256 hashes matched exactly.

Rendered with bundled Poppler:
`pdftoppm -r 100 -png output/pdf/market_system_status_pre_research_review_v5.pdf tmp/pdfs/r9i/page`.
All ten page images were inspected: readable text, intact tables and hashes,
no clipping, broken glyphs or accidental blank pages. Poppler emitted missing
display-font alias warnings for unused fonts; rendered report text was intact.
pypdf extraction confirmed ten nonempty pages and more than 20,000 characters.
Extracted text and the report/manifest passed private-location and
credential-pattern checks; no private configured value was read for comparison.
Only R.9I-generated temporary render files were removed after inspection.

### Safety and preservation

Existing R.9H adversarial tests still reject the unusable approval template and
the production entry point before configuration or connection. New focused
tests bind all report inputs, all-false authority, six decision sections, nine
unanswered owner questions, privacy patterns, page count and unchanged
fingerprint. No new production entry point exists: the scoped diff adds only
documents, a PDF, a generation manifest and offline report tests.

No private database bytes were read or sampled; no configured path value or
private runtime binding contents were read. No production SQLite connection,
SQL, schema inspection, rows, audit, approval issuance/registration/consumption,
acquisition, broker access, market analysis, scoring, simulation, backtesting,
recommendation or trading occurred as task work. Prior evidence and the
momentum hypothesis/golden fixtures/manifests remain untouched.

## Stop and next action

Owner reviews PDF v5. The single recommended subsequent task is
`BOUNDED_SYNTHETIC_BOUNDARY_DESIGN_INVESTIGATION_ONLY`, separately authorized
after that review. It is not authorized by this report. Free lawful alternatives
including NSE F&O bhavcopies remain candidates, not acquisition permission or
proof of research fitness. No implementation or approval recording follows now.

`PDF_V5_GENERATED_AWAITING_OWNER_REVIEW`
