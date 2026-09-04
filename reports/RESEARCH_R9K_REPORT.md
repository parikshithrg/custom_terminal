# R.9K - Synthetic Windows containment and resource-enforcement feasibility

## Decision

**SYNTHETIC_CONTAINMENT_FEASIBILITY_RECORDED_PRODUCTION_BLOCKED**

Small Windows-native probes demonstrated main-file sharing restrictions,
suspended Job Object assignment, fixed process-tree cleanup and a per-process
committed-memory cap. They did not establish complete database quiescence or a
target-specific logical read-byte cap. The latter is
**NOT_FEASIBLE_WITH_CURRENT_APPROVED_STACK** without binding/VFS-level changes
excluded by this task. No requirement has been weakened.

## Baseline and authority

Started on clean `4611d7e5025531e3e1dae690c71fa8f5dd105b39`. No applicable
AGENTS.md was found; existing repository test configuration and the attached
R.9K authorization were followed. Read the R.9J source, tests, assessment and
manifests; all source/result hashes reconciled before implementation. The exact
PDF v5, review record, R.9H package and R.9F evidence checks passed.

The active interlock remains `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`.
No production package, approval schema, historical evidence or PDF changed.
No private configuration/runtime binding or real database was read, resolved,
sampled, opened or copied. No production approval, acquisition, broker access,
market analysis, scoring, simulation, backtesting or trading occurred.

## Artifacts and bounded method

- `docs/investigations/r9k/EXPERIMENT_PLAN.md`: matrix written before prototype.
- `tools/r9k_windows_feasibility.py`: fixed-function exploratory native probes.
- `tests/test_research_r9k_windows_feasibility.py`: focused native and mocked tests.
- `docs/investigations/r9k/results_v1.json`: immutable sanitized observed run.
- `docs/investigations/r9k/feasibility_v1.json`: decision table and evidence keys.
- `docs/investigations/r9k/manifest_v1.json`: source/fixture/result/report hashes.
- This report; narrow `.gitattributes` additions preserve new hashed bytes.

No third-party binding, custom VFS, driver, system policy change or administrator
elevation was introduced. ctypes calls the existing Windows APIs. Prototypes
are outside production packages and expose no arbitrary database-path argument
or configuration fallback. Internal children accept a generated token under a
dedicated temporary root, not a private locator. This is not a general sandbox.

Fresh SQLite fixture: 8,192 bytes; one synthetic table and one sentinel row.
Only catalog structure was queried, to test read-only compatibility and native
file access, not to repeat R.9J catalog qualification.

- Recipe hash: `9674b9afb78bcba92af932555102de573f714202cd8eb961c85f3b75e58d5b00`.
- Fixture hash: `163263c21ba0b1a0b59c4c0bcbf8c2a232528dc304dc166e69bcee803cd851a5`.
- Result hash: `048b06de230729c1243dd1d5effdd13dbe3582e3abf81430b23891d688181148`.
- Runtime: Windows 11 / 10.0.26200, 64-bit, Python 3.14.6, SQLite 3.50.4.

Workers self-expire after eight seconds as a final safety net. Job cleanup was
observed within milliseconds, before self-expiry, not inferred from eventual
exit. Only exact newly generated temporary directories were cleaned up. No
usable approval artifacts were created. No registry/provenance experiment was
rerun; R.9J findings were reused.

## 1. Main-file handle and identity interval

