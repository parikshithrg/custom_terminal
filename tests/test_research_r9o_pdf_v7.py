"""Static R.9O report checks; no candidate execution or private-data access."""
import hashlib,json,re
from pathlib import Path
from research_contracts.pre_research_review import compute_research_state_fingerprint
ROOT=Path(__file__).resolve().parents[1]
M=ROOT/'docs/project_status/pre_research_generation_manifest_v7.json'
def manifest(): return json.loads(M.read_text())
def source(): return (ROOT/manifest()['source_path']).read_text()
def test_all_hash_bindings():
 m=manifest(); rows=m['evidence_inputs']+[{"path":m[k+'_path'],"sha256":m[k+'_sha256']} for k in ('source','pdf','generator','report','test')]
 for r in rows: assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']
def test_pdf_and_visual_result():
 m=manifest(); b=(ROOT/m['pdf_path']).read_bytes()
 assert b.startswith(b'%PDF-') and b.rstrip().endswith(b'%%EOF')
 assert len(re.findall(rb'/Type\s*/Page\b',b))==m['rendered_page_count']==6
 assert m['deterministic_render_verified'] and m['visual_verification_result']=='PASS_6_PAGES_NO_MATERIAL_DEFECTS'
def test_nonapproval_and_no_entrypoint():
 m=manifest(); assert m['manifest_kind']=='NON_APPROVAL_REPORT_GENERATION'
 assert m['lifecycle_state']=='PDF_V7_GENERATED_AWAITING_OWNER_DECISION'
 assert not m['owner_review_recorded'] and all(not v for v in m['authority'].values())
 assert not (ROOT/'docs/project_status/pre_research_review_record_v7.json').exists()
def test_exact_candidate_facts_and_classifications():
 t=source()
 for x in ('3.53.4.0','3.53.4','13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5','DEMONSTRATED_WITH_LIMITATIONS','PENDING_OFFICIAL_FORMAT_EVIDENCE','R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE'):
  assert x in t
 assert 'Root environment and dependency files still contain no APSW' in t
def test_meter_and_restrictions_complete():
 t=source()
 for x in ('Requested','Reserved','Delegated','Returned','not OS process I/O','not physical disk I/O','No mmap, WAL, rollback journal','No caller-provided SQL','discard buffered output','reproducible build provenance was not established'):
  assert x in t
def test_options_acceptance_and_questions():
 t=source(); assert 'A - Recommended' in t and 'Option B' not in t  # table uses B; prose label is intentionally absent
 assert 'Proposed acceptance criteria for Option A - not implemented' in t
 q=t.split('## 7. Owner questions')[1].split('## Evidence')[0]
 assert re.findall(r'^(\d+)\. ',q,re.M)==list(map(str,range(1,8)))
 assert 'No answers are pre-filled' in q
def test_fingerprint_unchanged_but_direct_bindings_fresh():
 m=manifest(); state=compute_research_state_fingerprint(ROOT,json.loads((ROOT/'specs/pre_research_review_policy_v1.json').read_text()))
 assert state['sha256']==m['research_state_fingerprint']=='1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef'
 assert {r['path'] for r in m['evidence_inputs']}>={'docs/investigations/r9m/manifest_v1.json','docs/investigations/r9n/manifest_v1.json'}
 assert not m['fingerprint_policy_changed']
def test_no_private_paths_or_secrets():
 t=source()+M.read_text()+(ROOT/manifest()['report_path']).read_text()
 assert not re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|\\Users\\',t)
 assert not re.search(r'(?i)(api_secret|access_token|password)\s*[:=]\s*\S+',t)
