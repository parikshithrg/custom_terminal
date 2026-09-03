# F&O Durable Approval and Event Model

## Storage separation

The R.9D registry is a dedicated SQLite governance store, separate from the F&O
database, its source directory, research governance catalogs, canonical market
evidence, and legacy evidence. R.9D initializes it only inside marked pytest
temporary directories. No production registry was created.

## Immutable authority

The `approvals` table stores exact canonical approval JSON and its payload
SHA-256. Update and delete triggers make approvals immutable. Registration uses
`BEGIN IMMEDIATE`, rejects duplicate IDs and payloads, and appends a chained
`APPROVAL_REGISTERED` event.

The immutable `consumptions` table is the one-use authority. Atomic consumption
validates the exact approval before a `BEGIN IMMEDIATE` transaction inserts the
unique approval-to-attempt binding. The attempt projection records
`CONSUMED_BEFORE_CONNECTION`; the hash-chained event ledger independently
records the same transition. A second process cannot consume the approval.

## Crash and terminal behavior

- Crash before the transaction commits: approval remains unused.
- Crash after consumption: approval remains consumed and the incomplete attempt
  is detectable.
- Normal completion, controlled abort, and unexpected failure append distinct
  terminal events.
- Approval reuse after process restart fails against durable state.

Event rows are append-only. Every event binds its sequence, type, approval,
attempt, sanitized detail, timestamp, and previous-event hash. Verification
recomputes approval hashes and the complete event chain and reconciles the
attempt projection. Ordinary updates/deletes are rejected; deliberate test
corruption is detected.

## Security truth

The registry is tamper-evident within the application contract, not physically
tamper-proof against the filesystem owner. It rejects private absolute paths
and secret-like values in approval payloads. Approval identity uses sanitized
owner classifications, not personal paths. Backups are not claimed.
