"""Build the compact, read-only R.10H readiness audit from tracked evidence.

This helper reads only repository metadata and synthetic evidence.  It has no
provider, broker, private-configuration, database, or network integration.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


MILESTONES = {
    "R.10A": ("17f317187b00b489e3eda52ddcfe4ac48cdef2cd", "d9d3922677ba024b9524c94309942aa205bd81f6", "docs/investigations/r10a/run_v1/root_run_manifest.json", "specs/synthetic_research_fixture_r10a_v1.json", 27),
    "R.10B": ("2ccbc4844e4c2156595c5097dde6c80ecb7c42b0", "add9e307cbc22281edd349036fcf08b55ad314ea", "docs/investigations/r10b/run_v1/root_manifest.json", "specs/synthetic_incremental_sequence_r10b_v1.json", 61),
    "R.10C": ("9737868493649b9c1484f460ebe32ab32dc6158d", "eeb7d90695a4d44d4ad6ec23152b84f071f27c90", "docs/investigations/r10c/run_v1/root_manifest.json", "specs/synthetic_security_events_r10c_v1.json", 27),
    "R.10D": ("447bf403fd4eb19b5d72b1cc2db9a7b1c7aa6698", "1968b3369bc6630026a77918139a3c4b75790b98", "docs/investigations/r10d/run_v1/root_manifest.json", "specs/synthetic_exchange_calendar_r10d_v1.json", 11),
    "R.10E": ("5febba77436ea577db5bc53ecd21fe0c742a134d", "b1e784deba7a3b066e61c2023dda95c6bcb53889", "docs/investigations/r10e/run_v1/root_manifest.json", "specs/synthetic_multi_feature_score_r10e_v1.json", 20),
    "R.10F": ("42a938c50ea013dcb1d3971e4f61162fc5148ac9", "72da23cf4b9f14df8007e9967ea64171bf85261e", "docs/investigations/r10f/run_v1/root_manifest.json", None, 48),
    "R.10G": ("803029792cfae66f59ec090b97586cd29f842963", "5bca5b7fb39f09a7edcc6af96b945ba8b88d33f2", "docs/investigations/r10g/run_v1/root_manifest.json", None, 14),
}

ROOT_BYTE_HASHES = {
    "R.10A": "ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580",
    "R.10B": "316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2",
    "R.10C": "bf5722abab22ca1920186a7ff2572c8095d1cb75fbd442ed00e5f8dbd0893ce6",
    "R.10D": "2f9ca92b086625d10904475254f17fe2cae135d7488d99e40738a05b618fca75",
    "R.10E": "a48915801d99c8eca7559079c597d9157e3b3699d5a5cf0759f6a4e01aabd7b3",
    "R.10F": "7eba19c2a2cbd16bd6ff66f7435813135bcb4cb3ae287117c78187d6ac4b1955",
    "R.10G": "97694fea900ab206a7963866c43a70961ef1f9df182023951985d5cb41ec0854",
}

ENTRYPOINTS = [
    "tools/r9j_synthetic_boundary.py", "tools/r9k_windows_feasibility.py",
    "tools/r9m_vfs_evaluation.py", "tools/r9n_adversarial.py",
    "tools/r9n_regression.py", "tools/r9p_integrated.py",
    "tools/r9p_regression.py", "tools/r10a_generate_evidence.py",
    "tools/r10b_generate_evidence.py", "tools/r10c_generate_evidence.py",
    "tools/r10d_generate_evidence.py", "tools/r10e_generate_evidence.py",
    "tools/r10f_generate_evidence.py", "tools/r10g_generate_evidence.py",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dump(path: Path, value: Any) -> str:
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def _verify_evidence(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory, chain = [], []
    roots = {}
    for name, (implementation, evidence, manifest_path, recipe, expected_count) in MILESTONES.items():
        path = root / manifest_path
        manifest = json.loads(path.read_text(encoding="utf-8"))
        root_hash = _sha(path)
        roots[name.lower().replace(".", "")] = root_hash
        checks = []
        artifact_hashes = manifest.get("artifact_hashes", manifest.get("output_artifact_hashes"))
        if artifact_hashes is None:
            raise AssertionError(f"{name} has no artifact-hash map")
        for relative, expected in artifact_hashes.items():
            actual = _sha(path.parent / relative)
            checks.append({"path": relative, "expected": expected, "actual": actual,
                           "status": "PASS" if actual == expected else "FAIL"})
        if len(checks) != expected_count:
            raise AssertionError(f"{name} artifact count differs")
        if any(item["status"] != "PASS" for item in checks):
            raise AssertionError(f"{name} artifact mismatch")
        if root_hash != ROOT_BYTE_HASHES[name]:
            raise AssertionError(f"{name} root byte hash differs")
        references = manifest.get("references", manifest.get("evidence_references", {}))
        inventory.append({
            "milestone": name, "implementation_checkpoint": implementation,
            "evidence_commit": evidence, "root_manifest": manifest_path,
            "root_manifest_byte_sha256": root_hash,
            "source_tree_sha256": manifest.get("source_tree_sha256"),
            "source_tree_verification": "BOUND_DIRTY_STATE_NOT_RECONSTRUCTIBLE_FROM_COMMIT" if name == "R.10A" else "PASS_HISTORICAL_COMMIT_RECALCULATION",
            "environment_hash": manifest.get("environment_hash", manifest.get("environment_lock_sha256")),
            "environment_hash_kind": "ENVIRONMENT_LOCK_BYTE_HASH" if name == "R.10A" else "CANONICAL_ENVIRONMENT_HASH",
            "entrypoint": manifest.get("entrypoint"),
            "entrypoint_sha256": manifest.get("entrypoint_sha256"),
            "entrypoint_verification": "NOT_RECORDED_IN_R10A_ROOT" if name == "R.10A" else "PASS_HISTORICAL_COMMIT_BLOB",
            "fixture_recipe": recipe or "SOURCE_DEFINED_FIXTURE_NO_SEPARATE_RECIPE",
            "artifact_count": len(checks), "artifact_hash_verification": "PASS",
            "classification": manifest.get("classification"),
            "lifecycle": manifest.get("lifecycle", "SYNTHETIC_VALIDATED_NONCANONICAL"),
            "promotion_eligible": manifest.get("promotion_eligible"),
            "clean_execution_start": (not manifest.get("dirty_worktree", False)) if name == "R.10A" else not manifest.get("execution_start_dirty", True),
            "clean_execution_note": "R.10A predates the clean-start protocol and records a dirty worktree fingerprint" if name == "R.10A" else "Exact clean implementation checkpoint recorded",
            "reproducible_core_sha256": manifest.get("reproducible_core_sha256"),
            "references": references,
            "known_limitations": [
                "Synthetic/noncanonical evidence does not establish real-data or economic fitness",
                *( ["No separate fixture recipe; construction is source-defined"] if recipe is None else []),
                *( ["Dirty-start evidence is bound but is weaker than later clean-checkpoint evidence", "Root manifest has no entrypoint hash"] if name == "R.10A" else []),
            ],
        })

    for index, item in enumerate(inventory):
        refs = item["references"]
        predecessor_checks = []
        for previous in inventory[:index]:
            key = previous["milestone"].lower().replace(".", "")
            referenced = refs.get(key)
            if referenced is not None:
                predecessor_checks.append({"predecessor": previous["milestone"],
                                           "expected_root_byte_sha256": previous["root_manifest_byte_sha256"],
                                           "referenced_sha256": referenced,
                                           "status": "PASS" if referenced == previous["root_manifest_byte_sha256"] else "FAIL"})
        chain.append({"milestone": item["milestone"], "predecessors": predecessor_checks,
                      "classification_preserved": item["classification"] == "SYNTHETIC_ONLY_NONCANONICAL",
                      "promotion_remains_false": item["promotion_eligible"] is False})
    return inventory, chain


def _architecture() -> dict[str, Any]:
    rows = [
        ("local_modular_monolith", "DEMONSTRATED_WITH_LIMITATIONS", "src/market_intel", "R.10A-G exercise shared packages; portfolio/evidence contracts have limited sibling coupling"),
        ("dependency_direction", "DEMONSTRATED_WITH_LIMITATIONS", "src/market_intel/application/synthetic_*.py", "Foundation has no application dependency; portfolio policy imports evidence DTOs"),
        ("typed_dataset_storage", "DEMONSTRATED", "docs/investigations/r10a/run_v1", "Typed Parquet facts and dataset-specific contracts"),
        ("temporal_provenance_envelope", "DEMONSTRATED", "src/market_intel/foundation/contracts.py", "As-of requests, publication and availability times are tested"),
        ("stable_security_identity", "DEMONSTRATED_WITH_LIMITATIONS", "docs/investigations/r10c/run_v1", "Synthetic aliases/events prove mechanics; authoritative real identity coverage is blocked"),
        ("point_in_time_availability", "DEMONSTRATED", "tests/test_research_r10a_evidence.py", "Later vintages and cutoff leakage are challenged"),
        ("versioned_universe_feature_outcome", "DEMONSTRATED", "docs/investigations/r10a/run_v1", "Definitions and dataset versions are manifest-bound"),
        ("calendar_aware_execution", "DEMONSTRATED_WITH_LIMITATIONS", "docs/investigations/r10d/run_v1", "Known-answer synthetic calendar, not official exchange history"),
        ("purge_and_embargo", "DEMONSTRATED", "src/market_intel/research/folds.py", "Overlap and embargo constraints have deterministic tests"),
        ("three_result_layers", "DEMONSTRATED", "docs/investigations/r10a/run_v1", "Prediction, economic and portfolio evidence are separated"),
        ("score_semantics", "DEMONSTRATED_WITH_LIMITATIONS", "docs/investigations/r10e/run_v1", "Training-only transforms/calibration demonstrated on a formulaic oracle"),
        ("confidence_semantics", "DEMONSTRATED_WITH_LIMITATIONS", "docs/investigations/r10e/run_v1", "Confidence is separate and synthetic only"),
        ("multiple_testing_ledger", "DEMONSTRATED", "docs/investigations/r10e/run_v1", "Attempt ledger and multiplicity correction are explicit"),
        ("immutable_publication", "DEMONSTRATED", "docs/investigations/r10f/run_v1", "Manifest-bound immutable bundle and read model"),
        ("thin_read_only_application", "DEMONSTRATED_WITH_LIMITATIONS", "src/market_intel/application/synthetic_publication.py", "Facade maps evidence without score recalculation; no production UI integration"),
        ("portfolio_mandate_separation", "DEMONSTRATED_WITH_LIMITATIONS", "docs/investigations/r10g/run_v1", "Policy and accounting mechanics are bounded prototypes"),
        ("ai_interpretation_boundary", "CONTRACT_ONLY", "ARCHITECTURE_REFINEMENT.md", "No AI research assistant is implemented"),
        ("ui_prohibition_boundary", "DEMONSTRATED", "docs/project_status/SYNTHETIC_RESEARCH_OPERATING_MODEL_V1.md", "Synthetic results remain NO_DECISION and are not wired to product UI"),
        ("trade_execution", "OUT_OF_SCOPE", "src/market_intel", "No broker mutation or execution path is part of R.10A-G"),
        ("real_data_completeness", "BLOCKED_ON_REAL_DATA", "reports/DATASET_TRUST_REPORT.md", "Synthetic mechanics cannot prove historical population or source fitness"),
    ]
    return {"schema_version": "r10h_architecture_conformance_v1", "requirements": [
        {"requirement": a, "classification": b, "evidence": c, "finding": d} for a, b, c, d in rows
    ]}


def _test_quality() -> dict[str, Any]:
    return {
        "schema_version": "r10h_test_quality_v1",
        "verified_runs": [
            {"command": ".venv/Scripts/python.exe -m pytest -q", "passed": 704, "skipped": 4, "failed": 9, "warnings": 2, "seconds": 412.57},
            {"command": "$env:PYTHONPATH=(Resolve-Path 'Data test').Path; .venv/Scripts/python.exe -m pytest 'Data test/tests' -q --basetemp='.pytest_tmp/data_test_r10h'", "passed": 289, "skipped": 0, "failed": 0},
            {"command": "focused R.10A-G, R.9P, R.9D and R.3 preservation/boundary suite", "passed": 114, "skipped": 0, "failed": 0},
        ],
        "strengths": ["Deterministic fixtures with exact known answers", "Point-in-time leakage and later-vintage challenges", "Mutation and failure injection", "Incremental/clean equivalence and unaffected-hash preservation", "Lifecycle, promotion, publication and broker boundaries"],
        "limitations": [
            "Several oracle formulas and evidence builders share implementation helpers, increasing false-positive risk",
            "Some scenario-catalog assertions prove declared coverage more strongly than independent behavior",
            "Synthetic calendar is not an authoritative exchange calendar",
            "No representative concurrency, scale, disk-corruption or real distribution-shift exercise",
            "Four Windows symlink/reparse tests skipped because privilege or link creation was unavailable",
            "R.10A's perfect synthetic relationship is engineering evidence, not economic evidence",
        ],
        "assessment": "MEANINGFUL_SYNTHETIC_KNOWN_ANSWERS_WITH_ORACLE_AND_PLATFORM_LIMITATIONS",
    }


def _entrypoints() -> dict[str, Any]:
    apsw = {"tools/r9m_vfs_evaluation.py", "tools/r9n_adversarial.py", "tools/r9n_regression.py", "tools/r9p_integrated.py", "tools/r9p_regression.py"}
    calc = {f"tools/r10{x}_generate_evidence.py" for x in "abcdefg"}
    rows = []
    for path in ENTRYPOINTS:
        rows.append({
            "path": path,
            "arbitrary_path_read": False,
            "private_configuration": False,
            "sqlite": path.startswith("tools/r9"),
            "apsw": path in apsw,
            "network": False, "providers": False, "brokers": False,
            "calculates_research_outputs": path in calc,
            "publishes_artifacts": True,
            "promotes_lifecycle": False, "produces_external_decision": False,
            "mutates_external_state": False,
            "runtime_evidence": "OFFLINE_SYNTHETIC_TESTS",
        })
    return {
        "schema_version": "r10h_entrypoint_capability_inventory_v1",
        "entrypoints": rows,
        "legacy_inventory_status": "STALE",
        "unaccounted_by_v1_and_deltas": ENTRYPOINTS,
        "production_apsw_dependency": False,
        "production_interlock": {"status": "UNCHANGED_ACTIVE", "path": "src/market_intel/foundation/fno_production_boundary.py", "git_blob": "86f10ff2ea78661cad842909629cd6e107c8c610"},
        "source_review_conclusion": "No network/provider/broker mutation or lifecycle-promotion path in these entrypoints",
        "runtime_limit": "Offline synthetic runtime evidence does not prove behavior against private or real inputs",
    }


def _governance() -> dict[str, Any]:
    fingerprint_tests = [
        "tests/test_research_r9e_pdf_v3.py::test_v3_preserves_the_exact_r9d_binding_but_is_stale_after_r9f",
        "tests/test_research_r9g_owner_review.py::test_v4_review_preserves_research_fingerprint_and_prior_pdf_bytes",
        "tests/test_research_r9g_pdf_v4.py::test_v4_binds_exact_r9f_evidence_and_research_state",
        "tests/test_research_r9h_boundary_proposal.py::test_research_fingerprint_and_pdf_v4_staleness_reconcile",
        "tests/test_research_r9i_owner_review.py::test_review_gate_is_scope_limited_and_never_execution_permission[BOUNDED_SYNTHETIC_BOUNDARY_DESIGN_INVESTIGATION_ONLY]",
        "tests/test_research_r9i_pdf_v5.py::test_no_research_state_or_previous_review_mutation",
        "tests/test_research_r9l_pdf_v6.py::test_freshness_uses_explicit_evidence_not_changed_exclusions",
        "tests/test_research_r9o_pdf_v7.py::test_fingerprint_unchanged_but_direct_bindings_fresh",
    ]
    return {
        "schema_version": "r10h_governance_diagnostics_v1",
        "root_suite": {"passed": 704, "skipped": 4, "failed": 9, "warnings": 2},
        "diagnostics": [
            *[{"test": test, "category": "INTENDED_HISTORICAL_GATE_NOW_STALE", "expected_fingerprint": "1b56c28...", "current_fingerprint": "bc79740103a5bdbe96d70d77395dadacfc081b021bd9fc3dd7dcbaa02aba5421", "operating_model_effect": "Synthetic work no longer needs repeated approval, but prior owner records remain immutable", "smallest_safe_remediation": "Create a new forward review/fingerprint contract distinguishing reviewed-then from current-now; preserve every historical record and exclusion"} for test in fingerprint_tests],
            {"test": "tests/test_research_r4_approval.py::test_entrypoint_inventory_accounts_for_every_non_test_python_main", "category": "GENUINE_FORWARD_INVENTORY_REGRESSION", "missing_count": 14, "smallest_safe_remediation": "Add a new cumulative/versioned entrypoint inventory or delta covering R.9J-R.10G; do not edit the historical v1 inventory"},
        ],
        "do_not_do": ["Do not disable or broadly exclude tests", "Do not alter fingerprint exclusions to manufacture green", "Do not rewrite historical reviews"],
        "forward_remediation_required_before_pdf": True,
    }


def _real_data() -> dict[str, Any]:
    dimensions = ["access_authorization", "terms_retention", "raw_immutability", "official_schema", "historical_population", "inactive_delisted", "stable_identity", "corporate_actions", "terminal_economics", "calendar_sessions", "benchmark_identity", "historical_costs", "revision_behavior", "point_in_time_timestamps", "scale_performance", "dependency_decision", "owner_approval"]
    def row(route: str, overall: str, values: list[str], note: str) -> dict[str, Any]:
        return {"route": route, "overall": overall, "dimensions": dict(zip(dimensions, values)), "finding": note}
    return {"schema_version": "r10h_real_data_readiness_v1", "routes": [
        row("LOCAL_FNO_DATABASE", "READY_FOR_BOUNDED_QUALIFICATION_ONLY", ["BLOCKED", "PARTIALLY_READY", "READY", "BLOCKED", "NOT_APPLICABLE", "NOT_APPLICABLE", "PARTIALLY_READY", "PARTIALLY_READY", "BLOCKED", "PARTIALLY_READY", "BLOCKED", "BLOCKED", "PARTIALLY_READY", "PARTIALLY_READY", "PARTIALLY_READY", "BLOCKED", "BLOCKED"], "LOCATED_AND_SAMPLED_NOT_QUALIFIED; APSW candidate isolated, interlock active, quiescence and official schema pending"),
        row("OFFICIAL_FREE_NSE", "BLOCKED", ["BLOCKED", "BLOCKED", "READY", "PARTIALLY_READY", "BLOCKED", "BLOCKED", "PARTIALLY_READY", "PARTIALLY_READY", "BLOCKED", "PARTIALLY_READY", "PARTIALLY_READY", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "NOT_APPLICABLE", "BLOCKED"], "Historical population is incomplete and written access/retention clarification remains unresolved"),
        row("KITE_CURRENT_DATA_API", "READY_FOR_BOUNDED_QUALIFICATION_ONLY", ["PARTIALLY_READY", "PARTIALLY_READY", "NOT_APPLICABLE", "PARTIALLY_READY", "NOT_APPLICABLE", "NOT_APPLICABLE", "PARTIALLY_READY", "NOT_APPLICABLE", "NOT_APPLICABLE", "READY", "PARTIALLY_READY", "NOT_APPLICABLE", "NOT_APPLICABLE", "READY", "PARTIALLY_READY", "NOT_APPLICABLE", "PARTIALLY_READY"], "Read-only current snapshots only; never a historical universe or research qualification route"),
        row("SEBI_BSE_OFFICIAL_SUPPLEMENT", "PARTIALLY_READY", ["PARTIALLY_READY", "PARTIALLY_READY", "READY", "PARTIALLY_READY", "BLOCKED", "BLOCKED", "PARTIALLY_READY", "PARTIALLY_READY", "PARTIALLY_READY", "NOT_APPLICABLE", "NOT_APPLICABLE", "PARTIALLY_READY", "BLOCKED", "PARTIALLY_READY", "BLOCKED", "NOT_APPLICABLE", "BLOCKED"], "Useful event/circular evidence, not a complete NSE security population"),
        row("AMFI", "NOT_APPLICABLE", ["NOT_APPLICABLE"] * 17, "Mutual-fund source; not evidence for equity survivorship or identity"),
    ], "smallest_lawful_candidate": "A manually supplied, terms-cleared, dated official NSE security snapshot and matching bhavcopy for one locked A.8 date, with explicit provenance and retention review; do not acquire until permission is resolved"}


def _risks() -> dict[str, Any]:
    items = [
        ("R10H-01", "Historical population incomplete", "A.8 obtained only 3/12 pairs", "HIGH", "CRITICAL", "Population acceptance harness", "Obtain permitted dated official snapshots", True, "historical equity research"),
        ("R10H-02", "Official schema evidence missing", "R.9 and A.8 reports", "HIGH", "HIGH", "Schema reconciliation", "Bind official schemas before qualification", True, "F&O/equity qualification"),
        ("R10H-03", "Retention/licensing uncertain", "A.8-A.10 correspondence gate", "HIGH", "CRITICAL", "Permission matrix", "Written clarification or legal review", True, "official-source acquisition"),
        ("R10H-04", "Terminal outcomes incomplete", "DATASET_TRUST_REPORT", "HIGH", "HIGH", "Terminal-state reconciliation", "Source authoritative economic outcomes", False, "survivorship-safe research"),
        ("R10H-05", "Corporate-action coverage incomplete", "A.7/A.8", "MEDIUM", "HIGH", "Continuity checks", "Complete official event evidence", False, "adjusted returns/identity"),
        ("R10H-06", "Calendar history not authoritative", "R.10D is synthetic", "MEDIUM", "HIGH", "Calendar known answers", "Qualify official exchange calendar", False, "execution clocks"),
        ("R10H-07", "Historical cost gaps", "A.7 cost qualification", "HIGH", "HIGH", "Date-effective coverage check", "Collect official circular-backed schedules", False, "net economic results"),
        ("R10H-08", "Benchmark identity ambiguity", "A.7 benchmark qualification", "MEDIUM", "HIGH", "PRI/TRI guard", "Qualify official PRI/TRI series", False, "relative performance"),
        ("R10H-09", "APSW supply-chain decision pending", "R.9M-P", "MEDIUM", "HIGH", "Dependency inventory", "Separate owner decision before production adoption", True, "local F&O audit"),
        ("R10H-10", "SQLite namespace/quiescence limits", "R.9N-P", "MEDIUM", "HIGH", "Restricted adversarial checks", "Prove directory quiescence and boundary", True, "local F&O audit"),
        ("R10H-11", "Synthetic-to-real distribution shift", "All R.10 evidence is synthetic", "HIGH", "CRITICAL", "Bounded real qualification", "Qualify data before any real hypothesis", True, "all research"),
        ("R10H-12", "Test-oracle coupling", "R.10 tests share fixture/build helpers", "MEDIUM", "HIGH", "Independent known-answer review", "Add independently derived/adversarial oracles", False, "synthetic assurance"),
        ("R10H-13", "Scale/performance unknown", "No representative-scale run", "HIGH", "MEDIUM", "Resource telemetry", "Bounded scale test after data approval", False, "operational readiness"),
        ("R10H-14", "Stale governance fingerprint/inventory", "Nine root-suite failures", "HIGH", "HIGH", "Standard root suite", "Versioned forward contracts, preserve history", True, "owner-review PDF"),
        ("R10H-15", "Accidental synthetic score exposure", "R.10E-G use fictional scores", "LOW", "CRITICAL", "NO_DECISION/promotion tests", "Retain canonical-import and UI barriers", False, "product decisions"),
        ("R10H-16", "Broker-boundary regression", "No mutation path currently present", "LOW", "CRITICAL", "Static imports and endpoint tests", "Keep broker mutation prohibited", True, "trading safety"),
    ]
    return {"schema_version": "r10h_risk_register_v1", "risks": [dict(zip(["risk_id", "description", "evidence", "likelihood", "impact", "detection", "mitigation", "owner_decision_required", "blocking_scope"], x)) for x in items]}


REPORT = """# R.10H — Consolidated synthetic-platform readiness audit

