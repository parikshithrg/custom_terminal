# Governed Execution Operations

## Required operator flow

```text
generate current status PDF and fingerprint
  -> owner reviews exact PDF and covered scope
  -> validate report gate
  ->
register family
  -> lock preregistration
  -> declare and hash inputs
  -> run side-effect-free preflight
  -> review exact proposed run
  -> issue and register user approval
  -> execute once through the gateway
  -> produce root manifest and atomic bundle
  -> validate canonical import
  -> interpret only within permitted split
```

These are separate decisions. Preflight diagnoses; approval authorizes one
execution; the gateway executes; the importer verifies evidence; scientific
review interprets it; a later promotion process decides whether it can affect
an actionable system. None implies the next.

For market research, the first three steps are mandatory. The preregistration
and later run approval both bind the reviewed PDF and research-state
fingerprint. Report review never substitutes for the separate exact one-use run
approval. Infrastructure-only canaries and synthetic governance fixtures are
exempt because they contain no market analysis and remain nonpromotable.

## Side-effect-free preview

The documented interface is `scripts/preview_governed_run.py`. It requires an
explicit evaluation timestamp so expiry results are reproducible. It reports
family/experiment/preregistration/input hashes, datasets, source/environment
fingerprints, runner and split availability, approval state, destinations,
blocking issues and `execution_permitted`. It does not create directories,
append events, register/consume approval, import evidence or call a runner.

A deliberately blocked synthetic example is safe to run because the committed
registry has no synthetic family registration and the supplied object is only
a non-authorizing template:

```powershell
.\.venv\Scripts\python.exe scripts\preview_governed_run.py `
  --family tests\fixtures\research_r3\synthetic_family_v1.json `
  --preregistration tests\fixtures\research_r3\synthetic_preregistration_v1.json `
  --inputs tests\fixtures\research_r3\synthetic_input_declaration_v1.json `
  --approval specs\governed_run_approval_template_v1.json `
  --governance-catalog .pytest_tmp\empty-governance.jsonl `
  --attempts-root .pytest_tmp\preview-attempts `
  --canonical-catalog .pytest_tmp\preview-canonical.jsonl `
  --runner-entry-point synthetic:runner `
  --evaluated-at 2026-01-01T00:00:00+00:00
```

It returns blocking issues and exit code 2; it still creates no listed path.
The valid synthetic preview path is exercised twice, byte-equivalently and
without side effects, by `test_preflight_is_deterministic_side_effect_free_and_does_not_consume_approval`.

Market-research previews additionally require `--repository-root` and
`--review-record`; omitting either produces a fail-closed report-gate issue.

## Approval issuance

1. Copy the template outside canonical evidence.
2. Replace every placeholder from the exact reviewed preflight proposal.
3. Set `template_only=false`, positive limits and the accurate enforcement map.
4. Canonically seal the payload with `seal_approval`.
5. Review the complete object; then call `register_run_approval` once.
6. Rerun preflight and require `VALID_UNUSED` plus no blocking issues.

Do not create an approval from chat implication, an old approval, a family-level
blanket permission or a validation approval when test access is requested.

## Execution and evidence

Only `GovernedExecutionGateway.run` can start a canonical attempt. It requires
the exact registered approval, consumes it at `RUN_STARTED`, writes into a
temporary attempt directory, inventories declared outputs, writes the root
manifest, atomically renames the bundle and appends its final catalog event.
The canonical importer independently validates family, preregistration,
approval, inputs, split, artifacts, lifecycle and event bindings.

Direct Data-test scripts remain development-only. They emit a warning and a
noncanonical marker under the configured artifacts root. The deprecated Slice
A momentum CLI exits before parsing data; direct `run_momentum` calls are marked
noncanonical and no longer update the old SQLite catalog. The canonical
importer remains the decisive control and rejects direct or subprocess output.

## Permissions and limits

- Training, validation, test and replication remain distinct.
- Validation/test/replication require their R.3 catalog authorization.
- Test approval is explicit and one-use.
- Approval attempts are enforced at one; wall time and memory are declarative.
- The filesystem owner can still read local files outside these tools.
- R.4 authorizes no real run and no action in the trading interface.
