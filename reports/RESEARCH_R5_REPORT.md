# Research R.5 — First Governed Run Proposal and Synthetic Canary Readiness

## Baseline and scope

R.5 began from clean, synchronized `main` commit `c689cb8`. It reviewed the
complete R.3–R.4 governance, approval, preflight, importer, schemas, tests and
synthetic fixtures. No real governance registry or catalog was changed. No
family was registered, preregistration locked, usable approval issued, gateway
run started, approval consumed or canonical evidence created.

No market, broker or external network was contacted. No hypothesis, metric,
quarantined alpha row or validation/test data was accessed. Historical trust
verdicts and protected evidence remain authoritative and unchanged.

## Prepared proposal

The quarantined `proposals/first_governed_run` package defines family
`governance_canary__v1`, experiment `governance_canary_execution_v1__v1`, a
committed three-row synthetic fixture, exact candidate contracts, deterministic
outputs, an unsealed approval template, conservative resource envelope and
operator checklist. Every proposal object is hash-addressed by the proposal
manifest and marked collectively as proposal-only and unauthorized.

The proposed runner accepts only the declared fixture and produces three known
artifacts. Its lifecycle result is `INFRASTRUCTURE_CANARY_COMPLETED`, which the
governance contract now recognizes as permanently nonpromotable and restricts
to the dedicated canary family. The canonical importer rejects any attempt to
claim that lifecycle as promotable or use it for another family.

## Approval and runtime binding boundary

The committed proposed approval remains `template_only=true`, has placeholder
issue/expiry and identity fields, and has no usable payload hash. It cannot be
registered or executed. The candidate input contains an explicit future Git
commit binding marker because a commit cannot contain its own hash. A later
ceremony must bind the exact clean committed source and actual environment,
recompute and display the input hash, then obtain a separate explicit approval
tied to every final hash.

Approval of R.5, silence, earlier conversation or “continue” is not execution
authorization. The exact remaining boundary is a separate affirmative response
to the hash-bound question in `FIRST_GOVERNED_CANARY_REVIEW_CHECKLIST.md`.

## Resource truth

The proposal declares one attempt, five wall-clock seconds, 64 MiB memory,
32 KiB maximum disk output and four bundle artifacts including the root
manifest. One attempt is enforced by approval consumption. Wall time and memory
remain `DECLARED_NOT_ENFORCED`; R.5 does not misstate them as process controls.
The estimate is conservative and based on static deterministic output plus
ordinary unit tests, not a governed execution.

## Preflight forecast

Offline temporary-directory tests exercise all six states: proposal-only,
family-only, preregistration-ready/approval-missing, exact unused approval,
consumed approval and attempted reuse. Only the exact unused temporary approval
state previews as permitted. The simulation appends temporary forecast events
but never invokes the gateway, creates a run directory or writes canonical
evidence.

## Entry points and research isolation

The R.4 inventory remains unchanged. R.5 adds one direct callable runner,
classified `DEVELOPMENT_ONLY_NONCANONICAL` when called outside the gateway.
The versioned R.5 inventory delta produces effective totals of two governed,
65 development-only, two deprecated and zero unsafe bypasses. The runner uses
only Python standard-library file operations and neutral governance hashing; it
has no network, provider, research, scoring, portfolio, Streamlit or trading
dependency.

## What remains blocked

The proposal changes no historical-population, identity, inactive-security,
terminal-outcome, corporate-action, benchmark, archive, retention or official
access capability. Real cross-sectional research, momentum promotion, Slice B,
production scores and trading recommendations remain blocked by their existing
trust and approval gates.

## Verification

- Focused R.5 proposal suite: **9 passed**.
- Combined R.3–R.5 governance suite: **64 passed**.
- Complete root suite: **200 passed**, with two expected deprecated-runner
  development-boundary warnings.
- Complete separate Data-test suite: **289 passed**, with the existing SWIG
  deprecations and expected noncanonical-log boundary warnings.
- JSON/schema/proposal validation: **56 versioned objects valid**.
- Python compilation: **passed**.
- Entry-point inventory base plus R.5 delta: **69 accounted for; zero unsafe
  bypasses**.
- Proposal review: deterministic, side-effect-free and explicitly unauthorized.
- Protected-evidence diff against `c689cb8`: **empty**.
- `git diff --check`: **passed** (Windows line-ending notices only).

## Primary decision

`FIRST_GOVERNED_CANARY_PROPOSAL_READY_FOR_USER_REVIEW`
