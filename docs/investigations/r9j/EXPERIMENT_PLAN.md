# R.9J bounded synthetic investigation plan

Prepared before experiment execution. Baseline db3d872; authority is only
BOUNDED_SYNTHETIC_BOUNDARY_DESIGN_INVESTIGATION_ONLY. No production entry point
or private configuration/data access. No AGENTS.md found in the repository or
its ancestor directories; existing pyproject test configuration applies.

## Matrix

| Question | Hypothesis / expected result | Generated fixture | Measurement | Safety bound / stop |
| --- | --- | --- | --- | --- |
| Closed target | No sidecars observed, not proof of quiescence | Tiny SQLite table/index/FK/view | Sidecars, identity | Under 1 MiB target; no real target argument |
| WAL/SHM and journal | Detect active writer sidecars | New WAL transaction; separate rollback transaction | Types and writer state | Rollback/close only synthetic setup; 2 s SQLite timeout |
| Inspection-to-open races | Replacement/mutation can occur after validation; checkpoints detect, do not prevent | Replace or append to generated file; late sidecar | Before/after digest and open result | At most 16 bytes mutation; no target repair |
| During-inspection mutation | Postcheck detects committed synthetic change | Concurrent generated writer | Full tiny-file digest difference | Small update, no table scan |
| Statement / row / output controls | Count and output checks reject overflow; row cap may be absent | Catalog plus bounded 64-row catalog product | Statements, rows, emitted bytes | Threshold 3 statements, 2 rows, 16 output bytes; only 64 rows attempted |
| Progress deadline | Execute interruption works; fetch/blocking coverage may not | Small catalog query and 30 ms synthetic UDF | Callback state, elapsed time | Child deadline 8 s, at most 0.3 s deliberate UDF work |
| Whole worker / descendants | Parent can terminate direct worker; descendants may survive | Sleeping worker and one self-expiring child | Exit code, surviving child probe | 0.3 s wait; child self-exits within 3 s; join cap 8 s |
| Memory / temp | Existing stack has no hard process quota | 1 MiB allocation and 8 KiB scratch write | Controlled threshold crossings; Windows working-set observation | Never exceed 2 MiB incremental allocation or 64 KiB scratch |
| Database read bytes | Row/page/callback counts are not hard byte accounting | Repeat tiny catalog operation | Identity logical bytes, OS ReadTransferCount if available | No cache flush; no physical disk claim |
| One-use IDs | Durable uniqueness and exactly one concurrent consumer; restart preserves consumption | Disposable marked registry and synthetic approvals | Registry versus target connections, winners, incomplete attempts | Two spawned contenders, 8 s each; no persisted usable approval |
| Crash phases | Pre-consume unused; post-consume always consumed | Three child processes with explicit crash codes | Durable restart state, target connection count | os._exit only in spawned synthetic child |
| Minimal catalog | Structure available without EQP or app rows | Sentinel rows, table/view/index/FK | Authorizer events, exact statements, sentinel absence | Existing 50-statement cap; no caller SQL in public entry |
| Containment | Unknown IDs/outside paths rejected before open; links rejected when supported | Generated files only; generated link | Rejections, platform skip | Fixed new temporary root, no db-path CLI or env fallback |

All successful or failed expectations must appear in sanitized results. No host
exhaustion, unbounded workload, current-market data or external access. Fixtures
are newly generated beneath a dedicated temporary root. Generated target and
registry paths are explicitly allowed in an investigation-only connect guard.
This guard is not an OS security sandbox against hostile same-user Python code.

Reuse ReadOnlyCatalogConnection, catalog/provenance inventory, synthetic
approval validation and DurableAuditRegistry. Fault injection changes only
in-process test settings, never production source. Helpers live under tools,
not production packages. Report missing enforcement instead of inventing it.

## Reproduction and regression selection

Run `.\.venv\Scripts\python.exe -m pytest tests/test_research_r9j_synthetic_boundary.py -q`.
Run `.\.venv\Scripts\python.exe -m tools.r9j_synthetic_boundary --record` once to
write fixed report artifacts; recording refuses to overwrite existing results.
Plain module invocation prints a fresh sanitized run without replacing evidence.

Before broader testing, inspect test source. R.9B/R.9D tests create disposable
synthetic SQLite fixtures and R.9H/R.9I tests read only tracked sanitized
governance/report artifacts. Run these explicit suites only; do not run the full
root or Data test suites merely to match prior counts. No production database
access is authorized by test discovery. Tests with uncertain data access are
not part of this investigation.

## Decision standard

Classify controls ENFORCED, MONITORED_ONLY, DECLARED_ONLY or NOT_SUPPORTED with
scope and limitations. A passing test can confirm a gap exists. No synthetic
success qualifies the real database. Changes under tools/docs/tests are outside
existing research fingerprint inclusions; recompute without modifying policy.
