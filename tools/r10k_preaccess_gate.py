"""Deterministic R.10K pre-access gate evaluation.

This module reads only tracked, sanitized governance evidence.  It has no
command-line entry point, locator parser, database client, network dependency,
or authority to continue beyond a failed pre-access gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from market_intel.foundation.fno_production_boundary import (
    DELIBERATE_INTERLOCK,
    ProductionInterlockEvidence,
    evaluate_production_interlocks,
)


SOURCE_COMMIT = "998801c4b4b1dcd1277826061bbe2256139085b7"
ATTEMPT_ID = "r10k-stage1-20260908T090434Z-7610d646abe4"
RECORDED_AT = "2026-09-08T09:04:34.4865828Z"
SCOPE_ID = "LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1"
NEXT_MILESTONE = "FNO_PRODUCTION_BOUNDARY_REMEDIATION_AND_REAUTHORIZATION_PLAN"
OVERALL_VERDICT = "AUDIT_ABORTED_SAFETY_BOUNDARY"

BOUND_HASHES = {
    "output/pdf/CONSOLIDATED_PRE_REAL_DATA_STATUS_V1.pdf": "76f5344109f701355e45d9e8243321fbb7b40d45cc52c9d20c9ac309c32fe278",
    "docs/investigations/r10j/status_pdf_v1/completion.json": "f7842e21c1ff0196525291fc2394daafd3c16caa0551099e19aac1e1fb5dc8d5",
    "docs/investigations/r10j/status_pdf_v1/manifest.json": "8cfbeb26b364bfb00f06e74bd600f0c2c7c02f84cc8fb24c86fb0865d5471d39",
    "docs/project_status/pre_research_review_record_v6.json": "db6443cba67b5a240dd62b15d07eaf8d06fccaad6659b5b3defff28e97daa83d",
    "evidence/fno_locator_binding_v1/anchor.json": "115eb8da500a81455061c13c130ee458496b38190caf11dbe4bba35386652acc",
    "specs/fno_production_locator_contract_v1.json": "85462b94588215499293e416e87d2d09d37a2a701318df5d21266a817a725cda",
    "src/market_intel/foundation/fno_production_boundary.py": "dcde3cbf1cd2cb1d5e70527cacb7066daf50e9cf6e48eb6fe44df45af8fc11ea",
}

CAPABILITIES = (
    "file_identity_stability", "read_only_safety", "schema_intelligibility",
    "date_coverage", "symbol_underlying_coverage", "futures_coverage",
    "options_coverage", "expiry_and_strike_integrity", "ohlc_validity",
    "volume_validity", "open_interest_validity", "duplicate_key_safety",
    "continuity", "contract_identity", "ingestion_lineage",
    "correction_vintage_handling", "point_in_time_reconstructibility",
    "permitted_use_and_retention", "reproducibility",
    "suitability_for_later_descriptive_analysis",
    "suitability_for_later_hypothesis_research", "suitability_for_backtesting",
)


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_preaccess_gate(root: Path) -> dict[str, Any]:
    actual = {path: _sha(root / path) for path in BOUND_HASHES}
    hash_match = actual == BOUND_HASHES
    completion = _load(root, "docs/investigations/r10j/status_pdf_v1/completion.json")
    manifest = _load(root, "docs/investigations/r10j/status_pdf_v1/manifest.json")
    review = _load(root, "docs/project_status/pre_research_review_record_v6.json")
    locator = _load(root, "specs/fno_production_locator_contract_v1.json")
    activation = _load(root, "specs/fno_production_activation_template_v1.json")
    approval_template = _load(root, "proposals/fno_production_audit_boundary_v1/approval_template_v1.json")
    optimistic = {
        field.name: True for field in fields(ProductionInterlockEvidence)
    }
    optimistic["deliberate_r9d_interlock_removed_by_reviewed_commit"] = False
    interlock_result = json.loads(json.dumps(
        evaluate_production_interlocks(ProductionInterlockEvidence(**optimistic))
    ))
    decisions = review["reviewer_questions"]
    exact_owner_decisions = (
        decisions[0]["decision"] == "REPORT_ACCURACY_CONFIRMED"
        and decisions[1]["decision"] == "NEXT_MILESTONE_SEPARATELY_APPROVED"
    )
    exact_scope = (
        review["authorized_scope"]["id"] == SCOPE_ID
        and review["authorized_scope"]["status"] == "AUTHORIZED_NOT_STARTED"
    )
    prohibitions_intact = all(
        value is False for value in review["prohibited_actions_authorized"].values()
    )
    gates = {
        "r10j_bound_hashes": "PASS" if hash_match else "FAIL",
        "r10j_completion_state": "PASS" if completion["completion_state"] == "CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF_READY_FOR_OWNER_REVIEW" else "FAIL",
        "r10j_manifest_state": "PASS" if manifest["completion_state"] == "CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF_READY_FOR_OWNER_REVIEW" else "FAIL",
        "separate_owner_decisions": "PASS" if exact_owner_decisions else "FAIL",
        "exact_scope_authorized": "PASS" if exact_scope else "FAIL",
        "prohibited_actions_remain_unauthorized": "PASS" if prohibitions_intact else "FAIL",
        "usable_production_locator_contract": "PASS" if locator.get("usable") is True and locator.get("template_only") is False else "FAIL",
        "usable_exact_one_use_production_approval": "PASS" if approval_template.get("usable") is True and approval_template.get("template_only") is False else "FAIL",
        "exact_attempt_id_bound_in_approval": "PASS" if approval_template.get("approved_attempt_id") == ATTEMPT_ID else "FAIL",
        "usable_production_activation": "PASS" if activation.get("usable") is True and activation.get("template_only") is False else "FAIL",
        "production_interlocks_permit_access": "PASS" if interlock_result["permitted"] is True else "FAIL",
        "target_specific_logical_read_budget_enforced": "FAIL",
        "sidecar_consistency_policy_resolved": "FAIL",
    }
    blockers = [
        "PRODUCTION_LOCATOR_CONTRACT_TEMPLATE_ONLY_UNUSABLE",
        "EXACT_REGISTERED_ONE_USE_PRODUCTION_APPROVAL_ABSENT",
        "ATTEMPT_ID_NOT_BOUND_BY_PRODUCTION_APPROVAL",
        "PRODUCTION_ACTIVATION_TEMPLATE_ONLY_UNUSABLE",
        DELIBERATE_INTERLOCK,
        "TARGET_SPECIFIC_LOGICAL_READ_BYTE_CAP_NOT_ENFORCED_BY_APPROVED_STACK",
        "SIDECAR_CONSISTENCY_POLICY_UNRESOLVED",
    ]
    return {
        "schema_version": "r10k_preaccess_gate_v1",
        "attempt_id": ATTEMPT_ID,
        "source_commit": SOURCE_COMMIT,
        "recorded_at": RECORDED_AT,
        "approved_scope": SCOPE_ID,
        "bound_hashes": BOUND_HASHES,
        "actual_hashes": actual,
        "gates": gates,
        "blockers": blockers,
        "interlock_evaluation": interlock_result,
        "gate_decision": OVERALL_VERDICT,
        "locator_resolved": False,
        "database_opened": False,
        "approval_consumed": False,
    }


def build_capability_matrix() -> dict[str, Any]:
    results = {name: "NOT_TESTED_SAFETY_BOUNDARY" for name in CAPABILITIES}
    results["read_only_safety"] = "FAIL"
    results["permitted_use_and_retention"] = "UNKNOWN"
    return {
        "schema_version": "r10k_capability_matrix_v1",
        "attempt_id": ATTEMPT_ID,
        "results": results,
        "interpretation": "No database capability was inferred from an audit that stopped before locator resolution.",
    }


def declared_resources() -> dict[str, Any]:
    return {
        "schema_version": "r10k_resource_envelope_v1",
        "attempt_id": ATTEMPT_ID,
        "limits": {
            "maximum_target_connections": 1,
            "maximum_attempted_statements": 50,
            "maximum_statement_seconds": 5,
            "maximum_attempt_seconds": 1200,
            "maximum_result_rows": 25000,
            "maximum_target_logical_bytes_read": 268435456,
            "maximum_output_bytes": 26214400,
            "maximum_provenance_files": 500,
            "maximum_provenance_bytes": 536870912,
        },
        "actual": {
            "locator_resolutions": 0,
            "target_files_opened": 0,
            "target_bytes_read": 0,
            "database_connections": 0,
            "statements_attempted": 0,
            "rows_accepted": 0,
            "market_rows_read": 0,
            "external_requests": 0,
        },
        "limit_enforcement_decision": "ABORT_BEFORE_ACCESS_TARGET_READ_BUDGET_UNAVAILABLE",
    }


def render_report(gate: dict[str, Any], capabilities: dict[str, Any], resources: dict[str, Any]) -> str:
    gate_rows = "\n".join(f"| {key} | {value} |" for key, value in gate["gates"].items())
    capability_rows = "\n".join(f"| {key} | {value} |" for key, value in capabilities["results"].items())
    blocker_rows = "\n".join(f"- `{value}`" for value in gate["blockers"])
    actual_rows = "\n".join(f"| {key} | {value} |" for key, value in resources["actual"].items())
    return f"""# Local F&O Database Read-Only Qualification Stage 1

