# R.9L - Owner decision brief and PDF v6

## Outcome and scope

**PDF_V6_GENERATED_AWAITING_OWNER_ARCHITECTURE_DECISION**

Five-page owner brief prepared from tracked sanitized evidence only. The PDF
skill supplied the deterministic rendering and page-by-page visual QA workflow.
No experiment, dependency evaluation/installation, production implementation,
private configuration/runtime artifact read, real database access, sampling,
audit, acquisition, broker access or market research occurred. No approval or
execution authority was created. version2.0 remains separate and noncanonical.

## Baseline and preservation

Inspected clean main at `846f28fe740841c3e58de9caa2842b1a062d18de`.
Recent commits: 846f28f (CRLF evidence rule), dd695fe (R.9K), 4611d7e (R.9J).
No applicable AGENTS.md found in repository or ancestors. Read complete R.9J
and R.9K reports, assessments, manifests and the v5 owner-review record.

The 27 source/artifact bindings in the R.9J source/completion and R.9K manifests
matched, as did R.9J's result hash. Existing review/protection checks verified
v1-v5 PDFs, the v5 historical review, R.9F binding and R.9H proposal evidence.
The production source and R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE interlock
remain unchanged. No research fingerprint exclusion changed: the fingerprint
remains 1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef,
252 files. Equality does not make v5 a summary of R.9J/R.9K.

The v6 generation manifest binds the new summary/PDF/generator and explicitly
binds both investigations and their relevant evidence. Earlier records retain
their original authority; no v6 review record exists. The new report does not
mutate the earlier generation manifest or infer further authority from v5.

The only whitespace override remains scoped to the exact R.9K raw-result file:
it recognizes preserved CRLF while retaining blank-at-eol, blank-at-eof and
space-before-tab checks. New narrow -text rules preserve hashed v6 artifacts;
they do not disable whitespace checks. Prior raw payloads were not normalized.

## Findings and proposed decision

R.9J durable synthetic consumption/replay evidence and R.9K main-file sharing,
fixed process-tree cleanup and per-process committed-memory enforcement are
useful but bounded. Mocked job-creation failure is distinct from native tests;
source inspection is distinct from empirical I/O interception. None proves
a filesystem/network sandbox, complete quiescence, aggregate memory control or
hard real-time behavior.

The approved stack cannot enforce target-specific logical database-read bytes.
Sidecars/namespace, temporary-storage quota, returned rows, fetch deadline,
exact SQL templates and sealed attempt ID remain unresolved independently.
Resource protection, exposure restriction and audit scope require distinct
controls; row/time/output limits are not an equivalent byte cap.

Proposed option A: a separately authorized bounded synthetic-only evaluation
of a maintained VFS-capable approach, only if the owner accepts evaluating a
new dependency. No library selected. Evaluate read interception, mapped access,
sidecars and fail-closed exhaustion; a no-go outcome remains valid. Otherwise
recommend option C, deferral. Option B requires a separate explicit requirement
decision; weaker guarantees have not been accepted. No market recommendation.

The PDF contains four unanswered owner questions. Evaluation authorization
must be distinguished from dependency adoption, production implementation and
audit execution. Stop for the owner's decision.

## Files

- docs/project_status/market_system_status_pre_research_review_v6.md
- output/pdf/market_system_status_pre_research_review_v6.pdf
- docs/project_status/pre_research_generation_manifest_v6.json
- reports/RESEARCH_R9L_REPORT.md
- tests/test_research_r9l_pdf_v6.py
- .gitattributes: narrow byte-preservation rules only.

## Verification commands and results

Baseline focused checks: **20 passed**. Final static/offline selection:

```
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9l_pdf_v6.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9i_pdf_v5.py tests/test_research_r9i_owner_review.py -q
```

Result: **28 passed, 0 skipped**. These inspect reports, hashes, policy and
unusable approval examples; the interlock test substitutes a connection trap
and confirms zero calls. No native containment experiments or broad root/Data
test suites were rerun. R.9J's 91 passed/3 skipped and R.9K's 25 passed/0 skipped
are historical counts only.

Using the existing bundled Python (no installation), rendered twice:

```
python tools/generate_project_status_pdf.py --source docs/project_status/market_system_status_pre_research_review_v6.md --output output/pdf/market_system_status_pre_research_review_v6.pdf
python tools/generate_project_status_pdf.py --source docs/project_status/market_system_status_pre_research_review_v6.md --output tmp/pdfs/r9l/repeat.pdf
pdftoppm -r 95 -png output/pdf/market_system_status_pre_research_review_v6.pdf tmp/pdfs/r9l/page
```

Both render byte streams identical. All five rendered pages inspected: readable
text and tables, no clipped content, overlaps or broken page transitions.
Poppler emitted missing display-font configuration warnings for unused font
families; the rendered Helvetica/Courier content showed no material defect.
Extracted PDF text and new report/manifest checked for private locations and
secret assignment patterns: PASS. This is a bounded content scan, not a claim
of universal secret detection. Relevant JSON parsed and hashes reconciled.

PDF SHA-256:
`a23a89c4590688185955231f82f597243a6db2805acdfc0a6c2be3f4c0c3c04d`.

Git checks: `git diff --check`, `git diff --cached --check`, and protected-path
diffs against 846f28f. Only the six named deliverables are staged. No prior
PDF, investigation, proposal, binding, production source or specification changed.
Temporary duplicate PDF/page renders are QA intermediates, not committed evidence.

**PDF_V6_GENERATED_AWAITING_OWNER_ARCHITECTURE_DECISION**
