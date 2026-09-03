# Research R.9F - Exact Production Locator Binding Preparation

## Outcome

The owner-approved filesystem-only locator-binding preparation completed
successfully. The target was safely resolved and sampled exactly once without a
SQLite connection, SQL, schema inspection, market-row access, audit execution,
analysis, backtesting, broker activity, or trading.

The lifecycle result is `FNO_PRODUCTION_LOCATOR_BINDING_PREPARED`. This is a
sanitized sampled-identity anchor, not database qualification and not production
activation.

## Baseline and authorization

- Starting commit: `de3e17a0aa772506d2b967c5bc3ff3d4714d8564`.
- Approved PDF v3 SHA-256:
  `75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2`.
- Approved R.9D research fingerprint:
  `f7978db65c011c0dccf43dfd94623528a2e9672cc40c8c8505cb7666d6a69f38`.
- Owner-approved scope: `EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION`.
- Exact ceremony implementation commit:
  `816333959097519297b3095da9c81a1677f50bf8`.

Synthetic destructive and failure-path testing completed before the production
locator was read. The implementation was committed cleanly before the one real
pass, allowing the anchor to bind an exact source commit.

## Locator source and privacy

The only configured locator read was `paths.fno_db` from
`Data test/config/config.toml`. The configuration file SHA-256 is
`cb68999f6e0dd16796d017f1104cc630483ada44ed1959143b99c9e9d11d29a2`.
No unrelated configuration value was parsed or emitted.

The target is represented in tracked evidence only as
`PRIVATE_FNO_DATABASE_V1`. The absolute configured and resolved paths, user
profile, and machine-specific directories do not appear in tracked evidence,
reports, logs, exceptions, or console output. A private machine-local result is
stored under the ignored `artifacts/` boundary. Its presence and Git-ignore rule
were verified without reading or displaying its contents after creation.

Path checks established that the locator was non-empty, the target existed, the
configured and resolved path did not differ, and the resolved target was a
regular file with no target symlink or reparse status. No file or sidecar was
created, modified, renamed, moved, copied, repaired, or deleted.

## Bounded raw-byte identity

The 100-byte header carried the expected SQLite magic. Only the format prefix
was checked; no database page or schema field was interpreted. Header SHA-256:
`9d708fa6ca29946338e85c37c74cfd058312013721a348278981756067faedc2`.

The sampling algorithm was `ORDERED_64_POSITION_SAMPLED_IDENTITY_V1`:

- first chunk;
- last chunk;
- 62 deterministic evenly distributed interior offsets;
- 4 MiB maximum chunk size;
- exact duplicate-offset removal;
- ordered canonical offset, length, and chunk-hash records;
- SHA-256 of those ordered records as the sampled-identity root.

The file was large enough to produce 64 unique chunks. Sampled chunk bytes were
268,435,456. Total raw bytes read were exactly 268,435,556 because the first
header read was reused in the first chunk and only the 100-byte final header
comparison added to sampled bytes.

Sampled-identity root:
`b1b8c0ca1338d477987da28e6d9647b151c120a0eac7bb17c9e9293edfd4bc47`.

This is not a full-file SHA-256. Unchanged sampled chunks do not prove unchanged
unsampled bytes. Modification time is metadata, not identity.

## Stability and artifacts

Before/after size, modification time, file identity, regular-file status,
link/reparse status, and 100-byte header hash matched. The verdict is
`STABLE_DURING_SINGLE_BOUNDED_PASS`. The pass was not retried.

- Sanitized anchor:
  `evidence/fno_locator_binding_v1/anchor.json`.
- Anchor SHA-256:
  `115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc`.
- Binding proposal:
  `proposals/fno_locator_binding_v1/binding_proposal.json`.
- Proposal SHA-256:
  `995524b670dc95b717fa7d4b27935c788d661bcf75b8f7f4400d76831a8f434f`.
- Private raw result: present under ignored `artifacts/`; not committed.

Both tracked objects use deterministic canonical JSON and explicit schema
versions. The proposal is `PENDING_PDF_V4_AND_EXPLICIT_OWNER_REVIEW`, requests
no connection, audit, or activation, and remains ineligible for production
activation.

## Non-activation proof

The sanitized anchor records:

```text
database_connected: false
sql_executed: false
schema_inspected: false
market_rows_read: false
audit_started: false
analysis_started: false
backtest_started: false
trading_enabled: false
production_activation_eligible: false
```

The production locator state remains
`PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING`. The interlock
`R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` was not removed or weakened. No
production registry, activation object, approval, consumption, or attempt was
created.

## Research-state and next report gate

R.9F changed research-relevant source, specifications, and binding evidence. The
research fingerprint is now
`6218f979610ae66562ab070b55ef2e270b4d31ef52c9ccd78c7e877f194672db`
over 242 files. PDF v3 is therefore preserved as approved historical evidence
but marked `PDF_V3_STALE_AFTER_R9F_BINDING_PREPARATION`.

PDF v4 is now mandatory. The next separate milestone may only generate and
obtain owner review of PDF v4 for
`EXACT_BINDING_REVIEW_AND_INTERLOCK_REMOVAL_PROPOSAL_ONLY`. It may not implement
interlock removal, connect to SQLite, create an audit approval, execute Stages
1-3, inspect market rows, analyze, backtest, score, recommend, access a broker,
or trade.

## Verification

- Focused R.9F suite: 24 passed, 1 skipped.
- Combined R.7-R.9F governance suite: 146 passed, 3 skipped.
- Complete root suite: 359 passed, 3 skipped, with the two established
  development-only warnings.
- Separate Data-test suite: 289 passed with its established dependency and
  development-only warnings.
- JSON validation, Python compilation, entry-point reconciliation, private-path
  and secret scans, protected-evidence comparison, PDF v3 byte preservation,
  research-fingerprint reconciliation, and Git whitespace checks: passed.

The platform-specific symlink test remains skipped where Windows privileges are
unavailable; mocked reparse rejection and the existing direct path guards pass.

FNO_PRODUCTION_LOCATOR_BINDING_PREPARED
