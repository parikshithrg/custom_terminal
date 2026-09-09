# F&O Production Boundary Remediation and Reauthorization Plan

## Decision

`FNO_PRODUCTION_BOUNDARY_PLAN_READY_FOR_OWNER_REVIEW`

Recommend **Option A: a restricted APSW/VFS boundary**, conditionally and only
for a separately approved implementation milestone. APSW is not installed,
adopted, or authorized by this plan. If the implementation cannot pass every
synthetic acceptance criterion, abandon the local F&O database route rather
than weaken the boundary.

This is a non-executable design record. It grants no locator resolution,
database access, implementation, research, backtesting, scoring, recommendation,
broker, or trading authority.

## Control and preservation

- Starting commit: `523da75a80e77b8e254ec97b2d74eb6726918d45`.
- R10K database state: `LOCATED_AND_SAMPLED_NOT_QUALIFIED`.
- R10K outcome: `AUDIT_ABORTED_SAFETY_BOUNDARY`.
- Private locator resolutions, database opens, SQL statements, and market rows
  during R10L: zero.
- R10K and R9L evidence, momentum specifications, golden fixtures, and the R10A
  holdout remain unchanged.
- `version2.0` remains separate. No external source was contacted.

## Why R10K stopped

Static checks reproduce all seven blockers:

1. The production locator contract is an unusable template.
2. No exact registered one-use production approval exists.
3. No production approval binds the R10K attempt ID.
4. Production activation is an unusable template.
5. `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` still rejects activation.
6. Standard-library `sqlite3` cannot enforce the target-specific logical
   read-byte cap.
7. The WAL, SHM, journal, and stale-sidecar policy was unresolved.

The owner’s R10K approval was valid. These were implementation and safety
contract failures, not missing owner permission.

## Option comparison

### Option A — restricted APSW/VFS

R9M demonstrated VFS read interception. R9N demonstrated cumulative logical
read, row, output, and fetch-deadline controls with explicit limitations. R9P
integrated exact attempt binding, durable one-use consumption, a one-connection
VFS, exact templates, Job Object containment, identity checkpoints, and terminal
reconciliation; all ten synthetic criteria passed across 512, 1024, and 4096
byte page layouts.

The evidence is strong enough to justify a bounded implementation proposal,
not production use. Remaining work includes production isolation, exact package
and runtime pinning, license/supply-chain review, aggregate Job Object memory
tests, a complete no-sidecar policy, and repeatable native adversarial tests.
Continuous directory quiescence and hostile same-user protection are not
claimed. Official F&O schema and data fitness remain separate later questions.

### Option B — standard-library sqlite3

`mode=ro`, `query_only`, an authorizer, progress callbacks, and application
counters are useful, but insufficient. Python’s standard interface exposes no
public VFS read interceptor; it cannot prove the exact logical read budget,
single main-file open, or complete refusal of native sidecar/temp opens.
Application estimates are not enforcement. Option B is rejected under the
current safety contract.

### Option C — abandon the local database route

Abandonment avoids a native dependency, private locator, uncertain database
provenance, and complex resource boundary. The cost is deferring historical
futures/options features and relying on separately qualified free official
sources whose completeness may remain limited. F&O product views would remain
hidden or mock-only. This is the mandatory fallback if Option A fails.

## Proposed private locator contract

The locator stays outside Git and binds only `PRIVATE_FNO_DATABASE_V1` in
committed evidence. A future resolver must return one local regular file and
reject directories, links, junctions, reparse points, devices, and unexpected
network resources. Parent and target handles remain pinned while identity is
checked.

The private binding must contain configuration content hash, size, SQLite
header hash, ordered 64-position sampled identity, and exact sidecar state.
Any material difference aborts. Refreshing a binding silently is prohibited;
a new identity ceremony and separate approval are required. This plan does not
resolve or populate the locator.

## Proposed exact one-use approval

A future sealed approval binds the reviewed R10L report and owner-review hashes,
database alias and locator binding, expected identity, predeclared attempt ID,
fixed executable and clean source commit, APSW/wheel/SQLite identity, stages
1–3, resource envelope, sidecar policy, output contract, issue time, and short
expiry.

Registration and consumption are distinct. `BEGIN IMMEDIATE` plus unique
approval and attempt keys atomically commits consumption before the first
target connection. Replay, mutation, expiry, duplicate ID, or any mismatch
fails before access. Consumed authority is never restored; crash recovery
reconciles an incomplete attempt to one terminal result.

## Proposed production activation

R9D remains closed. A later reviewed commit may replace its deliberate
rejection only after:

- the owner separately approves Option A implementation;
- the restricted boundary and dependency are committed and synthetically
  validated;
- every locator, identity, approval, dependency, stage, limit, sidecar,
  template, and output hash matches;
- approval consumption commits before the first target connection; and
- protected evidence and the R10A holdout remain unchanged.

Every condition is mandatory. A partial match provides no authority.

## Resource enforcement

