"""R.9J experiments. No caller database path; no production activation.

Run as a module from the repository. All database opens are guarded against an
allowlist of paths created in this invocation's disposable synthetic workspace.
This is an exploratory harness, not a hardened production boundary.
"""
from __future__ import annotations

import argparse
import ctypes
import dataclasses
import hashlib
import json
import multiprocessing as mp
import os
import platform
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from market_intel.foundation import local_fno_audit as audit
from market_intel.foundation import fno_production_boundary as boundary

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.pytest_tmp' / 'r9j'
OUT = ROOT / 'docs' / 'investigations' / 'r9j'
RECIPE = (
    'CREATE TABLE parent(id INTEGER PRIMARY KEY, note TEXT);'
    'CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id));'
    'CREATE INDEX child_parent ON child(parent_id);'
    'CREATE VIEW parent_shape AS SELECT id FROM parent;'
    "INSERT INTO parent VALUES(1,'R9J_SYNTHETIC_SENTINEL_NEVER_EXPORT');"
    'INSERT INTO child VALUES(1,1);'
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContainmentError(RuntimeError):
    pass


@dataclasses.dataclass
class _Capsule:
    root: Path
    allowed: tuple[Path, ...]

    def check(self, candidate):
        # Compare to known generated names before filesystem inspection.
        spelling = str(candidate)
        matches = [p for p in self.allowed if spelling in (str(p), p.as_uri() + '?mode=ro')]
        if len(matches) != 1:
            raise ContainmentError('unregistered synthetic fixture rejected')
        p = matches[0]
        if self.root.parent != BASE or not self.root.name.startswith('case-'):
            raise ContainmentError('invalid synthetic root')
        if not (self.root / '.r9j_created').is_file():
            raise ContainmentError('missing creation marker')
        for part in (p, *p.parents):
            if part.exists() or part.is_symlink():
                info = part.lstat()
                if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
                    raise ContainmentError('link or reparse rejected')
            if part == self.root:
                break
        if not p.is_relative_to(self.root):
            raise ContainmentError('synthetic containment rejected')
        return p


@contextmanager
def _guard(cap):
    original = sqlite3.connect
    counts = {'target_connections': 0, 'registry_connections': 0}

    def connect(database, *args, **kwargs):
        p = cap.check(database)
        connection = original(database, *args, **kwargs)
        key = 'registry_connections' if p.name == 'audit_governance.sqlite' else 'target_connections'
        counts[key] += 1
        return connection

    with patch.object(sqlite3, 'connect', connect):
        yield counts


class _Workspace:
    def __init__(self):
        BASE.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=BASE)
        self.root = Path(self.temp.name)
        (self.root / '.r9j_created').write_text('new synthetic files only')
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / '.synthetic_audit_fixture').write_text('synthetic only')
        self.target = self.source / 'fixture.sqlite'
        self.registry_path = self.root / 'registry' / 'audit_governance.sqlite'
        self.cap = _Capsule(self.root, (self.target, self.registry_path))
        with _guard(self.cap):
            c = sqlite3.connect(self.target)
            c.executescript(RECIPE)
            c.close()
        if self.target.stat().st_size > 1024 * 1024:
            raise ContainmentError('fixture size exceeded')
        self.initial = {'recipe_sha256': hashlib.sha256(RECIPE.encode()).hexdigest(),
                        'database_sha256': digest(self.target), 'bytes': self.target.stat().st_size}

    def close(self):
        self.temp.cleanup()

    def approval(self, name):
        identity = audit.capture_file_identity(self.target, synthetic_root=self.source)
        now = datetime.now(timezone.utc)
        return audit.seal_audit_approval(audit.AuditApproval(
            schema_version='local_data_audit_stage_1_3_approval_v1',
            approval_type=audit.AUDIT_APPROVAL_TYPE, approval_id='R9J_SYNTHETIC_' + name,
            proposal=audit.ProposalIdentity(), approved_locator_key='synthetic.fixture.path',
            approved_locator_sha256=audit.synthetic_locator_hash(),
            approved_database_identity_root=identity.sampled_root_sha256,
            approved_stages=(1, 2, 3), approved_resources=audit.approved_resource_contract(),
            approved_outputs=audit.PERMITTED_OUTPUTS, fixture_classification=audit.SYNTHETIC_FIXTURE_CLASS,
            issued_at=(now - timedelta(minutes=1)).isoformat(),
            expires_at=(now + timedelta(minutes=10)).isoformat(), approved_by='SYNTHETIC_TEST_ONLY',
            approval_statement='Disposable R9J synthetic experiment only; never production.'))


