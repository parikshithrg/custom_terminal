# Governed Canary Independent Audit

## Scope and method

This is a byte-level, read-only audit of attempt
`governance-canary-attempt-126aeed-001`, executed from source commit
`126aeedde9c50cce5f1896cdb656c89d678e30d6`. The auditor treats every ignored
runtime file as untrusted input. It loads data files, recomputes canonical and
file hashes, checks bindings and inspects gateway source ordering. It does not
execute the ceremony script, runner or gateway and does not register, approve,
consume, import or repair evidence.

All required ceremony declarations, governed catalog records, approval,
family, preregistration, input declaration, bundle files and canonical record
were present. The audit produced zero mismatches.

## Independently verified hashes

| Object | Recomputed SHA-256 | Result |
|---|---|---|
| Approval file bytes | `326afafdee722925c3fafbdbe3dc6b33ee61e0f2b7aaa48f564e8b6e993378e5` | MATCH |
| Approval contract payload | `e554f0c9968e9920fb2488028fa66a2627012b01eb58eb45587d9b48a557610c` | MATCH |
| Family | `ab7bd1ad7d106e08ebbd9bf54d9a109701e39e6a66229a1724b9bcb58b9117ed` | MATCH |
| Locked preregistration | `29f5bc780cdc4fcdbce58657e65d03695ea6b2ffeef9c449cd7af22e58a0f1a0` | MATCH |
| Final input declaration | `944de49313bdd5db57f047b7bf9f8cd36eacd7e3c8c1bbe0940647951fb06488` | MATCH |
| Three-row fixture | `b139b0d653a6171a2e07ae30ae770bdde5779d0d02cbc2f5fb6aee74bb1a15d2` | MATCH |
| Execution receipt | `29d63c1fb001d1512c1b0c3148f441b8aa7ef0a24a671b9671bb075c014562f8` | MATCH |
| Synthetic result | `27f57d6d0fe30591f8b5d0fb3a9f1a309e3914545ba31cb1b660a9bee6560775` | MATCH |
| Synthetic rows | `f0a3bd05e9829f9b1d6eb80b616d2606e8925961771475160287a671e5c72d25` | MATCH |
| Root manifest | `bdb3ee240ce2939dff6c523c305d5affdf9cd6b4deaf1fd0995efe675a9c40fb` | MATCH |
| Governance terminal event | `9ddfaedf8fb0dd113417645b127c7dd3c021c478ae89b1648cf5e5d3caa5a0bb` | MATCH |
| Sole canonical record/file | `63f9fa81774313355033841960a34c2f1ef6ef5c1ffdc69c34c0a652e6fa0c6e` | MATCH |

The same values match the committed R.5 proposal where applicable, finalized
runtime bindings, approval, root manifest, execution summary and catalogs.
Every artifact in the root-manifest inventory exists with its declared hash;
there are no unexpected outputs.

## Approval and execution lifecycle

The exact registered approval
`governance-canary-126aeed-20260828T075323962604Z` bound the expected family,
experiment, fixture, input declaration, runner and `train` split. Its validity
interval was exactly 1,800 seconds. `RUN_STARTED` occurred inside that interval.
The catalog contains one start and one terminal event for the sole attempt.
The approval permits one attempt and is consumed.

Side-effect-free post-run preflight returns `INVALID`, with reuse rejected
because the approval was already consumed. Source inspection confirms the
gateway checks authorization and approval availability before it creates an
attempt directory or invokes the runner. No second execution was attempted.
No validation or test access was authorized, and the registered approval bytes
still hash to their original value.

## Event and atomic-bundle validation

The exact seven-event sequence is:

1. `FAMILY_REGISTERED`
2. `PREREGISTRATION_CREATED`
3. `PREREGISTRATION_LOCKED`
4. `RUN_APPROVAL_REGISTERED`
5. `RUN_AUTHORIZED`
6. `RUN_STARTED`
7. `RUN_COMPLETED`

Every governance event hash and previous-event link validates. All execution
events bind the one attempt ID. The final directory has its intended name;
there is no temporary or incomplete sibling. The root manifest binds the start
and completion events and all four bundle files. The canonical import points to
that exact bundle, validates `PASS`, and the catalog contains exactly one
canonical record.

The canonical JSONL catalog currently has no per-record chain fields. The audit
therefore verifies its sole record and complete file bytes against the anchor;
it does not claim a canonical-record chain that the contract does not implement.
The legacy catalog and hypothesis log were not modified.

## Non-substantive status

The only input is the committed three-row synthetic fixture. Static dependency
inspection finds no market-data, network, broker, portfolio, scoring,
Streamlit, trading or external-provider dependency in the canary runner. The
recorded lifecycle is exactly `INFRASTRUCTURE_CANARY_COMPLETED`, and
`promotion_eligible` is `false`. The importer confines this lifecycle to the
canary family and rejects promotion claims.

This evidence cannot satisfy train, validation, test, replication, production
or actionable-score gates. It acquired no market data and performed no trading
action. It is an infrastructure result, not an investment experiment.

## Resources and limitations

- Attempt limit: **1, enforced by approval consumption**.
- Wall-time limit: **5 seconds, DECLARED_NOT_ENFORCED**.
- Memory limit: **64 MiB, DECLARED_NOT_ENFORCED**.
- Runner outputs: **3 files, 618 bytes**.
- Governed bundle: **4 files, 5,017 bytes**, including the root manifest.
- Actual peak memory: **NOT_RECORDED**.
- Trustworthy enforced-runtime measurement: **NOT_RECORDED**.

Absence of a timeout is not evidence of wall-time enforcement. A filesystem
owner can alter local evidence; alteration is detectable only relative to a
separately preserved anchor. Raw runtime evidence is ignored and stored only
locally, with no explicit backup/retention policy yet. Finally, a passing
governance canary says nothing about historical market-data completeness,
point-in-time correctness or survivorship safety.

## Audit result

All required hashes, bindings, lifecycle facts, catalog events, bundle contents
and canonical-import facts matched. The sanitized versioned anchor was created
only after this result was obtained.

**PASS**
