# R.9J - Bounded Synthetic Boundary Design Investigation

## Outcome

**SYNTHETIC_BOUNDARY_INVESTIGATION_COMPLETED_PRODUCTION_BLOCKED**

The bounded investigation completed. It found genuine enforcement gaps rather
than evidence supporting production implementation. No real dataset was opened,
read, sampled, resolved or copied. No production code, interlock, approval or
entry point changed. This was infrastructure testing, not market simulation.

## Baseline, authority and instructions

Baseline: `db3d8727807336560c1401ecadc80b4415c79897`, clean tree before work.
No AGENTS.md was found in the repository or its ancestors. The R.9J attached
brief, exact PDF v5 review and existing pytest configuration governed this task.
The review authorizes BOUNDED_SYNTHETIC_BOUNDARY_DESIGN_INVESTIGATION_ONLY.

Baseline checks passed before execution:

- PDF v5: `44502aa44d45ac666d4c849de00a62bae6d6fb5864014fa0214e92621fef46dd`.
- Owner-review record: `22fb038ebd5a3f4c889198561547f2b28057d9a2012dbb0248fd058a92d90729`.
- R.9H manifest: `a6529ec14520d163e327e2dcc7a7f469ea473d14b8d39e3ede345bc3d49dcdc1`.
- Research fingerprint: `1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`, 252 files.
- Interlock: `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`.

Read existing synthetic catalog/identity/provenance code, durable registry and
boundary implementation, R.9B/R.9D boundary tests and R.9H/R.9I review tests.
Only these inspected, offline suites were selected for regression. No broad
root discovery or separate Data test run was used to recreate historic counts.

## Artifacts and reproduction

- `docs/investigations/r9j/EXPERIMENT_PLAN.md`: pre-execution matrix and limits.
- `tools/r9j_synthetic_boundary.py`: exploratory harness outside production packages.
- `tests/test_research_r9j_synthetic_boundary.py`: 11 regression tests, including
  explicit assertions that observed enforcement gaps remain honestly reported.
- `docs/investigations/r9j/results_v1.json`: first observed sanitized results.
- `docs/investigations/r9j/manifest_v1.json`: source, fixture and result bindings.
- `docs/investigations/r9j/assessment_v1.json`: resource classifications and six decisions.
- `docs/investigations/r9j/completion_manifest_v1.json`: complete deliverable hashes.
- This report. Narrow `.gitattributes` rules preserve new hashed artifact bytes.

Run from the repository using the existing environment:

```
.\.venv\Scripts\python.exe -m tools.r9j_synthetic_boundary
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9j_synthetic_boundary.py -q
```

The first evidence recording used the same module with `--record`. It refuses
to overwrite existing results; the plain command runs fresh synthetic fixtures
and prints observations without changing committed evidence. No database-path
argument or environment fallback exists. Generated fixtures and registries are
removed after the run. Timing, process counters and race winner may vary;
equivalent assertions, not byte-identical runtime observations, are expected.

Observed runtime: Windows 11 build 10.0.26200, Python 3.14.6, SQLite 3.50.4.
Initial target was 16,384 bytes with four catalog objects, a foreign key and
recognizable synthetic row sentinel. No real schema was used.

- Fixture recipe SHA-256: `9ae21fe22db802a42b862384440dcf70833ff6ceff5dcdfb780ac6f0df3b95d0`.
- Initial fixture SHA-256: `1de9c31488668346fcae982321aa36ecdf7879061e75e167d6a937ac15ed62a9`.
- Results SHA-256: `01c519fa2645bb14e719fdca16c137ac543c669f798b884ab2a49e28f52f8db7`.

## Expected versus observed evidence

All keys below refer to `results_v1.json`. Source review identifies missing
controls; tiny fault injections demonstrate consequences within safe bounds.