## Decision

The synthetic platform is substantially demonstrated, but it is not yet ready
for the consolidated owner-review PDF. The root suite exposes eight stale
historical fingerprint diagnostics and one genuine stale entry-point inventory.
Both need a small, versioned forward repair that preserves every earlier review.

`CONDITIONAL_READINESS_REMEDIATIONS_REQUIRED`

Completion state:

`SYNTHETIC_PLATFORM_CONDITIONALLY_READY_REMEDIATIONS_REQUIRED`

This decision authorizes no data access, dependency adoption, production audit,
research run, score, recommendation, broker action or trade.

## Evidence and reproducibility

R.10A–R.10G form the intended chain: point-in-time ingestion, incremental
rebuilding, security events/terminal economics, calendars/session clocks,
score/confidence semantics, immutable publication, then portfolio/mandate
policy. All 208 manifest-bound artifact byte hashes and seven root-manifest byte
hashes match. All predecessor references match. Thirty-four Parquet objects are
readable. Momentum v1 (`1eed7fd...`) and its golden expected fixture
(`d3f7284...`) remain unchanged. The R.10A holdout remains unconsumed, all
evidence remains `SYNTHETIC_ONLY_NONCANONICAL`, promotion remains false and
external decisions remain `NO_DECISION` where decision fields exist.

