# F&O Auditor Adversarial Tests

## Fixture boundary

All R.9B execution tests create tiny SQLite databases in pytest temporary
directories. Each root carries an explicit `.synthetic_audit_fixture` marker.
The tests never import the production TOML parser, read the production locator,
or use network, broker, research, scoring or backtesting dependencies.

## Covered failures

The focused suite verifies dry-run no-connect behavior; missing, template,
expired, altered, unregistered and reused approvals; proposal, locator,
database-identity, stage, resource and output mismatches; and rejection of a
market-research approval substitute. Production classification and
`paths.fno_db` are rejected.

Filesystem tests cover path escape, symlink rejection where the Windows test
environment permits symlink creation, small-file chunk deduplication, database
mutation, sidecar appearance, Stage 3 file/byte limits, provenance symlinks,
secret non-disclosure, output-byte limits and unexpected outputs.

SQLite tests cover catalog-only reads, read-only planning, rejection of
user-table reads, DDL, DML, attach/detach, vacuum, reindex, analyze, journal and
writable pragmas, extension loading, statement count and progress-handler
cancellation. Completion, abort and unexpected failure paths verify one-use
approval consumption and terminal finalization.

## Result

The focused R.9B suite passes. Two symlink cases are skipped on the current
Windows environment because unprivileged symlink creation is unavailable; the
non-symlink path-escape checks pass, and the production code rejects symlinks
before resolving a target.

No real F&O database test exists or ran.
