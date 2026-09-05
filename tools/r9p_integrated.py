"""R.9P fixed synthetic-only integrated boundary; public invocation takes no inputs."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import dataclasses
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import apsw

from tools.r9k_windows_feasibility import BASIC, EXTENDED, IO, PROCESS, STARTUP, Native, _dead, _pin
from tools.r9n_adversarial import Attempt, TEMPLATES

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts" / "r9p_evaluation"
CLASSIFICATION = "SYNTHETIC_ONLY_NONCANONICAL"
SCHEMA_STATUS = "PENDING_OFFICIAL_FORMAT_EVIDENCE"
TERMINALS = {
    "SYNTHETIC_AUDIT_COMPLETED", "SYNTHETIC_AUDIT_FAILED",
    "SYNTHETIC_AUDIT_ABORTED", "SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH",
}
OPERATIONS = ("catalog", "columns")
RECIPE = "generic SQLite catalog with 35 SYNTHETIC_NNN(generic_id,generic_value) tables"


class BoundaryError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def source_hash():
    return sha_file(Path(__file__))


def _root(token):
    if not re.fullmatch(r"case-[a-f0-9]{16}", token):
        raise BoundaryError("invalid generated token")
    root = BASE / token
    if root.is_symlink() or not (root / ".r9p_synthetic_root").is_file():
        raise BoundaryError("unregistered or indirect synthetic root")
    resolved = root.resolve(strict=True)
    if resolved.parent != BASE.resolve(strict=True):
        raise BoundaryError("outside generated root")
    for part in (root, *root.parents):
        if getattr(part.lstat(), "st_file_attributes", 0) & 1024:
            raise BoundaryError("reparse path rejected")
        if part == BASE:
            break
    return root


def make_fixture(root, page_size):
    path = root / "fixture.sqlite"
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"PRAGMA page_size={page_size}")
        for index in range(35):
            connection.execute(f"CREATE TABLE SYNTHETIC_{index:03d}"
                               f"(generic_id TEXT, generic_value TEXT DEFAULT '{'S' * 200}')")
        connection.commit()
    finally:
        connection.close()
    identity = {"sha256": sha_file(path), "bytes": path.stat().st_size, "page_size": page_size}
    marker = {"classification": CLASSIFICATION, "recipe_sha256": sha_bytes(RECIPE.encode()), "identity": identity}
    (root / "fixture.marker.json").write_text(json.dumps(marker, sort_keys=True), encoding="utf-8")
    return path, marker


def approval(root, attempt_id, approval_id, marker, limits, *, expiry_seconds=300):
    now = datetime.now(timezone.utc)
    body = {
        "schema_version": "r9p_synthetic_approval_v1", "classification": CLASSIFICATION,
        "attempt_id": attempt_id, "approval_id": approval_id,
        "issued_at": now.isoformat(), "expires_at": (now + timedelta(seconds=expiry_seconds)).isoformat(),
        "one_use": True, "fixture_recipe_sha256": marker["recipe_sha256"],
        "fixture_identity": marker["identity"], "prototype_source_sha256": source_hash(),
        "operation_template_sha256": {name: sha_bytes(sql.encode()) for name, sql in TEMPLATES.items()},
        "limits": dict(limits), "connection_limit": 1,
        "job_policy": {"kill_on_close": True, "process_commit_bytes": 134217728, "suspended_before_assignment": True},
        "io_profile": {"read_only": True, "mmap": False, "sidecars": False},
        "outputs": {"success": "worker-success.json", "diagnostic": "worker-diagnostic.json"},
        "prohibitions": ["NETWORK", "BROKER", "PRODUCTION", "MARKET_RESEARCH", "TRADING"],
        "canonical": False, "promotion_eligible": False,
    }
    return {**body, "seal_sha256": sha_bytes(canonical(body))}


def validate_approval(value, marker, *, now=None):
    if not isinstance(value, dict) or value.get("schema_version") != "r9p_synthetic_approval_v1":
        raise BoundaryError("malformed synthetic approval")
    body = {key: item for key, item in value.items() if key != "seal_sha256"}
    if sha_bytes(canonical(body)) != value.get("seal_sha256"):
        raise BoundaryError("mutated approval")
    current = now or datetime.now(timezone.utc)
    if not (datetime.fromisoformat(value["issued_at"]) <= current <= datetime.fromisoformat(value["expires_at"])):
        raise BoundaryError("expired approval")
    exact = (
        value.get("classification") == CLASSIFICATION and value.get("one_use") is True
        and value.get("fixture_recipe_sha256") == marker["recipe_sha256"]
        and value.get("fixture_identity") == marker["identity"]
        and value.get("prototype_source_sha256") == source_hash()
        and value.get("operation_template_sha256") == {name: sha_bytes(sql.encode()) for name, sql in TEMPLATES.items()}
        and value.get("connection_limit") == 1
        and value.get("io_profile") == {"read_only": True, "mmap": False, "sidecars": False}
        and value.get("prohibitions") == ["NETWORK", "BROKER", "PRODUCTION", "MARKET_RESEARCH", "TRADING"]
        and re.fullmatch(r"attempt-[a-f0-9]{16}", value.get("attempt_id", ""))
    )
    if not exact:
        raise BoundaryError("incorrect approval binding")
    return value


class Ledger:
    def __init__(self, path):
        self.path = path
        connection = sqlite3.connect(path)
        try:
            connection.executescript("""
            PRAGMA journal_mode=DELETE;
            CREATE TABLE IF NOT EXISTS approvals(
              approval_id TEXT PRIMARY KEY, attempt_id TEXT UNIQUE NOT NULL,
              payload_hash TEXT NOT NULL, payload TEXT NOT NULL, consumed_at TEXT,
              terminal TEXT CHECK(terminal IS NULL OR terminal IN (
                'SYNTHETIC_AUDIT_COMPLETED','SYNTHETIC_AUDIT_FAILED',
                'SYNTHETIC_AUDIT_ABORTED','SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH')));
            CREATE TABLE IF NOT EXISTS events(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT NOT NULL,
              event_type TEXT NOT NULL, detail TEXT NOT NULL, recorded_at TEXT NOT NULL);
            """)
            connection.commit()
        finally:
            connection.close()

    def register(self, value, marker):
        validate_approval(value, marker)
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            try:
                connection.execute("INSERT INTO approvals VALUES(?,?,?,?,NULL,NULL)",
                    (value["approval_id"], value["attempt_id"], value["seal_sha256"], canonical(value).decode()))
                self._event(connection, value["attempt_id"], "APPROVAL_REGISTERED", {})
                connection.commit()
            except sqlite3.IntegrityError as exc:
                raise BoundaryError("duplicate approval or attempt ID") from exc
        finally:
            connection.close()

    def consume(self, value, marker):
        validate_approval(value, marker)
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT attempt_id,payload_hash,consumed_at FROM approvals WHERE approval_id=?",
                                     (value["approval_id"],)).fetchone()
            if row != (value["attempt_id"], value["seal_sha256"], None):
                raise BoundaryError("approval unavailable, changed or already consumed")
            changed = connection.execute("UPDATE approvals SET consumed_at=? WHERE approval_id=? AND consumed_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), value["approval_id"])).rowcount
            if changed != 1:
                raise BoundaryError("approval already consumed")
            self._event(connection, value["attempt_id"], "APPROVAL_CONSUMED", {"before_connection": True})
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def event(self, attempt_id, event_type, detail=None):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            self._event(connection, attempt_id, event_type, detail or {})
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _event(connection, attempt_id, event_type, detail):
        connection.execute("INSERT INTO events(attempt_id,event_type,detail,recorded_at) VALUES(?,?,?,?)",
            (attempt_id, event_type, canonical(detail).decode(), datetime.now(timezone.utc).isoformat()))

    def terminal(self, attempt_id, state, detail=None):
        if state not in TERMINALS:
            raise BoundaryError("invalid terminal")
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            changed = connection.execute("UPDATE approvals SET terminal=? WHERE attempt_id=? AND consumed_at IS NOT NULL AND terminal IS NULL",
                                         (state, attempt_id)).rowcount
            if changed != 1:
                raise BoundaryError("terminal is missing, duplicate or unconsumed")
            self._event(connection, attempt_id, "FINAL_TERMINAL_PUBLISHED", {"state": state, **(detail or {})})
            connection.commit()
        finally:
            connection.close()

    def projection(self, attempt_id):
        connection = sqlite3.connect(self.path)
        try:
            row = connection.execute("SELECT consumed_at,terminal FROM approvals WHERE attempt_id=?", (attempt_id,)).fetchone()
            events = [item[0] for item in connection.execute("SELECT event_type FROM events WHERE attempt_id=? ORDER BY sequence", (attempt_id,))]
        finally:
            connection.close()
        return {"consumed": bool(row and row[0]), "terminal": row[1] if row else None, "events": events}


def checkpoint(root, path, expected, name):
    sidecars = [suffix for suffix in ("-wal", "-shm", "-journal") if Path(str(path) + suffix).exists()]
    if sidecars:
        raise BoundaryError("sidecar present at " + name)
    if sha_file(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
        raise BoundaryError("fixture identity changed at " + name)


def validate_fixture_path(root, path):
    if path.is_symlink() or path.resolve(strict=True).parent != root.resolve(strict=True):
        raise BoundaryError("unsafe fixture path")
    if getattr(path.lstat(), "st_file_attributes", 0) & 1024:
        raise BoundaryError("fixture reparse point rejected")
    return path


def acquire_guard(path):
    native = Native()
    handle = native.k.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == C.c_void_p(-1).value:
        raise BoundaryError("main-file guard unavailable")
    return native, handle


def worker(token, attempt_id, mode):
    root = _root(token); path = root / "fixture.sqlite"
    validate_fixture_path(root, path)
    marker = json.loads((root / "fixture.marker.json").read_text(encoding="utf-8"))
    value = json.loads((root / "approval.json").read_text(encoding="utf-8"))
    validate_approval(value, marker)
    if value["attempt_id"] != attempt_id:
        raise BoundaryError("attempt ID mismatch")
    ledger = Ledger(root / "ledger.sqlite")
    projection = ledger.projection(attempt_id)
    if not projection["consumed"] or projection["terminal"]:
        raise BoundaryError("approval not durably consumable")
    if mode == "crash_before_connection":
        os._exit(81)
    native = handle = attempt = None
    try:
        native, handle = acquire_guard(path)
        checkpoint(root, path, marker["identity"], "before_connection")
        ledger.event(attempt_id, "TARGET_CONNECTION_ATTEMPT", {})
        limits = value["limits"]
        attempt = Attempt(path, cap=limits["read_bytes"], rows=limits["rows"], output=limits["output_bytes"])
        attempt.deadline = attempt.clock() + limits["deadline_seconds"]
        attempt.open()
        ledger.event(attempt_id, "TARGET_CONNECTION_ESTABLISHED", {})
        checkpoint(root, path, marker["identity"], "immediately_after_connection")
        if mode == "crash_after_connection":
            os._exit(82)
        if mode == "second_connection":
            attempt.open()
        elif mode == "unsupported_open":
            attempt.vfs.xOpen(str(root / "other.sqlite"),
                [apsw.SQLITE_OPEN_MAIN_DB | apsw.SQLITE_OPEN_READONLY, 0])
        elif mode == "arbitrary_sql":
            attempt.execute("SELECT * FROM synthetic")
        elif mode == "application_read":
            list(attempt.connection.execute("SELECT * FROM SYNTHETIC_000"))
        elif mode == "mmap":
            list(attempt.connection.execute("PRAGMA mmap_size"))
        else:
            for index, operation in enumerate(OPERATIONS):
                hook = None
                if mode == "deadline_fetch" and index == 0:
                    hook = lambda item: setattr(item, "deadline", item.clock() - 1)
                attempt.execute(operation, hook)
                ledger.event(attempt_id, "OPERATION_TEMPLATE_EXECUTED", {"template": operation})
                checkpoint(root, path, marker["identity"], "between_operations")
                if mode == "late_sidecar" and index == 0:
                    Path(str(path) + "-wal").write_bytes(b"synthetic injected sidecar")
                if mode == "descendant_timeout" and index == 0:
                    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], creationflags=subprocess.CREATE_NO_WINDOW)
                    (root / "descendant.pid").write_text(str(child.pid), encoding="ascii")
                    time.sleep(30)
        checkpoint(root, path, marker["identity"], "before_publication")
        rows = attempt.finish()
        checkpoint(root, path, marker["identity"], "after_connection_close")
        result = {"schema_version": "r9p_success_v1", "classification": CLASSIFICATION,
                  "attempt_id": attempt_id, "rows": len(rows), "diagnostic": attempt.diagnostic(len(rows))}
        (root / value["outputs"]["success"]).write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        return 0
    except BaseException as exc:
        if attempt:
            attempt.failed = attempt.failed or type(exc).__name__
            attempt.buffer.clear()
        reason = attempt.failed if attempt else type(exc).__name__
        try:
            ledger.event(attempt_id, "BUDGET_FAILURE" if reason in {
                "READ_BUDGET", "ROW_LIMIT", "OUTPUT_LIMIT", "DEADLINE"
            } else "ATTEMPT_FAILURE", {"reason": reason})
        except Exception:
            pass
        diagnostic = {"schema_version": "r9p_failure_v1", "classification": CLASSIFICATION,
                      "attempt_id": attempt_id, "failure": str(exc).splitlines()[0][:160],
                      "meter": attempt.diagnostic(0) if attempt else None}
        (root / value["outputs"]["diagnostic"]).write_text(json.dumps(diagnostic, sort_keys=True), encoding="utf-8")
        return 1
    finally:
        if attempt:
            attempt.close()
        if handle:
            native.close(handle)


def create_job(memory_bytes=134217728):
    native = Native(); job = native.check(native.k.CreateJobObjectW(None, None))
    limits = EXTENDED(); limits.basic.flags = 0x2000 | 0x100
    limits.process_memory = memory_bytes
    try:
        native.check(native.k.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)))
    except BaseException:
        native.close(job); raise
    return native, job


def spawn_suspended(token, attempt_id, mode):
    if mode not in {"normal", "deadline_fetch", "late_sidecar", "second_connection", "arbitrary_sql",
                    "application_read", "mmap", "unsupported_open", "crash_before_connection", "crash_after_connection", "descendant_timeout"}:
        raise BoundaryError("unapproved internal mode")
    command = subprocess.list2cmdline([sys.executable, "-m", "tools.r9p_integrated", "--internal-worker", token, attempt_id, mode])
    startup = STARTUP(); startup.cb = C.sizeof(startup)
    process = PROCESS(); native = Native()
    native.check(native.k.CreateProcessW(sys.executable, C.create_unicode_buffer(command), None, None, False,
        0x00000004 | 0x08000000, None, str(ROOT), C.byref(startup), C.byref(process)))
    return native, process


def supervise(root, value, mode, timeout_seconds=5):
    native, job = create_job(); process = None; timed_out = False; descendant_dead = None
    try:
        native, process = spawn_suspended(root.name, value["attempt_id"], mode)
        native.check(native.k.AssignProcessToJobObject(job, process.process))
        assigned = native.in_job(process.process, job)
        native.check(native.k.ResumeThread(process.thread) != 0xFFFFFFFF)
        wait = native.k.WaitForSingleObject(process.process, int(timeout_seconds * 1000))
        if wait != 0:
            timed_out = True
            native.check(native.k.TerminateJobObject(job, 91))
            native.k.WaitForSingleObject(process.process, 3000)
        if (root / "descendant.pid").exists():
            pid = int((root / "descendant.pid").read_text())
            try:
                pin = _pin(native, pid); descendant_dead = _dead(native, pin); native.close(pin)
            except RuntimeError:
                descendant_dead = True
        return {"assigned_before_resume": assigned, "timed_out": timed_out, "descendant_dead": descendant_dead}
    finally:
        native.close(job)
        if process:
            if not _dead(native, process.process, 100):
                native.k.TerminateProcess(process.process, 92); native.k.WaitForSingleObject(process.process, 3000)
            native.close(process.thread); native.close(process.process)


def one_case(page_size=1024, mode="normal", limits=None, mutate=None):
    BASE.mkdir(parents=True, exist_ok=True)
    token = "case-" + uuid.uuid4().hex[:16]
    root = BASE / token
    root.mkdir()
    try:
        (root / ".r9p_synthetic_root").write_text(CLASSIFICATION, encoding="ascii")
        path, marker = make_fixture(root, page_size)
        limits = limits or {"read_bytes": 1048576, "rows": 200, "output_bytes": 131072, "deadline_seconds": 5}
        attempt_id = "attempt-" + uuid.uuid4().hex[:16]
        value = approval(root, attempt_id, "approval-" + uuid.uuid4().hex[:16], marker, limits)
        (root / "approval.json").write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        ledger = Ledger(root / "ledger.sqlite"); ledger.register(value, marker); ledger.consume(value, marker)
        if mutate == "replace":
            replacement = root / "replacement.synthetic"; replacement.write_bytes(path.read_bytes() + b"X"); os.replace(replacement, path)
        containment = supervise(root, value, mode, timeout_seconds=0.8 if mode == "descendant_timeout" else 7)
        success = root / "worker-success.json"; diagnostic = root / "worker-diagnostic.json"
        projection = ledger.projection(attempt_id)
        if containment["timed_out"]:
            ledger.event(attempt_id, "CONTAINMENT_TERMINATION", {"worker_and_descendants": True})
            projection = ledger.projection(attempt_id)
        if projection["terminal"] is None:
            if success.exists(): state = "SYNTHETIC_AUDIT_COMPLETED"
            elif diagnostic.exists(): state = "SYNTHETIC_AUDIT_FAILED"
            else: state = "SYNTHETIC_AUDIT_INCOMPLETE_AFTER_CRASH"
            ledger.terminal(attempt_id, state, {"supervisor_timeout": containment["timed_out"]})
        projection = ledger.projection(attempt_id)
        payload = json.loads(success.read_text()) if success.exists() else (json.loads(diagnostic.read_text()) if diagnostic.exists() else None)
        return {"page_size": page_size, "mode": mode, "limits": limits, "fixture": marker["identity"],
                "approval_attempt_bound": value["attempt_id"] == attempt_id,
                "containment": containment, "projection": projection,
                "success_present": success.exists(), "diagnostic_present": diagnostic.exists(), "payload": payload}
    finally:
        # Exact root is generated here and contains synthetic-only files.
        import shutil
        for retry in range(20):
            try:
                shutil.rmtree(root, ignore_errors=False)
                break
            except PermissionError:
                if retry == 19:
                    raise
                time.sleep(0.05)


def approval_checks():
    token = "case-" + uuid.uuid4().hex[:16]; BASE.mkdir(parents=True, exist_ok=True); root = BASE / token; root.mkdir()
    try:
        (root / ".r9p_synthetic_root").write_text(CLASSIFICATION); _, marker = make_fixture(root, 1024)
        limits = {"read_bytes": 1, "rows": 1, "output_bytes": 1, "deadline_seconds": 1}
        value = approval(root, "attempt-" + uuid.uuid4().hex[:16], "approval-" + uuid.uuid4().hex[:16], marker, limits)
        ledger = Ledger(root / "ledger.sqlite"); ledger.register(value, marker)
        malformed = mutated = expired = wrong = False
        for name, candidate in (
            ("malformed", {}),
            ("mutated", {**value, "limits": {**limits, "rows": 2}}),
            ("expired", approval(root, "attempt-" + uuid.uuid4().hex[:16], "approval-" + uuid.uuid4().hex[:16], marker, limits, expiry_seconds=-1)),
            ("wrong", dataclasses.replace if False else {**value, "classification": "PRODUCTION"}),
        ):
            try: validate_approval(candidate, marker)
            except Exception:
                if name == "malformed": malformed = True
                elif name == "mutated": mutated = True
                elif name == "expired": expired = True
                else: wrong = True
        winners = []
        barrier = threading.Barrier(2)
        def consume():
            barrier.wait()
            try: ledger.consume(value, marker); winners.append(True)
            except BoundaryError: winners.append(False)
        threads = [threading.Thread(target=consume) for _ in range(2)]
        [item.start() for item in threads]; [item.join() for item in threads]
        replay = False
        try: ledger.consume(value, marker)
        except BoundaryError: replay = True
        duplicate = False
        try: ledger.register(value, marker)
        except BoundaryError: duplicate = True
        unused = approval(root, "attempt-" + uuid.uuid4().hex[:16], "approval-" + uuid.uuid4().hex[:16], marker, limits)
        ledger.register(unused, marker)
        crash_before_consumption_unused = not ledger.projection(unused["attempt_id"])["consumed"]
        return {"malformed_rejected": malformed, "mutated_rejected": mutated, "expired_rejected": expired,
                "wrong_binding_rejected": wrong, "concurrent_winners": sum(winners),
                "replay_rejected": replay, "duplicate_id_rejected": duplicate,
                "crash_before_consumption_unused": crash_before_consumption_unused}
    finally:
        import shutil; shutil.rmtree(root)


def path_checks():
    outside = link = current_list = False
    try: _root("not-a-generated-token")
    except BoundaryError: outside = True
    token = "case-" + uuid.uuid4().hex[:16]; root = BASE / token; root.mkdir(); (root / ".r9p_synthetic_root").write_text("x")
    try:
        target = root / "target"; target.write_text("x")
        candidate = root / "link"
        try:
            candidate.symlink_to(target)
            try: validate_fixture_path(root, candidate)
            except BoundaryError: link = True
        except OSError:
            link = None
        current_list = "current" not in RECIPE.lower()
    finally:
        import shutil; shutil.rmtree(root)
    return {"outside_root_rejected": outside, "unsafe_link_rejected_or_unavailable": link,
            "current_list_substitution_absent": current_list}


def run():
    if os.name != "nt": raise BoundaryError("Windows-only integrated evaluation")
    if apsw.apswversion() != "3.53.4.0": raise BoundaryError("unpinned APSW runtime")
    layouts = [one_case(size) for size in (512, 1024, 4096)]
    need = layouts[1]["payload"]["diagnostic"]["reserved"]
    cases = {
        "one_below_read": one_case(limits={"read_bytes": need - 1, "rows": 200, "output_bytes": 131072, "deadline_seconds": 5}),
        "row_limit": one_case(limits={"read_bytes": 1048576, "rows": 35, "output_bytes": 131072, "deadline_seconds": 5}),
        "output_second_operation": one_case(limits={"read_bytes": 1048576, "rows": 200, "output_bytes": 10400, "deadline_seconds": 5}),
        "deadline_fetch": one_case(mode="deadline_fetch"), "late_sidecar": one_case(mode="late_sidecar"),
        "replacement": one_case(mutate="replace"), "crash_before_connection": one_case(mode="crash_before_connection"),
        "crash_after_connection": one_case(mode="crash_after_connection"), "timeout_descendant": one_case(mode="descendant_timeout"),
        "second_connection": one_case(mode="second_connection"), "arbitrary_sql": one_case(mode="arbitrary_sql"),
        "application_read": one_case(mode="application_read"), "mmap": one_case(mode="mmap"),
        "unsupported_open": one_case(mode="unsupported_open"),
    }
    checks = approval_checks(); paths = path_checks()
    failed_cases = [name for name, item in cases.items() if item["success_present"]]
    acceptance = {
        "1_exact_attempt_binding": all(x["approval_attempt_bound"] for x in layouts) and checks["malformed_rejected"] and checks["mutated_rejected"] and checks["expired_rejected"] and checks["wrong_binding_rejected"],
        "2_durable_one_use": checks["concurrent_winners"] == 1 and checks["replay_rejected"] and checks["duplicate_id_rejected"] and checks["crash_before_consumption_unused"],
        "3_one_connection": cases["second_connection"]["diagnostic_present"],
        "4_guard_and_checkpoints": all(x["success_present"] for x in layouts) and cases["late_sidecar"]["diagnostic_present"],
        "5_unsupported_io": cases["mmap"]["diagnostic_present"] and cases["late_sidecar"]["diagnostic_present"] and cases["unsupported_open"]["diagnostic_present"],
        "6_exact_templates": cases["arbitrary_sql"]["diagnostic_present"] and cases["application_read"]["diagnostic_present"],
        "7_cumulative_budgets": all(cases[name]["diagnostic_present"] for name in ("one_below_read", "row_limit", "output_second_operation", "deadline_fetch")) and cases["timeout_descendant"]["containment"]["timed_out"] and cases["timeout_descendant"]["containment"]["descendant_dead"],
        "8_no_success_after_failure": not failed_cases,
        "9_terminal_reconciliation": all(item["projection"]["terminal"] in TERMINALS for item in [*layouts, *cases.values()]),
        "10_synthetic_containment": paths["outside_root_rejected"] and paths["current_list_substitution_absent"] and cases["replacement"]["diagnostic_present"],
    }
    return {"schema_version": "r9p_integrated_results_v1", "classification": CLASSIFICATION,
            "official_schema_status": SCHEMA_STATUS, "runtime": {"python": sys.version, "apsw": apsw.apswversion(), "sqlite": apsw.sqlitelibversion()},
            "layouts": layouts, "cases": cases, "approval_checks": checks, "path_checks": paths,
            "acceptance": acceptance, "passed": all(acceptance.values()),
            "limitations": ["Checkpoint observation does not prove continuous quiescence.",
                "Job Objects constrain process trees and committed memory, not database bytes or temporary storage.",
                "Direct xOpen probes do not prove every native SQLite path.",
                "Synthetic software evidence is not market evidence or production authorization."],
            "temporary_roots_removed": True}


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--internal-worker":
        raise SystemExit(worker(sys.argv[2], sys.argv[3], sys.argv[4]))
    if len(sys.argv) != 1:
        raise SystemExit("R.9P public interface accepts no inputs")
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
