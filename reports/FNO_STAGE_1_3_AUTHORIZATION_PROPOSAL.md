# Local F&O Audit Stages 1-3 - Authorization Proposal

## Proposal identity

- Proposal ID: `local_fno_audit_stage_1_3_v1`
- Classification: quarantined data-audit proposal
- Baseline: `b4768207a9a322f7ba676c0d3c47262b37afe44c`
- Requested authorization type: `LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1`
- Package content hash: `9eff345b453d1f0f0072c927f2a7dcb5b60cd98af6d9c415703fa0e504016acd`
- Proposal manifest SHA-256: `4fe0091ac405fbd5eac027038f6350b3b6a8bbe88d9141a982516b6489e95ed8`
- Current state: proposal only; not registered, sealed, approved or executable

The package is under
`docs/quarantined_proposals/local_fno_audit_stage_1_3/`. It is outside the
canonical market-research proposal tree because it is a planning-only data
audit request. This placement preserves the exact reviewed research-state
fingerprint and cannot grant execution authority.

## Exact requested stages

### Stage 1 - locate and freeze identity

After a separate exact approval, resolve only the approved `paths.fno_db`
configuration key, confirm a regular file, record size and modification time,
read the 100-byte SQLite header, and calculate the bounded 64-chunk identity.
Inspect only already-local backup and retention metadata. Never commit the
resolved personal path.

### Stage 2 - SQLite read-only safety and catalog

After the same approval and a successful Stage 1 identity freeze, open one
SQLite URI connection with `mode=ro`, enforce and verify `query_only`, install
a five-second busy timeout and progress deadline, inventory schema/catalog
metadata, and inspect later-stage query plans without executing those later
queries. Neither `quick_check` nor `integrity_check` is requested because their
runtime cannot be reliably bounded before catalog inspection.

### Stage 3 - local provenance and retention inventory

Inspect at most 500 already-local manifests, configuration files, documents,
ingestion scripts and raw-file inventory entries, subject to a 512 MiB read
budget. Record only existing evidence about report types, hashes, acquisition,
parsers, schema changes, corrections, vintages, backups and rights. Do not
acquire missing evidence or contact any external service.

## Operations not requested

Stages 4-6, market-row coverage/integrity checks, full scans, exports, outcomes,
returns, features, signals, scores, ranks, strategy work, sentiment, participant
positioning, recommendation generation, broker calls, trading, repair and every
database write are excluded. Interesting findings cannot expand scope.

## Approval boundary

The included approval object is an unusable template with null approval fields,
no approved stages and `usable=false`. A later approval must be data-audit
specific, exact, unexpired and one-use; it must bind the committed proposal
manifest, scope, resource envelope, expected outputs, locator configuration hash
and stages 1-3. A market-research approval cannot substitute for it.

The future implementation does not yet exist. Before any approved run, it must
be implemented, tested against synthetic fixtures, reviewed and committed. Its
default must remain proposal/dry-run mode, with the approval consumed before the
first database connection.

This proposal does not authorize the audit or any empirical research.
