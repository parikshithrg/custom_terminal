# R.9N - Restricted APSW adversarial validation

**RESTRICTED_VFS_ADVERSARIAL_EVALUATION_RECORDED_PRODUCTION_BLOCKED**

## Decisions

| Area | Conclusion | Boundary |
| --- | --- | --- |
| Scoped logical read budget | DEMONSTRATED_WITH_LIMITATIONS | Three finite layouts; reservation before delegation; sticky failures; not whole-process/physical I/O |
| Cursor/row/output controls | DEMONSTRATED_WITH_LIMITATIONS | Iteration and cumulative limits; injected-clock deadlines; cooperative checks, not hard real time |
| Restricted access | DEMONSTRATED_WITH_LIMITATIONS | Exact facade templates, authorizer, one connection, no mapped/temp/sidecar support; full sidecar-path coverage INCONCLUSIVE |
| Official F&O schema provenance | INCONCLUSIVE | PENDING_OFFICIAL_FORMAT_EVIDENCE; no authoritative fields or types inferred |
| Production readiness | NOT_TESTED | Interlock unchanged; no adoption, production integration or real data |

Recommendation: **prepare an updated owner decision report before any adoption
or production implementation is proposed**. Do not automatically begin that task.
These results support review of a restricted candidate, not production approval.

## Baseline, authority and preservation

Started at clean fcddaa3. Read the R.9M source, tests, report, owner scope and
manifest. Candidate APSW 3.53.4.0, SQLite 3.53.4, Python 3.14.6. Wheel hash
13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5
matches R.9M. Reused only the ignored isolated environment. No new package,
native VFS, driver or system-policy change. This R.9N brief is new bounded
authority; the R.9M authorization is historical and completed.

Baseline selected preservation tests: 26 passed. No private configuration,
runtime binding or real database opened. No market records/current lists
acquired. Production packages, dependencies, PDFs, approvals and prior immutable
evidence remain unchanged. R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE persists.
No applicable AGENTS.md found in the repository.

Root installed-distribution inventory hash before/after:
27fd4f9f7952c7b8b172b180a52357a8eedd0f0d868b46e7686fa90194ced386.
Root environment still contains no APSW. This inventory measures names/versions,
not every environment file byte; dependency-file hashes are checked separately.

## Contract: exactly what is metered

One attempt begins before its single read-only open and ends at close or failure.
Opening/header reads and fixed cache setup reads count. Permitted statements
share one cumulative meter. Reservation precedes the underlying xRead call.

- Requested: all xRead lengths asked for, including refused requests.
- Reserved: full admitted lengths; no refund after short reads/errors.
- Delegated: lengths passed to the underlying read, including erroring calls.
- Returned: actual byte-string lengths obtained, including a short result before
  rejecting it. An exception returns no bytes to this counter.

Repeated offsets cost again. Failure clears buffered output and is sticky;
supported APIs cannot reset/reopen a failed or closed attempt. A second native
connection using its VFS is rejected. A new Attempt is a distinct experiment,
not resumption of consumed authority. Hostile same-process mutation is excluded.

Fixture creation, hashes, directory checks, controls and imports are outside
the meter. Scoped logical requests are not physical disk I/O, OS-cache traffic
or a whole-process quota. Read-byte limits are supplemented, not replaced, by
row/deadline/output limits. No temporary-storage quota was established.

## Matrix and measured results

The plan preceded execution. Generic fixtures have 35 tables with synthetic
names/values. Sizes: 36,352 / 49,152 / 159,744 bytes for page sizes 512 / 1024 /
4096. No fixture exceeds 256 KiB. Each result binds its exact synthetic main-file
hash; source/runtime/scope and expected/observed results are recorded separately.

| Page size | Observed successful budget | Exact | One below | Fetch-failure rows already seen |
| --- | --- | --- | --- | --- |
| 512 | 36,468 | 35 rows | 0 published | 1 |
| 1024 | 25,716 | 35 rows | 0 published | 3 |
| 4096 | 28,788 | 35 rows | 0 published | 12 |

Thresholds come from the adequate native observation for each layout, not the
R.9M 4,212-byte value. Zero and insufficient budgets reject before exceeding
reservation. Multiple catalog statements share the budget; a second statement
fails at the first-query budget and publishes nothing. With sufficient budget,
two statements return 70 rows. A cumulative 40-row limit detects row 41 and
discards everything. The detector can fetch one excess row but never accepts or
publishes it. An 11,000-byte output limit fails during the second statement;
bounded serialized accumulation never exceeds that limit. Output accounting
includes JSON brackets/separators, not Python allocator overhead.

