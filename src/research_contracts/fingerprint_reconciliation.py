"""Forward-only reconciliation of historical review and current fingerprints."""

from __future__ import annotations

from copy import deepcopy
import fnmatch
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

from .legacy_ledger import canonical_json_bytes, sha256_bytes, sha256_file
from .pre_research_review import compute_research_state_fingerprint


RECONCILIATION_SCHEMA_VERSION = "research_fingerprint_reconciliation_v1"
COHERENCE_AMENDMENT_SCHEMA_VERSION = "research_fingerprint_coherence_amendment_v2"
CURRENT_FOR_DECLARED_SCOPE = "CURRENT_FOR_DECLARED_SCOPE"
HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE = (
    "HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE"
)
INVALID = "INVALID"
VALID_RELATIONSHIPS = frozenset({
    CURRENT_FOR_DECLARED_SCOPE,
    HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE,
    INVALID,
})


class FingerprintReconciliationError(ValueError):
    """Raised when a checkpoint or historical binding cannot be verified."""


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate repository globs, treating ``**/`` as zero or more directories."""
    index = 0
    parts = ["^"]
    while index < len(pattern):
        if pattern[index:index + 3] == "**/":
            parts.append("(?:.*/)?")
            index += 3
        elif pattern[index:index + 2] == "**":
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    parts.append("$")
    return re.compile("".join(parts))


def _git(repository_root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=repository_root, input=input_bytes,
            check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise FingerprintReconciliationError("immutable Git object query failed") from exc


def git_commit_research_state_fingerprint(
    repository_root: str | Path, policy: Mapping[str, Any], commit: str,
) -> dict[str, Any]:
    """Fingerprint exact blob bytes from an immutable Git commit.

    This intentionally does not use ``git archive`` or a checkout: both can
    apply end-of-line conversion and therefore describe a working tree rather
    than the committed object bytes.
    """
    root = Path(repository_root).resolve()
    resolved = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    names = _git(root, "ls-tree", "-r", "--name-only", "-z", resolved).decode().split("\0")
    state = policy.get("research_state", {})
    include = [_glob_regex(str(item)) for item in state.get("include_globs", [])]
    exclude = list(state.get("exclude_globs", []))
    selected = sorted(
        path for path in names if path and any(rule.match(path) for rule in include)
        and not any(fnmatch.fnmatch(path, str(rule)) for rule in exclude)
    )
    if not selected:
        raise FingerprintReconciliationError("Git research-state inventory is empty")

    process = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None
    inventory: list[dict[str, Any]] = []
    try:
        for path in selected:
            process.stdin.write(f"{resolved}:{path}\n".encode())
            process.stdin.flush()
            header = process.stdout.readline().decode().rstrip("\n")
            fields = header.split()
            if len(fields) != 3 or fields[1] != "blob":
                raise FingerprintReconciliationError("Git inventory contains a non-blob object")
            size = int(fields[2])
            content = process.stdout.read(size)
            if len(content) != size or process.stdout.read(1) != b"\n":
                raise FingerprintReconciliationError("Git blob response was truncated")
            inventory.append({
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "byte_size": size,
            })
    finally:
        if process.stdin:
            process.stdin.close()
        process.wait(timeout=10)
    inventory_hash = sha256_bytes(canonical_json_bytes(inventory))
    return {
        "algorithm": "sha256_canonical_inventory_v1",
        "commit": resolved,
        "sha256": inventory_hash,
        "file_count": len(inventory),
        "fingerprint_input_inventory_hash": inventory_hash,
        "inventory": inventory,
    }


def validate_fingerprint_coherence_amendment(
    amendment: Mapping[str, Any], *, repository_root: str | Path,
    policy: Mapping[str, Any], preserved_v1_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Validate the forward amendment and its state-specific fingerprint claims."""
    if amendment.get("schema_version") != COHERENCE_AMENDMENT_SCHEMA_VERSION:
        raise FingerprintReconciliationError("unsupported coherence amendment schema")
    if amendment.get("payload_sha256") != _payload_hash(amendment):
        raise FingerprintReconciliationError("coherence amendment payload hash mismatch")
    if amendment.get("fingerprint_policy_version") != policy.get("policy_version"):
        raise FingerprintReconciliationError("coherence amendment policy mismatch")
    root = Path(repository_root).resolve()
    for relative, expected in preserved_v1_hashes.items():
        if not (root / relative).is_file() or sha256_file(root / relative) != expected:
            raise FingerprintReconciliationError("historical R10I v1 evidence was modified")
    for label in ("implementation_source", "evidence"):
        claim = amendment.get("state_references", {}).get(label, {})
        if claim.get("reference_kind") != "IMMUTABLE_GIT_COMMIT":
            raise FingerprintReconciliationError("commit fingerprint mislabeled")
        actual = git_commit_research_state_fingerprint(root, policy, str(claim.get("commit")))
        for key in ("sha256", "file_count", "fingerprint_input_inventory_hash"):
            if claim.get(key) != actual[key]:
                raise FingerprintReconciliationError(f"{label} fingerprint claim mismatch")
    authority = amendment.get("authority", {})
    if not authority or any(value is not False for value in authority.values()):
        raise FingerprintReconciliationError("coherence amendment cannot expand authority")
    return {
        "status": "VALID_STATE_SPECIFIC_COHERENCE_AMENDMENT",
        "authority_extended": False,
        "implementation_source_commit": amendment["state_references"]["implementation_source"]["commit"],
    }


