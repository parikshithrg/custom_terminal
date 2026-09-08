# R.10I.1 Fingerprint Coherence Amendment

## Outcome

The contradiction is resolved without rewriting R.10I v1 evidence. The value
`e0870bd050c2906f1aa81ead3ffe66871031db106e5ee39c046c5a011184759c`
is the stale pre-refresh working-tree fingerprint. The value
`236fddae8660e373eccdc6bb34a67a0dc0baaf7e91ff6203f4d24a43193a172f`
is the post-refresh working-tree fingerprint stored in the v1 checkpoint.
Neither value is a fingerprint of immutable Git commit objects.

The authoritative policy-v2 Git-object fingerprint for both the declared
implementation commit `89ba5b77708ac867688e0f4b9381d3bf47e31263` and the
evidence commit `886cf5687b094f648f960373fedeec3219dca67f` is:

`19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6`

It covers 280 files and is independently reproduced from exact Git blob bytes.

Completion decision:
`R10I_FINGERPRINT_COHERENCE_CONFIRMED_READY_FOR_CONSOLIDATED_PDF`

Coherence binding: `d2ef2f2d003e4f563d2d45a9f24bfb374078ebda7dc7669ae8181fa94dc0a382`

## State-specific mapping

| Reference | Kind | Fingerprint | Files | Interpretation |
|---|---|---|---:|---|
| `e07b616365517886620e88eb212c4f45562733d5` pre-refresh reconstruction | working-tree reconstruction | `e0870bd050c2906f1aa81ead3ffe66871031db106e5ee39c046c5a011184759c` | 280 | Stale value copied into the later report and completion record |
| `89ba5b77708ac867688e0f4b9381d3bf47e31263` checkpoint checkout | working-tree snapshot | `236fddae8660e373eccdc6bb34a67a0dc0baaf7e91ff6203f4d24a43193a172f` | 280 | Valid checkout-byte value recorded by the v1 checkpoint; clean start was recorded, but it was not a commit fingerprint |
| `89ba5b77708ac867688e0f4b9381d3bf47e31263` | immutable Git commit | `19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6` | 280 | Authoritative implementation-source fingerprint |
| `886cf5687b094f648f960373fedeec3219dca67f` | immutable Git commit | `19ed28f407ff62a44012f1d1e4b1870ba15be30155c9c19bee6288ab228f1bc6` | 280 | Authoritative evidence-commit fingerprint |

The Git-object and working-tree values differ because the original algorithm
hashes file bytes and a checkout can contain byte representations governed by
Git attributes and platform end-of-line handling. A commit claim must therefore
read blobs directly with `git cat-file`; it must not use the present checkout or
`git archive` with checkout conversion enabled.

## Exact root cause

Commit `89ba5b7` refreshed two included specification files. Replacing only
these two post-refresh inventory rows with their `e07b616` Git-blob rows exactly
reproduces `e0870bd...`:

- `specs/laboratory_entrypoint_inventory_v2.json` changed from
  `a78a6b4c...` to `f97899b5...`;
- `specs/pre_research_review_policy_v2.json` changed from `92d5d0a6...` to
  `dd81d4ba...`.

Restoring the two amendment-contract source rows to their `886cf56` bytes in
the present checkout exactly reproduces `236fddae...`. This proves that the v1
checkpoint captured the post-refresh working tree while the prose artifacts
retained the earlier value. There is no evidence that generated R.10I evidence
entered the policy inventory recursively.

The historical cleanliness of the moment when `e0870bd...` was copied was not
recorded in a machine-verifiable artifact, so this amendment does not invent a
boolean answer. It identifies that state as `NOT_INDEPENDENTLY_RECORDED`. The
v1 checkpoint explicitly records a clean start for `236fddae...`.

## Why the old tests passed

The v1 checkpoint validator compared its value only with the then-current
working tree. The manifest checked byte hashes but did not compare semantic
fingerprint claims. The report was tested as prose, and the completion record
was not reconciled with the checkpoint. No validator reproduced a
commit-attributed fingerprint from Git blobs. Consequently, individually valid
files could disagree about the same declared state.

## Correct forward contract

The amendment separates:

- `implementation_source_commit` and its immutable Git-object fingerprint;
- `evidence_commit` and its immutable Git-object fingerprint;
- working-tree snapshots and their recorded cleanliness;
- policy version, file count, and input-inventory hash for every state;
- human presentation from a shared machine-readable coherence binding.

For `sha256_canonical_inventory_v1`, the fingerprint and input-inventory hash
are intentionally identical: both hash the same canonical JSON inventory. The
two names describe role, not two different calculations.

Generated evidence is deliberately non-recursive. `docs/investigations/**` and
this report are not selected by policy-v2 include globs;
`docs/project_status/**` and `tests/**` are explicitly excluded. The file count
therefore remains 280 from implementation commit to evidence commit.

## Manifest hash design

The amendment manifest does not pretend to contain its own byte hash. Its
`payload_sha256` hashes every manifest field except `payload_sha256` and
`root_sha256`. Its `root_sha256` hashes the pair consisting of that payload hash
and the complete output-hash map. This non-self-referential root/payload design
binds all declared outputs and all manifest metadata deterministically and is
tested directly.

## Preservation and authority

The original report, v1 completion, v1 manifest, and v1 checkpoint remain
byte-for-byte unchanged and are bound in the structured amendment. The
amendment supersedes only the erroneous assertion that `e0870bd...` represented
the current state at `89ba5b7`.

The original R.10I completion decision remains valid after correction because
the implementation and evidence commits have an identical, reproducible
280-file Git fingerprint. This amendment does not expand historical review
scope or authorize real/private data, providers, research, backtesting,
holdout consumption, scoring, recommendations, PDF generation, or broker and
trading activity.

## Validation

Validation covers immutable commit reproduction, both conflicting working-tree
reconstructions, cross-artifact semantic agreement, policy/count/source/inventory
agreement, manifest payload/root hashes, v1 byte preservation, entrypoint
inventory validity, protected Momentum v1 files, and fail-closed authority.

Executed commands and results:

- `.\.venv\Scripts\python.exe -m pytest -q tests/test_research_r10i1_fingerprint_coherence.py tests/test_research_r10i_governance_remediation.py tests/test_research_r4_approval.py tests/test_research_r9c_pdf_v2.py` — 58 passed.
- `.\.venv\Scripts\python.exe -m pytest -q` — 742 passed, 4 expected Windows symlink skips, 2 existing development warnings, 0 failures.
- with `PYTHONPATH` set to the absolute `Data test` directory,
  `.\.venv\Scripts\python.exe -m pytest "Data test\tests" -q --disable-warnings --basetemp=.pytest_tmp/data_test_r10i1_xml --junitxml=.pytest_tmp/data_test_r10i1.xml`
  — JUnit records 289 tests, 0 failures, 0 errors, and 0 skips.
- JSON parsing — 730 files valid, 0 invalid.
- `git diff --check` — passed.

Two preliminary Data-test invocations did not execute the suite: the first
omitted its documented `PYTHONPATH` and failed collection; the second used the
host temporary directory and hit a sandbox permission error. Neither changed
code or data. The final documented invocation above used both the required
import root and repository-local `--basetemp` and passed completely.

## Next milestone

The next milestone is `CONSOLIDATED_PRE_REAL_REQ_DATA_STATUS_PDF`. This task did
not generate that PDF.
