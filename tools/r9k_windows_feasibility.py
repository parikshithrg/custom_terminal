"""Fixed-function R.9K synthetic Windows probes; no production paths or APIs."""
from __future__ import annotations

import argparse
import builtins
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.pytest_tmp' / 'r9k'
OUT = ROOT / 'docs' / 'investigations' / 'r9k'
RECIPE = 'CREATE TABLE synthetic(id INTEGER PRIMARY KEY); INSERT INTO synthetic VALUES(1);'


def hash_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def _root(token):
    if not re.fullmatch(r'case-[a-z0-9_]{8}', token):
        raise ValueError('invalid generated fixture token')
    p = BASE / token
    if not (p / '.created_here').is_file() or p.is_symlink():
        raise ValueError('unregistered generated root')
    for part in (p, *p.parents):
        if getattr(part.lstat(), 'st_file_attributes', 0) & 1024:
            raise ValueError('reparse path rejected')
    return p


class BASIC(C.Structure):
    _fields_ = [('process_time', C.c_longlong), ('job_time', C.c_longlong),
                ('flags', W.DWORD), ('min_ws', C.c_size_t), ('max_ws', C.c_size_t),
                ('active', W.DWORD), ('affinity', C.c_size_t), ('priority', W.DWORD), ('scheduling', W.DWORD)]


class IO(C.Structure):
    _fields_ = [(x, C.c_ulonglong) for x in ('readops', 'writeops', 'otherops', 'readbytes', 'writebytes', 'otherbytes')]


class EXTENDED(C.Structure):
    _fields_ = [('basic', BASIC), ('io', IO), ('process_memory', C.c_size_t),
                ('job_memory', C.c_size_t), ('peak_process', C.c_size_t), ('peak_job', C.c_size_t)]


class STARTUP(C.Structure):
    _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR), ('title', W.LPWSTR),
                ('x', W.DWORD), ('y', W.DWORD), ('xsize', W.DWORD), ('ysize', W.DWORD),
                ('xchars', W.DWORD), ('ychars', W.DWORD), ('fill', W.DWORD), ('flags', W.DWORD),
                ('show', W.WORD), ('reserved_size', W.WORD), ('reserved2', C.POINTER(C.c_byte)),
                ('stdin', W.HANDLE), ('stdout', W.HANDLE), ('stderr', W.HANDLE)]


class PROCESS(C.Structure):
    _fields_ = [('process', W.HANDLE), ('thread', W.HANDLE), ('pid', W.DWORD), ('tid', W.DWORD)]


class PROCESS_LIST(C.Structure):
    _fields_ = [('assigned', W.DWORD), ('count', W.DWORD), ('ids', C.c_size_t * 16)]


