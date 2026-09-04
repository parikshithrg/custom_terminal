# R.9M - Initial bounded synthetic VFS evaluation

## Result

**SYNTHETIC_VFS_READ_INTERCEPTION_DEMONSTRATED_FURTHER_REVIEW_REQUIRED**

APSW is a promising candidate for a restricted non-mapped, no-sidecar access
approach. It is not adopted or production-approved. The exact production
interlock remains active; real-database work remains deferred. No cap weakened.

Baseline: clean main at d0102dce57acb8bebffbfc002f865f8abee3245c. Owner accepted
v6, clarified **begin the evaluation** after the defer/evaluate question, and
requested separate later NSE accuracy testing. The task-scope record binds v6
without rewriting its generation manifest or creating executable audit authority.

## Candidate and maintenance assessment

APSW 3.53.4.0 exposes VFS hooks. Upstream release history shows continuing
development, but also API/build changes; this is evidence of activity, not a
support SLA. Standard sqlite3 retains the R.9K interception limitation.
One candidate was examined, not an exhaustive vendor/library comparison.

- [APSW VFS documentation](https://rogerbinns.github.io/apsw/vfs.html).
- [Release history](https://rogerbinns.github.io/apsw/changes.html).
- [Pinned source](https://github.com/rogerbinns/apsw/blob/3.53.4.0/src/vfs.c).
- [Installation](https://rogerbinns.github.io/apsw/install.html).
- [Distribution metadata](https://pypi.org/pypi/apsw/3.53.4.0/json).

Binary cp314/win_amd64 wheel: 3,341,532 bytes, SHA-256
13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5,
matching PyPI's published digest; upload 2026-07-26, not yanked when checked.
Installed only under ignored artifacts/r9m_evaluation/venv. No application
dependency or root environment changed. The candidate bundles SQLite 3.53.4,
whereas the root sqlite3 runtime is 3.50.4: parity cannot be assumed.

Future adoption would require supported-version policy, licensing review
(metadata says any-OSI, not a completed project legal review), wheel/supply-chain
review, SQLite upgrade regression tests, API compatibility, performance and
maintenance ownership. No recommendation to replace every sqlite3 use is made.

## Method and observations

Fixed standalone tool, no target-path or SQL arguments. A fresh 8,192-byte
fixture uses the existing NSE MII parser's seven header names, a synthetic table
name and explicitly synthetic values. Only a fixed catalog query is evaluated.
Creation and native control run outside the candidate meter on this generated
fixture; this is not a total-process byte cap. Fixture content was unchanged
and the temporary directory removed after each run.

| Case | Logical bytes delegated | Result |
| --- | --- | --- |
| Zero-byte budget | 0 | First read refused; no published rows |
| 200-byte budget | 100 | Next 4,096-byte request refused; no published rows |
| Adequate budget | 4,212 | One synthetic catalog row published |
| Exact observed 4,212-byte budget | 4,212 | Succeeded |
| One byte below observed requirement | 4,196 | Next 16-byte request refused; no published rows |
| Request mapped access | 4,212 | Wrapper readback empty; same xRead events |
| Late synthetic WAL-named sibling | 4,212 | Postcheck failed; buffered output discarded |

The exact/one-under thresholds derive from the initial adequate observation,
not a tuned market experiment. All delegated requests were charged before the
underlying read. Requested bytes include refused requests and can exceed the
budget; delegated bytes cannot. These are logical requests, not physical disk
I/O or rows. Failed underlying requests would still consume their reservation.

Direct method probes against the same native synthetic file read 16 bytes twice
at the same offset, consuming exactly 32 bytes; next 1-byte and 0-byte requests
were rejected after sticky exhaustion. Four direct forbidden opens were refused:
WAL, journal, temporary file and read-write main file. These are direct-method
tests, not proof of every SQLite sidecar path. No mocks are counted as native
SQLite execution here.

## Mapped access and sidecars: restrictive, not comprehensive

Pinned vfs.c SHA-256:
55650ae46ea5f86b1e2ac6e96fa09559b9c065469a02d7fdf16ac4ad200cd047.
Source inspection shows plain Python file objects use io_methods v1; inherited
VFSFile instances may receive v2 shared-memory proxy methods. Neither installs
xFetch. The prototype intentionally uses a plain proxy, does not forward file
control pointers and rejects non-main-file opens. This avoids the inherited
shared-memory proxy rather than claiming to meter it.

Native win32 control accepted mmap_size=16,777,216; the wrapper returned no
mmap_size row and catalog reads traversed xRead. Together with pinned source,
this supports **mapped access unavailable in this wrapper**, not metered mapped
access. No xFetch interception was implemented or proven. If mapped access or
WAL must be supported later, this restricted experiment does not satisfy it.

Late-sidecar detection is only a checkpoint. It does not prevent a sibling
appearing/disappearing between checks, namespace substitution or another writer.
No active WAL recovery/checkpoint, adversarial reparse race, full corruption
matrix, concurrent VFS use or large-fixture workload was tested. The tool is
not a security boundary against hostile code in its own process. Source pinning
does not prove a wheel was reproducibly built from that tag.

## NSE schema alignment and separate accuracy validation

Copied names: FinInstrmId, TckrSymb, SctySrs, ISIN, Xchg, Sts, FinInstrmNm,
from the existing canonical NSE MII normalization implementation. They are not
a complete F&O bhavcopy schema. Types are deliberately text for this I/O probe;
the invalid synthetic ISIN is a sentinel, not an authoritative identifier.

[NSE Forms & Formats](https://www.nseindia.com/static/resources/forms-formats-members)
identifies official UDiFF format documentation. The browser retrieval of its
format link failed; a direct page request first met a local sandbox socket
restriction, then timed out under ordinary permitted networking. An initial
unverified fo_bhavcopy.csv URL also returned a browser internal error; no object
was acquired and it is not treated as a source. No controls were bypassed.

Therefore exact F&O header/type matching is **PENDING_OFFICIAL_FORMAT_EVIDENCE**,
not silently declared passed. No market data or current security list was
downloaded. Later schema fixtures should bind the official format/version,
use its exact columns/types and explicit synthetic identifier values, and
test schema changes/missing fields. Separate, subsequently authorized NSE-data
tests must assess accuracy, revisions, provenance and coverage; synthetic tests
cannot establish those properties. No real NSE validation is run now.

## Verification and saved artifacts

Baseline focused static checks: 20 passed. New static checks verify the task
scope, candidate limits, source/result hashes, header provenance, no production
adoption and unchanged prior evidence. No native R.9K or registry experiments
were rerun. No broad root/Data test suite used to recreate historic totals.

Run the new fixed probe only using the isolated candidate environment:

```
artifacts/r9m_evaluation/venv/Scripts/python.exe tools/r9m_vfs_evaluation.py
```

Executed through subprocess.run with capture_output=True and timeout=30.
Initial exploratory run passed; the final expanded run and one replay passed,
with equivalent results. Recorded results are normalized JSON from stdout,
not original transport bytes. The tool cannot overwrite the record.

Static verification command:

```
.\.venv\Scripts\python.exe -m pytest tests/test_research_r9m_vfs_evaluation.py tests/test_research_r9l_pdf_v6.py tests/test_research_r9h_boundary_proposal.py tests/test_research_r9i_owner_review.py -q
```

Final result: 26 passed. Prior v6 hashes bind earlier evidence; production files,
dependencies, specs and prior fixtures unchanged. JSON/hash and whitespace
checks passed. New tracked text screened for private-path/credential patterns.
The wheel/environment remain ignored, not committed or promoted to dependencies.

New files: docs/investigations/r9m/{EVALUATION_PLAN.md,owner_scope_v1.json,
results_v1.json,manifest_v1.json}, tools/r9m_vfs_evaluation.py,
tests/test_research_r9m_vfs_evaluation.py and this report. Narrow -text rules
preserve new evidence hashes; prior whitespace rules unchanged.

## Next bounded step, not production permission

Review whether the no-mapping/no-sidecar candidate restriction is acceptable for
further synthetic engineering. Then define a reviewed adversarial matrix for
the remaining gaps: sidecar/namespace stability, temp quota, row and fetch
limits, exact templates and sealed attempt IDs. No single initial probe closes
those blockers. Obtain exact official F&O format evidence before claiming F&O
schema parity. Continue to defer all real-database work and dependency adoption.