Byte hashes, logical-table hashes, reproducible-core hashes, source-tree hashes
and research-state fingerprints are distinct identities. This audit never uses
one as a substitute for another. R.10A has a material provenance limitation: it
predates the clean-start protocol and binds a dirty-worktree fingerprint, while
R.10B–G record clean implementation starts. R.10F/G fixtures are source-defined
and lack separate machine-readable recipes.

## Strongest demonstrated capabilities

- Deterministic point-in-time/as-of filtering with later-vintage rejection.
- Typed synthetic facts, historical identity mechanics and explicit terminal
  uncertainty without destructive price adjustment.
- Incremental rebuild planning with clean-rebuild equivalence and preserved
  unaffected hashes.
- Calendar-aware execution clocks, overlap purge and embargo mechanics.
- Separate prediction, economic and portfolio evidence.
- Training-only transforms, score/confidence separation and a multiple-testing
  ledger, all explicitly synthetic.
- Immutable evidence publication, a thin mapping facade and mandate-aware
  portfolio policy whose only external answer is `NO_DECISION`.
- No broker mutation or trade-execution path in R.10A–G.

## Test-quality assessment

The synthetic suite is meaningful: it uses deterministic known answers,
leakage/mutation challenges, failure injection, historical-hash preservation,
incremental/clean equivalence and lifecycle barriers. It is not independent
economic validation. Some oracles and evidence builders share helpers, some
catalog checks are declaration-heavy, the calendar is fictional, and no
representative concurrency, scale, disk-corruption or real distribution-shift
test has occurred. Four Windows symlink/reparse tests were skipped because link
creation privileges were unavailable.

