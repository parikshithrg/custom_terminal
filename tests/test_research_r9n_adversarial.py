"""Static R.9N evidence checks; no APSW installation or native execution."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/investigations/r9n'


def results(): return json.loads((BASE/'results_v1.json').read_text())
def cases(): return {x['name']:x for x in results()['cases']}


def test_all_evidence_hashes_and_json():
    m=json.loads((BASE/'manifest_v1.json').read_text())
    for row in m['artifacts']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    for path in BASE.glob('*.json'): json.loads(path.read_text())
    assert results()['source_sha256']==hashlib.sha256((ROOT/'tools/r9n_adversarial.py').read_bytes()).hexdigest()


def test_three_layouts_observed_not_universal_threshold():
    c=cases()
    needs=[]
    for size in ('512','1024','4096'):
        need=c[size+'_sufficient']['observed']['reserved']; needs.append(need)
        assert c[size+'_exact']['observed']['cap']==need
        assert c[size+'_below']['observed']['cap']==need-1
        assert c[size+'_exact']['observed']['published_rows']==35
        assert c[size+'_below']['observed']['published_rows']==0
        assert c[size+'_fetch']['observed']['row_seen']>0
    assert len(set(needs))==3


def test_meter_accounting_and_no_failed_publication():
    for item in results()['cases']:
        o=item['observed']
        assert o['returned']<=o['delegated']==o['reserved']<=o['cap']
        assert o['requested']>=o['reserved']
        if o['failed']:
            assert o['published_rows']==0 and o['kind']=='FAILED_ATTEMPT_DIAGNOSTIC'
    c=cases()
    assert c['error']['observed']['reserved']==16 and c['error']['observed']['returned']==0
    assert c['short']['observed']['reserved']==16 and c['short']['observed']['returned']==15
    assert c['repeat']['observed']['reserved']==32


def test_shared_statement_cursor_and_output_controls():
    extra=json.loads((BASE/'supplemental_results_v1.json').read_text())
    byname={c['name']:c['observed'] for c in extra}
    assert byname['shared_success']['published_rows']==70
    assert byname['shared_rows']['row_seen']==41 and byname['shared_rows']['published_rows']==0
    assert byname['shared_output']['buffered_bytes_peak']<=11000
    for name in ('fetch_deadline','execute_deadline'):
        assert cases()[name]['observed']['failed']=='DEADLINE'


def test_restricted_access_and_attempt_lifecycle():
    c=cases()
    for name in ('readwrite','create','temp','wal','journal','WAL_active','DELETE_active',
                 'reopen','second','closed','after_exhaustion','facade_sql'):
        assert c[name]['observed']['failed'] and c[name]['observed']['published_rows']==0
    assert all(c[name]['observed']['failed']=='SQL_AUTHORIZATION' for name in c if name.startswith('native_sql_'))


def test_official_schema_is_not_inferred():
    e=json.loads((BASE/'official_format_evidence_v1.json').read_text())
    assert e['status']=='PENDING_OFFICIAL_FORMAT_EVIDENCE'
    assert e['document_sha256'] is None and e['field_definitions']==[]
    assert not e['market_records_acquired'] and not e['security_lists_acquired']
    source=(ROOT/'tools/r9n_adversarial.py').read_text()
    assert 'generic_id' in source and 'generic_value' in source


def test_scope_and_production_blocks_remain():
    m=json.loads((BASE/'manifest_v1.json').read_text())
    assert m['production_interlock']=='R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE'
    assert not m['dependency_adopted'] and not m['real_database_accessed']
    assert m['research_state_fingerprint']=='1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef'
    assert 'apsw' not in (ROOT/'pyproject.toml').read_text().lower()
    assert results()['temporary_root_removed']


def test_sanitized_evidence_and_no_private_inputs():
    for path in BASE.iterdir():
        text=path.read_text()
        assert not re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\\Users\\',text)
        assert not re.search(r'(?i)(api_secret|access_token|password)\s*[:=]\s*\S+',text)
    source=(ROOT/'tools/r9n_adversarial.py').read_text()
    for value in ('config.toml','raw_binding','getenv','requests.'):
        assert value not in source