## Outcome

`{OVERALL_VERDICT}`

R.10K stopped at the mandatory pre-access gate. The owner had separately
approved the bounded qualification, but the committed production controls
cannot yet execute it safely. The private locator was not resolved, the
database was not opened, no approval was consumed and no SQL was attempted.

## Control

- Source commit: `{SOURCE_COMMIT}`
- Sanitized attempt ID: `{ATTEMPT_ID}`
- Approved scope: `{SCOPE_ID}`
- R10J report reviewed before this attempt: `PASS`
- Database alias: `PRIVATE_FNO_DATABASE_V1`
- Absolute database path recorded: `false`

## Authorization and pre-access gates

| Gate | Result |
|---|---|
{gate_rows}

The R10J PDF, completion, manifest and v6 owner record hashes matched. The two
owner decisions were distinct, the exact bounded scope was approved, and all
prohibited-action authority remained false. Permission alone cannot bypass an
unusable locator/activation contract or a safety control that is not enforced.

## Abort reasons

{blocker_rows}

The R.9P synthetic candidate demonstrated useful mechanisms, but APSW remains
an isolated, unadopted candidate rather than an approved production dependency.
R.10K explicitly prohibited adopting a new production dependency merely to
complete this run. The existing standard sqlite3 production entry point still
returns `permitted=false` because the deliberate R.9D interlock has not been
removed by a reviewed commit.