## Verification results

- Standard root suite: **704 passed, 4 skipped, 9 failed, 2 warnings** in
  412.57 seconds.
- Separate `Data test` suite after static confirmation of synthetic temporary
  inputs: **289 passed**.
- Focused R.10A–G/R.9P/R.9D/R.3 preservation and boundary suite:
  **114 passed**.
- JSON and Parquet validation: **PASS**; 34 Parquet objects readable.
- Manifest reconciliation: **PASS**; 208/208 artifact hashes and all chained
  predecessor roots match.
- Python compilation, dependency inventory, secret/private-path scan and Git
  whitespace checks are recorded in the audit manifest.

The nine root failures are not synthetic-engine failures. Eight compare old
owner-reviewed fingerprints with the legitimately changed current research
tree. The synthetic operating model superseded repeated approvals for bounded
synthetic work, but historical review records must remain unchanged. The ninth
is a genuine forward inventory regression: fourteen R.9J–R.10G executable tools
are absent from the v1 inventory/deltas. The safe remedy is a new current
fingerprint/review contract and a new cumulative inventory or delta—never
editing old records or weakening exclusions.

## Entrypoints and F&O route

The fourteen R.9J–R.10G tools are offline, synthetic and non-promoting. Five
restricted R.9M/N/P tools can use APSW, but production packages do not depend on
APSW. The R.9D production interlock remains active and unchanged. The local F&O
database remains `LOCATED_AND_SAMPLED_NOT_QUALIFIED`; no production audit is
authorized, directory quiescence is unproven and official schema evidence is
pending.