| Experiment | Expected | Observed |
| --- | --- | --- |
| Closed fixture | No sidecars, no quiescence proof | Zero sidecars |
| Active WAL writer | WAL/SHM observable | Both present during uncommitted synthetic update |
| Active rollback writer | Journal observable | JOURNAL present |
| Late sidecar | Checkpoint detects, not prevents | Detected after initial clean observation |
| Writer during inspection | Read-only connection does not prohibit other writers | Another generated connection committed a change while reader was open |
| Mutation between checks | Postcheck detects | Tiny append changed identity |
| Replacement after validation | SQLite can open changed file; mismatch needs checks | Replacement opened successfully; full tiny-file hash detected change afterward |
| Catalog without EQP | Table/view/index/FK metadata obtainable | Four objects, FK found, zero EQP and zero application READ authorizer events |
| Prohibited SQL | Rejected before execution | App-row SELECT, write, ATTACH, load_extension, SELECT 1 and multiple statements rejected |
| Exact catalog allowlist | Existing generic class may be broader | Caller-supplied catalog SELECT with WHERE 1=1 accepted: unresolved exact-template gap |
| Statement cap | Reject extra statement | Rejected after test-adjusted cap, including setup statements |
| Output cap | Reject before emission | 17 bytes against 16-byte patched writer cap rejected; zero output bytes |
| Row cap | Existing cursor lacks a cap | 64 catalog-only rows returned against declared two-row probe; no row-budget counter/parameter exists |
| Execute deadline | Immediate cancellation works | Zero-deadline query rejected |
| Fetch deadline | Handler lifetime may not cover fetch | Handler removed before fetch; four rows returned after 20 ms deadline |
| Worker timeout | Direct worker terminates | Dead after 0.309 seconds for a 0.3-second wait; latency is not zero |
| Descendant cleanup | Parent kill alone may not clean tree | Child survived parent kill, then self-expired by its three-second lifetime |
| Memory | No current hard quota | 1 MiB allocation succeeded across declared 512 KiB probe; working set observed at 35,381,248 bytes |
| Scratch storage | No current process quota | 8 KiB write succeeded across declared 4 KiB probe |
| OS read accounting | Not target or physical disk I/O | Process cumulative ReadTransferCount available (4,062,645 bytes), not a per-target measurement |
| Outside/unknown path | Deny before SQLite | Both rejected by generated-path allowlist |
| Symlink/reparse | Reject when platform permits creating link | Symlink creation unavailable; test explicitly skipped, not passed |

The planned short UDF delay was not necessary: a bounded 30 ms pause before
fetch directly demonstrated callback removal. No UDF/blocking-call cancellation
claim is made. Process-bound experiments ran in children with eight-second join
limits; the direct sleep worker had a 0.3-second deadline and a self-expiring
three-second descendant. Workloads did not attempt host exhaustion.

Synthetic WAL/rollback modes were deliberately configured to generate test
states; synthetic transactions were rolled back/closed. No production target was
checkpointed, repaired or transformed. Fault files were removed only inside the
new generated workspace. Checking no sidecars cannot prevent a later writer.
Even full hashes of these tiny fixtures are before/after observations, not
continuous immutability. Sampled equality of a large target would be weaker still.

## Resource-control classification

These classifications apply only at the stated layer, not to a production audit.

| Control | Classification | Boundary of the finding |
| --- | --- | --- |
| Statement count | ENFORCED | Existing wrapper rejects statements over its counter; not an I/O bound |
| Returned rows | DECLARED_ONLY | Proposal mentions a limit; existing cursor/fetchall has no enforcing counter |
| Output bytes | ENFORCED | Existing artifact writer checks payload size; not whole-process temp/storage |
| SQLite progress deadline | MONITORED_ONLY | Execute-time interruption works, but callback removed before cursor fetching |
| Whole-attempt wall time | MONITORED_ONLY | Exploratory supervisor measures and terminates a direct child; no full-attempt hard limit proven |
| Direct worker termination | ENFORCED | One synthetic child killed/joined; scheduling and cleanup latency remain |
| Descendant cleanup | NOT_SUPPORTED | Parent termination alone leaves the descendant alive |
| Process memory | MONITORED_ONLY | Working set measured; hard process quota absent |
| Temporary storage | MONITORED_ONLY | Generated scratch measured after writing; process-wide cap absent |
| Database bytes read | NOT_SUPPORTED | No logical-target read interception or enforced byte cap |

