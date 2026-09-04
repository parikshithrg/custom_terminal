# R.9M - Bounded synthetic dependency evaluation

Baseline: d0102dc. Clean tree before work. This is an exploratory tools/docs
evaluation, not production implementation or adoption of a dependency.

## Owner clarification

The owner accepted PDF v6, authorized evaluation, initially said defer, then
answered the explicit scope clarification with **begin the evaluation**.
Interpretation: start synthetic-only evaluation now; real-database access stays
deferred. No resource requirement is relaxed. Later NSE-data validation remains
separate. Use verified NSE headers where available, with unmistakably synthetic
values; never imply matching headers establishes real-data accuracy.

## Bounded candidate and checks

Evaluate APSW as one maintained VFS-capable candidate, not an adopted dependency.
Compare against the existing sqlite3 limitation using already recorded evidence.
Do not repeat R.9J registry/catalog or R.9K containment experiments.

1. Inspect upstream documentation, release-tagged VFS source and distribution
   metadata. Pin candidate version and wheel SHA-256. No source build or global
   installation; use only an ignored, isolated evaluation environment.
2. Generate a tiny new marked SQLite fixture with synthetic values, under a
   fresh temporary directory. No arbitrary target path, config or binding input.
3. Test pre-delegation logical xRead charging, zero/exact/insufficient budgets,
   repeated reads, sticky exhaustion and no partial published result.
4. Inspect whether mapped xFetch can bypass the wrapper. Test an attempted
   mmap enablement; report disabled path separately from interception support.
5. Deny sidecar/temp opens and writes, do not repair or checkpoint. Sidecar
   detection is not proof of continuous namespace exclusion. WAL/SHM proxying
   needs explicit source review. Unknown behavior remains blocked.
6. Record limitations and maintenance burden. Do not integrate with production
   code, approve a library, open real data, acquire market history or run research.

Bounds: one pinned candidate; binary wheel only; fixture below 128 KiB; no host
exhaustion; no arbitrary SQL interface; one local process, fixed finite queries;
maximum 30 seconds for a probe subprocess. All test observations are synthetic.
Stop if wheel unavailable, source/version inconsistent, unbounded behavior or
unclear I/O coverage. Do not claim production readiness even if probes pass.

The main application dependencies, production interlock, historic PDFs and
immutable prior manifests stay untouched. Record new evidence separately.