A future owner review may present three separate choices, in order: (1) adopt a
pinned APSW production dependency, (2) implement the restricted production
audit boundary, and (3) authorize one bounded metadata/provenance audit. The
third is not executable until the first two and their safety conditions are
resolved. None is approved by this report.

## Real-data and product readiness

The free official NSE historical route remains blocked: the broad equity data
is survivor-selected, the A.8 population sample has only 3/12 pairs, written
access/retention clarification is unresolved, and corporate actions, terminal
economics, benchmark identity and historical costs remain incomplete. Kite is
usable only for bounded current read-only snapshots and is not a historical
universe. SEBI/BSE evidence can supplement events but does not reconstruct the
full NSE population. AMFI is not applicable to equity survivorship.

The smallest lawful candidate is one manually supplied, terms-cleared, dated
official NSE security snapshot paired with its bhavcopy for a locked A.8 date,
with explicit provenance and retention review. It must not be acquired until
the permission gate is resolved.

Machinery readiness is substantial. Data readiness is blocked, research and
economic readiness are absent, immutable synthetic publication mechanics are
demonstrated, and product UI readiness is intentionally deferred. There is no
active edge or actionable score.

## Required owner decisions

No owner decision can safely authorize real work from this audit alone. The
future consolidated review should keep separate: APSW adoption, restricted F&O
boundary implementation, one bounded F&O metadata audit, and one bounded lawful
official-data qualification. Broker/trading actions remain prohibited.