The small declared probe thresholds are investigative thresholds, not existing
configured production limits. Returning 64 rows is not empirical proof of
exceeding 25,000 rows; source inspection establishes the absent counter. Likewise
the memory and scratch probes do not pretend a quota was configured and failed.
They demonstrate that declarations alone impose no refusal.

Logical database reads are requests for database bytes. Pages visited depend on
page size, repeated access and caches. SQLite VM callbacks count execution work,
not bytes. OS ReadTransferCount covers process I/O, including imports and other
files; the reported sample was taken before the two catalog probes, not a
target-specific delta. Physical disk I/O also depends on the OS/storage cache.
No physical disk counter, cache flushing or target read-byte enforcement was
performed. The byte-budget question remains open, without substituting rows,
statements, pages or callbacks for bytes.

## Explicit IDs, concurrency and crashes

Reused the unmodified DurableAuditRegistry in a new marked temporary registry.
All approvals were unmistakably SYNTHETIC, disposable and invalid for production;
none were committed. Registry connections are not target connections.

- Two spawned consumers raced: exactly one winner; each used one registry
  connection and zero target connections. Uniqueness survived reopening.
- Duplicate registration, reused approval, reused attempt ID, expired approval
  and modified approval were rejected. Ledger verification passed.
- Crash before consumption: exit 21, zero registry and target connections;
  approval remained unused and no incomplete attempt was created.
- Crash after durable consumption before target open: exit 22, one registry
  connection, zero target connections. Consumption survived restart; incomplete
  attempt visible; replay rejected.
- Crash after target open before terminal recording: exit 23, one registry and
  one synthetic target connection. Consumption survived restart; incomplete
  attempt visible; replay rejected. The recorded state still says
  CONSUMED_BEFORE_CONNECTION: it is an incomplete projection, not proof that
  connection did not happen. Instrumented child observations distinguish this.
- Parent registry setup/observations used 19 registry connections and zero
  target connections. These counts cover the registry experiment, not fixture
  creation or all other experiments.

**Important gap:** the current synthetic approval payload contains no attempt ID.
The registry enforces uniqueness at consumption, but does not prove the caller
ID was the owner's preapproved ID. A future distinct production approval must
seal an explicit ID before use; the current synthetic schema must not be
misrepresented as already satisfying that contract.

## Minimal Stage 1-3 metadata

The tested catalog used these templates only (catalog-derived identifiers are
quoted/escaped, never supplied by an operator):

```
PRAGMA query_only=ON
PRAGMA query_only
PRAGMA busy_timeout=5000
SELECT type, name, tbl_name, sql FROM sqlite_schema
  WHERE type IN ('table','view','index') ORDER BY type, name
PRAGMA table_info(<catalog identifier>)
PRAGMA foreign_key_list(<catalog identifier>)
PRAGMA index_list(<catalog identifier>)
PRAGMA index_info(<catalog index identifier>)
```

Stage 1 used only the generated identity. Stage 2 returned the synthetic catalog
with no EQP and no application READ authorizer event; the sentinel was absent.
Stage 3 inventoried one generated provenance manifest. Rights remained MISSING;
keyword presence is not verification of rights, backup or correction fidelity.
This supports omitting EQP from a minimal proposed metadata path, not changing
the canonical specification here. It cannot prove completeness for an unknown
production schema or qualify market rows. Generic caller catalog SQL still
needs an exact enumerated-template interface in any future approved work.

## Privacy, containment and residual assurance

