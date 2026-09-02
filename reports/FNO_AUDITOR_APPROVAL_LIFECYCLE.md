# F&O Auditor Approval Lifecycle

## Separate authority

The auditor accepts only the typed
`LOCAL_DATA_AUDIT_STAGE_1_3_APPROVAL_V1`. A governed market-research approval,
the R.9A template, conversational permission, or a modified payload is invalid.

An approval binds the proposal ID and four exact proposal hashes, the synthetic
locator declaration, the sampled database identity root, stages `(1, 2, 3)`,
the exact resource contract, all nine permitted outputs, issue/expiry times,
one-use status and synthetic fixture classification. The payload is sealed by
canonical SHA-256 and must match the exact registered object.

## Registration and consumption

Registration validates purpose, payload, scope and expiry and rejects duplicate
IDs. Before consumption, the entry point performs only bounded filesystem
identity work: containment, regular-file/header checks and sampled reads. It
does not call SQLite or read market rows.

After matching the approval's database identity, the registry atomically checks
the exact registered object and records its attempt ID under a lock. This occurs
before `sqlite3.connect`. Reuse fails before creating a second attempt or
opening a connection. Once consumed, the approval remains consumed whether the
attempt completes, aborts or fails.

The R.9B registry is process-local and synthetic-only. It is deliberately
unsuitable for a real audit. Production enablement requires a durable reviewed
registration mechanism and a separate commit; no approval object for the real
database is created or consumed here.
