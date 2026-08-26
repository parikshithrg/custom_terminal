# Research Integration Plan

## Ownership decision

Retain the proposed boundary:

- `Data test/dtest` is the hypothesis-development laboratory.
- `market_intel` owns canonical dataset trust, evidence, approval and
  application publication.
- `research_contracts` is a small neutral, dependency-free package.

Neither engine imports the other's implementation. Both eventually emit or
consume versioned neutral artifacts.

## Phase 1 — Contract boundary (implemented in R.1)

Introduce population, corporate-action, terminal-state, hypothesis-component
and lifecycle contracts plus JSON specifications.

Acceptance criteria:

- imports are dependency-neutral;
- ambiguous legacy rows map to `UNRESOLVED_LEGACY_STATE`;
- train acceptance cannot map to validation or production;
- inferred actions cannot become verified actions;
- unresolved terminal economics cannot gain consideration.

Rollback: remove the new package/specifications; neither existing engine has
been changed to depend on them.

## Phase 2 — Read-only compatibility adapters

Build a `dtest` exporter that reads an explicit log path and emits:

- immutable log snapshot hash and original row number;
- experiment-family ID assigned through a reviewed mapping file;
- row-level lifecycle mapping;
- hypothesis component contract;
- references to run artifacts and manifests, or explicit missing references.

Build a `market_intel` importer that validates the neutral artifact but cannot
promote it. Do not copy raw data or mutate the CSV.

Acceptance criteria: byte-identical source log before/after; every exported row
accounted for; missing manifests remain failures; adapter round-trip is stable.

Rollback: discard generated adapter artifacts; original evidence is untouched.

## Phase 3 — Canonical artifact formats

Define immutable JSON root manifests and typed Parquet facts for predictions,
trades, population membership, costs and evidence. Required references include
code/dirty fingerprints, environment, config, input datasets, security identity,
corporate-action series, terminal policy and outputs.

Acceptance criteria: every new laboratory run has one root manifest; an absent
input hash fails import; canonical hashes reproduce; no current-market data is
accepted as historical evidence.

Rollback: retain legacy outputs and version the importer; never rewrite them.

## Phase 4 — Contract tests at both boundaries

Run shared fixtures through both adapters for prices, universe membership,
next-open fill, costs, horizon, unresolved terminal state and lifecycle. Record
intentional semantic differences rather than forcing numerical parity.

Acceptance criteria: all differences are classified, expected, and versioned;
unknown terminal/corporate-action cases remain blocked.

Rollback: adapter versions remain side-by-side.

## Phase 5 — Governance and access ledger

Add preregistration, family ledger, diagnostic/confirmatory label, validation
approval and one-time test access events to the canonical catalog.

Acceptance criteria: ordinary commands cannot open test artifacts; all access
is append-only; multiplicity policy is fixed before confirmation.

Rollback: disable promotion while preserving all governance events.

## Phase 6 — Selective deprecation

Only after adapter parity, deprecate duplicate lifecycle/manifest/promotion
logic in `dtest`. Keep laboratory signal/features/simulators that remain useful.
Do not deprecate its append-only evidence, and do not move provider acquisition
into research definitions.

Candidate later deprecations:

- free-text `accepted/rejected` as an approval vocabulary;
- per-script acceptance formulas;
- optional/rare run manifests;
- ticker-only artifact keys;
- implicit raw-price series selection.

## Protected evidence

The original PDF, hypothesis CSV rows, momentum specification, golden fixture,
experiment manifests, historical trust verdicts and Kite allowlist/scope remain
immutable. Each migration phase starts and ends with hash comparison.

## Safest next implementation milestone

Implement Phase 2 only: a read-only, manifest-required `dtest` export adapter
over a user-designated canonical 32-row log snapshot. First make the log an
immutable versioned artifact without changing any row, then reconcile every row
to a family and manifest reference. Do not run a hypothesis.
