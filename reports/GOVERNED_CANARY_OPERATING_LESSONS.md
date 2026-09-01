# Governed Canary Operating Lessons

## What the canary proved

The bounded synthetic run demonstrated that the repository can bind a locked
family, preregistration, declared input and runner to an exact short-lived
approval; consume that approval once; record a hash-linked governance event
sequence; finalize an atomic artifact bundle; and import exactly one validated
canonical record. Independent byte-level validation reproduced every declared
hash without rerunning the work.

The post-run rejection path is as important as completion: an already consumed
approval fails preflight, and gateway ordering rejects it before runner
invocation or attempt-directory creation.

## What it did not prove

The canary did not test a market hypothesis, acquire market data, establish
historical-population completeness, address survivorship or look-ahead bias,
validate a score, or authorize any portfolio or trading decision. Its three-row
synthetic result is permanently nonpromotable.

It also did not enforce the declared five-second wall-time or 64 MiB memory
limits. Actual peak memory and an independently enforced runtime were not
recorded. Those declarations must continue to be labelled
`DECLARED_NOT_ENFORCED`.

## Evidence operations

The tracked anchor is deliberately small: it records identifiers, hashes,
status and the relative ignored storage location. Raw approvals, catalogs,
scripts and run outputs remain outside Git. This avoids publishing runtime
material but creates an operational dependency on the local ignored artifact
directory. Before meaningful governed research, the project needs a documented
backup, retention, restore-verification and access policy for those bytes.

Hash anchors detect later filesystem-owner tampering only if the anchor itself
is preserved independently. The governance catalog has a verified hash chain.
The canonical catalog currently has one exact anchored record but no record
chain; adding canonical append-chain fields is a future hardening opportunity,
not a reason to rewrite this completed canary.

## Contract conclusion

No governance contract change is required to close this infrastructure canary.
The new auditor is read-only and recorded in the entry-point inventory as a
governed administrative audit callable, not an execution path. Future work may
add enforced process limits, canonical-catalog chaining and durable evidence
retention, but must not silently reinterpret the existing run.

## Safest next milestone

Research R.7 should be planning-only and assess free-source data capability
before any alpha testing. It should map bounded research questions to legally
accessible official evidence from NSE, BSE, SEBI, AMFI where relevant, RBI,
government publications and issuer filings; separate access from retention and
completeness; and define rejection gates. It should not acquire a bulk archive,
choose a profitable-looking strategy, reopen momentum/Slice B, or create
production scores or trading decisions.
