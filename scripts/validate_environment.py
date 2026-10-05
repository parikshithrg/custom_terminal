"""One-command Windows/Linux migration validation.

Run from the repository root after binding the five DTEST_* paths documented
by ``--help``.  The default is intentionally strict: it hashes the complete
external snapshot and runs both test suites.  ``--quick`` and ``--skip-tests``
are diagnostic conveniences and cannot produce an operational PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_MANIFEST = ROOT / "config" / "data_snapshot_manifest.json"
PYTHON_VERSION_FILE = ROOT / ".python-version"
LOCK_FILE = ROOT / "requirements.lock"
REQUIRED_BINDINGS = (
    "DTEST_PRICE_DIR",
    "DTEST_FNO_DB",
    "DTEST_INDUSTRY_MAP",
    "DTEST_ARTIFACTS_DIR",
    "DTEST_RUNS_DIR",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _price_inventory(root: Path) -> tuple[int, int, str]:
    lines = []
    total = 0
    files = sorted(root.glob("*_DAILY.csv"), key=lambda path: path.name)
    for path in files:
        size = path.stat().st_size
        total += size
        lines.append(f"{path.name}:{size}:{_sha256(path)}")
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return len(files), total, digest


def _locked_versions() -> dict[str, str]:
    versions = {}
    for raw in LOCK_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        versions[name] = version
    return versions


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    return {"commit": commit, "clean": not bool(status.strip()), "status_sha256": hashlib.sha256(status.encode()).hexdigest()}


def _run_tests() -> list[dict[str, Any]]:
    results = []
    with tempfile.TemporaryDirectory(prefix="terminal-builder-pytest-") as temp:
        base = Path(temp)
        commands = (
            ("root", [sys.executable, "-m", "pytest", "-q", f"--basetemp={base / 'root'}"]),
            ("data_test", [sys.executable, "-m", "pytest", "-q", "Data test/tests", f"--basetemp={base / 'data-test'}"]),
        )
        for name, command in commands:
            environment = os.environ.copy()
            if name == "data_test":
                roots = [str(ROOT / "Data test"), str(ROOT / "src")]
                environment["PYTHONPATH"] = os.pathsep.join(roots)
            completed = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True)
            results.append({
                "suite": name,
                "returncode": completed.returncode,
                "passed": completed.returncode == 0,
                "output_tail": (completed.stdout + completed.stderr)[-4000:],
            })
    return results


def validate(*, quick: bool, skip_tests: bool, allow_dirty: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    required_python = PYTHON_VERSION_FILE.read_text(encoding="utf-8").strip()
    actual_python = platform.python_version()
    check("python_version", actual_python == required_python, {"required": required_python, "actual": actual_python})

    mismatches = {}
    for distribution, required in _locked_versions().items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != required:
            mismatches[distribution] = {"required": required, "actual": actual}
    check("locked_dependencies", not mismatches, mismatches or "all exact")

    git = _git_state()
    check("clean_git_commit", git["clean"] or allow_dirty, git)

    missing = [name for name in REQUIRED_BINDINGS if not os.environ.get(name, "").strip()]
    check("machine_bindings", not missing, {"missing": missing})
    if missing:
        return _result(checks, quick=quick, skip_tests=skip_tests)

    price_root = Path(os.environ["DTEST_PRICE_DIR"])
    fno_db = Path(os.environ["DTEST_FNO_DB"])
    industry_map = Path(os.environ["DTEST_INDUSTRY_MAP"])
    artifacts = Path(os.environ["DTEST_ARTIFACTS_DIR"])
    runs = Path(os.environ["DTEST_RUNS_DIR"])
    expected = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))["datasets"]

    check("price_directory", price_root.is_dir(), str(price_root))
    check("fno_database", fno_db.is_file(), str(fno_db))
    check("industry_map", industry_map.is_file(), str(industry_map))
    for name, target in (("artifact_root", artifacts), ("runs_root", runs)):
        parent = next((candidate for candidate in (target, *target.parents) if candidate.exists()), None)
        check(name, parent is not None and os.access(parent, os.W_OK), str(target))

    if price_root.is_dir():
        count, total, digest = _price_inventory(price_root)
        target = expected["nse_cash_daily"]
        check("price_snapshot_identity", (count, total, digest) == (
            target["file_count"], target["total_bytes"], target["inventory_sha256"]
        ), {"file_count": count, "total_bytes": total, "inventory_sha256": digest})
    if industry_map.is_file():
        target = expected["nifty500_industry_map"]
        check("industry_map_identity", industry_map.stat().st_size == target["bytes"] and _sha256(industry_map) == target["sha256"],
              {"bytes": industry_map.stat().st_size, "sha256": _sha256(industry_map)})
    if fno_db.is_file():
        target = expected["nse_fno_sqlite"]
        size_ok = fno_db.stat().st_size == target["bytes"]
        digest = None if quick else _sha256(fno_db)
        check("fno_snapshot_identity", size_ok and (quick or digest == target["sha256"]),
              {"bytes": fno_db.stat().st_size, "sha256": digest, "quick": quick})
        try:
            uri = f"{fno_db.resolve().as_uri()}?mode=ro&immutable=1"
            with sqlite3.connect(uri, uri=True) as connection:
                if quick:
                    table_count = connection.execute(
                        "SELECT count(*) FROM sqlite_master WHERE type='table'"
                    ).fetchone()[0]
                    result = f"quick mode: {table_count} tables readable"
                    passed = table_count > 0
                else:
                    result = connection.execute("PRAGMA quick_check(1)").fetchone()[0]
                    passed = result == "ok"
            check("fno_sqlite_quick_check", passed, result)
        except (OSError, sqlite3.Error) as exc:
            check("fno_sqlite_quick_check", False, f"{type(exc).__name__}: {exc}")

    try:
        import pyarrow.parquet as parquet
        parquet_files = sorted((ROOT / "tests" / "fixtures").rglob("*.parquet"))
        for path in parquet_files:
            parquet.read_schema(path)
        check("tracked_parquet_read", bool(parquet_files), {"files": len(parquet_files)})
    except Exception as exc:  # environment diagnostic must report, not conceal, reader failures
        check("tracked_parquet_read", False, f"{type(exc).__name__}: {exc}")

    if not skip_tests:
        for result in _run_tests():
            check(f"tests_{result['suite']}", result["passed"], result)
    else:
        check("tests_skipped", False, "--skip-tests cannot produce an operational PASS")

    return _result(checks, quick=quick, skip_tests=skip_tests)


def _result(checks: list[dict[str, Any]], *, quick: bool, skip_tests: bool) -> dict[str, Any]:
    operational = not quick and not skip_tests and all(item["passed"] for item in checks)
    return {
        "schema_version": "linux_migration_validation_v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "operational": operational,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the exact Terminal Builder environment and migration snapshot.",
        epilog="Required bindings: " + ", ".join(REQUIRED_BINDINGS),
    )
    parser.add_argument("--quick", action="store_true", help="skip the 45 GB database hash; never operational")
    parser.add_argument("--skip-tests", action="store_true", help="skip test suites; never operational")
    parser.add_argument("--allow-dirty", action="store_true", help="development diagnostics only")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "migration_validation.json")
    args = parser.parse_args()
    result = validate(quick=args.quick, skip_tests=args.skip_tests, allow_dirty=args.allow_dirty)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for item in result["checks"]:
        print(("PASS" if item["passed"] else "FAIL") + f"  {item['name']}: {item['detail']}")
    print("OPERATIONAL" if result["operational"] else "NOT OPERATIONAL")
    return 0 if result["operational"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