def _reject(call):
    try:
        call()
        return False
    except (audit.LocalFnoAuditError, ContainmentError):
        return True


def _registry_worker(cap, approval, attempt, mode, ready, send):
    with _guard(cap) as counts:
        registry = boundary.DurableAuditRegistry(cap.allowed[1])
        ready.wait(4)
        if mode == 'before':
            send.send({'phase': mode, **counts})
            os._exit(21)
        try:
            registry.consume(approval, attempt)
            if mode == 'after_open':
                connection = audit.ReadOnlyCatalogConnection(cap.allowed[0], event_sink=[])
                # Deliberately crash with an open synthetic connection. OS closes it.
                assert connection.statement_count == 3
            send.send({'phase': mode, 'winner': True, **counts})
            if mode != 'race':
                os._exit(22 if mode == 'after' else 23)
        except audit.LocalFnoAuditError:
            send.send({'phase': mode, 'winner': False, **counts})


def _wait(process):
    process.join(8)
    if process.is_alive():
        process.terminate()
        process.join(3)
        raise RuntimeError('synthetic child deadline exceeded')
    return process.exitcode


def _resource_child(cap, send):
    # Failure injection bounded to tiny allocations and writes, not host exhaustion.
    allocated = bytearray(1024 * 1024)
    scratch = cap.root / 'scratch.bin'
    scratch.write_bytes(b'x' * 8192)
    working_set = None
    os_read = None
    if os.name == 'nt':
        from ctypes import wintypes
        class IO(ctypes.Structure):
            _fields_ = [(k, ctypes.c_ulonglong) for k in (
                'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessIoCounters.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO)]
        info = IO()
        if kernel.GetProcessIoCounters(kernel.GetCurrentProcess(), ctypes.byref(info)):
            os_read = info.ReadTransferCount
        class MEMORY(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (k, ctypes.c_size_t) for k in ('peak', 'working', 'pagedpeak', 'paged',
                                             'nonpagedpeak', 'nonpaged', 'pagefile', 'peakfile')]
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MEMORY), wintypes.DWORD]
        mem = MEMORY(); mem.cb = ctypes.sizeof(mem)
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(mem), mem.cb):
            working_set = mem.working
    with _guard(cap) as counts:
        connection = audit.ReadOnlyCatalogConnection(cap.allowed[0], event_sink=[])
        for _ in range(2):
            connection.execute('SELECT name FROM sqlite_schema ORDER BY name').fetchall()
        connection.close()
    send.send({'allocated_bytes': len(allocated), 'declared_memory_probe_limit': 524288,
               'scratch_bytes': scratch.stat().st_size, 'declared_temp_probe_limit': 4096,
               'process_working_set_bytes': working_set, 'process_os_read_transfer_bytes': os_read,
               'os_accounting_is_target_or_physical_bytes': False, **counts})


def _sleep_worker(send):
    # Descendant self-expires; killing its parent is tested, not assumed to kill it.
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)'],
                             creationflags=flags)
    send.send(child.pid)
    time.sleep(2)
    child.wait(timeout=4)


def _descendant_alive(pid):
    if os.name != 'nt':
        return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    code = wintypes.DWORD()
    ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel.CloseHandle(handle)
    return code.value == 259 if ok else None


