import json
from pathlib import Path

import pytest

from research_contracts.legacy_ledger import sha256_file
from research_contracts.pre_research_review import validate_review_record, PreResearchReviewError

ROOT = Path(__file__).resolve().parents[1]


def test_v5_review_exact_bindings_and_nine_answers():
    record = json.loads((ROOT / 'docs/project_status/pre_research_review_record_v5.json').read_text())
    for key in ('pdf', 'source', 'generation_manifest'):
        assert sha256_file(ROOT / record[key + '_path']) == record[key + '_sha256']
    assert [r['question'] for r in record['reviewer_questions']] == list(range(1, 10))
    assert all(r['answer'] and r['decision'] for r in record['reviewer_questions'])
    authority = record['execution_authority']
    assert authority['synthetic_only_design_investigation_authorized'] is True
    assert all(v is False for k, v in authority.items() if k != 'synthetic_only_design_investigation_authorized')


@pytest.mark.parametrize('scope', [
    'BOUNDED_SYNTHETIC_BOUNDARY_DESIGN_INVESTIGATION_ONLY', 'PRODUCTION_AUDIT'])
def test_review_gate_is_scope_limited_and_never_execution_permission(scope):
    record = json.loads((ROOT / 'docs/project_status/pre_research_review_record_v5.json').read_text())
    policy = json.loads((ROOT / 'specs/pre_research_review_policy_v1.json').read_text())
    # Exact checkpoint bindings for this record; do not mutate the policy file.
    policy['external_repository_bindings'] = record['external_repository_bindings']
    reference = {k: record[k] for k in (
        'report_id', 'report_version', 'pdf_sha256', 'research_state_fingerprint',
        'external_repository_bindings')}
    reference.update(review_record_path=record['record_path'], covered_scope=scope)
    pre = {'proposed_research_scope': scope, 'pre_research_review': reference}
    # An authentic historical review is not current authority for either its
    # former synthetic scope or a newly proposed production scope.
    with pytest.raises(PreResearchReviewError):
        validate_review_record(record, preregistration=pre, repository_root=ROOT, policy=policy)
    checkpoint = json.loads((ROOT / 'docs/project_status/research_fingerprint_reconciliation_r10i_v1.json').read_text())
    row = next(x for x in checkpoint['historical_reviews'] if x['record_path'].endswith('review_record_v5.json'))
    assert row['reviewed_fingerprint'] == record['research_state_fingerprint']
    assert row['review_scope'] == record['covered_future_scope']
    assert row['current_scope_status'] == 'HISTORICALLY_VALID_NOT_CURRENT_FOR_EXPANDED_SCOPE'
    assert checkpoint['authority']['historical_scope_expansion'] is False