The initial exploratory run found no fetch-phase read because all catalog pages
remained cached. It failed its assertion rather than being reported as a pass.
Fixed PRAGMA cache_size=2 was then added only to the synthetic prototype, forcing
the intended fetch path without changing production or widening SQL support.
The final 46-case matrix replayed exactly in native regression tests.

Native malformed/truncated files fail; short underlying data never becomes a
completed output. Direct same-offset native file reads reserve 16+16 bytes;
next read and continuation after failure refuse further delegation. Injected
underlying error and short-read probes retain 16 reserved bytes, returning 0
and 15 respectively. Those two are **mocked underlying responses**, not claims
of induced OS failure. Execute/fetch expiry uses an **injected clock/deadline**
around real SQLite iteration. No whole-process hard-deadline proof is claimed.

## Access enforcement and limits

The public experimental facade accepts only catalog/columns template keys, not
arbitrary SQL. Native authorizer challenges reject app-table SELECT, ATTACH,
CREATE TEMP and mmap requests. Read-write/create connections are refused by
the VFS. Temporary, WAL and journal xOpen probes are direct-method tests.
The helper is not a hardened security product; internal connection access used
for challenge injection is outside its facade and hostile-code model.

Actual native writer fixtures generated active WAL and rollback journals. The
candidate refused them during preflight, before its SQLite connection opened.
Thus **native SQLite sidecar xOpen coverage was not reached**. No direct xOpen
test is promoted to comprehensive sidecar coverage. Generating/closing these
disposable writer fixtures is outside the candidate; no target was repaired
and no real database was checkpointed. R.9M mapped-control/source findings are
reused, unchanged: plain proxy exposes no xFetch or xShm interface. This is
support exclusion, not metered mmap/WAL operation.

Namespace replacement, transient sidecars, writer exclusion, preexisting mappings,
same-process hostile code and other host behavior remain unresolved. No Windows
Job Object integration or earlier containment workloads were repeated. The
external 30-second subprocess timeout is a safety bound, not a production
process-tree guarantee. All test subprocesses exited normally.

## Official documentation and synthetic-schema provenance

Only the known official landing page was requested:
https://www.nseindia.com/static/resources/forms-formats-members

Ordinary request with a 20-second timeout returned ReadTimeout, no HTTP status
or response body. Retrieval attempt time is in official_format_evidence_v1.json.
No format/version/effective date, document hash or field definitions are available.
No access-control bypass or guessed URL was used. No market data acquired.

Status: **PENDING_OFFICIAL_FORMAT_EVIDENCE**. R.9N uses clearly generic_id and
generic_value columns, not purported F&O parity. R.9M's historical seven-column
MII finding is preserved. No new F&O recipe is manufactured. Once documentation
is available, CSV fields/types must be documented separately from locally chosen
SQLite representations; official CSV types do not mandate SQLite column types.

## Verification and artifacts

Native command, using the already installed isolated candidate:

```
artifacts/r9m_evaluation/venv/Scripts/python.exe -m tools.r9n_regression
```

Executed through subprocess.run(capture_output=True, timeout=30): **4 passed**,
including an exact replay of 46 recorded cases and three cumulative-control
tests. Native tests are explicit, not silently skipped under root discovery.

Static/offline command:

```
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9n_adversarial.py tests/test_research_r9m_vfs_evaluation.py tests/test_research_r9l_pdf_v6.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9i_owner_review.py -q
```

**34 passed**. Source/result/manifest JSON and hashes, protected-file diffs,
private-location/secret patterns and whitespace checks passed. No unrelated
root/Data test suites were run. Historical counts remain historical.

New artifacts: docs/investigations/r9n/EXPERIMENT_PLAN.md, results_v1.json,
supplemental_results_v1.json, official_format_evidence_v1.json, manifest_v1.json;
tools/r9n_adversarial.py; tools/r9n_regression.py;
tests/test_research_r9n_adversarial.py; this report; narrow .gitattributes rules.
Result JSON is normalized captured stdout, not an original network payload.

All temporary fixture roots were removed by their scoped TemporaryDirectory
contexts, including assertion-failure cleanup. The isolated dependency itself
is retained ignored for reproducibility. No running experimental workers remain.

Mechanical research fingerprint remains
1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef
(252 files). No exclusions changed. PDF v6 does not summarize R.9M/R.9N despite
fingerprint equality. No PDF or owner approval generated or rewritten.

**RESTRICTED_VFS_ADVERSARIAL_EVALUATION_RECORDED_PRODUCTION_BLOCKED**
