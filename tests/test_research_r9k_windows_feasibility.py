"""OS experiments use newly generated fixtures only; no R.9J workload reruns."""
import ast
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tools import r9k_windows_feasibility as probe


@pytest.fixture(scope='module')
def observed():
    if os.name != 'nt':
        pytest.skip('R.9K requires Windows native APIs')
    return probe.run()


def test_guard_allows_reader_but_prevents_independent_main_file_changes(observed):
    r = observed['file_guard']
    assert r['sqlite_readonly_compatible'] and r['guard_held_through_reader_close']
    assert r['main_hash_unchanged']
    for phase in (r, r['verification_to_open_adversary'], r['reader_open_adversary']):
        assert all(phase[op]['prevented'] for op in ('write', 'rename', 'replace'))


def test_sibling_sidecars_are_not_protected(observed):
    r = observed['file_guard']
    assert r['sidecar_creation_and_change_succeeded']
    assert r['detected_sidecars'] == 3


def test_guard_cleanup_after_error_and_actual_process_exit(observed):
    r = observed['file_guard']
    assert r['writer_after_error_cleanup'] and r['owner_blocks_writer']
    assert r['writer_after_owner_termination']
    assert r['guard_release_seconds'] < 4


@pytest.mark.parametrize('key', ['job_timeout', 'job_close'])
def test_job_assignment_and_tree_cleanup_native(observed, key):
    r = observed[key]
    assert r['no_worker_marker_before_assignment'] and r['assigned_before_resume']
    assert r['leaf_in_same_job'] and r['pinned_job_processes_before_termination'] >= 2
    assert r['worker_dead'] and r['leaf_dead'] and r['all_pinned_job_processes_dead']
    assert r['observed_before_8_second_self_expiry']
    assert 0 <= r['deadline_overshoot_seconds'] < 2
    assert r['cleanup_seconds'] < 4


def test_actual_supervisor_death_closes_job_not_self_expiry(observed):
    r = observed['supervisor_crash']
    assert r['supervisor_terminated'] and r['all_pinned_job_processes_dead']
    assert r['worker_dead'] and r['leaf_dead'] and r['not_self_expiry']


def test_committed_memory_limit_vs_unlimited_control(observed):
    limited = observed['job_memory']; control = observed['job_memory_control']
    assert limited['metric'] == 'committed_virtual_memory_not_working_set'
    assert limited['observations'][0]['allocated']
    assert not limited['observations'][1]['allocated']
    assert control['observations'][1]['allocated']
    assert limited['peak_process_commit_bytes'] <= limited['process_limit_bytes']
    assert limited['worker_dead'] and control['worker_dead']


def test_native_assignment_failure_stays_suspended_and_cleans_up(observed):
    r = observed['failure_paths']
    assert r['native_invalid_assignment_rejected'] and r['winerror'] == 6
    assert r['worker_never_resumed'] and r['worker_dead']


def test_mock_creation_failure_prevents_spawn(tmp_path):
    # Distinct mocked control-flow test, not evidence of OS enforcement.
    with patch.object(probe, '_root', return_value=tmp_path), \
         patch.object(probe.Native, '__init__', return_value=None), \
         patch.object(probe.Native, 'job', side_effect=RuntimeError('injected')), \
         patch.object(probe.Native, 'suspended') as spawn:
        with pytest.raises(RuntimeError, match='injected'):
            probe.job_probe('case-aaaaaaaa', 'timeout')
        spawn.assert_not_called()


def test_no_logical_byte_interception_claim(observed):
    r = observed['byte_budget']
    assert r['catalog_operations'] == 2 and r['python_file_hook_calls'] == 0
    assert r['public_vfs_registration_api'] is False
    assert r['conclusion'] == 'NOT_FEASIBLE_WITH_CURRENT_APPROVED_STACK'


def test_no_survivors_and_fixture_is_tiny(observed):
    assert observed['all_experimental_processes_confirmed_dead']
    assert observed['fixture']['bytes'] <= 32768
    assert observed['production_access'] is False


def test_no_path_arguments_private_fallback_or_production_imports():
    source = Path(probe.__file__).read_text()
    tree = ast.parse(source)
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    modules |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and m.startswith(('market_intel', 'requests', 'tomllib', 'kiteconnect')) for m in modules)
    assert 'config.toml' not in source and 'raw_binding.json' not in source
    assert 'getenv(' not in source and 'os.environ' not in source
    with pytest.raises(ValueError):
        probe._root('../outside')