Mechanism: acquire CreateFileW with GENERIC_READ, FILE_SHARE_READ and
OPEN_EXISTING before hashing. Keep it open through the independent adversary
tests, SQLite mode=ro connection and reader closure. Windows sharing rules
apply while the handle remains open. [Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

| Hypothesis | Actual native observation |
| --- | --- |
| A legitimate read-only SQLite open remains compatible | Query succeeded while guard held |
| Independent write/rename/replace is excluded | All three prevented before SQLite open, with reader open, and after reader close while guard remained held |
| Main-file identity is stable under tested attacks | Full tiny-file hash unchanged |
| Sibling sidecars are not covered | Independent process created and changed WAL/SHM/journal-named siblings; all three detected afterward |
| Error unwinding releases guard | Writer succeeded after deliberate exception/finally cleanup |
| Actual guard-owner termination releases handle | Writer succeeded, measured release 0.004339 seconds |

Rename returned Win32 error 32; replace returned 5. The Python buffered write
denial did not expose a Win32 code (null), so none was invented. These are real
independent-process operations, not mocks. The adversary attempted a write of
the existing first header byte: this required write permission but did not
damage the synthetic target if it unexpectedly succeeded.

**Partial result only.** This tests ordinary Win32 opens against the main file.
Sidecar creation/change is merely detected; no continuous sibling protection
exists. The sidecar injection was after reader closure, so it does not prove
SQLite remains safe while malicious journal state is introduced during queries.
Preexisting writers/mappings, parent-directory substitution, reparse races,
hostile same-user handle manipulation and unusual filesystem/kernel behavior
were not proven safe. Cooperative shutdown may be an operational prerequisite,
not a substitute for proof. No target was checkpointed or repaired.

The first exploratory run failed during cleanup because the venv launcher PID
was not the actual handle-owner PID. The revised probe reports that mismatch,
pins the actual worker process and terminates it directly. Later runs passed.
This failure was not discarded as a passed test or attributed to secure erasure.

## 2. Windows Job Object feasibility

The native prototype creates a noninherited unnamed Job Object with
KILL_ON_JOB_CLOSE and no breakaway flags. CreateProcessW starts the worker
suspended and hidden; successful assignment is checked before ResumeThread.
The runtime was already in a host job and nested assignment succeeded here.
Other hosts can impose different restrictions and must fail closed on setup
failure. [Assignment rules](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
[creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags).

| Experiment | Expected | Recorded observation |
| --- | --- | --- |
| Assignment before worker execution | No startup marker before resume; assigned worker/descendant | Confirmed; inherited host job true |
| Timeout at 300 ms after ready | TerminateJobObject kills fixed tree | 5 pinned job processes exited; overshoot 0.000507 s, cleanup 0.005615 s |
| Close last job handle | Tree exits before eight-second self-expiry | 4 pinned processes exited; overshoot 0.000032 s, cleanup 0.007215 s |
| Terminate actual supervisor | OS closes its last job handle and kills associated tree | 5 pinned processes exited; 0.005823 s cleanup |
| Job creation failure | No worker launch | Mocked failure-path test confirms no suspended-process call |
| Assignment failure | Do not resume; destroy suspended worker | Native invalid-handle call returned error 6; no marker, worker terminated |

Process-list counts differ because launchers are also processes and the list is
a point-in-time census. Handles were pinned to avoid treating reused PIDs as
the observed processes. Job membership and fixed-worker behavior were checked;
there is no claim of exhaustive hostile-process containment.

Microsoft documents job inheritance for ordinary CreateProcess descendants and
last-handle cleanup. This probe does not test service/WMI-mediated creation,
hostile same-user code or every job hierarchy. A Job Object is not an identity,
network or filesystem permission sandbox. The supervisor's own liveness and
scheduling matter for wall-clock deadlines. No hard real-time guarantee is
claimed. [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

### Memory metric and safe fault injection

With a 48 MiB per-process committed-memory limit, VirtualAlloc of 1 MiB
succeeded; a 64 MiB request failed with error 1455. The same 64 MiB request
succeeded in a no-cap control under the same host. Peak process commitment
reported by the job was 24,477,696 bytes in the capped run, and 87,437,312 in
the control. This is committed virtual memory, not resident working set.
Successful allocations were immediately released without touching the large
buffer; host resources were not deliberately exhausted.
[Extended job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information),
[VirtualAlloc](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc).

Aggregate job memory and arbitrary allocation patterns were not tested. The
prototype uses only the process commitment limit, not an aggregate tree cap.
The maximum workload is finite and small; this is evidence of a mechanism, not
a production-safe resource envelope.

## 3. Logical database read-byte budget: no-go on approved stack

Proposed metric: cumulative bytes requested from the target database at the
SQLite I/O boundary over the attempt, including repeated cache-miss reads and
any mapped-fetch access. It is not the number of returned bytes, rows, pages,
statements or VM steps. An implementation would have to define how mapped ranges
are charged and cover applicable sidecar paths explicitly. A physical-storage
budget would be a different, harder requirement.

- **Logical SQLite file requests:** xRead and potentially xFetch at the VFS
  boundary; SQLite cache hits need not issue another request.
- **OS process I/O:** includes unrelated process files and accounting effects;
  cannot be substituted for per-target logical requests.
- **Physical storage reads:** affected by OS/device caching and read-ahead;
  not measured by SQLite row counters or this prototype.

Python's documented sqlite3 API provides no public VFS registration/read-byte
interceptor. A tiny probe executed two catalog operations with Python builtins.open
replaced by a rejection hook: zero hook calls. This demonstrates that a Python
file hook is not the interceptor, not that zero file I/O occurred. The observed
mmap_size was zero on this fixture only. Mapped SQLite access can use xFetch
instead of xRead; zero mmap on one connection is not coverage of all access
paths. [Python sqlite3](https://docs.python.org/3.14/library/sqlite3.html),
[SQLite I/O methods](https://www.sqlite.org/c3ref/io_methods.html),
[memory-mapped I/O](https://www.sqlite.org/mmap.html).

**NOT_FEASIBLE_WITH_CURRENT_APPROVED_STACK.** Genuine interception would require
separately approved binding/VFS-level infrastructure. No custom VFS, alternative
binding or native database integration was implemented. This branch stops here.
Disabling mmap alone would not supply an xRead interceptor. Job limits do not
change that conclusion.

Alternatives, not authorized:

- Evaluate a maintained VFS-capable binding: new dependency and version/support
  surface, plus careful read/mapping/sidecar accounting and failure tests.
- Custom native VFS: larger ongoing maintenance and correctness burden; excluded
  here and not recommended as the next automatic implementation.
- A separately approved, bounded data-access/ingestion approach: changes the
  access contract and still requires evidence of provenance, identity, retention
  and resource limits. Free official data does not waive these requirements.
- Keep the present stack and hard cap unchanged: remain blocked; do not relabel
  statement/output limits as database-read enforcement.

## Feasibility and resource boundaries

| Blocker | Classification | What remains |
| --- | --- | --- |
| Writer exclusion and identity | PARTIALLY_PROVEN | Main-file sharing works; siblings and namespace/same-user threats remain |
| Fixed process-tree cleanup | PROVEN_WITH_STATED_LIMITATIONS | Native timeout/close/supervisor-death paths work; not general sandbox or hard real time |
| Process committed memory | PROVEN_WITH_STATED_LIMITATIONS | Safe capped/control probe; aggregate tree memory not tested |
| Logical database read-byte cap | NOT_FEASIBLE_WITH_CURRENT_APPROVED_STACK | Binding/VFS interception unavailable under constraints |
| Temporary-storage quota | INCONCLUSIVE | Tested job settings offer no disk quota; alternatives not investigated |

Whole-attempt timeout requires a supervisor plus job termination; a job's CPU
time limit is not elapsed wall time. Descendant cleanup and process commitment
benefit from jobs. Temporary storage and target read bytes do not acquire hard
limits just because a job exists. Output-byte limits remain narrower than a
process-wide scratch-space quota. R.9J row-limit, fetch-deadline, exact-template
and sealed-attempt-ID gaps remain explicitly open and unmodified.

## Reproduction and verification

```
.\.venv\Scripts\python.exe -m tools.r9k_windows_feasibility
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9k_windows_feasibility.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9i_owner_review.py tests/test_research_r9j_synthetic_boundary.py::test_committed_result_manifest_matches_sources -q
```

Plain module execution uses fresh fixtures and prints sanitized observations.
Initial recording used `--record`; it refuses to overwrite results. Expected
outcomes reproduce; timing, process counts and memory peaks are runtime-dependent.

Newly observed: **25 passed, 0 skipped** in the selected suites. The native
R.9K cases used real OS APIs; the creation-failure test is explicitly mocked.
The first mocked test initially failed on its missing synthetic-root setup; the
test was corrected to isolate creation failure, not excluded. No previous
registry, catalog or provenance workload was repeated. No root/Data test suite
was run merely to match historical counts.

After final recording, all tracked experimental process handles were signaled.
A read-only process census independently found **zero remaining R.9K Python
workers**. Its sandboxed first attempt was access-denied and provided no valid
count; a same-user read-only retry outside that sandbox succeeded. No admin
elevation, system-policy change or broad process termination was used.
The dedicated temporary root was empty after cleanup.

Manifest hashes, JSON, source compilation, sanitized-artifact privacy scan and
Git whitespace checks passed. R.9H/R.9F immutable evidence, old PDFs and review
record hashes remained unchanged. No production entry point or authority was
added. The exact source hashes and all deliverables are bound by the manifest.

## Review handling and exact next decision

Research fingerprint is unchanged:
`1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`, 252 files.
Existing rules exclude this tools/docs/tests work; exclusions were not changed.
No staleness was manufactured and no PDF or owner approval was generated.
**The older PDF summary does not cover these new engineering findings**, despite
the unchanged mechanical fingerprint. It must not be treated as approval of
these conclusions or of production implementation.

Smallest next step: **an explicit owner decision on the incompatible stack and
read-byte requirements**, not another open-ended investigation. Recommend keeping
the hard cap and production block unless the owner separately authorizes a
bounded evaluation of a maintained VFS-capable access approach. That evaluation
would stop at documented coverage of xRead/mapping/sidecars or a no-go result;
it would not grant real-data access. If no dependency/access-contract change is
acceptable, stop the SQLite audit route. Any weakening of the cap requires a
separate explicit decision; none is inferred here.

**SYNTHETIC_CONTAINMENT_FEASIBILITY_RECORDED_PRODUCTION_BLOCKED**