class Native:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Windows only')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateFileW': ([W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE], W.HANDLE),
            'CloseHandle': ([W.HANDLE], W.BOOL),
            'CreateJobObjectW': ([C.c_void_p, W.LPCWSTR], W.HANDLE),
            'SetInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
            'QueryInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p], W.BOOL),
            'AssignProcessToJobObject': ([W.HANDLE, W.HANDLE], W.BOOL),
            'CreateProcessW': ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL,
                                W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(STARTUP), C.POINTER(PROCESS)], W.BOOL),
            'ResumeThread': ([W.HANDLE], W.DWORD),
            'TerminateProcess': ([W.HANDLE, W.UINT], W.BOOL),
            'TerminateJobObject': ([W.HANDLE, W.UINT], W.BOOL),
            'WaitForSingleObject': ([W.HANDLE, W.DWORD], W.DWORD),
            'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            'GetCurrentProcess': ([], W.HANDLE),
            'IsProcessInJob': ([W.HANDLE, W.HANDLE, C.POINTER(W.BOOL)], W.BOOL),
            'VirtualAlloc': ([C.c_void_p, C.c_size_t, W.DWORD, W.DWORD], C.c_void_p),
            'VirtualFree': ([C.c_void_p, C.c_size_t, W.DWORD], W.BOOL),
        }
        for name, (args, result) in signatures.items():
            f = getattr(self.k, name); f.argtypes = args; f.restype = result

    def check(self, result):
        if not result:
            raise RuntimeError('native operation rejected: ' + str(C.get_last_error()))
        return result

    def close(self, handle):
        if handle:
            self.check(self.k.CloseHandle(handle))

    def in_job(self, process, job=None):
        value = W.BOOL()
        self.check(self.k.IsProcessInJob(process, job, C.byref(value)))
        return bool(value.value)

    def guard(self, token):
        target = _root(token) / 'fixture.sqlite'
        handle = self.k.CreateFileW(str(target), 0x80000000, 1, None, 3, 0x80, None)
        if handle == C.c_void_p(-1).value:
            raise RuntimeError('file guard rejected: ' + str(C.get_last_error()))
        return handle

    def job(self, memory=False):
        job = self.check(self.k.CreateJobObjectW(None, None))
        limits = EXTENDED(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        if memory:
            limits.basic.flags |= 0x100  # PROCESS_MEMORY, committed virtual memory
            limits.process_memory = 48 * 1024 * 1024
        try:
            self.check(self.k.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)))
        except BaseException:
            self.close(job); raise
        return job

    def suspended(self, token, mode):
        _root(token)
        if mode not in {'tree', 'memory', 'marker'}:
            raise ValueError('unapproved worker mode')
        command = subprocess.list2cmdline([sys.executable, '-m', 'tools.r9k_windows_feasibility',
                                           '--child', mode, '--token', token])
        startup = STARTUP(); startup.cb = C.sizeof(startup)
        pi = PROCESS()
        self.check(self.k.CreateProcessW(sys.executable, C.create_unicode_buffer(command), None,
            None, False, 0x00000004 | 0x08000000, None, str(ROOT), C.byref(startup), C.byref(pi)))
        return pi


def _cmd(token, mode):
    return [sys.executable, '-m', 'tools.r9k_windows_feasibility', '--child', mode, '--token', token]


def _wait_file(path, seconds=4):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                pass
        time.sleep(0.01)
    raise RuntimeError('synthetic worker readiness timeout')


def _child(mode, token):
    root = _root(token)
    n = Native()
    if mode in ('adversary', 'adversary_main'):
        target = root / 'fixture.sqlite'; result = {}
        for name in ('write', 'rename', 'replace'):
            try:
                if name == 'write':
                    with target.open('r+b') as f:
                        f.write(b'S')  # Same SQLite header byte; real write attempt.
                elif name == 'rename':
                    os.rename(target, root / 'renamed.sqlite')
                else:
                    replacement = root / 'replacement.synthetic'
                    replacement.write_bytes(b'new synthetic replacement')
                    os.replace(replacement, target)
                result[name] = {'prevented': False, 'winerror': None}
            except OSError as exc:
                result[name] = {'prevented': True, 'winerror': exc.winerror}
        if mode == 'adversary':
            for suffix in ('-wal', '-shm', '-journal'):
                side = Path(str(target) + suffix)
                side.write_bytes(b'new'); side.write_bytes(b'changed')
            result['sidecar_creation_and_change_succeeded'] = True
        print(json.dumps(result))
    elif mode == 'guard_owner':
        h = n.guard(token)
        dump(root / 'guard-ready.json', {'ready': True, 'pid': os.getpid()})
        try:
            time.sleep(8)
        finally:
            n.close(h)
    elif mode == 'leaf':
        time.sleep(8)
    elif mode == 'marker':
        dump(root / 'marker.json', {'ran': True})
    elif mode == 'tree':
        leaf = subprocess.Popen(_cmd(token, 'leaf'), creationflags=subprocess.CREATE_NO_WINDOW)
        dump(root / 'tree-ready.json', {'worker': os.getpid(), 'leaf': leaf.pid,
                                      'in_job': n.in_job(n.k.GetCurrentProcess())})
        time.sleep(8)
        leaf.wait(timeout=2)
    elif mode == 'memory':
        observations = []
        for size in (1024 * 1024, 64 * 1024 * 1024):
            pointer = n.k.VirtualAlloc(None, size, 0x3000, 4)
            error = C.get_last_error() if not pointer else None
            observations.append({'requested_bytes': size, 'allocated': bool(pointer), 'winerror': error})
            if pointer:
                n.check(n.k.VirtualFree(pointer, 0, 0x8000))
        dump(root / 'memory.json', {'observations': observations,
             'metric': 'committed_virtual_memory_not_working_set'})
    elif mode == 'supervisor':
        job = n.job(); pi = None
        try:
            pi = n.suspended(token, 'tree')
            n.check(n.k.AssignProcessToJobObject(job, pi.process))
            n.check(n.k.ResumeThread(pi.thread) != 0xFFFFFFFF)
            _wait_file(root / 'tree-ready.json')
            process_list = PROCESS_LIST()
            n.check(n.k.QueryInformationJobObject(job, 3, C.byref(process_list), C.sizeof(process_list), None))
            if process_list.count != process_list.assigned or process_list.count > 16:
                raise RuntimeError('unbounded process list')
            dump(root / 'supervisor-ready.json', {'assigned': True, 'pid': os.getpid(),
                 'job_pids': [process_list.ids[i] for i in range(process_list.count)]})
            time.sleep(8)
        finally:
            n.close(job)
            if pi:
                n.k.WaitForSingleObject(pi.process, 3000)
                n.close(pi.thread); n.close(pi.process)


