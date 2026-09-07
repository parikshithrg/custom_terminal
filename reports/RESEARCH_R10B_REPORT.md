# R.10B synthetic incremental ingestion and dependency-aware rebuilding

## Result

R.10B validates a provider-neutral, synthetic-only incremental ingestion and
dependency-rebuild boundary. It does not validate market data, momentum, a
score, profitability, or production readiness.

Implementation was checkpointed first. The final implementation checkpoint is
commit `2ccbc4844e4c2156595c5097dde6c80ecb7c42b0`. Evidence generation began with
an empty `git status --porcelain`; the root manifest records
`execution_start_dirty: false`. Creating the immutable run then produced the
expected untracked evidence for the separate evidence commit.

## R.10A components reused

The slice reuses R.10A's provider-neutral object contract, causal
`materialize_as_of` interface, immutable hashes, stable identity concepts and
the existing research dependency boundaries. It does not change R.10A's
fixture, evidence, momentum feature, outcome, universe rule or fold behavior.

The R.10A root manifest remains byte-identical with SHA-256
`ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580`.

## New contracts

- `IncrementalRawStore` publishes payload and manifest together through an
  atomic directory rename. Stable source identity is indexed separately from
  content identity. Identical bytes are idempotent; different bytes under the
  same immutable source identity fail as
  `IMMUTABLE_SOURCE_IDENTITY_CONFLICT`.
- `SchemaRegistry` binds dataset, accepted raw schema, explicit normalized
  output version, required and optional fields, type/coercion policy, unknown-
  field policy, quality policy, availability policy and parser implementation
  hash.
- `DependencyGraph` records node type/version, exact input and definition
  hashes, logical output hash, temporal scope, parents, downstream nodes,
  parameters, schema, environment and build state.
- The impact planner intersects the change domain, economic time, availability
  time, effective interval and instrument scope with declared node scopes.
- Selective reuse requires every relevant binding and output hash to match. A
  matching path alone has no authority.
- `canonical_table_hash` includes logical rows, dtypes, null representation,
  ordering keys and timezone-bearing dtypes. It is distinct from a container-
  file hash.
- Artifact-set publication stages all children, writes the root manifest last,
  and atomically exposes the completed directory.

## Synthetic update sequence

The versioned fixture covers an initial history, appended session, late-arriving
session, old price correction, universe-input correction, feature-only
correction, outcome-window correction, new listing, alias rename, terminal
update, benchmark correction, identical duplicate retrieval, immutable identity
conflict, malformed object, supported additive schema, and unsupported breaking
schema.

These use fictional identifiers and generic synthetic fields. Official NSE F&O
format status remains `PENDING_OFFICIAL_FORMAT_EVIDENCE`; no compatibility is
claimed.

## Schema drift results

- Exact `synthetic_bar_raw_v1` routed to
  `synthetic_incremental_bar_v1`.
- Additive `synthetic_bar_raw_v1_1`, including optional `trade_count`, routed to
  the explicitly distinct `synthetic_incremental_bar_v2`.
- Identity, terminal and benchmark updates used their own typed contracts.
- The malformed daily object was preserved raw and its row quarantined.
- The unknown breaking version was preserved raw and quarantined before
  downstream use with `UNKNOWN_SCHEMA_VERSION`.
- Tests also cover missing required columns, renamed columns, changed types,
  strict/permissive unknown fields, and mixed known schema versions. No migration
  is guessed.

## Rebuild and reuse results

Across 11 supported update stages, the ledger contains 231 node decisions:

- 94 `REBUILT_INPUT_CHANGED`;
- 137 `REUSED_HASH_IDENTICAL`.

The planner preserves the pre-availability snapshot for late observations and
corrections. Feature-only changes do not rebuild the historical universe.
Terminal changes preserve predictions and rebuild outcome/economic descendants.
Benchmark-only changes do not rebuild security features. Identity changes are
bounded by their knowledge and effective intervals.

Every ledger row records a named reason. Impact records retain the economic
event time, availability time and earliest affected downstream cutoff.

## Incremental versus clean equivalence

All 11 supported stages produced the same complete dependency graph as an
independently constructed clean candidate. Equality covers output hashes and
the node's input, definition, parameter, availability, schema and environment
bindings.

The point-in-time daily records were also materialized as logical tables. The
pre-correction and final logical hashes are separately recorded. The earlier
cutoff retains revision 1; the correction appears only after publication and
availability.

This slice validates dependency selection and canonical identity. It does not
claim that the compact evidence package repeats R.10A's full economic backtest
at every update stage; R.10A remains the evidence for those calculation
engines.

## Historical hash preservation

All 137 decisions classified as unaffected retained the exact prior node hash.
Tests explicitly preserve a pre-correction snapshot, pre-change fold, unrelated
feature dependencies and R.10A's committed evidence. New versions are linked by
dependency records; no old artifact is overwritten at its path.

## Failure recovery

- Interruptions after raw payload creation and after staged manifest creation
  leave only non-evidence staging and restart as a new verified ingestion.
- Interruption after atomic object publication but before identity-index
  publication restarts by verifying and reusing the immutable object.
- Conflicting partial final state fails closed.
- Artifact-set interruptions during child publication or before the root
  manifest expose no final run and leave an existing valid target untouched.
- Generator source staging is removed before final evidence publication.

Cleanup operations are rooted at exact generated staging paths.

## Evidence package

`docs/investigations/r10b/run_v1` is approximately 164 KB and contains:

- 14 initial/update raw-object manifests and their content-addressed payloads;
- four parser/schema contracts;
- initial and final dependency graphs;
- stage impact and rebuild plans;
- reuse/rebuild decision ledger;
- clean-equivalence results;
- historical hash-preservation results;
- failure-recovery results;
- logical-table hashes;
- a root manifest binding commit, clean execution start, source tree,
  environment, fixture, entry point, R.10A reference and every artifact hash.

## Verification

- R.10B implementation/foundation tests: 33 passed during checkpointing.
- R.10A/R.10B compatibility selection: 51 passed before the checkpoint, with
  no failures.
- Final R.10B implementation and evidence suite: 29 passed.
- Python compilation and Git whitespace checks pass.
- JSON, raw payload, artifact and dependency hashes reconcile.
- R.10A, momentum golden evidence, R.9P and the production interlock remain
  unchanged.
- No APSW production dependency, private configuration, real dataset, network,
  Kite, broker, Streamlit, scoring, recommendation or trading path was added.

## Limitations

- Synthetic fields deliberately do not claim official exchange schema parity.
- The dependency graph uses compact deterministic node identities; it does not
  establish real-data scale, vendor correction behavior or exchange-calendar
  coverage.
- Recovery tests inject controlled local failures, not operating-system or disk
  corruption.
- Market validity and economic validity remain completely untested.

## Next smallest synthetic task

Test security-master, corporate-action and terminal-outcome reconstruction for
synthetic mergers, demergers, splits, relistings and delistings, using this
incremental dependency machinery and no new approval ceremony.

`SYNTHETIC_INCREMENTAL_PIPELINE_VALIDATED_NONCANONICAL`
