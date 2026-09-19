# Offline equity quality diagnostics v1

Implemented 2026-09-19 from baseline `141e1ba` after the owner directed work to
continue to the next recorded milestone. This is a read-only synthetic diagnostic
layer over the existing current-equity readiness result. It is not UI wiring or
provider qualification.

## Contract

The contract produces aggregate counts for implicated duplicate identities,
declared-universe gaps, unexpected identities, missing/invalid/nonfinite prices,
timestamp problems, incompatible semantics and source failures. It binds the
complete upstream readiness input/content hashes and a sanitized expected-universe
hash. No identities or prices are emitted.

Gap expectations require an explicit versioned synthetic session context. A
declared trading session can report expected gaps. A declared non-trading day
reports gap checking as not applicable, and an unknown session remains
indeterminate; neither is mislabelled as missing trading data. The contract never
infers a calendar or holiday.

Stronger synthetic fixtures cover duplicate identity, missing row/price,
nonfinite price, stale timestamp and incompatible currency together. Malformed
identities fail at the existing readiness boundary before diagnostics.

## Preservation and boundaries

Original immutable records and exact Decimal facts remain unchanged. The
diagnostic cannot interpolate or replace prices, substitute zero, fill gaps,
silently deduplicate records, select a provider, persist outputs, promote evidence
or become production eligible. It performs no network, file/database, wall-clock,
provider, UI or background operation.

F&O remains deferred, hidden and unqualified. Provider activation, Dashboard
wiring, exact-price live testing, research, retention changes and production use
remain separately gated.

## Next separately scoped milestone

Prepare the consumer/display eligibility decision for wiring equity prices and
data-health states into the Dashboard. Real values require separately established
source eligibility, display/caching permission, identity, currency, adjustment,
session and freshness evidence. Until then, the Dashboard remains synthetic.
