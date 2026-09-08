# R.10H — Consolidated synthetic-platform readiness audit

## Decision

The synthetic platform is substantially demonstrated, but it is not yet ready
for the consolidated owner-review PDF. The root suite exposes eight stale
historical fingerprint diagnostics and one genuine stale entry-point inventory.
Both need a small, versioned forward repair that preserves every earlier review.

`CONDITIONAL_READINESS_REMEDIATIONS_REQUIRED`

Completion state:

`SYNTHETIC_PLATFORM_CONDITIONALLY_READY_REMEDIATIONS_REQUIRED`

This decision authorizes no data access, dependency adoption, production audit,
research run, score, recommendation, broker action or trade.

## Evidence and reproducibility

R.10A–R.10G form the intended chain: point-in-time ingestion, incremental
rebuilding, security events/terminal economics, calendars/session clocks,
score/confidence semantics, immutable publication, then portfolio/mandate
policy. All 208 manifest-bound artifact byte hashes and seven root-manifest byte
hashes match. All predecessor references match. Thirty-four Parquet objects are
readable. Momentum v1 (`1eed7fd...`) and its golden expected fixture
(`d3f7284...`) remain unchanged. The R.10A holdout remains unconsumed, all
evidence remains `SYNTHETIC_ONLY_NONCANONICAL`, promotion remains false and
external decisions remain `NO_DECISION` where decision fields exist.

Byte hashes, logical-table hashes, reproducible-core hashes, source-tree hashes
and research-state fingerprints are distinct identities. This audit never uses
one as a substitute for another. R.10A has a material provenance limitation: it
predates the clean-start protocol and binds a dirty-worktree fingerprint, while
R.10B–G record clean implementation starts. R.10F/G fixtures are source-defined
and lack separate machine-readable recipes.

## Strongest demonstrated capabilities

- Deterministic point-in-time/as-of filtering with later-vintage rejection.
- Typed synthetic facts, historical identity mechanics and explicit terminal
  uncertainty without destructive price adjustment.
- Incremental rebuild planning with clean-rebuild equivalence and preserved
  unaffected hashes.
- Calendar-aware execution clocks, overlap purge and embargo mechanics.
- Separate prediction, economic and portfolio evidence.
- Training-only transforms, score/confidence separation and a multiple-testing
  ledger, all explicitly synthetic.
- Immutable evidence publication, a thin mapping facade and mandate-aware
  portfolio policy whose only external answer is `NO_DECISION`.
- No broker mutation or trade-execution path in R.10A–G.

## Test-quality assessment

The synthetic suite is meaningful: it uses deterministic known answers,
leakage/mutation challenges, failure injection, historical-hash preservation,
incremental/clean equivalence and lifecycle barriers. It is not independent
economic validation. Some oracles and evidence builders share helpers, some
catalog checks are declaration-heavy, the calendar is fictional, and no
representative concurrency, scale, disk-corruption or real distribution-shift
test has occurred. Four Windows symlink/reparse tests were skipped because link
creation privileges were unavailable.

## Verification results

- Standard root suite: **704 passed, 4 skipped, 9 failed, 2 warnings** in
  412.57 seconds.
- Separate `Data test` suite after static confirmation of synthetic temporary
  inputs: **289 passed**.
- Focused R.10A–G/R.9P/R.9D/R.3 preservation and boundary suite:
  **114 passed**.
- JSON and Parquet validation: **PASS**; 34 Parquet objects readable.
- Manifest reconciliation: **PASS**; 208/208 artifact hashes and all chained
  predecessor roots match.
- Python compilation, dependency inventory, secret/private-path scan and Git
  whitespace checks are recorded in the audit manifest.

The nine root failures are not synthetic-engine failures. Eight compare old
owner-reviewed fingerprints with the legitimately changed current research
tree. The synthetic operating model superseded repeated approvals for bounded
synthetic work, but historical review records must remain unchanged. The ninth
is a genuine forward inventory regression: fourteen R.9J–R.10G executable tools
are absent from the v1 inventory/deltas. The safe remedy is a new current
fingerprint/review contract and a new cumulative inventory or delta—never
editing old records or weakening exclusions.

## Entrypoints and F&O route

The fourteen R.9J–R.10G tools are offline, synthetic and non-promoting. Five
restricted R.9M/N/P tools can use APSW, but production packages do not depend on
APSW. The R.9D production interlock remains active and unchanged. The local F&O
database remains `LOCATED_AND_SAMPLED_NOT_QUALIFIED`; no production audit is
authorized, directory quiescence is unproven and official schema evidence is
pending.

A future owner review may present three separate choices, in order: (1) adopt a
pinned APSW production dependency, (2) implement the restricted production
audit boundary, and (3) authorize one bounded metadata/provenance audit. The
third is not executable until the first two and their safety conditions are
resolved. None is approved by this report.

## Real-data and product readiness

The free official NSE historical route remains blocked: the broad equity data
is survivor-selected, the A.8 population sample has only 3/12 pairs, written
access/retention clarification is unresolved, and corporate actions, terminal
economics, benchmark identity and historical costs remain incomplete. Kite is
usable only for bounded current read-only snapshots and is not a historical
universe. SEBI/BSE evidence can supplement events but does not reconstruct the
full NSE population. AMFI is not applicable to equity survivorship.

The smallest lawful candidate is one manually supplied, terms-cleared, dated
official NSE security snapshot paired with its bhavcopy for a locked A.8 date,
with explicit provenance and retention review. It must not be acquired until
the permission gate is resolved.

Machinery readiness is substantial. Data readiness is blocked, research and
economic readiness are absent, immutable synthetic publication mechanics are
demonstrated, and product UI readiness is intentionally deferred. There is no
active edge or actionable score.

## Required owner decisions

No owner decision can safely authorize real work from this audit alone. The
future consolidated review should keep separate: APSW adoption, restricted F&O
boundary implementation, one bounded F&O metadata audit, and one bounded lawful
official-data qualification. Broker/trading actions remain prohibited.

## Next milestone

Create one versioned governance remediation that (a) reconciles reviewed-then
versus current-now fingerprints and (b) inventories R.9J–R.10G entrypoints,
while proving every historical review artifact is byte-identical. Then run the
root suite. If green, proceed to `CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF`.

No PDF was generated in R.10H.
