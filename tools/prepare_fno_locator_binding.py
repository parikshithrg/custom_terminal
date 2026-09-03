"""Run one approved filesystem-only F&O locator-binding preparation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from market_intel.foundation.fno_locator_binding import (
    PREPARED,
    LocatorBindingError,
    prepare_production_binding,
    write_binding_artifacts,
)
from research_contracts.legacy_ledger import sha256_file


EXPECTED_PDF_SHA256 = "75af99e3e481a4d8e490e24cbf24c979a2111067412d2a14344630beaca8b2a2"
APPROVED_SCOPE = "EXACT_PRODUCTION_LOCATOR_BINDING_PREPARATION"


def _head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def _require_clean_source_and_ignored_private_destination(root: Path) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=True,
        capture_output=True, text=True, timeout=10,
    )
    if status.stdout.strip():
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "source tree is not clean")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "artifacts/private_fno_binding/r9f/raw_binding.json"],
        cwd=root, check=False, capture_output=True, timeout=10,
    )
    if ignored.returncode != 0:
        raise LocatorBindingError(
            "FNO_BINDING_SCOPE_VIOLATION", "private binding destination is not ignored"
        )


def _validate_review(root: Path) -> None:
    record = json.loads(
        (root / "docs/project_status/pre_research_review_record_v3.json").read_text(
            encoding="utf-8"
        )
    )
    if record.get("review_status") != "REPORT_REVIEWED_APPROVED":
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "PDF v3 is not approved")
    if record.get("covered_future_scope") != [APPROVED_SCOPE]:
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "approved scope mismatch")
    authority = record.get("execution_authority", {})
    required = (
        "locator_binding_preparation_authorized",
        "configuration_value_read_authorized",
        "filesystem_identity_pass_authorized",
    )
    prohibited = (
        "sqlite_access_authorized",
        "audit_execution_authorized",
        "market_row_access_authorized",
        "scoring_or_backtesting_authorized",
        "broker_actions_authorized",
        "trading_authorized",
    )
    if not all(authority.get(key) is True for key in required):
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "preparation authority missing")
    if not all(authority.get(key) is False for key in prohibited):
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "prohibited authority present")
    if sha256_file(root / record["pdf_path"]) != EXPECTED_PDF_SHA256:
        raise LocatorBindingError("FNO_BINDING_SCOPE_VIOLATION", "approved PDF mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    try:
        _validate_review(root)
        _require_clean_source_and_ignored_private_destination(root)
        source_commit = _head(root)
        binding = prepare_production_binding(
            config_path=root / "Data test/config/config.toml",
            source_commit=source_commit,
        )
        hashes = write_binding_artifacts(
            binding,
            private_path=root / "artifacts/private_fno_binding/r9f/raw_binding.json",
            anchor_path=root / "evidence/fno_locator_binding_v1/anchor.json",
            proposal_path=root / "proposals/fno_locator_binding_v1/binding_proposal.json",
        )
    except LocatorBindingError as exc:
        print(json.dumps({"decision": exc.decision, "message": str(exc)}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({
            "decision": "FNO_BINDING_SCOPE_VIOLATION",
            "message": "binding preparation failed without private diagnostic disclosure",
        }, sort_keys=True))
        return 2
    print(json.dumps({
        "decision": PREPARED,
        "sanitized_alias": binding.tracked_anchor["sanitized_alias"],
        "anchor_sha256": hashes["anchor_sha256"],
        "proposal_sha256": hashes["proposal_sha256"],
        "private_artifact_persisted_outside_git": True,
        "database_connected": False,
        "sql_executed": False,
        "market_rows_read": False,
        "audit_started": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
