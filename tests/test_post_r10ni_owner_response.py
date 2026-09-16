"""Owner responses are append-only decisions, not implicit execution gates."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/investigations/post_r10ni_policy/owner_response_v1'


def test_owner_response_preserves_separate_decisions_and_closed_execution():
    response = json.loads((PACKAGE / 'owner_response.json').read_text())
    evidence = response['r10ni_evidence']
    assert hashlib.sha256((ROOT / evidence['path']).read_bytes()).hexdigest() == evidence['sha256']
    assert evidence['interpretation'] == 'ACCEPT_R10N_I_AGGREGATE_EVIDENCE_NOT_SOURCE_QUALIFICATION'
    assert response['source_policy']['route_selected'] is True
    assert response['source_policy']['execution_scope_approval'].startswith('PENDING')
    assert response['retention']['anchor_clarified_deadline'] == '2026-12-31'
    assert set(response['retention']['other_deadlines'].values()) == {'2026-12-31'}
    assert response['closeout']['r10ne_owner_acceptance_trigger_now_applies'] is True
    assert response['deletion']['general_authorization_received'] is True
    assert response['deletion']['execution_ready'] is False
    assert response['deletion']['per_package_target_confirmation'] == 'PENDING'
    assert response['deletion']['packages_deleted'] == response['source_policy']['network_requests'] == 0
    for key in ('source_qualified', 'production_activated', 'adapter_changed', 'requalification_performed',
                'ingestion', 'research', 'fingerprint_refreshed', 'historical_evidence_modified'):
        assert response[key] is False


def test_owner_response_is_sanitized_and_hash_bound():
    manifest = json.loads((PACKAGE / 'root_manifest.json').read_text())
    assert [item['path'] for item in manifest['artifacts']] == ['owner_response.json']
    for item in manifest['artifacts']:
        payload = (PACKAGE / item['path']).read_bytes()
        assert len(payload) == item['byte_length']
        assert hashlib.sha256(payload).hexdigest() == item['sha256']
        text = payload.decode().lower()
        for marker in ('c:\\users\\', '/home/', '/users/', 'cookie:', 'authorization:', 'bearer '):
            assert marker not in text
