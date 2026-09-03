# Research R.9D - Production-Enablement Boundary with Synthetic Testing Only

## Baseline

R.9D began from clean synchronized `main` commit
`a08ca45c30484f331401e9f84f898c76db4274ee`. PDF v2 remained byte-identical at
SHA-256 `765c2facad827a3a6473b605037d9975135885e767420ca810ebbc28852c2adf`.
Its explicit owner review occurred after generation and covered exactly
`FNO_PRODUCTION_ENABLEMENT_DESIGN_AND_SYNTHETIC_TESTING`.

No production locator was resolved. No production configuration value was
read. No real database was located, opened, hashed, inspected, copied, or
queried. No real approval or production registry was created. All executable
tests used small temporary synthetic fixtures.

## Implemented boundary

`market_intel.foundation.fno_production_boundary` adds:

- an immutable SQLite approval registry and append-only hash-chained events;
- atomic cross-process one-use consumption using `BEGIN IMMEDIATE` and unique
  constraints;
- crash-detectable nonterminal attempt state and terminal completion, abort,
  and failure events;
- approval, event-chain, and attempt-projection tamper checks;
- typed production locator and interlock contracts;
- a production entry point that always fails before configuration, filesystem,
  attempt, or SQLite activity;
- runtime dependency-injection rejection;
- a task-scoped, bounded, atomic synthetic evidence store with exact hashes and
  truthful restore/retention metadata.

The R.9B synthetic auditor can use the durable registry through the same narrow
registration/consumption interface and records a durable terminal event after
atomic output finalization.

## Atomicity and adversarial evidence

The focused suite launches two spawned processes against separate SQLite
connections. Exactly one consumes a shared approval; the loser fails before any
target connection. A process terminated before consumption leaves the approval
unused. A process terminated immediately after committed consumption leaves it
durably consumed with a discoverable incomplete attempt. Restarted registry
instances reject reuse.

Tests also cover immutable registration, duplicate IDs, altered and expired
approvals, market-research approval substitution, private-path and secret
rejection, ledger corruption, exact attempt binding, normal terminal events,
consumption-before-connection, catalog-only access, production locator
non-resolution, configuration-reader non-use, every required interlock,
network/broker isolation, output colocation, overflow, unexpected artifacts,
atomic finalization, and immutable final attempts.

## Production state and limitations

The locator state is
`PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING`. The deliberately impossible
R.9D interlock is `R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`. The activation
template is unsealed, unregistered, unusable, and contains null or placeholder
binding fields.

The durable mechanism is application-level tamper-evident governance; it is not
physical protection against the machine owner. Windows symlink execution cases
remain skipped where privileges are unavailable. No real target, production
registry, backup, restore, historical completeness, point-in-time fitness,
market-row integrity, or database qualification was tested.

## Verification

- Focused R.9D suite: 19 passed.
- Focused R.9C and R.9D lifecycle/boundary suites: 30 passed.
- Combined R.7-R.9D governance suites: 111 passed, 2 skipped.
- Complete root suite: 324 passed, 2 skipped, 2 established development-only warnings.
- Separate Data-test suite: 289 passed with established dependency and development-only warnings.
- Cross-process tests: passed; exactly one of two spawned contenders consumed the approval.
- JSON validation: 84 valid, 0 invalid outside ignored runtime/artifact directories.
- Python compilation: passed.
- Entry-point reconciliation: passed; unsafe bypass count remains zero.
- Network, broker, Streamlit, research, scoring, portfolio, and trading isolation: passed statically and through runtime injection rejection.
- Production locator non-resolution and configuration-reader non-use: passed.
- Protected evidence comparison: 0 changed protected paths.
- Secret-pattern scan: 0 credential-pattern hits.
- `git diff --check`: passed with line-ending notices only.

The research-state fingerprint changed from
`9382d3d7511dba094a1321294d4f6575cf2cd857a0e43c6d0c024df55202ec31`
over 231 files to
`f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38`
over 237 files. This is the expected result of adding the R.9D source and
contracts.

## PDF staleness and next step

R.9D changes research-relevant source and specifications. PDF v2 remains exact
historical reviewed evidence but is marked `PDF_V2_STALE_AFTER_R9D_IMPLEMENTATION`.
The safest next milestone is to generate and review PDF v3 covering exact
binding preparation. That milestone must not resolve the production locator,
create an audit approval, or execute the audit.

FNO_PRODUCTION_BOUNDARY_IMPLEMENTED_BUT_DISABLED
