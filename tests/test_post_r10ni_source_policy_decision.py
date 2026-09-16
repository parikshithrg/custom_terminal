"""Artifact-only governance for bounded post-R10N-I decision preparation."""

import hashlib
import json
import socket
import subprocess
from pathlib import Path

from market_intel.foundation.nse_fno_candidate import LIFECYCLE_STATE, OHLC_SEMANTICS_CONTRACT
import tools.requalify_nse_fno_r10ni as r10ni


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/investigations/post_r10ni_policy/decision_v1'
REPORT = 'reports/NSE_FNO_POST_R10NI_SOURCE_POLICY_DECISION.md'


def load(name):
    return json.loads((PACKAGE / name).read_text(encoding='utf-8'))


def test_decision_has_no_qualification_or_execution_authority():
    decision = load('decision.json')
    assert decision['task_type'] == 'DECISION_PREPARATION_ONLY'
    assert decision['later_execution_authorized'] is False
    assert decision['established']['overall'] == 'MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED'
    assert LIFECYCLE_STATE == 'CANDIDATE_NOT_PRODUCTION_AUTHORIZED'
    assert not any(PACKAGE.glob('*.py'))
    effects = decision['effects']
    assert all(value == 0 or value is False for value in effects.values())
    assert set(decision['authorized_work']) == {
        'READ_EXISTING_TRACKED_SANITIZED_EVIDENCE',
        'PREPARE_DECISION_ARTIFACTS_REPORT_AND_GOVERNANCE_TESTS', 'LOCAL_COMMIT',
    }
    assert {'NETWORK', 'INGESTION', 'RESEARCH', 'FINGERPRINT_REFRESH', 'DELETION',
            'SOURCE_QUALIFICATION', 'PRODUCTION_ACTIVATION', 'REQUALIFICATION'} <= set(decision['prohibited_work'])


def test_blocking_counts_and_all_dates_policy_are_unchanged():
    established = load('decision.json')['established']
    sealed = json.loads((ROOT / 'docs/investigations/r10n_i/requalification_v1/fatal_diagnostic_counts.json').read_text())
    assert established['blocking_codes'] == sealed['dates'][1]['blocking_codes'] == {
        'CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS': 2,
        'TRADE_STATE_ATTRIBUTION_UNAVAILABLE': 1,
    }
    assert OHLC_SEMANTICS_CONTRACT['qualifying_trade_coverage_authoritatively_established'] is False
    assert OHLC_SEMANTICS_CONTRACT['price_mutation_or_imputation'] is False
    assessment = dict(package_integrity='PASS', required_schemas='PASS', identity_join_rate='1',
                      expiry_agreement_rate='1', fatal_count=0, blocking_diagnostic_count=3,
                      price_immutability=True, required_fields_explicit=True)
    assert r10ni.date_acceptance(assessment)['accepted'] is False
    assert 'NO_PARTIAL_SOURCE_QUALIFICATION' in established['all_dates_policy']
    matrix = json.loads((ROOT / 'docs/investigations/r10n_i/requalification_v1/acceptance_matrix_results.json').read_text())
    assert matrix['all_dates_pass'] is False and matrix['partial_source_qualification_produced'] is False


def test_evidence_policy_and_observation_are_not_conflated():
    distinctions = load('decision.json')['distinctions']
    assert {item['classification'] for item in distinctions} == {
        'DOCUMENTED_EXCHANGE_SEMANTICS', 'OBSERVED_SOURCE_VALUES', 'CONSERVATIVE_PROJECT_POLICY'}
    assert 'not proof' in distinctions[2]['limitation']
    assert all(item['limitation'] and item['evidence'] for item in distinctions)
    assert all((ROOT / 'docs/investigations' / path).is_file()
               for item in distinctions for path in item['evidence'])