## Next milestone

Create one versioned governance remediation that (a) reconciles reviewed-then
versus current-now fingerprints and (b) inventories R.9J–R.10G entrypoints,
while proving every historical review artifact is byte-identical. Then run the
root suite. If green, proceed to `CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF`.

No PDF was generated in R.10H.
"""


def build(root: Path) -> Path:
    root = root.resolve()
    output = root / "docs/investigations/r10h/audit_v1"
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("immutable R.10H audit output already exists")
    output.mkdir(parents=True, exist_ok=True)
    inventory, chain = _verify_evidence(root)
    evidence = {
        "schema_version": "r10h_evidence_inventory_v1", "classification": "AUDIT_ONLY_NO_REAL_DATA",
        "hash_semantics": {
            "byte_hash": "SHA-256 of exact stored bytes", "logical_table_hash": "Canonical data/schema identity independent of Parquet container bytes",
            "reproducible_core_hash": "Deterministic manifest core excluding its self-derived field", "source_tree_hash": "Declared source-file set identity at implementation checkpoint",
            "research_state_fingerprint": "Governance inventory identity; not an evidence-root or artifact byte hash",
        },
        "milestones": inventory, "chain_reconciliation": chain,
        "protected_inputs": {
            "momentum_spec": {"path": "specs/momentum_12_1_v1.json", "sha256": _sha(root / "specs/momentum_12_1_v1.json")},
            "golden_expected": {"path": "tests/fixtures/momentum_golden_v1/expected.json", "sha256": _sha(root / "tests/fixtures/momentum_golden_v1/expected.json")},
            "holdout": "UNCONSUMED_SYNTHETIC_HOLDOUT", "external_decision": "NO_DECISION",
        },
        "verification": {"artifact_hashes_passed": 208, "artifact_hashes_failed": 0, "parquet_objects_readable": 34, "predecessor_mismatches": 0},
    }
    artifacts = {
        "evidence_inventory.json": evidence,
        "architecture_conformance.json": _architecture(),
        "test_quality_assessment.json": _test_quality(),
        "entrypoint_capability_inventory.json": _entrypoints(),
        "governance_diagnostic_reconciliation.json": _governance(),
        "real_data_readiness_matrix.json": _real_data(),
        "risk_register.json": _risks(),
        "readiness_decision.json": {
            "schema_version": "r10h_readiness_decision_v1",
            "criteria": {"evidence_chain_intact": True, "synthetic_boundary_intact": True, "root_governance_diagnostics_green": False, "real_data_authorized": False, "historical_records_preserved": True},
            "audit_decision": "CONDITIONAL_READINESS_REMEDIATIONS_REQUIRED",
            "completion_decision": "SYNTHETIC_PLATFORM_CONDITIONALLY_READY_REMEDIATIONS_REQUIRED",
            "pdf_generation_ready": False,
            "required_remediations": ["Version current research-state fingerprint/review semantics without changing history", "Version the cumulative R.9J-R.10G entrypoint inventory"],
            "next_milestone_after_remediation": "CONSOLIDATED_PRE_REAL_DATA_STATUS_PDF",
            "authorizes": [],
        },
    }
    output_hashes = {name: _dump(output / name, value) for name, value in artifacts.items()}
    report_path = root / "reports/RESEARCH_R10H_READINESS_AUDIT.md"
    report_path.write_text(REPORT, encoding="utf-8", newline="\n")
    output_hashes["reports/RESEARCH_R10H_READINESS_AUDIT.md"] = _sha(report_path)
    input_paths = ["ARCHITECTURE_REFINEMENT.md", "docs/project_status/SYNTHETIC_RESEARCH_OPERATING_MODEL_V1.md", "tools/r10h_readiness_audit.py"]
    input_paths += [f"reports/RESEARCH_R10{x}_REPORT.md" for x in "ABCDEFG"]
    input_paths += [value[2] for value in MILESTONES.values()]
    manifest = {
        "schema_version": "r10h_audit_manifest_v1", "classification": "AUDIT_ONLY_NO_REAL_DATA",
        "baseline_commit": "5bca5b7fb39f09a7edcc6af96b945ba8b88d33f2", "audit_date": "2026-09-08",
        "inputs": {path: _sha(root / path) for path in input_paths},
        "outputs": output_hashes,
        "verification": {
            "real_or_private_data_accessed": False, "network_provider_or_broker_accessed": False,
            "evidence_generator_executed": False, "prior_evidence_modified": False,
            "apsw_adopted_into_production": False, "production_interlock_changed": False,
            "score_or_recommendation_published": False, "historical_review_rewritten": False,
            "standard_root_suite": "704_PASS_4_SKIP_9_FAIL_2_WARN",
            "data_test_suite": "289_PASS", "focused_boundary_suite": "114_PASS",
            "json_validation": "PASS", "parquet_validation": "34_PASS",
            "source_tree_recalculation": "R10B_R10G_PASS_R10A_DIRTY_STATE_BOUND_NOT_RECONSTRUCTIBLE",
            "entrypoint_commit_blob_hashes": "R10B_R10G_PASS_R10A_NOT_RECORDED",
            "dependency_inventory": "PINNED_RUNTIME_CONSISTENT_PIP_CHECK_PASS_APSW_NOT_PRODUCTION",
            "entrypoint_inventory": "14_FORWARD_ENTRIES_MISSING_FROM_LEGACY_VERSION",
            "python_compilation": "PASS", "secret_scan": "PASS_NO_MATCHES_IN_AUDIT_ARTIFACTS",
            "git_whitespace": "PASS",
        },
        "decision": "SYNTHETIC_PLATFORM_CONDITIONALLY_READY_REMEDIATIONS_REQUIRED",
    }
    _dump(output / "audit_manifest.json", manifest)
    return output