def _catalog_and_resources(w):
    evidence = {}
    with _guard(w.cap):
        events = []
        connection = audit.ReadOnlyCatalogConnection(w.target, event_sink=events)
        reads = []
        original = connection._authorize
        def instrument(action, a, b, db, trigger):
            result = original(action, a, b, db, trigger)
            if action == sqlite3.SQLITE_READ:
                reads.append({'table': a, 'column': b, 'allowed': result == sqlite3.SQLITE_OK})
            return result
        connection._connection.set_authorizer(instrument)
        catalog = audit._catalog_inventory(connection)
        evidence['catalog'] = {'objects': len(catalog['objects']),
            'has_fk': any(o.get('foreign_keys') for o in catalog['objects']),
            'application_read_events': [r for r in reads if not r['table'].startswith('sqlite_')],
            'sentinel_in_output': 'R9J_SYNTHETIC_SENTINEL' in json.dumps(catalog),
            'statements': [e['statement'] for e in events],
            'eqp_count': sum('EXPLAIN' in e['statement'] for e in events)}
        denied = ['SELECT * FROM parent', 'UPDATE parent SET note=1',
                  "ATTACH DATABASE 'outside' AS other", "SELECT load_extension('no')",
                  'SELECT 1', 'PRAGMA query_only; SELECT 1']
        evidence['rejected_statements'] = [_reject(lambda s=s: connection.execute(s)) for s in denied]
        # Existing SQL policy accepts arbitrary catalog SELECT; not an exact template API.
        evidence['arbitrary_catalog_sql_accepted'] = bool(connection.execute(
            'SELECT name FROM sqlite_schema WHERE 1=1 ORDER BY name').fetchall())
        rows = connection.execute('SELECT a.name FROM sqlite_schema a, sqlite_schema b, sqlite_schema c LIMIT 64').fetchall()
        evidence['row_probe'] = {'declared_probe_cap': 2, 'actual_rows': len(rows), 'rejected': False}
        with patch.object(audit, 'MAX_STATEMENTS', connection.statement_count):
            evidence['statement_cap_rejected'] = _reject(lambda: connection.execute('PRAGMA query_only'))
        with patch.object(audit, 'STATEMENT_TIMEOUT_SECONDS', 0):
            evidence['execute_deadline_rejected'] = _reject(lambda: connection.execute('SELECT name FROM sqlite_schema ORDER BY name'))
        handlers = []
        class Proxy:
            def __getattr__(self, key):
                return getattr(raw, key)
            def set_progress_handler(self, callback, n):
                handlers.append(callback is not None)
                return raw.set_progress_handler(callback, n)
        raw = connection._connection
        connection._connection = Proxy()
        with patch.object(audit, 'STATEMENT_TIMEOUT_SECONDS', 0.02):
            cur = connection.execute('SELECT name FROM sqlite_schema')
            handler_active = handlers[-1]
            time.sleep(0.03)
            fetched = cur.fetchall()
        evidence['fetch_deadline'] = {'handler_active_during_fetch': handler_active,
                                      'rows_after_deadline': len(fetched)}
        connection.close()
    out = w.root / 'bounded_output'; out.mkdir()
    with patch.object(audit, 'MAX_OUTPUT_BYTES', 16):
        writer = audit._ArtifactWriter(out)
        rejected = _reject(lambda: writer.write_text('completion_report.md', 'x' * 17))
    evidence['output_cap'] = {'rejected': rejected, 'emitted_bytes': sum(p.stat().st_size for p in out.iterdir())}
    provenance = w.root / 'provenance'; provenance.mkdir()
    (provenance / 'manifest.json').write_text(json.dumps({
        'source': 'SYNTHETIC', 'parser': 'r9j', 'corrections': 'none in fixture',
        'backup': 'not proven', 'retention': 'test only'}))
    inv, rights = audit._provenance_inventory([provenance])
    evidence['provenance'] = {'files': inv['file_count'], 'rights': rights['statuses'],
                              'absence_is_permission': rights['absence_is_permission']}
    return evidence


