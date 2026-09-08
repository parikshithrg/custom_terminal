"""Build R.10I forward governance artifacts from tracked repository state.

The module intentionally has no command-line entrypoint.  It discovers Python
main guards, hashes tracked sources, and writes governance metadata only.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from research_contracts.fingerprint_reconciliation import create_fingerprint_reconciliation


ROOTS = ("Data test", "scripts", "tools", "src", "views")
CAPABILITY_FIELDS = (
    "real_or_private_data_eligibility", "network_or_provider_access",
    "arbitrary_filesystem_or_private_config", "sqlite_capability", "apsw_capability",
    "broker_connectivity", "research_computation", "evidence_publication",
    "lifecycle_promotion", "decision_output", "external_mutation",
)
R10_MILESTONES = {
    "tools/r9j_synthetic_boundary.py": "R.9J", "tools/r9k_windows_feasibility.py": "R.9K",
    "tools/r9m_vfs_evaluation.py": "R.9M", "tools/r9n_adversarial.py": "R.9N",
    "tools/r9n_regression.py": "R.9N", "tools/r9p_integrated.py": "R.9P",
    "tools/r9p_regression.py": "R.9P", **{f"tools/r10{x}_generate_evidence.py": f"R.10{x.upper()}" for x in "abcdefg"},
}
APSW_TOOLS = {path for path in R10_MILESTONES if path.startswith(("tools/r9m", "tools/r9n", "tools/r9p"))}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, sort_keys=True, indent=2) + "\n"
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(data, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def discover_entrypoints(root: Path) -> list[str]:
    found = set()
    for root_name in ROOTS:
        for path in (root / root_name).rglob("*.py"):
            relative = path.relative_to(root).as_posix()
            if "/tests/" in f"/{relative}/":
                continue
            if "__main__" in path.read_text(encoding="utf-8"):
                found.add(relative)
    return sorted(found)


def _legacy_classifications(root: Path) -> dict[str, str]:
    inventory = json.loads((root / "specs/laboratory_entrypoint_inventory_v1.json").read_text())
    result = dict(inventory["executable_paths"])
    for path in sorted((root / "specs").glob("research_*_entrypoint_delta_v1.json")):
        delta = json.loads(path.read_text())
        for entry in delta.get("added_executable_entrypoints", []):
            result[entry["path"]] = entry["classification"]
    return result


def _purpose(path: str, source: str) -> str:
    first = re.search(r'^[uUrR]*(?:"""|\'\'\')([^\n]+)', source)
    return first.group(1).strip() if first else f"Governed inventory of {Path(path).stem}"


def build_cumulative_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    legacy = _legacy_classifications(root)
    entries = []
    for relative in discover_entrypoints(root):
        source = (root / relative).read_text(encoding="utf-8")
        r10 = relative in R10_MILESTONES
        data_test = relative.startswith("Data test/")
        network = bool(re.search(r"\b(requests|urllib|httpx|yfinance)\b", source))
        private_config = "load_config" in source or "configured_database" in source
        sqlite = bool(re.search(r"\b(sqlite3|apsw)\b", source, re.I))
        classification = legacy.get(relative, "OFFLINE_SYNTHETIC_NONCANONICAL_NONPROMOTING" if r10 else "UNCLASSIFIED_BLOCKED")
        entries.append({
            "path": relative, "source_sha256": _sha(root / relative),
            "introduction_milestone": R10_MILESTONES.get(relative, "PRE_R9J_OR_LEGACY_DELTA"),
            "entrypoint_mechanism": "PYTHON_MAIN_GUARD", "intended_purpose": _purpose(relative, source),
            "real_or_private_data_eligibility": "SYNTHETIC_ONLY" if r10 else ("DEVELOPMENT_NONCANONICAL_REAL_CAPABLE" if data_test else "AS_GOVERNED_BY_EXISTING_CLASSIFICATION"),
            "network_or_provider_access": "NO" if r10 else ("YES" if network else "NO_SOURCE_INDICATION"),
            "arbitrary_filesystem_or_private_config": "NO" if r10 else ("YES" if private_config else "BOUNDED_OR_UNDETERMINED"),
            "sqlite_capability": "RESTRICTED_SYNTHETIC" if r10 and (relative.startswith("tools/r9") or sqlite) else ("YES" if sqlite else "NO"),
            "apsw_capability": "RESTRICTED_SYNTHETIC_NOT_PRODUCTION" if relative in APSW_TOOLS else "NO",
            "broker_connectivity": "NO" if r10 else "NO_SOURCE_INDICATION",
            "research_computation": "SYNTHETIC_ENGINEERING_ONLY" if relative.startswith("tools/r10") else ("NO" if relative.startswith("tools/r9") else "POSSIBLE_DEVELOPMENT_ONLY"),
            "evidence_publication": "SYNTHETIC_NONCANONICAL_ONLY" if r10 else "AS_GOVERNED_BY_EXISTING_CLASSIFICATION",
            "lifecycle_promotion": "NO" if r10 else "GOVERNANCE_INTERLOCK_REQUIRED",
            "decision_output": "NO_EXTERNAL_DECISION" if r10 else "NONCANONICAL_OR_GOVERNED_ONLY",
            "external_mutation": "NO" if r10 else "UNDETERMINED_BY_INVENTORY",
            "permitted_operating_mode": "OFFLINE_SYNTHETIC_ONLY" if r10 else "EXISTING_GOVERNANCE_CLASSIFICATION_ONLY",
            "governance_classification": classification,
            "applicable_interlocks": ["SYNTHETIC_NONCANONICAL", "NO_PROMOTION", "NO_EXTERNAL_DECISION"] if r10 else [classification],
        })
    return {
        "schema_version": "laboratory_entrypoint_inventory_v2",
        "inventory_kind": "CUMULATIVE_CURRENT_FORWARD_INVENTORY",
        "supersedes_for_current_enforcement": "specs/laboratory_entrypoint_inventory_v1.json",
        "preserves_historical_inventory": True,
        "discovery_roots": list(ROOTS), "detection": "NON_TEST_PYTHON_FILE_CONTAINING___main__",
        "entrypoint_count": len(entries), "entries": entries,
        "unsafe_bypass_count": sum(e["governance_classification"] == "UNSAFE_BYPASS" for e in entries),
    }


