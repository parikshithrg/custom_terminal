"""Fixed synthetic-only APSW probe. No arbitrary database or SQL arguments."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import uuid
from pathlib import Path


HEADERS = ("FinInstrmId", "TckrSymb", "SctySrs", "ISIN", "Xchg", "Sts", "FinInstrmNm")
SCHEMA = 'CREATE TABLE SYNTHETIC_NSE_SECURITY (' + ','.join('"'+h+'" TEXT' for h in HEADERS) + ')'
CATALOG = "SELECT name, sql FROM sqlite_schema WHERE type='table' ORDER BY name"
ROOT = Path(__file__).resolve().parents[1]


def run():
    # Import only in the isolated candidate environment, never a production module.
    import apsw
    if apsw.apswversion() != "3.53.4.0":
        raise RuntimeError("Candidate version mismatch")

    class Meter:
        def __init__(self, limit):
            self.limit = limit
            self.requested = self.delegated = self.calls = 0
            self.failed = False
            self.events = []

        def charge(self, amount):
            self.requested += amount
            self.calls += 1
            if self.failed or amount < 0 or self.delegated + amount > self.limit:
                self.failed = True
                raise apsw.IOError("SYNTHETIC_READ_BUDGET_EXHAUSTED")
            self.delegated += amount

    class File:
        # Deliberately NOT derived from VFSFile: APSW installs v1 io_methods,
        # excluding both native shared-memory proxying and mapped xFetch.
        def __init__(self, name, flags, owner):
            self.owner = owner
            self.base = apsw.VFSFile("win32", name, flags)

        def xRead(self, amount, offset):
            self.owner.check()
            self.owner.meter.charge(amount)  # before underlying read
            self.owner.meter.events.append([amount, offset])
            return self.base.xRead(amount, offset)

        def xClose(self): self.base.xClose()
        def xFileSize(self): return self.base.xFileSize()
        def xLock(self, level): return self.base.xLock(level)
        def xUnlock(self, level): return self.base.xUnlock(level)
        def xCheckReservedLock(self): return self.base.xCheckReservedLock()
        def xSectorSize(self): return self.base.xSectorSize()
        def xDeviceCharacteristics(self): return 0
        def xFileControl(self, op, ptr): return False
        def xWrite(self, *args): raise apsw.ReadOnlyError("SYNTHETIC_WRITE_DENIED")
        def xTruncate(self, *args): raise apsw.ReadOnlyError("SYNTHETIC_TRUNCATE_DENIED")
        def xSync(self, *args): raise apsw.ReadOnlyError("SYNTHETIC_SYNC_DENIED")

    class ProbeVFS(apsw.VFS):
        def __init__(self, target, meter):
            self.target = target
            self.meter = meter
            self.name = "r9m_" + uuid.uuid4().hex
            self.opened = 0
            super().__init__(self.name, "win32", makedefault=False, iVersion=1)

        def check(self):
            if self.meter.failed:
                raise apsw.IOError("SYNTHETIC_ATTEMPT_ALREADY_FAILED")
            if any(Path(str(self.target)+s).exists() for s in ("-wal", "-shm", "-journal")):
                self.meter.failed = True
                raise apsw.IOError("SYNTHETIC_SIDECAR_PRESENT")

        def xOpen(self, name, flags):
            self.check()
            raw = name.filename() if isinstance(name, apsw.URIFilename) else name
            required = apsw.SQLITE_OPEN_MAIN_DB | apsw.SQLITE_OPEN_READONLY
            forbidden = apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE | apsw.SQLITE_OPEN_URI
            if raw is None or Path(raw) != self.target or flags[0] & required != required or flags[0] & forbidden:
                self.meter.failed = True
                raise apsw.CantOpenError("SYNTHETIC_TARGET_ONLY")
            self.opened += 1
            if self.opened != 1:
                raise apsw.CantOpenError("SYNTHETIC_SINGLE_OPEN")
            return File(name, flags, self)

        def xAccess(self, path, flags):
            self.check()
            if path != str(self.target):
                return False
            return super().xAccess(path, flags)

        def xDelete(self, *args): raise apsw.ReadOnlyError("SYNTHETIC_DELETE_DENIED")
        def xDlOpen(self, *args): return 0

    results = {"classification": "SYNTHETIC_ONLY_NOT_PRODUCTION",
               "apsw": apsw.apswversion(), "sqlite": apsw.sqlitelibversion(),
               "headers": list(HEADERS), "schema_sha256": hashlib.sha256(SCHEMA.encode()).hexdigest(),
               "header_provenance": "Existing NSE MII parser subset; not F&O UDiFF schema qualification",
               "cases": {}}
    scratch = ROOT / "artifacts/r9m_evaluation/fixtures"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="synthetic_", dir=scratch) as directory:
        target = Path(directory) / "SYNTHETIC_ONLY.sqlite"
        with sqlite3.connect(target) as c:
            c.execute(SCHEMA)
            c.execute('INSERT INTO SYNTHETIC_NSE_SECURITY VALUES (?,?,?,?,?,?,?)',
                      ("9999999999", "SYNTHETIC", "EQ", "SYNTHETIC_NOT_ISIN", "NSE", "SYNTHETIC", "SYNTHETIC ONLY"))
        c.close()
        original = target.read_bytes()
        assert len(original) < 128 * 1024
        results["fixture_bytes"] = len(original)
        results["fixture_sha256"] = hashlib.sha256(original).hexdigest()
        control = apsw.Connection(str(target), flags=apsw.SQLITE_OPEN_READONLY)
        try:
            list(control.execute("PRAGMA mmap_size=16777216"))
            results["native_mmap_control"] = list(control.execute("PRAGMA mmap_size"))
        finally:
            control.close()

        for case, cap in (("zero", 0), ("small", 200), ("adequate", 1048576),
                          ("exact_observed", 4212), ("one_under_observed", 4211),
                          ("mmap_requested", 1048576), ("late_sidecar", 1048576)):
            meter = Meter(cap)
            vfs = ProbeVFS(target, meter)
            connection = None
            published = []
            error = None
            mmap = None
            try:
                connection = apsw.Connection(str(target), flags=apsw.SQLITE_OPEN_READONLY, vfs=vfs.name)
                connection.enable_load_extension(False)
                if case == "mmap_requested":
                    mmap = list(connection.execute("PRAGMA mmap_size=16777216"))
                    mmap = {"set_result": mmap, "readback": list(connection.execute("PRAGMA mmap_size"))}
                buffered = list(connection.execute(CATALOG))
                if case == "late_sidecar":
                    # Generated adversarial sibling, never an exchange/database artifact.
                    Path(str(target)+"-wal").touch()
                vfs.check()  # fail closed even if SQLite served cached pages
                published = buffered
            except apsw.Error as exc:
                error = type(exc).__name__  # no raw exception paths
            finally:
                if connection is not None: connection.close()
                vfs.unregister()
                Path(str(target)+"-wal").unlink(missing_ok=True)
            assert meter.delegated <= cap
            results["cases"][case] = {"limit": cap, "requested": meter.requested,
                "delegated": meter.delegated, "read_calls": meter.calls,
                "read_events": meter.events, "failed": meter.failed,
                "error": error, "published_rows": len(published), "mmap": mmap}

        # Direct method tests use an actual native file, not SQLite scheduling.
        meter = Meter(32)
        vfs = ProbeVFS(target, meter)
        file = vfs.xOpen(str(target), [apsw.SQLITE_OPEN_MAIN_DB | apsw.SQLITE_OPEN_READONLY, 0])
        try:
            file.xRead(16, 0)
            file.xRead(16, 0)
            rejected = []
            for amount in (1, 0):
                try: file.xRead(amount, 0)
                except apsw.IOError: rejected.append(True)
            results["direct_repeated_exact_sticky"] = {"delegated": meter.delegated, "rejections": len(rejected)}
        finally:
            file.xClose()
            vfs.unregister()

        rejected_opens = []
        for suffix, flags in (("-wal", apsw.SQLITE_OPEN_WAL | apsw.SQLITE_OPEN_READONLY),
                              ("-journal", apsw.SQLITE_OPEN_MAIN_JOURNAL | apsw.SQLITE_OPEN_READONLY),
                              (None, apsw.SQLITE_OPEN_TEMP_DB | apsw.SQLITE_OPEN_READWRITE),
                              ("", apsw.SQLITE_OPEN_MAIN_DB | apsw.SQLITE_OPEN_READWRITE)):
            vfs = ProbeVFS(target, Meter(1024))
            try:
                try: vfs.xOpen(None if suffix is None else str(target)+suffix, [flags, 0])
                except apsw.Error: rejected_opens.append(str(suffix))
            finally: vfs.unregister()
        results["direct_forbidden_opens_rejected"] = len(rejected_opens)
        results["fixture_unchanged"] = target.read_bytes() == original
    results["temporary_fixture_removed"] = not target.exists()
    assert results["cases"]["adequate"]["published_rows"] == 1
    assert results["cases"]["zero"]["published_rows"] == 0
    assert results["cases"]["small"]["published_rows"] == 0
    assert results["cases"]["late_sidecar"]["published_rows"] == 0
    assert results["direct_repeated_exact_sticky"] == {"delegated": 32, "rejections": 2}
    assert results["direct_forbidden_opens_rejected"] == 4
    assert results["fixture_unchanged"]
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 1:
        raise SystemExit("No arguments accepted; synthetic fixture only")
    print(json.dumps(run(), indent=2, sort_keys=True))