def _quiescence(w):
    def snapshot():
        return audit.capture_file_identity(w.target, synthetic_root=w.source)
    data = {'closed_sidecars': len(snapshot().sidecars)}
    with _guard(w.cap):
        writer = sqlite3.connect(w.target, timeout=2)
        writer.execute('PRAGMA journal_mode=WAL')  # Generated fixture setup only.
        writer.execute("UPDATE parent SET note='SYNTHETIC_CHANGED'")
        data['active_wal_writer_sidecars'] = [s['kind'] for s in snapshot().sidecars]
        writer.rollback(); writer.close()
        # A different fresh rollback-mode fixture is not needed: this is still
        # generated setup, never a production target safety transformation.
        writer = sqlite3.connect(w.target, timeout=2)
        writer.execute('PRAGMA journal_mode=DELETE')
        writer.execute("UPDATE parent SET note='SYNTHETIC_CHANGED'")
        data['active_rollback_writer_sidecars'] = [s['kind'] for s in snapshot().sidecars]
        writer.rollback(); writer.close()
        first = snapshot()
        sidecar = Path(str(w.target) + '-wal')
        sidecar.write_bytes(b'synthetic late sidecar')
        data['late_sidecar_detected'] = first.sidecars != snapshot().sidecars
        sidecar.unlink()  # Remove only this explicitly generated fault injection.
        before = digest(w.target)
        connection = audit.ReadOnlyCatalogConnection(w.target, event_sink=[])
        writer = sqlite3.connect(w.target, timeout=2)
        writer.execute("UPDATE parent SET note='SYNTHETIC_DURING_INSPECTION'")
        writer.commit(); writer.close()
        connection.execute('SELECT name FROM sqlite_schema').fetchall()
        connection.close()
        data['writer_succeeded_during_inspection'] = before != digest(w.target)
        original = snapshot()
        # Full hash is feasible for this tiny fixture only, not the real target.
        with w.target.open('ab') as stream:
            stream.write(b'R9J_APPEND')
        data['mutation_between_checks_detected'] = audit._identity_key(original) != audit._identity_key(snapshot())
        replacement = w.source / 'replacement.generated'
        replacement.write_bytes(w.target.read_bytes() + b'R9J')
        pre = digest(w.target)
        os.replace(replacement, w.target)
        connection = audit.ReadOnlyCatalogConnection(w.target, event_sink=[])
        connection.close()
        data['replacement_open_succeeded'] = True
        data['replacement_postcheck_detected'] = pre != digest(w.target)
    data['prevention_claim'] = False
    return data


def _registry_experiments(w):
    ctx = mp.get_context('spawn')
    with _guard(w.cap) as parent_counts:
        registry = boundary.DurableAuditRegistry.create_synthetic(w.root / 'registry', forbidden_roots=[w.source])
        one = w.approval('race'); registry.register(one)
        facts = {'duplicate_registration_rejected': _reject(lambda: registry.register(one))}
        ready = ctx.Event()
        workers = []
        for i in range(2):
            recv, send = ctx.Pipe(duplex=False)
            p = ctx.Process(target=_registry_worker, args=(w.cap, one, f'R9J-race-{i}', 'race', ready, send))
            p.start(); workers.append((p, recv, send))
        ready.set()
        outcomes = []
        for p, recv, send in workers:
            assert _wait(p) == 0
            assert recv.poll(1)
            outcomes.append(recv.recv()); recv.close(); send.close()
        facts['race'] = outcomes
        facts['winners'] = sum(o['winner'] for o in outcomes)
        winning_attempt = registry.consumed_by(one.approval_id)
        facts['replay_rejected_after_restart'] = _reject(lambda: boundary.DurableAuditRegistry(w.registry_path).consume(one, 'R9J-other'))
        two = w.approval('second'); registry.register(two)
        facts['reused_attempt_rejected'] = _reject(lambda: registry.consume(two, winning_attempt))
        facts['modified_rejected'] = _reject(lambda: registry.consume(dataclasses.replace(two, approval_statement='changed'), 'R9J-modified'))
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        expired = audit.seal_audit_approval(dataclasses.replace(two, approval_id='R9J_SYNTHETIC_expired',
            issued_at=(past - timedelta(hours=1)).isoformat(), expires_at=past.isoformat()))
        facts['expired_rejected'] = _reject(lambda: registry.register(expired))
        facts['crashes'] = []
        for mode in ('before', 'after', 'after_open'):
            approval = w.approval(mode); registry.register(approval)
            recv, send = ctx.Pipe(duplex=False)
            p = ctx.Process(target=_registry_worker, args=(w.cap, approval, 'R9J-' + mode, mode, ready, send))
            p.start(); code = _wait(p)
            assert recv.poll(1)
            observed = recv.recv(); recv.close(); send.close()
            reopened = boundary.DurableAuditRegistry(w.registry_path)
            consumed = reopened.consumed_by(approval.approval_id)
            observed.update(exit_code=code, consumed_after_restart=consumed is not None,
                incomplete=any(a['approval_id'] == approval.approval_id for a in reopened.incomplete_attempts()))
            if consumed:
                observed['replay_rejected'] = _reject(lambda: reopened.consume(approval, 'R9J-retry-' + mode))
            facts['crashes'].append(observed)
        facts['ledger_verified'] = registry.verify()['tamper_check']
        facts['parent_connections'] = dict(parent_counts)
        # Existing approval does not bind an attempt ID; registry binds it only at consumption.
        facts['approval_payload_has_attempt_id'] = 'attempt_id' in one.body()
    return facts


