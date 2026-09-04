"""Report-only R.9I checks; no private locator, SQLite or network access."""
import hashlib
import json
import re
from pathlib import Path

from research_contracts.pre_research_review import compute_research_state_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/project_status/pre_research_generation_manifest_v5.json'


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def text():
    return (ROOT / load_manifest()['source_path']).read_text(encoding='utf-8')


def test_exact_source_pdf_generator_and_evidence_hashes():
    m = load_manifest()
    rows = m['evidence_inputs'] + [
        {'path': m[k + '_path'], 'sha256': m[k + '_sha256']}
        for k in ('source', 'pdf', 'generator')]
    for row in rows:
        assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256']


def test_pdf_complete_page_count_and_reviewed_render():
    m = load_manifest()
    pdf = (ROOT / m['pdf_path']).read_bytes()
    assert pdf.startswith(b'%PDF-') and pdf.rstrip().endswith(b'%%EOF')
    assert len(re.findall(rb'/Type\s*/Page\b', pdf)) == m['rendered_page_count'] == 10
    assert m['deterministic_render_verified'] is True
    assert m['visual_verification_result'] == 'PASS_10_PAGES_NO_MATERIAL_DEFECTS'


def test_report_is_not_approval_and_all_authority_false():
    m = load_manifest()
    assert m['manifest_kind'] == 'NON_APPROVAL_REPORT_GENERATION'
    assert m['lifecycle_state'] == 'PDF_V5_GENERATED_AWAITING_OWNER_REVIEW'
    # Generation remains non-approving even after a separate owner review.
    assert m['owner_review_recorded'] is False
    for key, value in m.items():
        if key.endswith('_authorized') or key in (
            'owner_review_recorded', 'approval_issued', 'approval_registered',
            'approval_consumed', 'private_database_accessed'):
            assert value is False, key


def test_all_six_decisions_keep_recommendations_and_evidence_open():
    sections = re.split(r'## \d+\. Decision \d+ - ', text())[1:]
    assert len(sections) == len(load_manifest()['unresolved_decisions']) == 6
    for section in sections:
        for label in ('**Question:**', '**Why it matters:**', '**Options and trade-offs:**',
                      '**PROPOSED_NOT_APPROVED:**', '**Engineering evidence needed:**', '**Gate:**'):
            assert label in section


def test_owner_questions_are_numbered_without_answers_or_execution_request():
    questions = text().split('## 11. Owner questions')[1].split('[PAGE BREAK]')[0]
    assert re.findall(r'^(\d+)\. ', questions, re.M) == [str(i) for i in range(1, 10)]
    assert 'No immediate audit authority is requested' in questions
    assert 'No answers, consent or owner-review record have been recorded' in questions
    assert 'Summary confirmation' in questions and 'Technical questions needing evidence' in questions


def test_no_research_state_or_previous_review_mutation():
    policy = json.loads((ROOT / 'specs/pre_research_review_policy_v1.json').read_text())
    state = compute_research_state_fingerprint(ROOT, policy)
    m = load_manifest()
    assert state['sha256'] == m['research_state_fingerprint'] == '1b56c28fabed28672d140cf76ba8b242f00e0b4965ab682ebc7704bb38742fef'
    assert state['file_count'] == m['research_state_file_count'] == 252
    record = json.loads((ROOT / 'docs/project_status/pre_research_review_record_v4.json').read_text())
    assert record['staleness']['status'] == 'PDF_V4_STALE_AFTER_R9H_PROPOSAL_PREPARATION'


def test_report_preserves_research_limits_and_budget_distinctions():
    content = text()
    for phrase in ('A sampled fingerprint is not a full-file hash',
                   'Stage 3 does not authorize research', 'version2.0 separate',
                   'bytes read, pages visited, statements executed and returned rows',
                   'SQLite progress callbacks alone cannot enforce',
                   'official NSE F&O bhavcopies', 'No acquisition or external-source access',
                   'R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE'):
        assert phrase.lower() in content.lower()


def test_report_and_manifest_no_private_locations_or_credentials():
    content = text() + MANIFEST.read_text(encoding='utf-8')
    assert not re.search(r'[A-Za-z]:[\\/]|/Users/|\\Users\\', content)
    assert not re.search(r'(?i)(api_secret|access_token|password)\s*[:=]\s*\S+', content)
