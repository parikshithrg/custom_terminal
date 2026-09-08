# R.10I — Governance forward remediation

## Result

R.10I resolves the two forward-governance defects found by R.10H without
rewriting historical reviews, PDFs, manifests or synthetic evidence.

`GOVERNANCE_FORWARD_REMEDIATION_COMPLETE_READY_FOR_CONSOLIDATED_PDF`

This state means only that the consolidated owner-review PDF may be generated.
It authorizes no real/private data access, dependency adoption, database audit,
research, simulation, backtest, score, recommendation, broker action or trade.

## Starting checkpoint and reproduced failures

- Starting branch and commit: `main` at
  `e7c437504eb4e971a5b5fb9fe38fa7a05da17801`.
- Working tree: clean and synchronized at task start.
- R.10H decision: `CONDITIONAL_READINESS_REMEDIATIONS_REQUIRED`.
- The exact nine R.10H failures reproduced: eight stale historical-fingerprint
  assumptions and one incomplete executable-entrypoint inventory.
- R.10H's 208 artifact hashes, seven evidence-root hashes and 34 readable
  Parquet objects validated before remediation.

## Root causes

The historical review tests used policy v1 both as an immutable record of the
reviewed state and as a moving calculation of today's repository. Later R.10
synthetic infrastructure legitimately changed today's included files, so those
two meanings diverged. Merely replacing the eight expected hashes would have
destroyed the distinction and still implied that an old review covered new
scope.

The entrypoint test still assembled the v1 inventory and early deltas. Fourteen
offline R.9J–R.10G tools had been added since, so current discovery correctly
reported them as unaccounted.

## Fingerprint reconciliation semantics

Policy v1 is now explicitly a sealed historical compatibility projection. Its
last reviewed-era state remains `1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef`
over 252 files, bound to the original v5–v7 generation manifests. It cannot pass
a current execution/report gate.

Policy v2 retains the exact v1 include globs, exclude globs and canonical
inventory algorithm, but computes the current repository independently. The
clean R.10I implementation checkpoint is:

- source commit: `89ba5b77708ac867688e0f4b9381d3bf47e31263`;
- current fingerprint:
  `e0870bd050c2906f1aa81ead3ffe66871031db106e5ee39c046c5a011184759c`;
- current inventory: 280 research-state files;
- execution start: clean.

The reconciliation ledger records each review's immutable
`reviewed_fingerprint`, exact review-record byte hash and `review_scope`, then
classifies its relationship to the current state. Reviews v1–v5 are all
`HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE`. Authenticity is preserved;
authority is not extended. Tampering with a checkpoint, current fingerprint,
historical hash, review scope, policy rule or exclusion fails closed.

## Historical preservation

Review records v1–v5, historical PDFs, generation manifests, R.10A–R.10H
evidence, Momentum v1 and its golden fixture remain byte-identical. The two
historical tests bound directly by PDF manifests were restored byte-for-byte
after the first unrestricted run exposed that preservation constraint. The
R.10A holdout remains `UNCONSUMED_SYNTHETIC_HOLDOUT`. Lifecycle, promotion,
publication, F&O production and trading interlocks are unchanged.

## Cumulative entrypoint inventory

`laboratory_entrypoint_inventory_v2` is a cumulative, forward inventory built
from repository discovery rather than the R.10H list. It contains all 77
applicable non-test Python files detected by the unchanged `__main__` rule,
exactly once, with a current source hash and explicit capabilities.

The former current contract accounted for 63 entrypoints. V2 adds the fourteen
missing R.9J–R.10G tools. They are recorded as offline, synthetic-only,
noncanonical and nonpromoting. Five R.9M/R.9N/R.9P tools may use APSW only in
the restricted synthetic evaluation; APSW remains absent from production
dependencies. Inventorying a capability grants no additional permission.

The historical v1 inventory and all historical delta files are unchanged. V2
is the sole current enforcement inventory and rejects duplicates, stale source
hashes, missing classifications and newly unaccounted entrypoints.

## Files added or changed

- Added `src/research_contracts/fingerprint_reconciliation.py` and public
  exports.
- Added `specs/pre_research_review_policy_v2.json`.
- Added `specs/laboratory_entrypoint_inventory_v2.json`.
- Added the excluded, current-state reconciliation checkpoint under
  `docs/project_status/`.
- Added the narrowly scoped governance artifact builder and R.10I tests.
- Updated the current inventory test and historical-policy gate tests to reject
  authority expansion.
- Added this report, completion record and final manifest.

No production market, research, scoring, portfolio, UI, provider or broker
implementation changed.

## Validation

- Reproduced baseline diagnostics: **9 failed**, exactly as R.10H recorded.
- Focused final reconciliation/inventory set: **18 passed**.
- Additional historical-policy rejection set: **13 passed**.
- Complete root suite: **730 passed, 4 skipped, 2 warnings** in 405.41 seconds.
- Separate offline Data-test suite: **289 passed**.
- The four skips are the established Windows symlink/reparse privilege cases.
- The two warnings are the established deprecated Slice A development-only
  `UNGOVERNED_NONCANONICAL_OUTPUT` warnings.
- JSON validation, Python compilation, Git whitespace, inventory/source hashes,
  dependency checks, preservation hashes and private-path/secret scans: pass.
- R.10A–R.10G: 208/208 artifact hashes valid, seven root manifests unchanged,
  and 34/34 Parquet schemas readable.

Two intermediate full runs were intentionally retained in the record: the
first found two altered historical test-byte bindings; the second found one
legacy test whose mutation scenario needed to assert rejection under the new
policy. Both causes were repaired without weakening a gate. The final complete
run is green.

## Remaining limitations

- The sealed v1 projection has no retained 252-row inventory, so it is verified
  through the original reviewed generation manifests and record hashes rather
  than regenerated as today's inventory. Policy v2 is the authoritative current
  calculation.
- This remediation proves governance mechanics only. It does not improve data
  quality, real-data availability, economic evidence, scale readiness or edge
  validity.
- The known Windows symlink/reparse limitation remains platform-dependent.

## Next milestone

`CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF`

That PDF must be generated and presented for owner review before any real-data
qualification, backtesting, simulation, market-sentiment scoring or stock
scoring begins. R.10I does not generate it.