def _pin(n, pid):
    return n.check(n.k.OpenProcess(0x100000 | 0x1000 | 1, False, pid))


def _dead(n, handle, timeout=3000):
    return n.k.WaitForSingleObject(handle, timeout) == 0


def file_probe(token):
    root = _root(token); target = root / 'fixture.sqlite'; n = Native()
    h = n.guard(token)
    try:
        verified = hash_file(target)
        def adversary(mode):
            child = subprocess.run(_cmd(token, mode), capture_output=True, text=True,
                                   timeout=4, creationflags=subprocess.CREATE_NO_WINDOW)
            if child.returncode:
                raise RuntimeError('adversary failed')
            return json.loads(child.stdout)
        gap = adversary('adversary_main')
        c = sqlite3.connect(target.as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            during = adversary('adversary_main')
            c.execute('SELECT name FROM sqlite_schema').fetchall()
        finally:
            c.close()
        # Independent adversary while guard remains held, after identity verification.
        observations = adversary('adversary')
        observations['verification_to_open_adversary'] = gap
        observations['reader_open_adversary'] = during
        observations.update(sqlite_readonly_compatible=True, guard_held_through_reader_close=True,
                            main_hash_unchanged=hash_file(target) == verified,
                            detected_sidecars=sum(Path(str(target) + s).exists() for s in ('-wal','-shm','-journal')))
    finally:
        n.close(h)
    # Error cleanup test: leave a guarded scope through a deliberate exception.
    try:
        h = n.guard(token)
        try:
            raise ValueError('synthetic error')
        finally:
            n.close(h)
    except ValueError:
        with target.open('r+b') as f:
            f.write(b'S')
        observations['writer_after_error_cleanup'] = True
    owner = subprocess.Popen(_cmd(token, 'guard_owner'), creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        owner_info = _wait_file(root / 'guard-ready.json')
        actual_owner = _pin(n, owner_info['pid'])
        observations['guard_owner_differs_from_launcher'] = owner_info['pid'] != owner.pid
        try:
            with target.open('r+b'):
                observations['owner_blocks_writer'] = False
        except OSError:
            observations['owner_blocks_writer'] = True
        start = time.monotonic()
        try:
            n.check(n.k.TerminateProcess(actual_owner, 74))
            n.check(_dead(n, actual_owner))
        finally:
            n.close(actual_owner)
        owner.wait(timeout=3)
        deadline = time.monotonic() + 1
        while True:
            try:
                with target.open('r+b') as f:
                    f.write(b'S')
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        observations['writer_after_owner_termination'] = True
        observations['guard_release_seconds'] = round(time.monotonic() - start, 6)
    finally:
        if owner.poll() is None:
            owner.kill(); owner.wait(timeout=3)
    return observations


def job_probe(token, how):
    root = _root(token); n = Native(); job = n.job(memory=how == 'memory'); pi = None
    pins = []; result = {}
    for name in ('tree-ready.json', 'memory.json', 'marker.json'):
        (root / name).unlink(missing_ok=True)
    try:
        pi = n.suspended(token, 'memory' if how in ('memory', 'memory_control') else 'tree')
        result['inherited_host_job'] = n.in_job(pi.process)
        result['no_worker_marker_before_assignment'] = not (root / 'tree-ready.json').exists()
        n.check(n.k.AssignProcessToJobObject(job, pi.process))
        result['assigned_before_resume'] = n.in_job(pi.process, job)
        n.check(n.k.ResumeThread(pi.thread) != 0xFFFFFFFF)
        if how in ('memory', 'memory_control'):
            result.update(_wait_file(root / 'memory.json'))
            result['process_limit_bytes'] = 48 * 1024 * 1024 if how == 'memory' else 0
            result['worker_dead'] = _dead(n, pi.process)
            limits = EXTENDED()
            n.check(n.k.QueryInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits), None))
            result['peak_process_commit_bytes'] = limits.peak_process
            return result
        ready = _wait_file(root / 'tree-ready.json')
        pins = [_pin(n, ready['leaf'])]
        result['leaf_in_same_job'] = n.in_job(pins[0], job)
        process_list = PROCESS_LIST()
        n.check(n.k.QueryInformationJobObject(job, 3, C.byref(process_list), C.sizeof(process_list), None))
        if process_list.assigned != process_list.count or process_list.count > 16:
            raise RuntimeError('unbounded process list')
        pins.extend(_pin(n, process_list.ids[i]) for i in range(process_list.count))
        result['pinned_job_processes_before_termination'] = process_list.count
        deadline = time.monotonic() + 0.3
        time.sleep(0.3)
        action = time.monotonic()
        if how == 'timeout':
            n.check(n.k.TerminateJobObject(job, 71))
        else:
            n.close(job); job = None
        result['worker_dead'] = _dead(n, pi.process)
        result['leaf_dead'] = _dead(n, pins[0])
        result['all_pinned_job_processes_dead'] = all(_dead(n, h) for h in pins)
        result['deadline_overshoot_seconds'] = round(action - deadline, 6)
        result['cleanup_seconds'] = round(time.monotonic() - action, 6)
        result['observed_before_8_second_self_expiry'] = time.monotonic() - deadline < 4
        return result
    finally:
        if job:
            n.close(job)
        if pi:
            if not _dead(n, pi.process, 100):
                n.k.TerminateProcess(pi.process, 72)
                n.k.WaitForSingleObject(pi.process, 3000)
            n.close(pi.thread); n.close(pi.process)
        for handle in pins:
            n.close(handle)


