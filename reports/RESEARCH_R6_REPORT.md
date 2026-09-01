# Research R.6B — Independent Canary Audit and Operational Closure

## Baseline and authorization boundary

R.6B started from clean, synchronized `main` commit `126aeed` and audited the
already completed attempt `governance-canary-attempt-126aeed-001`. Runtime
files were treated as untrusted evidence. The ceremony script was inspected as
data and never executed. R.6B did not rerun the canary, create or modify an
approval, invoke the gateway, import a second record, access market data or
execute a market hypothesis.

## Result

The independent audit found every required runtime object and produced zero
mismatches. It independently verified the approval file and payload; family,
preregistration, input and fixture; three runner artifacts; root manifest;
seven-event governance chain; governed-bundle inventory; and sole canonical
record. Exact values and comparison details are in
`reports/GOVERNED_CANARY_AUDIT.md`.

The exact approval was valid for 30 minutes, authorized one attempt and the
train split only, and was consumed by one `RUN_STARTED`. One terminal event
followed. Side-effect-free post-run preflight rejects reuse, and gateway source
ordering confirms rejection precedes runner invocation or attempt-directory
creation. No second execution was attempted.

The event order was `FAMILY_REGISTERED`, `PREREGISTRATION_CREATED`,
`PREREGISTRATION_LOCKED`, `RUN_APPROVAL_REGISTERED`, `RUN_AUTHORIZED`,
`RUN_STARTED`, `RUN_COMPLETED`. The governance hash chain is intact. The final
bundle has four files (5,017 bytes), of which three runner outputs total 618
bytes. No temporary sibling or unexpected output exists. Canonical validation
is `PASS` and exactly one canonical record exists. The canonical catalog does
not implement record chaining, so only the exact sole-record and file hash are
claimed.

## Evidence anchor and entry points

After the audit passed, R.6B added the sanitized versioned anchor
`evidence/governance/canary_execution_anchor_v1.json` and its contract. It
contains only declared identifiers, hashes, status, audit timestamp and the
exact relative ignored attempt location. Raw ceremony and runtime evidence remains
ignored and local; none was staged for Git.

The read-only `audit_canary_evidence` callable is the only entry-point addition.
The R.6 inventory delta accounts for 70 entry points: three governed, 65
development-only, two deprecated and zero unsafe bypasses. The auditor cannot
register, authorize, execute, import or mutate evidence.

## Promotion and protected evidence

The lifecycle remains exactly `INFRASTRUCTURE_CANARY_COMPLETED`, with
`promotion_eligible=false`. The three-row synthetic fixture cannot satisfy
train, validation, test, replication, production or actionable-score gates.
This is not a successful investment experiment. No historical trust verdict,
legacy evidence file, momentum artifact, score or decision surface changed.

The four protected evidence hashes remained unchanged:

- divergence: `9f5fa4bf8211eec4f4e9c86a88dc289f0ff64490543af04720e5a6dacd190174`
- neutral ledger: `79df7b785fef5025f605e0cef4a6dd49a039b034d66a92ea0aaafd99056fb392`
- frozen log: `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d`
- legacy catalog: `ef62824f3fab15c192f515eea2074752bcfe954673ad3570c8deb33d9e887cf5`

## Resource truth and remaining limitations

The one-attempt limit was enforced through approval consumption. The five-second
wall-time and 64 MiB memory limits remain `DECLARED_NOT_ENFORCED`. Actual peak
memory and an enforced-runtime measurement were not recorded. Filesystem-owner
tampering is detectable only relative to a separately preserved anchor.
Ignored local raw evidence still needs an explicit backup and retention policy.
A passing canary does not make historical market data trustworthy.

No existing contract needs revision to close R.6B. Canonical-catalog chaining,
enforced process limits and durable raw-evidence retention remain legitimate
future hardening work.

## Verification

- Focused R.6 audit suite: **13 passed**.
- Combined R.3–R.6 governance suite: **77 passed**.
- Complete root suite: **213 passed**, with two expected deprecated-runner
  development-boundary warnings.
- Complete separate Data-test suite: **289 passed**, with existing SWIG
  deprecations and expected noncanonical-log boundary warnings.
- JSON/schema validation: **61 versioned JSON objects parsed; anchor contract
  and inventory invariants passed**.
- Python compilation: **passed**.
- Entry-point inventory: **70 accounted for; zero unsafe bypasses**.
- Protected-evidence comparison against `126aeed`: **empty**.
- `git diff --check`: **passed** (Windows line-ending notices only).

## Next milestone

The safest next step is a separate R.7 planning milestone for legally
accessible free-source data capability. It should determine which bounded
questions official NSE, BSE, SEBI, AMFI, RBI, government and issuer evidence
can support, without acquiring a bulk archive or selecting/testing alpha.

## Primary decision

GOVERNED_CANARY_AUDIT_PASSED
