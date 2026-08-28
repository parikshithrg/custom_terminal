# First Governed Run Approval Boundary

## Purpose

`governed_run_approval_v1` is a prospective, exact, one-use authorization. It
does not authorize any current hypothesis. The committed template has
`template_only=true`, zero limits and placeholders, so it cannot be registered
or executed.

An issued approval binds the family and experiment IDs/versions, the complete
locked-preregistration hash (also the R.4 executable experiment-specification
hash), input-declaration hash, exact dataset snapshot triples, permitted split,
gateway action, operational limits, issue/expiry times, local approving
identity and reason. Its payload hash covers every field except the hash field
itself.

## Fail-closed behavior

Missing, incomplete, template, altered, expired, unregistered, reused or
mismatched approvals fail before an attempt directory or runner invocation.
Changing the family, preregistration, input declaration, dataset snapshot,
split or runner requires a new exact approval. Validation permission does not
permit test access; test requires both the R.3 split event and explicit `test`
permission in the approval.

Registration preserves the exact approval as immutable JSON and appends
`RUN_APPROVAL_REGISTERED`. Preflight reads that object and event but writes
nothing. The approval is consumed by the single `RUN_STARTED` event that is
appended immediately before calling the runner. Completed, failed and aborted
root manifests retain the approval ID, file hash, payload hash and consuming
event ID/hash.

## Atomicity and crash boundary

There is no separate mutable “used” flag. A matching `RUN_STARTED` event is the
one authoritative consumption record, so there is no gap between a start event
and approval consumption. A crash after `RUN_AUTHORIZED` but before
`RUN_STARTED` leaves the approval unconsumed and the runner uncalled. A crash
after `RUN_STARTED` consumes the approval even if the process dies before a
final manifest; the incomplete catalog sequence is detectable and cannot be
canonically imported. This local JSONL design cannot guarantee recovery from
filesystem or power failure, but it fails closed rather than making a partial
bundle canonical.

## Compute-budget truth

The one-attempt limit is enforced by approval consumption. Wall-time and memory
values are currently declared operational limits only. The in-process Python
gateway does not terminate or isolate a runner at those thresholds, and both
fields are machine-labelled `DECLARED_NOT_ENFORCED`. They must not be described
as resource controls until a bounded worker/process implementation exists.

Approval to execute is not approval to interpret, confirm, promote, publish,
score, trade or deploy.
