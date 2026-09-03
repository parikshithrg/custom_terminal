# Research R.9H - F&O Production Audit Boundary Proposal

## Outcome

R.9H prepared a complete non-executable proposal for a future fail-closed,
exact, one-use production F&O database-quality audit boundary. It does not
implement that boundary and creates no usable approval or production entry
point.

Completion state:

`FNO_PRODUCTION_AUDIT_BOUNDARY_PROPOSAL_PREPARED`

Next requested scope:

`GENERATE_PRE_RESEARCH_STATUS_PDF_V5_ONLY`

## Baseline and authority

- Baseline commit: `18449fedafc21acbbabf2be3a395d07c8b4dc28c`.
- Reviewed PDF v4 SHA-256:
  `02a76f6d46bc74a69b7f0b10331ae26da1d07d60934091ce9d31c0abe8cdaec9`.
- PDF v4 owner-review-record SHA-256:
  `f35a6319d855845876ec888d58acaf7a5fe1a66be6ecf2232ed50a71823a5066`.
- Authorized work: proposal preparation only.
- R.9F anchor SHA-256:
  `115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc`.
- R.9F sampled root:
  `b1b8c0ca1338d477987da28e6d9647b151c120a0eac7bb17c9e9293edfd4bc47`.

The ignored private runtime artifact was not read. No additional private
database bytes were read and the R.9F sampling ceremony was not repeated.

## Proposal artifacts

The directory `proposals/fno_production_audit_boundary_v1/` contains:

- architecture, security rationale, reuse boundaries, gaps, non-goals and the
  owner-approved alternative-source policy;
- an explicitly unusable exact approval template;
- an explicitly unusable immutable input-declaration template;
- current and proposed state machines, event model, and failure/recovery rules;
- a proposed layered SQLite read-only safety contract;
- current and future entry-point capability deltas;
- a prevention/detection/fail-closed threat model;
- a test matrix, operator checklist and implementation sequence;
- the exact Stage 1-3 scope reference and unresolved decision ledger;
- a deterministic manifest binding every other proposal object.

Proposal manifest SHA-256:

`a6529ec14520d163e327e2dcc7a7f469ea473d14b8d39e3ede345bc3d49dcdc1`

Package-content SHA-256:

`628be5879d34a0a2f7c53ca493279c0a797f4ad45575988083d58e7b27f2945f`

## Current and proposed state machines

Current R.9H state:

`PROPOSAL_PREPARED -> OWNER_REVIEW_REQUIRED -> IMPLEMENTATION_NOT_AUTHORIZED`

Proposed future execution lifecycle, not implemented:

`APPROVAL_ISSUED -> APPROVAL_REGISTERED_UNUSED -> APPROVAL_ATOMICALLY_CONSUMED_BEFORE_CONNECTION -> AUDIT_ATTEMPT_STARTED -> AUDIT_COMPLETED | AUDIT_FAILED | AUDIT_ABORTED`

Registration is not consumption. Consumption must be atomic and durable before
the first target connection. A crash cannot restore consumed authority. Every
retry requires a new approval. Missing terminal events remain detectable as
incomplete consumed attempts.

## Exact future approval bindings proposed

The future approval would bind its schema, unique ID, approval type, explicit
owner classification, issue/short-expiry times, one-use status, exact attempt,
Stages 1-3, audit-specification hash, reviewed implementation commit, current
research fingerprint, current PDF and owner-review hashes, database alias,
R.9F anchor, configuration hash and key, sampled algorithm/root, expected file
size, modification time and header hash, resolved sidecar state, one read-only
open mode, exact statement classes, prohibited operations, connection/time/
statement/row/database-byte/output budgets, output schemas, and every network,
broker, research, scoring, simulation, backtesting and trading prohibition.

Any mismatch is terminal and fail-closed. Generic language such as `continue`,
`approved`, or `go ahead` is not execution authority.