def failure_probe(token):
    n = Native(); root = _root(token)
    (root / 'marker.json').unlink(missing_ok=True)
    # Mock tests only control flow; native invalid assignment is separately tested.
    with patch.object(n, 'job', side_effect=RuntimeError('injected creation failure')):
        try:
            n.job()
        except RuntimeError:
            create_rejected = True
    pi = n.suspended(token, 'marker')
    try:
        assigned = bool(n.k.AssignProcessToJobObject(None, pi.process))
        error = C.get_last_error()
        # Never resume on failure.
        n.check(n.k.TerminateProcess(pi.process, 73))
        dead = _dead(n, pi.process)
        return {'mock_create_failure_rejected': create_rejected,
                'native_invalid_assignment_rejected': not assigned, 'winerror': error,
                'worker_never_resumed': not (root / 'marker.json').exists(), 'worker_dead': dead}
    finally:
        n.close(pi.thread); n.close(pi.process)


def supervisor_crash(token):
    root = _root(token); n = Native(); pins = []
    for name in ('tree-ready.json', 'supervisor-ready.json'):
        (root / name).unlink(missing_ok=True)
    supervisor = subprocess.Popen(_cmd(token, 'supervisor'), creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        supervisor_info = _wait_file(root / 'supervisor-ready.json')
        ready = _wait_file(root / 'tree-ready.json')
        pins = [_pin(n, ready['worker']), _pin(n, ready['leaf'])]
        pins.extend(_pin(n, pid) for pid in supervisor_info['job_pids'])
        start = time.monotonic()
        actual_supervisor = _pin(n, supervisor_info['pid'])
        try:
            n.check(n.k.TerminateProcess(actual_supervisor, 75))
            n.check(_dead(n, actual_supervisor))
        finally:
            n.close(actual_supervisor)
        supervisor.wait(timeout=3)
        dead = [_dead(n, h) for h in pins]
        return {'supervisor_terminated': True, 'worker_dead': dead[0], 'leaf_dead': dead[1],
                'all_pinned_job_processes_dead': all(dead),
                'pinned_job_processes': len(supervisor_info['job_pids']),
                'cleanup_seconds': round(time.monotonic() - start, 6),
                'not_self_expiry': time.monotonic() - start < 4}
    finally:
        if supervisor.poll() is None:
            supervisor.kill(); supervisor.wait(timeout=3)
        for handle in pins:
            n.close(handle)


def byte_probe(token):
    target = _root(token) / 'fixture.sqlite'
    # New independent tiny fixture: sibling corruption from file probe is absent.
    c = sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)
    try:
        called = []
        def reject_open(*args, **kwargs):
            called.append(True)
            raise AssertionError('Python-level file hook unexpectedly used')
        with patch.object(builtins, 'open', reject_open):
            c.execute('SELECT name FROM sqlite_schema').fetchall()
            c.execute('SELECT name FROM sqlite_schema').fetchall()
        return {'python_file_hook_calls': len(called), 'catalog_operations': 2,
                'mmap_size': c.execute('PRAGMA mmap_size').fetchone()[0],
                'public_vfs_registration_api': any('vfs' in name.lower() for name in dir(sqlite3.Connection)),
                'conclusion': 'NOT_FEASIBLE_WITH_CURRENT_APPROVED_STACK',
                'metric': 'sum of target sqlite VFS logical read-request bytes, including cache-miss reads and mapped access; not result bytes or OS I/O'}
    finally:
        c.close()


