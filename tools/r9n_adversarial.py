"""Isolated synthetic candidate; fixed entrypoint, no private inputs."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import tempfile
import time
import uuid
import sys
from pathlib import Path
import apsw

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "SELECT name, sql FROM sqlite_schema WHERE type='table'"
COLUMNS = "PRAGMA table_info('SYNTHETIC_000')"
TEMPLATES = {"catalog": CATALOG, "columns": COLUMNS}


class Attempt:
    def __init__(self, target, cap=1048576, rows=200, output=131072, clock=time.monotonic):
        self.target, self.cap, self.row_cap, self.output_cap = target, cap, rows, output
        self.clock, self.deadline = clock, clock()+5
        self.requested = self.reserved = self.delegated = self.returned = 0
        self.row_seen = self.row_accepted = self.output_bytes = 0
        self.phase, self.failed, self.opened, self.closed = 'open', None, False, False
        self.events, self.buffer = [], []
        self.connection = None
        self.fault = None
        self.vfs = Guard(self)

    def fail(self, reason):
        self.failed = self.failed or reason
        self.buffer.clear()
        raise apsw.IOError(self.failed)

    def check(self):
        if self.failed: self.fail(self.failed)
        if self.closed: self.fail('CLOSED_ATTEMPT')
        if self.clock() >= self.deadline: self.fail('DEADLINE')
        if any(Path(str(self.target)+s).exists() for s in ('-wal','-shm','-journal')):
            self.fail('SIDECAR_PRESENT')

    def read(self, amount, offset, underlying):
        self.requested += amount
        self.check()
        if amount < 0 or self.reserved+amount > self.cap: self.fail('READ_BUDGET')
        self.reserved += amount
        self.delegated += amount
        event = {'phase': self.phase, 'amount': amount, 'offset': offset, 'returned': 0}
        self.events.append(event)
        try:
            data = underlying(amount, offset)
        except Exception:
            self.fail('UNDERLYING_READ_ERROR')
        self.returned += len(data)
        event['returned'] = len(data)
        if len(data) != amount: self.fail('SHORT_READ')
        return data

    def open(self):
        self.check()
        if self.opened: self.fail('REOPEN_FORBIDDEN')
        self.opened = True  # consumption before connection; no retry on failure
        try:
            self.connection = apsw.Connection(str(self.target), flags=apsw.SQLITE_OPEN_READONLY, vfs=self.vfs.name)
            self.connection.enable_load_extension(False)
            # Fixed test setup: force fresh page reads during catalog iteration.
            self.connection.execute('PRAGMA cache_size=2')
            self.connection.set_authorizer(self.authorize)
            self.connection.set_progress_handler(lambda: bool(self.failed or self.clock() >= self.deadline), 1)
        except apsw.Error:
            self.failed = self.failed or 'OPEN_ERROR'
            raise

    def authorize(self, action, a, b, db, trigger):
        allowed = (action == apsw.SQLITE_SELECT or
                   action == apsw.SQLITE_READ and a in ('sqlite_master', 'sqlite_schema') or
                   action == apsw.SQLITE_PRAGMA and a == 'table_info' and b == 'SYNTHETIC_000')
        if not allowed:
            self.failed = self.failed or 'SQL_AUTHORIZATION'
            self.buffer.clear()
            return apsw.SQLITE_DENY
        return apsw.SQLITE_OK

    def execute(self, template, hook=None):
        self.check()
        if template not in TEMPLATES: self.fail('EXACT_TEMPLATE_REQUIRED')
        self.phase = 'execute'
        self.check()
        try:
            cursor = self.connection.execute(TEMPLATES[template], can_cache=False)
            while True:
                self.phase = 'fetch'
                if hook: hook(self)
                self.check()
                try: row = next(cursor)
                except StopIteration: break
                self.check()
                self.row_seen += 1
                if self.row_seen > self.row_cap: self.fail('ROW_LIMIT')
                encoded = json.dumps(row, separators=(',', ':'), ensure_ascii=True).encode()
                projected = self.output_bytes + len(encoded) + (1 if self.buffer else 2)
                if projected > self.output_cap: self.fail('OUTPUT_LIMIT')
                self.output_bytes = projected
                self.row_accepted += 1
                self.buffer.append(row)
        except apsw.Error:
            self.failed = self.failed or 'SQLITE_ERROR'
            self.buffer.clear()
            raise

    def finish(self):
        self.check()
        data = list(self.buffer)
        self.close()
        return data

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.closed = True
        self.vfs.unregister()

    def diagnostic(self, published):
        return {'kind': 'FAILED_ATTEMPT_DIAGNOSTIC' if self.failed else 'SYNTHETIC_COMPLETED_RESULT',
                'failed': self.failed, 'requested': self.requested, 'reserved': self.reserved,
                'delegated': self.delegated, 'returned': self.returned, 'cap': self.cap,
                'events': self.events, 'row_seen': self.row_seen, 'row_accepted': self.row_accepted,
                'buffered_bytes_peak': self.output_bytes, 'published_rows': published}


class File:
    # Plain proxy => APSW v1 io_methods, no xFetch or inherited xShm methods.
    def __init__(self, name, flags, owner):
        self.owner, self.base = owner, apsw.VFSFile('win32', name, flags)
    def xRead(self, amount, offset):
        return self.owner.read(amount, offset, self.owner.fault or self.base.xRead)
    def xClose(self): self.base.xClose()
    def xFileSize(self): return self.base.xFileSize()
    def xLock(self, n): return self.base.xLock(n)
    def xUnlock(self, n): return self.base.xUnlock(n)
    def xCheckReservedLock(self): return self.base.xCheckReservedLock()
    def xSectorSize(self): return self.base.xSectorSize()
    def xDeviceCharacteristics(self): return 0
    def xFileControl(self, op, ptr): return False
    def xWrite(self, *args): self.owner.fail('WRITE_FORBIDDEN')
    def xTruncate(self, *args): self.owner.fail('TRUNCATE_FORBIDDEN')
    def xSync(self, *args): self.owner.fail('SYNC_FORBIDDEN')


class Guard(apsw.VFS):
    def __init__(self, owner):
        self.owner, self.opens = owner, 0
        self.name = 'r9n_'+uuid.uuid4().hex
        super().__init__(self.name, 'win32', makedefault=False, iVersion=1)
    def xOpen(self, name, flags):
        o = self.owner
        o.check()
        raw = name.filename() if isinstance(name, apsw.URIFilename) else name
        required = apsw.SQLITE_OPEN_MAIN_DB | apsw.SQLITE_OPEN_READONLY
        forbidden = apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE | apsw.SQLITE_OPEN_URI
        if raw is None or Path(raw) != o.target or flags[0] & required != required or flags[0] & forbidden:
            o.fail('OPEN_FORBIDDEN')
        if self.opens: o.fail('SECOND_CONNECTION')
        self.opens += 1
        return File(name, flags, o)
    def xAccess(self, path, flags):
        self.owner.check()
        return super().xAccess(path, flags) if path == str(self.owner.target) else False
    def xDelete(self, *args): self.owner.fail('DELETE_FORBIDDEN')
    def xDlOpen(self, *args): return 0


def fixture(directory, page_size, tables=35):
    path = directory / ('generic_'+str(page_size)+'.sqlite')
    c = sqlite3.connect(path)
    try:
        c.execute('PRAGMA page_size='+str(page_size))
        for i in range(tables):
            c.execute(f"CREATE TABLE SYNTHETIC_{i:03d}(generic_id TEXT, generic_value TEXT DEFAULT '"+'S'*200+"')")
        c.commit()
    finally: c.close()
    assert path.stat().st_size < 256*1024
    return path


def exercise(path, operations=('catalog',), hook=None, **limits):
    a = Attempt(path, **limits)
    published = []
    try:
        a.open()
        for operation in operations: a.execute(operation, hook)
        published = a.finish()
    except apsw.Error:
        a.failed = a.failed or 'SQLITE_ERROR'
        a.buffer.clear()
    finally: a.close()
    return a.diagnostic(len(published))


def run():
    assert apsw.apswversion() == '3.53.4.0'
    out = {'runtime': {'apsw': apsw.apswversion(), 'sqlite': apsw.sqlitelibversion(), 'python':sys.version},
           'fixtures': [], 'cases': []}
    def record(name, hypothesis, expected, observed, evidence='NATIVE_SQLITE', fixture_path=None):
        bound = fixture_path or path
        out['cases'].append({'name': name, 'hypothesis': hypothesis, 'expected': expected,
                             'observed': observed, 'evidence_type': evidence,
                             'fixture_sha256':hashlib.sha256(bound.read_bytes()).hexdigest(),
                             'measurement_scope':'One attempt VFS xRead; setup/hash/control I/O excluded',
                             'limitations':'Fixed single-worker synthetic case; no namespace or hostile same-process guarantee'})
    scratch = ROOT / 'artifacts/r9n_evaluation'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='synthetic_', dir=scratch) as temporary:
        directory = Path(temporary)
        for size in (512,1024,4096):
            path = fixture(directory, size)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            out['fixtures'].append({'id':str(size), 'sha256':digest, 'bytes':path.stat().st_size})
            baseline = exercise(path)
            need = baseline['reserved']
            assert baseline['published_rows'] == 35
            for label, cap in (('sufficient',1048576),('zero',0),('insufficient',100),('exact',need),('below',need-1)):
                result = exercise(path, cap=cap)
                expected = 35 if label in ('sufficient','exact') else 0
                assert result['published_rows'] == expected
                record(f'{size}_{label}', 'Budget admission before file reads', {'published_rows':expected},result)
            shared = exercise(path, operations=('catalog','catalog'), cap=need)
            assert shared['published_rows'] == 0
            record(f'{size}_shared','Statements share one meter',{'published_rows':0},shared)
            used = 0
            for event in baseline['events']:
                if event['phase'] == 'fetch': break
                used += event['amount']
            else: raise AssertionError('No fetch-phase read observed')
            fetching = exercise(path, cap=used)
            assert fetching['failed'] == 'READ_BUDGET' and fetching['row_seen'] > 0
            record(f'{size}_fetch','Exhaustion during cursor iteration discards partial output',{'published_rows':0},fetching)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest

        for label, limits in (('rows',{'rows':2}),('output',{'output':10})):
            observed = exercise(path, **limits)
            assert observed['published_rows'] == 0
            record(label,'Bounded iteration/output',{'published_rows':0},observed)
        clock = [0.0]
        def tick(a):
            if a.row_seen: clock[0] = 6.0
        deadline = exercise(path, clock=lambda:clock[0], hook=tick)
        assert deadline['failed'] == 'DEADLINE' and deadline['row_seen'] == 1
        record('fetch_deadline','Deadline retained across fetch',{'published_rows':0},deadline,'NATIVE_SQLITE_WITH_INJECTED_CLOCK')
        a = Attempt(path, clock=lambda:0)
        try:
            a.open(); a.deadline = 0
            try: a.execute('catalog')
            except apsw.Error: pass
            assert a.failed == 'DEADLINE'
            record('execute_deadline','Check before execute',{'published_rows':0},a.diagnostic(0),'INJECTED_DEADLINE')
        finally: a.close()

        for query in ('SELECT * FROM SYNTHETIC_000', 'ATTACH DATABASE ":memory:" AS extra',
                      'CREATE TEMP TABLE x(a)', 'PRAGMA mmap_size=16777216'):
            a = Attempt(path)
            try:
                a.open()
                try: a.connection.execute(query, can_cache=False)
                except apsw.Error: pass
                # Syntax error also fails; exact-template facade tested separately.
                assert a.failed == 'SQL_AUTHORIZATION'
                record('native_sql_'+str(len(out['cases'])),'Native restricted SQL challenge',{'published_rows':0},a.diagnostic(0))
            finally: a.close()
        bad = exercise(path, operations=(CATALOG+' AND 1=1',))
        assert bad['failed'] == 'EXACT_TEMPLATE_REQUIRED'
        record('facade_sql','Enumerated templates only',{'published_rows':0},bad,'FACADE')

        for label, flags, name in (
            ('readwrite',apsw.SQLITE_OPEN_READWRITE,str(path)),
            ('create',apsw.SQLITE_OPEN_READWRITE|apsw.SQLITE_OPEN_CREATE,str(path)),
            ('temp',apsw.SQLITE_OPEN_TEMP_DB|apsw.SQLITE_OPEN_READWRITE,None),
            ('wal',apsw.SQLITE_OPEN_WAL|apsw.SQLITE_OPEN_READONLY,str(path)+'-wal'),
            ('journal',apsw.SQLITE_OPEN_MAIN_JOURNAL|apsw.SQLITE_OPEN_READONLY,str(path)+'-journal')):
            a=Attempt(path)
            try:
                try:
                    if label in ('readwrite','create'):
                        apsw.Connection(str(path),flags=flags,vfs=a.vfs.name)
                    else: a.vfs.xOpen(name,[flags,0])
                except apsw.Error: pass
                assert a.failed == 'OPEN_FORBIDDEN'
                record(label,'Forbidden open rejected',{'published_rows':0},a.diagnostic(0),
                       'NATIVE_SQLITE' if label in ('readwrite','create') else 'DIRECT_METHOD')
            finally:a.close()

        for mode in ('WAL','DELETE'):
            writer=sqlite3.connect(path)
            try:
                writer.execute('PRAGMA journal_mode='+mode)
                writer.execute('BEGIN IMMEDIATE')
                writer.execute("INSERT INTO SYNTHETIC_000 VALUES ('synthetic','only')")
                observed=exercise(path)
                assert observed['failed']=='SIDECAR_PRESENT'
                record(mode+'_active','Active synthetic sidecar state denied before access',{'published_rows':0},observed)
                writer.rollback()
            finally: writer.close()

        for label, body in (('malformed',b'not a sqlite file'*40),('truncated',path.read_bytes()[:100])):
            damaged=directory/(label+'.sqlite')
            damaged.write_bytes(body)
            observed=exercise(damaged)
            assert observed['published_rows']==0 and observed['failed']
            record(label,'Damaged synthetic file fails',{'published_rows':0},observed,fixture_path=damaged)

        for mode in ('error','short','repeat'):
            a=Attempt(path,cap=32)
            file=a.vfs.xOpen(str(path),[apsw.SQLITE_OPEN_MAIN_DB|apsw.SQLITE_OPEN_READONLY,0])
            try:
                if mode=='error':
                    def fault(n,o): raise apsw.IOError('INJECTED')
                    a.fault=fault
                if mode=='short': a.fault=lambda n,o:b'x'*(n-1)
                try:
                    file.xRead(16,0)
                    file.xRead(16,0)
                    file.xRead(1,0)
                except apsw.Error: pass
                before=a.delegated
                try: file.xRead(1,0)
                except apsw.Error: pass
                assert a.failed and before==a.delegated
                record(mode,'Reservation not refunded and failure sticky',{'published_rows':0},a.diagnostic(0),
                       'DIRECT_NATIVE_FILE' if mode=='repeat' else 'MOCKED_UNDERLYING_READ')
            finally:file.xClose();a.close()

        for challenge in ('reopen','second','closed','after_exhaustion'):
            a=Attempt(path,cap=0 if challenge=='after_exhaustion' else 1048576)
            try:
                try:a.open()
                except apsw.Error:pass
                if challenge=='closed':a.close()
                before=a.reserved
                try:
                    if challenge=='second': apsw.Connection(str(path),flags=apsw.SQLITE_OPEN_READONLY,vfs=a.vfs.name)
                    else:a.open()
                except apsw.Error:pass
                assert a.failed and a.reserved==before
                record(challenge,'No reset/reopen in same attempt',{'published_rows':0},a.diagnostic(0))
            finally:a.close()
    out['temporary_root_removed']=not directory.exists()
    out['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv)!=1: raise SystemExit('No arguments; generated fixtures only')
    print(json.dumps(run(),sort_keys=True,indent=2))