The template includes `template_only: true`, `usable: false`, and
`approval_payload_sha256: NOT_SEALED_PROPOSAL_ONLY`. Static tests prove that the
current `validate_audit_approval`, registration and consumption paths reject
the template.

## Proposed SQLite safety boundary

The proposal requires layered defenses: no-create `mode=ro`, verified
`query_only`, disabled extension loading, an authorizer, exact statement
templates, no caller SQL, escaped catalog-derived identifiers, a busy timeout,
progress-handler deadlines, deterministic ordering, one connection, bounded
results and outputs, identity checks, and closure plus terminal recording on
every path.

It explicitly states that URI `mode=ro` alone is insufficient. It does not
validate identity, approvals, sidecars or scope and does not independently stop
expensive reads, unsafe pragmas, attachment, extension loading, or disclosure.

## Unresolved design decisions

These are blockers before implementation:

1. Whether to require a quiescent database with no WAL/SHM/journal sidecars or
   bind and audit an exact reviewed sidecar set.
2. How to enforce a real target database-byte-read budget; Python's SQLite
   progress callback alone is insufficient.
3. Whether the attempt ID is explicitly named or derived from the sealed
   approval plus an operator nonce.
4. Which exact `EXPLAIN QUERY PLAN` templates, if any, are necessary for Stages
   1-3.
5. Whether declared but unenforced whole-process memory, wall-time and temporary
   storage limits are acceptable for the first audit.
6. A later exact decision on whether one short-lived audit approval may be
   created after implementation and review.

## Threat model

The proposal documents prevention, detection and fail-closed outcomes for
stale/substituted files, private-path leakage, approval forgery/replay,
duplicate registration, double consumption, races, crashes, concurrent
attempts, expiry, changed source/spec/report evidence, path redirection,
database and sidecar mutation, hidden writes, unbounded queries/outputs, SQL
injection, extension loading, network/broker access, accidental research
promotion, partial artifacts, missing terminal events and entry-point bypass.

## Alternative-source policy

If the local F&O database later fails qualification, lawful free alternatives
may be evaluated, including official NSE F&O bhavcopies for lawfully accessible
historical periods. This is not acquisition authority. Official status and
technical accessibility do not prove completeness, point-in-time fitness,
retention rights or research fitness. Access controls and licence restrictions
must not be bypassed, and every alternative must pass the same trust gates.

## Verification

- Focused R.9H plus R.9G review tests: 14 passed.
- Relevant R.7-R.9H suites: 169 passed, 3 expected Windows symlink skips.
- Complete root suite: 382 passed, 3 expected skips, 2 established
  development-only warnings.
- Separate Data-test suite: 289 passed, 0 failed, 0 errors, 0 skipped.
- Entrypoint reconciliation: 25 passed.
- JSON validation: 101 valid, 0 invalid.
- Python compilation: passed for `src`, `tools`, and `tests`.
- Proposal manifest and package-content hashes: reconciled.
- Entry-point delta: zero new executable production entry points, zero interlock
  changes, zero database connections and zero SQL/network/broker/analysis/
  trading capabilities added.
- Proposal private-path and secret scan: passed.
- PDFs v1-v4 and R.9F anchor/proposal hashes: unchanged.
- Git whitespace check: passed with Windows line-ending notices only.

New research fingerprint:

`1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`
over 252 files.

## Boundary and lifecycle result

PDF v4 retains its owner-review history but is now
`PDF_V4_STALE_AFTER_R9H_PROPOSAL_PREPARATION`. Its bytes were not changed.

The active interlock remains:

`R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE`

All required completion booleans remain false. No approval was issued,
registered or consumed. No interlock changed. No database connection, SQL,
schema inspection, market-row read, audit, alternative acquisition, analysis,
scoring, simulation, backtest, broker access, recommendation or trade occurred.

The next milestone must only generate PDF v5. That PDF must summarize this
proposal and unresolved decisions, and must be reviewed by the owner before any
interlock-change implementation can be considered.

`FNO_PRODUCTION_AUDIT_BOUNDARY_PROPOSAL_PREPARED`