def build_policy_v2(root: Path) -> dict[str, Any]:
    v1_path = root / "specs/pre_research_review_policy_v1.json"
    policy = json.loads(v1_path.read_text(encoding="utf-8"))
    policy["policy_version"] = "pre_research_review_policy_v2"
    policy["base_policy"] = {"path": "specs/pre_research_review_policy_v1.json", "sha256": _sha(v1_path)}
    policy["fingerprint_reconciliation"] = {
        "schema_version": "research_fingerprint_reconciliation_v1",
        "current_checkpoint_path": "docs/project_status/research_fingerprint_reconciliation_r10i_v1.json",
        "statuses": ["CURRENT_FOR_DECLARED_SCOPE", "HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE", "INVALID"],
        "rule": "Historical authenticity and present-scope currency are separate; no historical scope expands implicitly.",
    }
    policy["legacy_v1_projection"] = {
        "sha256": "1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef",
        "file_count": 252,
        "inventory_available": False,
        "reason": "Sealed reviewed-era compatibility projection; current scope must use policy v2.",
        "evidence_bindings": [
            {"path": "docs/project_status/pre_research_generation_manifest_v5.json", "sha256": "8f4b1da6cec5db38001e71f988c52809c6968d8f3a934592b637d98110209dd5"},
            {"path": "docs/project_status/pre_research_generation_manifest_v6.json", "sha256": "941e74bd0df3f46833b395a32aaa2702fd92ce406ea2697cb57e87212ad89dd7"},
            {"path": "docs/project_status/pre_research_generation_manifest_v7.json", "sha256": "8651a76f94ec1fbbb1fa53149d4ca70d9375d80e0fa7d0ea47e0de975952d430"},
        ],
    }
    return policy


def write_implementation_specs(root: Path) -> None:
    _write(root / "specs/laboratory_entrypoint_inventory_v2.json", build_cumulative_inventory(root))
    _write(root / "specs/pre_research_review_policy_v2.json", build_policy_v2(root))


def write_clean_checkpoint(root: Path, *, source_commit: str, generated_at: str) -> None:
    root = root.resolve()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("R10I checkpoint requires an exactly clean implementation commit")
    policy = json.loads((root / "specs/pre_research_review_policy_v2.json").read_text())
    records = [f"docs/project_status/pre_research_review_record_v{x}.json" for x in range(1, 6)]
    evidence_paths = ["docs/investigations/r10h/audit_v1/audit_manifest.json"]
    evidence_paths += [f"docs/investigations/r10{x}/run_v1/" + ("root_run_manifest.json" if x == "a" else "root_manifest.json") for x in "abcdefg"]
    checkpoint = create_fingerprint_reconciliation(
        repository_root=root, policy=policy, historical_records=records,
        checkpoint_id="r10i_current_research_state_v1", generated_at=generated_at,
        source_commit=source_commit, clean_start=True,
        evidence_hashes={path: _sha(root / path) for path in evidence_paths},
    )
    checkpoint["entrypoint_inventory"] = {
        "path": "specs/laboratory_entrypoint_inventory_v2.json",
        "sha256": _sha(root / "specs/laboratory_entrypoint_inventory_v2.json"),
    }
    # The inventory binding is part of the deterministic payload.
    payload = dict(checkpoint); payload.pop("deterministic_payload_sha256", None)
    from research_contracts.legacy_ledger import canonical_json_bytes, sha256_bytes
    checkpoint["deterministic_payload_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    _write(root / "docs/project_status/research_fingerprint_reconciliation_r10i_v1.json", checkpoint)