def coherence_binding_hash(amendment: Mapping[str, Any]) -> str:
    """Bind the state model reused by the amendment's human and machine outputs."""
    payload = {
        "fingerprint_policy_version": amendment.get("fingerprint_policy_version"),
        "fingerprint_algorithm": amendment.get("fingerprint_algorithm"),
        "state_references": amendment.get("state_references"),
        "conflicting_claims": amendment.get("conflicting_claims"),
        "original_completion_decision_remains_valid": amendment.get(
            "original_completion_decision_remains_valid"
        ),
        "completion_decision": amendment.get("completion_decision"),
        "authority": amendment.get("authority"),
    }
    return sha256_bytes(canonical_json_bytes(payload))


def validate_fingerprint_coherence_bundle(
    *, amendment: Mapping[str, Any], completion: Mapping[str, Any],
    manifest: Mapping[str, Any], report_text: str, repository_root: str | Path,
) -> dict[str, Any]:
    """Enforce cross-artifact agreement and the manifest payload/root design."""
    binding = coherence_binding_hash(amendment)
    if amendment.get("coherence_binding_sha256") != binding:
        raise FingerprintReconciliationError("amendment coherence binding mismatch")
    if completion.get("coherence_binding_sha256") != binding:
        raise FingerprintReconciliationError("completion disagrees with amendment")
    if manifest.get("coherence_binding_sha256") != binding:
        raise FingerprintReconciliationError("manifest disagrees with amendment")
    if f"Coherence binding: `{binding}`" not in report_text:
        raise FingerprintReconciliationError("report disagrees with structured evidence")
    if completion.get("completion_decision") != amendment.get("completion_decision"):
        raise FingerprintReconciliationError("completion decision mismatch")

    manifest_payload = dict(manifest)
    expected_payload = manifest_payload.pop("payload_sha256", None)
    expected_root = manifest_payload.pop("root_sha256", None)
    actual_payload = sha256_bytes(canonical_json_bytes(manifest_payload))
    if expected_payload != actual_payload:
        raise FingerprintReconciliationError("manifest payload hash mismatch")
    root_payload = {
        "manifest_payload_sha256": actual_payload,
        "outputs": manifest.get("outputs"),
    }
    if expected_root != sha256_bytes(canonical_json_bytes(root_payload)):
        raise FingerprintReconciliationError("manifest root hash mismatch")
    root = Path(repository_root).resolve()
    for relative, expected in manifest.get("outputs", {}).items():
        if not (root / relative).is_file() or sha256_file(root / relative) != expected:
            raise FingerprintReconciliationError("manifest output hash mismatch")
    return {"status": "VALID_COHERENT_AMENDMENT_BUNDLE", "coherence_binding_sha256": binding}


