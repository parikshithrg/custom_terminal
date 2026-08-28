# First Governed Canary Proposal

## Review status

This is a quarantined R.5 proposal. It is not a registered family, a locked
preregistration, an issued approval, an execution authorization, a run, or
canonical evidence. The machine-readable manifest explicitly records
`proposal_only=true` and `execution_authorized=false`.

## Exact identity and purpose

- Family: `governance_canary__v1`
- Experiment: `governance_canary_execution_v1__v1`
- Runner: `research_contracts.canary:run_governance_canary`
- Split: `train` only
- Lifecycle result: `INFRASTRUCTURE_CANARY_COMPLETED`
- Promotion eligibility: permanently `false`

The family has no economic mechanism, prediction, security, price, benchmark,
fundamental, news, option, fund, broker, portfolio or trading meaning. Its only
input is a committed three-row synthetic fixture. It cannot become a score,
recommendation, alert, position or promotion candidate.

## Candidate-object hashes

The proposal manifest file is SHA-256
`0379222ec8f3bf311a7032b8e47ae35303a2593b93047617e98fff18ff6e857d`.
Candidate object file hashes are:

| Object | File SHA-256 | Canonical registration hash where applicable |
|---|---|---|
| Family definition | `60eade3d890316d617c57a1ef5385c79bde01cbb217ebcd629b0160b9a644a52` | `ab7bd1ad7d106e08ebbd9bf54d9a109701e39e6a66229a1724b9bcb58b9117ed` |
| Preregistration | `cd87ab1f046bd2c1d4dff702a8e92939eb2139ee5276ca67d8e7df81b644216d` | `29f5bc780cdc4fcdbce58657e65d03695ea6b2ffeef9c449cd7af22e58a0f1a0` |
| Input declaration before runtime binding | `fe77c62722fced3454e0b9516223ab120f734bda4396c09b065d77bb33241761` | `2e3292520a40e7ca4e565fb59bc5580c92fc0495b1e66b858a21c6a15e0b931d` |
| Synthetic fixture | `b139b0d653a6171a2e07ae30ae770bdde5779d0d02cbc2f5fb6aee74bb1a15d2` | same bytes |
| Expected outputs | `eb04836e4b1ed85a6a183af6815f95a9ebf68dc3db7b6ba8c6118b27f1234142` | not registered |
| Proposed approval payload | `7a69743a8f62150f6e6cdaa688415cd13e8fed4b49f6c4033672a735e6fc6d1c` | deliberately unsealed |
| Resource envelope | `402b137f48148d6dae696101afa5a8f9e584730d07caa1858fbcd12b66a6d479` | not registered |
| Review checklist | `870974a6582f446fc9eb43b2d436ba585d9a9438ab5e4046d14155573e1ea8a8` | not registered |

The input declaration intentionally contains a non-executable future binding
marker for the clean Git commit. A future ceremony must replace that marker
with the exact reviewed committed state and actual environment, recompute the
input hash, display it to the user, and obtain separate approval. R.5 cannot
know its own final Git commit hash before it is committed. No approval in this
proposal binds or authorizes the provisional input hash.

## Deterministic behavior and artifacts

The runner validates the exact fixture identity, path, version and hash. It
accepts only the dedicated canary family and experiment. It writes exactly:

| Artifact | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `execution_receipt.json` | n/a | 372 | `29d63c1fb001d1512c1b0c3148f441b8aa7ef0a24a671b9671bb075c014562f8` |
| `synthetic_result.json` | n/a | 168 | `27f57d6d0fe30591f8b5d0fb3a9f1a309e3914545ba31cb1b660a9bee6560775` |
| `synthetic_rows.csv` | 3 | 78 | `f0a3bd05e9829f9b1d6eb80b616d2606e8925961771475160287a671e5c72d25` |

The gateway would add `root_manifest.json`; its hash cannot be known before
execution because it binds the future approval, attempt, catalog events and
timestamps. Missing, changed or unexpected runner artifacts fail the canary
validator. The deterministic seed is `0`; no randomness is used.

## Declared resource envelope

- Wall time: 5 seconds, `DECLARED_NOT_ENFORCED`
- Memory: 64 MiB, `DECLARED_NOT_ENFORCED`
- Attempts: exactly 1, `ENFORCED_BY_ONE_TIME_APPROVAL`
- Maximum disk output: 32,768 bytes
- Runner artifacts: 3; governed bundle artifacts including manifest: 4
- Network requests, market objects and trading actions: 0

These are conservative declarations derived from the static tiny outputs and
ordinary temporary-directory tests. No governed run was executed to measure
them. The current in-process gateway cannot enforce wall time or memory.

## Preflight forecast

Temporary, deterministic test catalogs establish the expected progression:

| Stage | Expected result |
|---|---|
| Proposal only | Blocked: exact family absent, preregistration unlocked, approval missing |
| Family registered, preregistration unlocked | Blocked: preregistration unlocked and approval missing |
| Family and preregistration ready | Blocked: approval missing |
| Exact approval registered and unused | `execution_permitted=true` only if every displayed binding matches |
| Approval consumed by `RUN_STARTED` | Blocked: approval already consumed |
| Attempted reuse | Same deterministic consumed-approval rejection |

The test simulation never invokes `GovernedExecutionGateway.run`, creates an
attempt directory or writes a canonical catalog.

## What later approval would mean

A later exact approval would authorize one call to
`GovernedExecutionGateway.run(family_path=..., preregistration_path=...,
input_declaration_path=..., approval_path=...)`. It would authorize only the
synthetic execution. It would not authorize interpretation, research,
promotion, market-data access, scoring, portfolio action or trading.
