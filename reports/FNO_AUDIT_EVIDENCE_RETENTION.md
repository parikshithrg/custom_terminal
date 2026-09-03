# F&O Audit Evidence Retention

R.9D adds a task-scoped evidence store tested only with temporary synthetic
fixtures. Its root must be separate from the source database and provenance
directories and carry an explicit synthetic marker.

The store validates the complete output set before writing, enforces a total
byte budget, rejects unexpected names, writes into an attempt-specific
temporary directory, records exact artifact SHA-256 values, and atomically
renames the directory into its final immutable attempt name. An existing final
attempt cannot be replaced.

The root manifest binds the approval ID, attempt ID, terminal state, approval
event-ledger head, artifact hashes, and byte count. It states:

- restore verification: `RESTORE_NOT_TESTED_BACKUP_NOT_CLAIMED`;
- backup verified: `false`;
- retention: `LOCAL_TASK_SCOPED_SYNTHETIC_ONLY`;
- canonical: `false`;
- promotion eligible: `false`.

Application-level immutability does not make local storage physically
tamper-proof. No backup, restore, redistribution, or long-term retention claim
is made. The real database is never copied.