def test_proposed_work_is_bounded_and_not_authorized():
    investigation = load('investigation_proposal.json')
    assert investigation['status'] == 'PROPOSED_NOT_AUTHORIZED_NOT_EXECUTED'
    limits = investigation['limits']
    assert limits['http_transactions_total_including_redirect_hops'] == 8
    assert limits['retries'] == limits['head_requests'] == limits['report_payloads'] == 0
    assert limits['max_response_bytes'] == 4194304 and limits['max_total_response_bytes'] == 8388608
    assert limits['date_enumeration'] is False and limits['https_only'] is True
    sources = investigation['authoritative_sources_sought']
    historical = json.loads((ROOT / 'docs/investigations/r10n_g/semantics_v1/official_evidence_inventory.json').read_text())
    assert len(sources) == 5 and set(sources) <= {item['url'] for item in historical['sources']}
    assert all(url.startswith('https://') and '/content/fo/' not in url for url in sources)
    assert len(investigation['questions']) == 3 and len(investigation['stopping_conditions']) >= 6
    proposal = load('exception_policy_proposal.json')
    assert proposal['status'] == 'PROPOSED_DESIGN_ONLY_NOT_APPROVED_IMPLEMENTED_OR_APPLIED'
    assert not proposal['implementation_authorized'] and not proposal['requalification_authorized']
    assert proposal['source_qualified'] is False
    assert 'OWNER_APPROVAL_IS_PROJECT_POLICY_PERMISSION_NOT_AUTHORITATIVE_SOURCE_EVIDENCE' in proposal['evidence_requirements']
    assert 'qualification-blocking' in proposal['unresolved_state_handling']
    assert len(proposal['required_tests']) >= 10 and len(proposal['invalidation_conditions']) >= 6


def test_owner_decisions_and_retention_are_independent_pending():
    owner = load('owner_decisions.json')
    evidence = owner['r10ni_evidence_root']
    assert hashlib.sha256((ROOT / evidence['path']).read_bytes()).hexdigest() == evidence['sha256']
    assert len(owner['decisions']) == 4
    assert all(item['answer'] == 'PENDING' for item in owner['decisions'])
    deadlines = {item['date']: item['recorded_deadline'] for item in owner['retention']}
    assert deadlines == {'2026-09-09': 'NO_R10NE_DEADLINE_RECORDED',
                         '2026-09-10': '2026-12-31', '2025-07-08': '2026-12-31'}
    assert owner['deadline_changes'] == owner['deletions'] == 0
    assert 'not deletion authorization' in owner['decisions'][0]['effects']
    assert 'not execution authorization' in owner['decisions'][1]['effects']


def test_artifact_read_has_no_network_adapter_ingestion_or_deletion(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('execution outside decision preparation')
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PACKAGE.glob('*.json')}
    with monkeypatch.context() as patch:
        patch.setattr(socket, 'create_connection', denied)
        patch.setattr(socket.socket, 'connect', denied)
        patch.setattr(r10ni, 'run_requalification', denied)
        patch.setattr(r10ni, 'adapt_package', denied)
        patch.setattr(Path, 'unlink', denied)
        patch.setattr(Path, 'rmdir', denied)
        for path in PACKAGE.glob('*.json'):
            assert isinstance(load(path.name), dict)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PACKAGE.glob('*.json')}
    assert before == after


def test_historical_evidence_contracts_and_tests_remain_baseline_exact():
    bindings = load('historical_bindings.json')
    assert bindings['baseline'] == '76bcbc5780e91bdcfa063960f47ae1f010b18770'
    assert len(bindings['protected']) >= 120
    for item in bindings['protected']:
        actual = subprocess.check_output(['git', 'hash-object', item['path']], cwd=ROOT, text=True).strip()
        assert actual == item['baseline_git_blob'], item['path']
    for path in ROOT.glob('docs/investigations/r10n_*/**/root_manifest.json'):
        for item in json.loads(path.read_text())['artifacts']:
            payload = (path.parent / item['path']).read_bytes()
            assert len(payload) == item['byte_length']
            assert hashlib.sha256(payload).hexdigest() == item['sha256']


def test_sanitized_complete_sha256_package_and_report():
    manifest = load('root_manifest.json')
    expected = sorted([str(path.relative_to(ROOT)).replace('\\', '/')
                       for path in PACKAGE.glob('*.json') if path.name != 'root_manifest.json'] + [REPORT])
    assert manifest['path_base'] == 'REPOSITORY_ROOT'
    assert [item['path'] for item in manifest['artifacts']] == expected
    for item in manifest['artifacts']:
        assert not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts
        payload = (ROOT / item['path']).read_bytes()
        assert len(payload) == item['byte_length']
        assert hashlib.sha256(payload).hexdigest() == item['sha256']
    encoded = '\n'.join(path.read_text() for path in PACKAGE.glob('*.json'))
    encoded += (ROOT / REPORT).read_text()
    for marker in ('c:\\users\\', '/users/', '/home/', 'cookie:', 'authorization:', 'bearer ',
                   'financial_instrument_id_sha256', 'raw_contract_inventory'):
        assert marker not in encoded.lower()
