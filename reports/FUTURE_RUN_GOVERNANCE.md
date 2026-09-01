# Future Research-Run Governance

## Prospective boundary

R.3 governs future attempts only. The 32 R.2 rows remain
`LEGACY_EXPLORATORY_EVIDENCE`; no manifest is inferred for them. Direct
laboratory outputs remain possible for development, but must be marked
`UNGOVERNED_NONCANONICAL_OUTPUT` and are rejected by the canonical importer.

## Required flow

```text
current status PDF + exact research-state fingerprint
→ explicit post-generation owner review
→ report-gate validation (not execution authorization)
→
versioned family registration
→ complete preregistration
→ canonical hash and lock event
→ immutable input declaration and capability gate
→ split authorization
→ RUN_AUTHORIZED
→ temporary attempt directory
→ RUN_STARTED
→ declared synthetic/future runner
→ artifact validation and hashing
→ root manifest
→ atomic final directory
→ completion/failure/abort catalog event
→ canonical-import validation
```

## Permanent owner-review boundary

Beginning with R.7, every market-research family must reference the exact
current status PDF, PDF hash, source hash, research-state fingerprint, approved
review record and covered scope before its preregistration can lock. The same
binding is checked again during preflight and by the gateway before any attempt
directory or runner invocation. Missing, pending, stale, superseded, changed,
predated, generic, synthetic or scope-mismatched review evidence fails closed.

Owner approval of the PDF permits only preparation of a separate research
proposal. It is not a run approval. The existing exact one-use approval,
dataset, split and gateway requirements remain mandatory. The completed
infrastructure canary is historical non-market evidence and is not
retroactively invalidated.

## Family registry

`family_registry_contract_v1` requires stable family and version identities,
economic mechanism, category, parents and supersession, registered variants,
diagnostic scope, metric, horizon, multiplicity policy, thresholds, minimum
effective sample and permutation counts, datasets, capability requirements,
allowed splits, lifecycle and retirement state.

The registry writes one canonical JSON object for each family ID/version and a
`FAMILY_REGISTERED` event. A changed object at the same path is rejected. Any
change requires a new family version. R.3's committed registry anchor contains
zero substantive families; only test-local synthetic families were registered.

## Preregistration

`preregistration_contract_v1` makes the economic and execution contract,
datasets, split, inference, multiplicity, outputs, runner, configuration and
research classification mandatory. The canonical hash is recorded in both
`PREREGISTRATION_CREATED` and `PREREGISTRATION_LOCKED` events before a run can
be authorized. A missing or blank mandatory field fails before execution.

## Input binding and preflight

`input_declaration_contract_v1` binds dataset IDs, versions and SHA-256 values;
security-master, population, corporate-action, terminal, benchmark, cost and
calendar versions; configuration and code state; environment; parser and
feature versions; and the exact split version.

- Mutable dataset paths without hashes are rejected.
- The configuration hash must match the locked expected configuration.
- Benchmark and cost versions must match preregistration.
- Failed or unknown required capabilities reject preflight.
- Limited exploratory data can proceed only when explicitly declared
  permanently non-promotable.
- Kite/current-market inputs are rejected as historical evidence.
- Dirty state is captured with a fingerprint; it is not claimed to be
  prevented or securely erased.

## Root manifest and artifacts

Every started attempt—completed, failed or aborted—receives a
`root_run_manifest_contract_v1` manifest. It binds the preregistration,
authorization, split event, code/configuration/environment/input state, seeds,
timestamps, runner, artifact hashes and sizes, row counts, result state,
sanitized failure category, lifecycle and final catalog-event ID.

The runner receives only a temporary attempt directory. Declared artifacts are
hashed and inventoried. Unexpected files are listed separately and are not
canonical. Missing required outputs turn an apparent success into an explicit
failure. The completed directory is moved atomically to its immutable attempt
ID before the final event is appended. An existing attempt ID is rejected.

## Governance catalog

The append-only JSONL catalog supports the complete R.3 event vocabulary. Each
event contains an ID, timestamp, actor classification, previous-event hash,
object references and hashes, reason and resulting state. Event and sequence
validation detects changed content, broken links, duplicate IDs and invalid run
or test-access ordering relative to the preserved catalog anchor.

The chain does not prevent the filesystem owner from rewriting both the file
and all following hashes. It makes changes detectable relative to an
independently preserved head hash or repository commit; it is not a secure
append-only service or cryptographic access-control system.

## Canonical import

`market_intel.foundation.future_evidence` accepts only a valid governed bundle.
It verifies the registered family and experiment, locked preregistration,
input declaration, capability result, authorization and final catalog events,
split access, artifact hashes/sizes, completion state and promotion claims.

Completed bundles are classified `CANONICAL_COMPLETED_EVIDENCE`; failed and
aborted bundles are `CANONICAL_GOVERNED_ATTEMPT`. Neither classification alone
authorizes promotion. Legacy and future catalogs remain separate.