def run():
    if os.name != 'nt':
        raise RuntimeError('Windows experiment unavailable')
    BASE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='case-', dir=BASE) as name:
        root = Path(name); (root / '.created_here').write_text('R9K newly generated synthetic only')
        token = root.name
        c = sqlite3.connect(root / 'fixture.sqlite'); c.executescript(RECIPE); c.close()
        fixture = {'recipe_sha256': hashlib.sha256(RECIPE.encode()).hexdigest(),
                   'database_sha256': hash_file(root / 'fixture.sqlite'), 'bytes': (root / 'fixture.sqlite').stat().st_size}
        # Byte experiment before file adversary, no repaired target.
        result = {'schema_version': 'r9k_results_v1', 'platform': {'system': platform.system(),
            'release': platform.release(), 'version': platform.version(), 'python': platform.python_version(),
            'sqlite': sqlite3.sqlite_version, 'pointer_bits': C.sizeof(C.c_void_p) * 8}, 'fixture': fixture,
            'host_process_in_job': Native().in_job(Native().k.GetCurrentProcess()),
            'byte_budget': byte_probe(token), 'file_guard': file_probe(token),
            'job_timeout': job_probe(token, 'timeout'), 'job_close': job_probe(token, 'close'),
            'job_memory': job_probe(token, 'memory'), 'failure_paths': failure_probe(token),
            'job_memory_control': job_probe(token, 'memory_control'),
            'supervisor_crash': supervisor_crash(token), 'production_access': False}
        result['all_experimental_processes_confirmed_dead'] = all([
            result['job_timeout']['worker_dead'], result['job_timeout']['leaf_dead'],
            result['job_close']['worker_dead'], result['job_close']['leaf_dead'],
            result['job_memory']['worker_dead'], result['failure_paths']['worker_dead'],
            result['job_memory_control']['worker_dead'], result['job_timeout']['all_pinned_job_processes_dead'],
            result['job_close']['all_pinned_job_processes_dead'],
            result['supervisor_crash']['worker_dead'], result['supervisor_crash']['leaf_dead'],
            result['supervisor_crash']['all_pinned_job_processes_dead']])
        if not result['all_experimental_processes_confirmed_dead']:
            raise RuntimeError('experimental cleanup not proven')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--child', choices=['adversary','adversary_main','guard_owner','leaf','tree','memory','marker','supervisor'])
    parser.add_argument('--token')
    args = parser.parse_args()
    if args.child:
        _child(args.child, args.token)
        return
    if args.token:
        parser.error('token only valid for internal child')
    path = OUT / 'results_v1.json'
    if args.record and path.exists():
        parser.error('immutable result already exists')
    result = run()
    if args.record:
        dump(path, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