The future attempt uses two pre-I/O byte counters: logical bytes requested by
SQLite and bytes delegated to the target filesystem handle. Both are capped at
256 MiB and reserve before delegation, with no refund after short reads or
errors. These measure target file requests, not physical device traffic.
Memory mapping is prohibited.

Additional cumulative limits are 50 statements, 25,000 accepted rows, 25 MiB
serialized output, 512 MiB per-process committed memory, 768 MiB aggregate Job
Object committed memory, 1,200 seconds per attempt, five seconds per statement,
two seconds maximum cancellation latency, eight exact templates, one million
VM progress callbacks, and zero SQLite temporary-file bytes. The aggregate
memory mechanism must be demonstrated synthetically before adoption.

Exact templates, authorizer checks, iterator and serializer counters, a
deadline retained through fetch, the restricted VFS, and a suspended worker
assigned to a Job Object enforce the limits. Any breach discards buffered
success output and creates only bounded terminal diagnostics.

## Sidecar decision policy

Proceed only when no sidecar exists, the main file is stable, and every other
gate passes. A rollback journal, WAL, SHM, active writer, changing database,
uncertain stale sidecar, late sidecar, or attempted non-main open causes abort.
The VFS denies the open; checkpoints discard any buffered result.

The audit must never delete, checkpoint, copy, repair, or reinterpret sidecars.
If WAL state is necessary, stop and request a separately approved immutable
snapshot workflow. No consumed approval may be retried.

## Evidence, privacy, and failures

Only sanitized IDs, aliases, categorical gates, schema/aggregate evidence,
resource counters, template hashes, identity comparison results, and lifecycle
events may be published. Raw rows, locator values, credentials, private paths,
database copies, and sidecars are prohibited.

Canonical deterministic JSON, immutable attempt directories, output byte caps,
hash manifests, before/after identity checkpoints, and pre-publication secret
and path scans are required. Every abort and crash path produces a terminal or
detectably incomplete event; no failure may publish a success artifact.

## R9L and v6 approval test reconciliation

The R9L test correctly recorded that no v6 owner-review file existed when PDF
v6 was generated. It incorrectly encoded that point-in-time fact as a permanent
repository invariant. A later, separate v6 owner-review record is now valid.

The hash-bound historical R9L file and manifest remain byte-exact. A narrowly
scoped strict `xfail` marks only that obsolete temporal assertion; an unexpected
pass is itself a failure. Forward tests verify both facts independently: R9L
had no authority at generation, and the later review grants only its exact
scope. Neither record rewrites the other.

## Implementation acceptance gate

The machine-readable matrix declares 17 mandatory criteria covering dependency
identity, locator safety, sealed approval, durable consumption, one main-file
open, byte metering, forbidden APIs, cumulative resources, Job containment,
sidecars, crashes, privacy, production interlocks, dependency isolation, and
historical preservation. One failure rejects the implementation. Passing all
criteria still authorizes no real database access.

## Product sequence

The owner’s sequence remains unchanged: review this plan; separately approve
an implementation; implement and validate it only on synthetic fixtures;
confirm pipeline readiness; build the interactive mock-data skeleton; freeze
interface and data requirements; issue an updated pre-real-data review; and
only then consider an exact real-data qualification request.

## Validation

- Focused R10L contracts before sealing: `10 passed, 1 deselected`.
- Combined R10L, R10K, approval-history, and synthetic adversarial checks:
  `75 passed, 1 skipped, 1 xfailed, 2 deselected`.
- Complete root suite after sealing: `776 passed, 4 skipped, 1 xfailed`, with
  7 warnings and no unexplained failure. The expected failure is the single
  documented R9L generation-time assertion described above.
- Data test was not rerun because no shared application or data contract
  changed; the latest recorded result remains `289 passed`.
- JSON parsing, manifest hashes, whitespace, private-path, credential, and
  secret scans: `PASS`.

APSW was neither installed nor adopted. The locator was not resolved; database
connections, SQL statements, and market rows remained zero. No external source,
research, holdout, broker, or trading function was accessed.

## Exact owner decisions required

The owner must answer separately:

1. Approve or reject Option A as the implementation direction.
2. Approve or reject adding exactly pinned APSW only to the dedicated boundary,
   subject to license, wheel-hash, runtime, and acceptance checks.
3. Accept or reject the proposed no-sidecar policy.
4. Accept or reject the resource metrics and limits, including the distinction
   between target filesystem requests and physical device traffic.
5. If approved, separately authorize only
   `IMPLEMENT_AND_SYNTHETICALLY_VALIDATE_RESTRICTED_APSW_FNO_BOUNDARY`.

No answer is recorded by R10L. Real-data qualification requires another later
review and authorization even if implementation succeeds.

## Recommended next milestone

`IMPLEMENT_AND_SYNTHETICALLY_VALIDATE_RESTRICTED_APSW_FNO_BOUNDARY`

Proposed only; not authorized.

`FNO_PRODUCTION_BOUNDARY_PLAN_READY_FOR_OWNER_REVIEW`
