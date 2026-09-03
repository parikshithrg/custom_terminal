# Research R.9G - Pre-Research Status PDF Version 4

## Outcome

Research R.9G generated a deterministic, owner-readable version 4 status PDF
from the tracked sanitized R.9F evidence. The report is for human review only.
It records no owner approval, changes no production interlock, creates no
database or audit authority, and performs no database, market, research,
scoring, simulation, backtesting, broker, recommendation, or trading action.

Lifecycle result:

`PDF_V4_GENERATED_AWAITING_OWNER_REVIEW`

## Baseline and evidence inputs

- Baseline branch: `main`.
- Baseline and summarized source commit:
  `b658033f7acf0fdc206831cedc5ef374c043e27d`.
- Baseline working tree: clean and synchronized with `origin/main`.
- Research-state fingerprint:
  `6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db`
  over 242 files.
- R.9F anchor:
  `evidence/fno_locator_binding_v1/anchor.json`, SHA-256
  `115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc`.
- R.9F binding proposal:
  `proposals/fno_locator_binding_v1/binding_proposal.json`, SHA-256
  `995524b670dc95b717fa7d4b27935c788d661bcf75b8f7f4400d76831a8f434f`.
- R.9F sampled-identity root:
  `b1b8c0ca1338d477987da28e6d9647b151c120a0eac7bb17c9e9293edfd4bc47`.
- PDF v3 remained byte-exact at
  `75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2`.
- The ignored private R.9F artifact was checked only for presence and Git-ignore
  status. Its contents were not read. The private database was not accessed.

## Files created or changed

Created:

- `docs/project_status/market_system_status_pre_research_review_v4.md`
- `output/pdf/market_system_status_pre_research_review_v4.pdf`
- `docs/project_status/pre_research_generation_manifest_v4.json`
- `tests/test_research_r9g_pdf_v4.py`
- `reports/RESEARCH_R9G_REPORT.md`

Changed:

- `tools/generate_project_status_pdf.py`

The generator now enables ReportLab invariant mode in both the process-wide
configuration and canvas construction. Two independent renders of the v4
source produced identical PDF bytes.

No `pre_research_review_record_v4.json` was created. The new manifest is
explicitly classified as `NON_APPROVAL_REPORT_GENERATION` so it cannot be
mistaken for owner approval.

## PDF result

- Filename:
  `output/pdf/market_system_status_pre_research_review_v4.pdf`.
- PDF SHA-256:
  `02a76f6d46bc74a69b7f0b10331ae26da1d07d60934091ce9d31c0abe8cdaec9`.
- Markdown SHA-256:
  `0c03197df4f3c6ef85112c407efe4f1321a8fcf509e962ac4c7edc5ec12bbab0`.
- Generation-manifest SHA-256:
  `e831d6c85651d3f5373c1e9e364d844c2fe955659a9a745efbcfd2cc74ee4148`.
- Page count: 14 A4 pages.
- PDF state: valid header/trailer, unencrypted, no form or JavaScript.
- Deterministic rendering: passed; two independent outputs had the same
  SHA-256.

The report explains the project objective, cautious evidence policy, completed
work, current evidence status, exact R.9F filesystem result and limitations,
unchanged safety boundary, proposed multi-approval sequence, and seven numbered
questions for the owner.

## Visual verification

Every page was rendered to PNG at 120 DPI and inspected. Result:

`PASS_14_PAGES_NO_MATERIAL_DEFECTS`

Typography, margins, headings, tables, page breaks, headers, footers, page
numbers, and glyphs were readable and consistent. There was no clipping,
overlap, broken table, orphaned heading, accidental blank page, or visible
private path. The split status table repeats its header correctly on page 8.

## Verification results

Successful commands and outcomes:

- Focused R.9G:
  `.\.venv\Scripts\python.exe -m pytest -q tests\test_research_r9g_pdf_v4.py`
  - 9 passed.
- Combined R.7-R.9G governance and boundary suites:
  `.\.venv\Scripts\python.exe -m pytest -q` with the nine explicit R.7-R.9G
  test modules.
  - 155 passed, 3 skipped for unavailable Windows symlink creation.
- Complete root suite:
  `.\.venv\Scripts\python.exe -m pytest -q`
  - 368 passed, 3 expected Windows symlink skips, 2 established
    development-only warnings.
- Separate Data-test suite, run from `Data test` with a repository-local ignored
  temporary directory:
  `..\.venv\Scripts\python.exe -m pytest -q --disable-warnings --basetemp '..\.pytest_tmp\data_test_r9g_xml' --junitxml '..\tmp\pdfs\r9g\data_test_results.xml'`
  - 289 passed, 0 failed, 0 errors, 0 skipped.
- Entrypoint reconciliation suite:
  `.\.venv\Scripts\python.exe -m pytest -q tests\test_research_r4_approval.py`
  - 25 passed.
- JSON parsing:
  - 90 valid, 0 invalid.
- Python compilation:
  - `src`, `tools`, and `tests` passed.
- Research fingerprint reconciliation:
  - exact match, 242 files.
- Private-path, user-home, and credential scan of v4 source, manifest, extracted
  PDF text, and its tracked R.9F report input:
  - passed with no matches.
- Protected evidence:
  - PDFs v1-v3, R.9F anchor, and R.9F proposal remained byte-exact.
- Git whitespace validation:
  - passed; only the established Windows LF-to-CRLF notice was emitted.

Two preliminary Data-test invocations did not represent code failures: the
first was launched from the repository root and could not resolve the separate
`dtest` package; the second used the system pytest temporary directory, which
the sandbox could not access. The documented separate working directory plus
the repository-local ignored temporary directory produced the clean 289-test
result above.

## Production and authority state

The local F&O database remains:

`LOCATED_AND_SAMPLED_NOT_QUALIFIED`

The production interlock remains unchanged:

`R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`

The following remain false:

- `owner_review_recorded`
- `interlock_change_authorized`
- `database_connection_authorized`
- `audit_authorized`
- `market_row_access_authorized`
- `analysis_authorized`
- `scoring_authorized`
- `backtesting_authorized`
- `trading_authorized`

R.9G did not repeat the sampled-identity pass, read additional private database
bytes, connect to SQLite, execute SQL or PRAGMAs, inspect schema or rows, begin
an audit, or create an interlock-removal implementation.

## Owner answers required

The owner must review the generated PDF and answer all seven numbered questions
in order. The final question asks only whether the next task may prepare an
interlock-removal proposal, without changing the interlock or creating any
database, audit, market-row, analysis, scoring, simulation, backtesting,
recommendation, broker, or trading authority.

Stop state: `PDF_V4_GENERATED_AWAITING_OWNER_REVIEW`.