def run_experiments():
    w = _Workspace()
    try:
        results = {'schema_version': 'r9j_synthetic_results_v1', 'classification': 'SYNTHETIC_ONLY_NONCANONICAL',
            'platform': {'system': platform.system(), 'release': platform.release(),
                         'version': platform.version(), 'python': platform.python_version(),
                         'sqlite': sqlite3.sqlite_version},
            'fixture': w.initial, 'fixture_recipe': RECIPE,
            'catalog_resources': _catalog_and_resources(w), 'quiescence': _quiescence(w),
            'registry': _registry_experiments(w)}
        with _guard(w.cap):
            results['containment'] = {'outside_rejected': _reject(lambda: sqlite3.connect(w.root.parent / 'not-created.sqlite')),
                                     'unknown_id_rejected': _reject(lambda: w.cap.check('arbitrary'))}
            link = w.source / 'link.sqlite'
            try:
                link.symlink_to(w.target)
                linked = _Capsule(w.root, w.cap.allowed + (link,))
                results['containment']['symlink'] = 'REJECTED' if _reject(lambda: linked.check(link)) else 'FAILED'
                link.unlink()
            except OSError:
                results['containment']['symlink'] = 'SKIPPED_PLATFORM_PRIVILEGE'
        ctx = mp.get_context('spawn')
        recv, send = ctx.Pipe(duplex=False)
        p = ctx.Process(target=_resource_child, args=(w.cap, send))
        p.start(); assert _wait(p) == 0
        assert recv.poll(1)
        results['resource_probe'] = recv.recv(); recv.close(); send.close()
        recv, send = ctx.Pipe(duplex=False)
        p = ctx.Process(target=_sleep_worker, args=(send,))
        p.start()
        assert recv.poll(5)
        pid = recv.recv()
        start = time.monotonic(); p.join(0.3)
        still_alive = p.is_alive()
        if still_alive:
            p.terminate()
        _wait(p)
        child_alive = _descendant_alive(pid)
        results['worker_timeout'] = {'deadline_seconds': 0.3, 'terminated': still_alive,
            'worker_dead': not p.is_alive(), 'elapsed_seconds': round(time.monotonic() - start, 3),
            'descendant_survived_parent': child_alive, 'descendant_lifetime_cap_seconds': 3}
        # Bounded wait for self-expiry, not a claim of tree termination enforcement.
        time.sleep(3.2)
        results['worker_timeout']['descendant_alive_after_self_expiry'] = _descendant_alive(pid)
        recv.close(); send.close()
        results['production_access'] = False
        return results
    finally:
        w.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', help='Create sanitized result artifacts once; refuses overwrite')
    args = parser.parse_args()
    result_path = OUT / 'results_v1.json'
    manifest_path = OUT / 'manifest_v1.json'
    if args.record and (result_path.exists() or manifest_path.exists()):
        parser.error('immutable investigation outputs already exist; run without --record')
    result = run_experiments()
    if args.record:
        sources = ['tools/r9j_synthetic_boundary.py', 'tests/test_research_r9j_synthetic_boundary.py',
                   'docs/investigations/r9j/EXPERIMENT_PLAN.md',
                   'src/market_intel/foundation/local_fno_audit.py',
                   'src/market_intel/foundation/fno_production_boundary.py',
                   'docs/project_status/pre_research_review_record_v5.json']
        result_path.write_bytes(canonical(result))
        manifest = {'schema_version': 'r9j_synthetic_manifest_v1',
            'classification': 'SYNTHETIC_ONLY_NONCANONICAL', 'production_authority': False,
            'baseline_commit': 'db3d8727807336560c1401ecadc80b4415c79897',
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'sources': [{'path': name, 'sha256': digest(ROOT / name)} for name in sources],
            'results_sha256': digest(result_path), 'fixture': result['fixture'],
            'fixture_retention': 'Fresh tiny fixtures generated per run and deleted; recipe and initial byte hash retained.',
            'reproducibility': 'Expect equivalent assertions, not identical timing, OS counters, or contender winner.',
            'decision': 'SYNTHETIC_BOUNDARY_INVESTIGATION_COMPLETED_PRODUCTION_BLOCKED'}
        manifest_path.write_bytes(canonical(manifest))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
