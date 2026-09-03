# F&O Production-Enablement Design

## Purpose and present state

R.9D implements the governance boundary needed before a future Stage 1-3 local
F&O audit can be considered. It does not implement production access. The
locator state is:

`PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING`

The production entry point accepts no database path. It has no configuration
parser and never calls the supplied configuration reader. It fails before path
resolution, filesystem identity reads, attempt creation, or SQLite connection.
R.9D did not read `paths.fno_db`.

## Preserved audit scope

The eventual scope remains limited to bounded sampled file identity, SQLite
read-only safety and catalog metadata, and already-local provenance and
retention evidence. Stages 4-6, market rows, coverage, integrity statistics,
`quick_check`, `integrity_check`, full scans, exports, external acquisition,
analysis, scores, strategies, recommendations, broker operations, and trading
remain excluded.

## Later ceremony

The minimum later sequence is:

```text
separately approved locator-resolution ceremony
  -> bounded filesystem identity only
  -> sanitized identity and proposal display
  -> explicit owner approval
  -> durable approval registration
  -> atomic one-use consumption
  -> first SQLite connection
  -> Stage 1-3 audit
```

PDF v2 approved only R.9D design and synthetic tests. It did not authorize the
locator-resolution ceremony. A future PDF v3 and review must cover exact
binding preparation. Absolute paths must remain outside committed and emitted
evidence; a redacted alias plus exact configuration hash and sampled identity
root provide the verifiable binding.

## Deliberate interlock

`R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE` is always unsatisfied. The
activation template requires a future reviewed PDF v3 binding but contains null
approval, locator, database-identity, issue, expiry, owner, and payload-hash
fields. No mutable Boolean can enable the path.

Production access remains disabled.
