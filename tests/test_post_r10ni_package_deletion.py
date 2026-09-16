"""Sanitized receipt binds explicit three-package deletion without source activation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/investigations/post_r10ni_policy/deletion_v1'


def test_deletion_receipt_is_explicit_bounded_and_hash_bound():
    manifest = json.loads((PACKAGE / 'root_manifest.json').read_text())
    assert [item['path'] for item in manifest['artifacts']] == ['deletion_receipt.json']
    for item in manifest['artifacts']:
        payload = (PACKAGE / item['path']).read_bytes()
        assert len(payload) == item['byte_length']
        assert hashlib.sha256(payload).hexdigest() == item['sha256']
    receipt = json.loads(payload)
    assert receipt['authorization']['target_confirmation'] == 'authorization covers all three packages'
    assert [item['trading_date'] for item in receipt['packages']] == ['2026-09-09', '2026-09-10', '2025-07-08']
    assert receipt['packages_deleted'] == receipt['acquisition_manifests_deleted'] == 3
    assert receipt['report_files_deleted'] == 6
    for item in receipt['packages']:
        assert item['relative_path'] == 'artifacts/nse_fno_reports/' + item['trading_date'] + '/'
        assert item['absence_verified'] and item['acquisition_manifest_deleted']
        assert item['preflight']['manifest_sha256'] == 'MATCH_SEALED_R10NE'
    evidence = receipt['evidence_root']
    assert hashlib.sha256((ROOT / evidence['path']).read_bytes()).hexdigest() == evidence['sha256']
    for key in ('tracked_historical_evidence_deleted', 'source_qualified', 'production_activated',
                'adapter_changed', 'requalification_performed', 'ingestion', 'research',
                'fingerprint_refreshed', 'investigation_execution_authorized'):
        assert receipt[key] is False
    assert receipt['network_requests'] == 0
    for marker in ('c:\\users\\', '/users/', '/home/', 'cookie:', 'authorization:', 'bearer '):
        assert marker not in payload.decode().lower()