def _payload_hash(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("deterministic_payload_sha256", None)
    return sha256_bytes(canonical_json_bytes(payload))


def create_fingerprint_reconciliation(
    *, repository_root: str | Path, policy: Mapping[str, Any],
    historical_records: Sequence[str], checkpoint_id: str,
    generated_at: str, source_commit: str, clean_start: bool,
    evidence_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Create a deterministic checkpoint without granting review authority."""
    root = Path(repository_root).resolve()
    current = compute_research_state_fingerprint(root, policy)
    reviews = []
    for relative in historical_records:
        path = root / relative
        record = __import__("json").loads(path.read_text(encoding="utf-8"))
        reviewed = str(record["research_state_fingerprint"])
        relationship = (
            CURRENT_FOR_DECLARED_SCOPE if reviewed == current["sha256"]
            else HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE
        )
        reviews.append({
            "review_id": f"{record['report_id']}:{record['report_version']}",
            "record_path": relative,
            "record_byte_sha256": sha256_file(path),
            "reviewed_fingerprint": reviewed,
            "reviewed_file_count": record.get("research_state_file_count"),
            "review_scope": list(record.get("covered_future_scope", [])),
            "review_source_commit": record.get("summarized_source_commit"),
            "current_scope_status": relationship,
            "transition_reason": (
                "Reviewed fingerprint equals the current policy inventory."
                if relationship == CURRENT_FOR_DECLARED_SCOPE else
                "The review remains authentic for its recorded scope, but later repository scope is not authorized by it."
            ),
        })
    result = {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "checkpoint_id": checkpoint_id,
        "generation_timestamp": generated_at,
        "source_commit": source_commit,
        "execution_start_clean": bool(clean_start),
        "fingerprint_policy": {
            "policy_version": policy["policy_version"],
            "algorithm": current["algorithm"],
            "include_globs": list(policy["research_state"]["include_globs"]),
            "exclude_globs": list(policy["research_state"]["exclude_globs"]),
        },
        "current_fingerprint": current["sha256"],
        "current_file_count": current["file_count"],
        "historical_reviews": reviews,
        "referenced_evidence_hashes": dict(sorted(evidence_hashes.items())),
        "authority": {
            "historical_scope_expansion": False,
            "research_execution_authorized": False,
            "real_data_access_authorized": False,
            "trading_authorized": False,
        },
    }
    result["deterministic_payload_sha256"] = _payload_hash(result)
    return result


def validate_fingerprint_reconciliation(
    checkpoint: Mapping[str, Any], *, repository_root: str | Path,
    policy: Mapping[str, Any], historical_records: Sequence[str],
) -> dict[str, Any]:
    """Verify current state and historical records without extending authority."""
    if checkpoint.get("schema_version") != RECONCILIATION_SCHEMA_VERSION:
        raise FingerprintReconciliationError("unsupported reconciliation schema")
    if checkpoint.get("deterministic_payload_sha256") != _payload_hash(checkpoint):
        raise FingerprintReconciliationError("reconciliation payload hash mismatch")
    declared_policy = checkpoint.get("fingerprint_policy")
    expected_policy = {
        "policy_version": policy["policy_version"],
        "algorithm": "sha256_canonical_inventory_v1",
        "include_globs": list(policy["research_state"]["include_globs"]),
        "exclude_globs": list(policy["research_state"]["exclude_globs"]),
    }
    if declared_policy != expected_policy:
        raise FingerprintReconciliationError("fingerprint policy or exclusions changed")
    root = Path(repository_root).resolve()
    current = compute_research_state_fingerprint(root, policy)
    if checkpoint.get("current_fingerprint") != current["sha256"] or checkpoint.get("current_file_count") != current["file_count"]:
        raise FingerprintReconciliationError("current fingerprint checkpoint is stale")
    expected_paths = list(historical_records)
    rows = checkpoint.get("historical_reviews")
    if not isinstance(rows, list) or [row.get("record_path") for row in rows] != expected_paths:
        raise FingerprintReconciliationError("historical review set or order mismatch")
    for row in rows:
        path = root / row["record_path"]
        if not path.is_file() or sha256_file(path) != row.get("record_byte_sha256"):
            raise FingerprintReconciliationError("historical review hash mismatch")
        record = __import__("json").loads(path.read_text(encoding="utf-8"))
        if row.get("reviewed_fingerprint") != record.get("research_state_fingerprint"):
            raise FingerprintReconciliationError("historical reviewed fingerprint mismatch")
        if row.get("review_scope") != record.get("covered_future_scope", []):
            raise FingerprintReconciliationError("historical review scope mismatch")
        expected_status = (
            CURRENT_FOR_DECLARED_SCOPE
            if row["reviewed_fingerprint"] == current["sha256"]
            else HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE
        )
        if row.get("current_scope_status") != expected_status:
            raise FingerprintReconciliationError("invalid historical-to-current relationship")
        if row.get("current_scope_status") not in VALID_RELATIONSHIPS:
            raise FingerprintReconciliationError("unknown scope relationship")
    authority = checkpoint.get("authority", {})
    if any(authority.get(key) is not False for key in (
        "historical_scope_expansion", "research_execution_authorized",
        "real_data_access_authorized", "trading_authorized",
    )):
        raise FingerprintReconciliationError("reconciliation cannot grant authority")
    return {
        "status": "VALID_FORWARD_RECONCILIATION",
        "current_fingerprint": current["sha256"],
        "historical_review_count": len(rows),
        "authority_extended": False,
    }


def tampered_copy(checkpoint: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    """Test helper returning a deep copy without resealing it."""
    result = deepcopy(dict(checkpoint))
    result.update(updates)
    return result