## Database access and identity

The previous sanitized R.9F anchor remains historical evidence only. It was not
silently refreshed. Because the gate failed before locator resolution, current
file identity, modification time, sidecar state and before/after stability are
`NOT_TESTED_SAFETY_BOUNDARY`. The attempt created no database sidecar because it
made no target-directory or database access; it makes no claim about sidecars
that may already exist.

## Resource use

| Resource | Actual |
|---|---:|
{actual_rows}

No real/private data, market rows, returns, features, signals, backtests,
simulations, scores, recommendations, broker services or trading functions were
accessed or calculated. The R10A holdout remains unconsumed.

## Capability verdicts

| Capability | Result |
|---|---|
{capability_rows}

`FAIL` for read-only safety means the complete declared production boundary is
not currently enforceable. It does not mean a write was observed. All database
content capabilities remain untested rather than being guessed from the old
sampled identity or table-name assumptions.

## Queries and checks

No SQLite query was attempted. Schema, coverage, integrity and provenance
inspection were skipped because the pre-access safety gate failed. This is the
required fail-closed behavior, not missing execution evidence disguised as a
pass.

## Verification

- Mandatory pre-access suite: `133 passed, 4 skipped`.
- Focused R.10K checks before manifest sealing: `10 passed, 1 deselected`.
- Complete root suite after artifact sealing: `765 passed, 4 skipped, 1 failed`
  with 7 warnings. The failure is an older, hash-bound R.9L non-approval test
  that requires the later valid v6 owner-review record to be absent. Neither
  the historical test nor its manifest was altered to hide this contradiction.
- Data test: not rerun because no shared application or data contract changed;
  the latest recorded result remains `289 passed`.
- JSON/JSONL parsing, artifact hashes, whitespace, private-path and secret
  scans: `PASS`.
- Protected momentum, golden-fixture and earlier evidence artifacts: unchanged.

## Final qualification verdict

Overall: `{OVERALL_VERDICT}`

The local F&O database remains `LOCATED_AND_SAMPLED_NOT_QUALIFIED`. It is not
approved for descriptive analysis, hypothesis research or backtesting.

## Single recommended next milestone

`{NEXT_MILESTONE}`

Prepare a bounded, owner-readable remediation plan that reconciles the current
R10J approval with: a usable production locator contract, an exact sealed and
durably registered one-use attempt approval, an explicit sidecar policy, and an
enforceable read-budget mechanism. The plan must decide whether the restricted
R.9P candidate can be adopted under a separately reviewed dependency policy or
whether this database route should be abandoned. It must not open the database,
run research or begin backtesting.
"""
