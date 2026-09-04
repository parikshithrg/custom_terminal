# R.9K pre-execution matrix

Baseline 4611d7e; only new synthetic fixtures and child processes. Production
packages, approval schemas, R.9J artifacts and owner review remain unchanged.
No applicable AGENTS.md found. Reuse R.9J conclusions without rerunning registry,
catalog or provenance experiments. No new dependencies, drivers or admin rights.

| Question / hypothesis | Fixture and expected observation | Measurement | Safety / stop |
| --- | --- | --- | --- |
| Main file guard | CreateFileW GENERIC_READ / FILE_SHARE_READ, OPEN_EXISTING; SQLite mode=ro should coexist, independent writes/deletes/rename should fail | Native error codes; query completion; hash under handle | Tiny database under 32 KiB; generated root only |
| Verification/open interval | Hold guard before hash through reader close; independent adversary during gap and read | Attempt results and full tiny-file hash | No real target; no checkpoint/repair |
| Sidecars | Main file guard does not cover sibling files | Independent create/modify sidecar, before/after check | At most 16 bytes each; no SQLite read after corrupt synthetic sidecar introduced |
| Handle cleanup | Errors and killed guard-owner release main-file restriction | Writer succeeds after scope/owner termination | Child finite 8 s self-expiry; 5 s parent deadline |
| Suspended assignment | CreateProcessW CREATE_SUSPENDED and CREATE_NO_WINDOW, assign to kill-on-close job, then ResumeThread | No worker marker before resume; IsProcessInJob; job limits | No breakaway flag; fail closed before resume on any setup error |
| Timeout tree cleanup | TerminateJobObject kills worker and its child before self-expiry | WaitForSingleObject on pinned process handles; latency | Two processes, 8 s self-expiry; 300 ms bounded deadline after ready |
| Supervisor closure/crash | Closing last noninherited job handle or process death kills descendants | Native process handle waits | Parent controller remains independent; no reliance on self-expiry |
| Create/assign failure | Injected create failure and native invalid-handle assignment keep worker suspended/unstarted | No marker; cleanup after failed assignment | Mocks explicitly labeled; actual success/cleanup tests use OS APIs |
| Memory | Job ProcessMemoryLimit controls committed virtual memory, not working set | VirtualAlloc 1 MiB success; 64 MiB request rejected under 48 MiB process cap | Reserve/commit without touching large buffer; allocation always freed; max request 64 MiB |
| Byte reads | Python sqlite3 has no target-specific VFS interception API | Public API inspection, 2 tiny reads while patching Python file open; mmap setting observed | No custom VFS, binding or dependency; stop if absent |

Job prototypes are exploratory and fixed-function, outside production packages.
They are not a general sandbox and cannot defend against all hostile same-user
or kernel/filesystem threats. Memory uses committed-memory limits; working set
is not treated as equivalent. Job objects do not provide per-database read-byte
caps or general temporary-storage quotas. Row/fetch/template/attempt-ID gaps
remain R.9J findings, not fixes in this task.

Reproduce with `.\.venv\Scripts\python.exe -m tools.r9k_windows_feasibility` and
focused pytest. `--record` writes once and rejects existing output. Every worker
accepts only an internally generated directory token (never a database path).
Results omit tokens/PIDs/paths. All experimental processes must be gone before
cleanup of the exact generated temporary directory.

## Authoritative sources consulted before native implementation (2026-09-04)

- [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew): sharing compatibility lasts for handle lifetime.
- [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects): child association, termination and kill-on-close.
- [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject): nested jobs, assignment constraints and error handling.
- [Process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags): suspended startup.
- [Extended job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information): process/job committed-memory limits.
- [Basic job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information): limit flags and breakaway.
- [Python sqlite3](https://docs.python.org/3.14/library/sqlite3.html): exposed connection callbacks, no public VFS registration.
- [SQLite I/O methods](https://www.sqlite.org/c3ref/io_methods.html): xRead and xFetch access paths.
- [SQLite mmap](https://www.sqlite.org/mmap.html): mapping can replace xRead with xFetch; cache implications.

No market-data source is contacted. Documentation-derived claims, mocked failure
tests and empirical native observations will be labeled separately.

Supplementary native references consulted during prototype refinement:

- [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).
- [VirtualAlloc](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualalloc).
- [Job process-list layout](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list).