Entry CLI accepts only --record, no database path. The fixture factory always
creates a new temporary root; the SQLite guard accepts only its generated target
and registry. Outside/unknown paths fail before database open. There is no
private config parser, environment fallback, network/broker import or import-time
production activation. Generated error/result artifacts omit absolute paths.

Link/reparse checks exist, but the actual symlink creation test was skipped for
Windows privilege. No junction/race-prevention guarantee is claimed. The Python
allowlist and marker are containment against mistakes, not an OS sandbox against
hostile same-user code that can forge objects or replace monkeypatches. No
production-capable approval artifact was emitted.

## Six owner questions - engineering decision

1. **Quiescence: unresolved.** Keep simple no-sidecar policy, but absence and
   checkpoints only detect. A credible writer-exclusion/handle-race design needs
   synthetic evidence. Production implementation blocked.
2. **Database byte budget: unresolved.** Define logical versus physical metric
   and prove interception/enforcement; no accepted substitution. Blocked.
3. **Explicit IDs: partially resolved.** Durable uniqueness/crash behavior works;
   exact ID binding in approval is absent. Recommend an explicit sealed ID in a
   future separately approved type. Blocked.
4. **EQP: unnecessary for this synthetic catalog.** Recommend omission subject
   to reviewed scope narrowing; exact-template API and real schema applicability
   remain unproven. Not permission to implement or inspect production.
5. **Resources: unresolved.** Address fetch callback lifetime, row counters,
   process-tree timeout, memory/temp enforcement and byte accounting. Do not
   accept merely declared limits. Blocked.
6. **Future audit approval: deferred.** No approval issuance or access until
   separate implementation review, current report and exact owner authorization.

## Newly observed verification

Baseline focused review/protection tests: 20 passed before new work.
Investigation command completed once to record evidence; a fresh second run in
pytest reproduced the behavioral findings. Applied regression command:

```
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9j_synthetic_boundary.py tests/test_research_r9b_fno_auditor.py tests/test_research_r9d_production_boundary.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9i_pdf_v5.py tests/test_research_r9i_owner_review.py -q
```

Result: **91 passed, 3 skipped** in 7.64 seconds. Skips: one R.9J and two
existing R.9B symlink tests. No tests were deleted or excluded to conceal errors.
These selected suites were inspected before execution and open only newly
generated synthetic databases, or read tracked sanitized evidence. Root/Data
test totals from earlier milestones are historical, not newly reproduced here.

JSON, source/result manifest hashes, compilation, artifact privacy patterns and
Git whitespace were checked separately. Protected R.9H proposal/R.9F evidence,
previous PDFs and production boundary remain byte-exact. No production entry
point was added. No speculative implementation is hidden in production packages.

## Review-state handling

Recomputed research fingerprint remains
`1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`
over 252 files. Tools, these investigation documents and tests are outside the
existing inclusion rules. No exclusion was changed. PDF v5's historical review
is preserved unchanged; no false fingerprint-staleness transition was added.
Its synthetic investigation authorization is not permission to repeat, implement
or access production indefinitely. This task completes the requested investigation.

## Exact recommended next task and required decision

**Proposed, not authorized: R.9K - Synthetic Windows containment and resource
enforcement feasibility.** Use newly generated fixtures only to test a reviewed
writer-exclusion/handle protocol and a small Windows process-tree supervisor
(timeout, child cleanup and low safe memory thresholds), and assess whether a
hard logical database-read cap is feasible without a large new dependency.
Use measured limits and report infeasibility if the byte contract cannot be met.
Do not repeat the completed registry or metadata experiments unless needed to
verify a specific proposed change. No production boundary implementation yet.

Owner must separately authorize that narrowly scoped synthetic follow-up. The
existing decision to hold resource limits pending evidence remains unchanged;
no acceptance of weaker budgets is requested now. Any later proposal to change
the read-budget definition requires a separate explicit decision. Production
and real-data access remain prohibited regardless of synthetic success.

**SYNTHETIC_BOUNDARY_INVESTIGATION_COMPLETED_PRODUCTION_BLOCKED**
