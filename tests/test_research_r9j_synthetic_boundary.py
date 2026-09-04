"""Fresh synthetic fixtures only. No private configuration or real-data tests."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from tools import r9j_synthetic_boundary as investigation


@pytest.fixture(scope='module')
def observed():
    return investigation.run_experiments()


def test_fixture_small_new_and_current_platform(observed):
    assert observed['fixture']['bytes'] < 1024 * 1024
    assert observed['fixture']['recipe_sha256'] == hashlib.sha256(investigation.RECIPE.encode()).hexdigest()
    assert observed['platform']['python']
    assert observed['production_access'] is False


def test_quiescence_is_detection_not_prevention(observed):
    q = observed['quiescence']
    assert q['closed_sidecars'] == 0
    assert {'WAL', 'SHM'} <= set(q['active_wal_writer_sidecars'])
    assert 'JOURNAL' in q['active_rollback_writer_sidecars']
    for field in ('late_sidecar_detected', 'writer_succeeded_during_inspection',
                  'mutation_between_checks_detected', 'replacement_open_succeeded',
                  'replacement_postcheck_detected'):
        assert q[field] is True
    assert q['prevention_claim'] is False


def test_catalog_no_eqp_or_sentinel_and_rejections(observed):
    r = observed['catalog_resources']
    assert r['catalog']['objects'] == 4
    assert r['catalog']['has_fk'] is True
    assert r['catalog']['eqp_count'] == 0
    assert r['catalog']['sentinel_in_output'] is False
    assert all(r['rejected_statements'])
    assert r['arbitrary_catalog_sql_accepted'] is True  # Existing gap, not endorsed.
    assert r['provenance']['absence_is_permission'] is False


def test_resource_enforcement_and_fetch_gap(observed):
    r = observed['catalog_resources']
    assert r['statement_cap_rejected'] is True
    assert r['output_cap'] == {'rejected': True, 'emitted_bytes': 0}
    assert r['execute_deadline_rejected'] is True
    assert r['fetch_deadline']['handler_active_during_fetch'] is False
    assert r['fetch_deadline']['rows_after_deadline'] > 0
    assert r['row_probe']['actual_rows'] == 64 > r['row_probe']['declared_probe_cap']


def test_memory_temp_and_io_are_not_hard_enforcement(observed):
    r = observed['resource_probe']
    assert r['allocated_bytes'] > r['declared_memory_probe_limit']
    assert r['scratch_bytes'] > r['declared_temp_probe_limit']
    assert r['os_accounting_is_target_or_physical_bytes'] is False


def test_parent_timeout_does_not_imply_descendant_cleanup(observed):
    r = observed['worker_timeout']
    assert r['terminated'] and r['worker_dead']
    assert r['elapsed_seconds'] < 8
    if observed['platform']['system'] == 'Windows':
        assert r['descendant_survived_parent'] is True
        assert r['descendant_alive_after_self_expiry'] is False


def test_registry_one_winner_replay_and_unique_attempt(observed):
    r = observed['registry']
    assert r['winners'] == 1
    for key in ('duplicate_registration_rejected', 'replay_rejected_after_restart',
                'reused_attempt_rejected', 'modified_rejected', 'expired_rejected'):
        assert r[key] is True
    assert r['ledger_verified'] == 'PASS'
    assert r['approval_payload_has_attempt_id'] is False
    assert all(o['target_connections'] == 0 for o in r['race'])
    assert sum(o['registry_connections'] for o in r['race']) == 2


def test_crash_phases_preserve_consumption(observed):
    before, after, opened = observed['registry']['crashes']
    assert before['exit_code'] == 21 and not before['consumed_after_restart']
    assert before['target_connections'] == before['registry_connections'] == 0
    assert after['exit_code'] == 22 and after['target_connections'] == 0
    assert opened['exit_code'] == 23 and opened['target_connections'] == 1
    for r in (after, opened):
        assert r['consumed_after_restart'] and r['incomplete'] and r['replay_rejected']
        assert r['registry_connections'] == 1


def test_containment_and_platform_limitations(observed):
    r = observed['containment']
    assert r['outside_rejected'] and r['unknown_id_rejected']
    if r['symlink'] == 'SKIPPED_PLATFORM_PRIVILEGE':
        pytest.skip('Windows symlink privilege unavailable; reparse defense not fully proven')
    assert r['symlink'] == 'REJECTED'


def test_source_has_no_private_configuration_network_or_path_cli():
    source = Path(investigation.__file__).read_text()
    tree = ast.parse(source)
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    imports |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not imports & {'tomllib', 'requests', 'kiteconnect', 'socket'}
    assert 'getenv(' not in source and 'os.environ' not in source
    assert 'config.toml' not in source and 'raw_binding.json' not in source
    assert "add_argument('--record'" in source
    assert len([n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'add_argument']) == 1


def test_committed_result_manifest_matches_sources():
    root = investigation.ROOT
    manifest = json.loads((investigation.OUT / 'manifest_v1.json').read_text())
    assert manifest['production_authority'] is False
    assert investigation.digest(investigation.OUT / 'results_v1.json') == manifest['results_sha256']
    for row in manifest['sources']:
        assert investigation.digest(root / row['path']) == row['sha256']
    content = (investigation.OUT / 'results_v1.json').read_text()
    assert ':\\' not in content and '/Users/' not in content
