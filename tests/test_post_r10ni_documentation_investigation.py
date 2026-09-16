"""Offline enforcement of the owner's fixed documentation-only scope."""
import io
import hashlib
import json
import zipfile
from pathlib import Path

import pytest
import support_nse_documentation_scope as investigation

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/investigations/post_r10ni_policy/investigation_v1'


@pytest.fixture
def authorized(tmp_path):
    proposal = tmp_path / investigation.PROPOSAL
    proposal.parent.mkdir(parents=True)
    proposal.write_bytes((ROOT / investigation.PROPOSAL).read_bytes())
    auth = json.loads((EVIDENCE / 'owner_authorization.json').read_text())
    return tmp_path, auth


class Response(io.BytesIO):
    def __init__(self, url, body=b'<html>Documentation</html>', status=200, headers=None):
        super().__init__(body)
        self.url, self.status = url, status
        self.headers = headers or {'Content-Type': 'text/html', 'Content-Length': str(len(body))}

    def geturl(self):
        return self.url


@pytest.mark.parametrize('gate', ['execution_approved', 'isolated_review_copy_retention_approved', 'owner_reviewed_permission'])
def test_approval_is_required_before_network_or_staging(authorized, gate):
    root, auth = authorized
    auth[gate] = False
    with pytest.raises(investigation.ScopeStop, match='OWNER_APPROVAL_REQUIRED'):
        investigation.fetch_documents(root, auth, send=lambda *a, **k: pytest.fail('network'))
    assert not (root / 'artifacts').exists()


def test_approved_hash_retention_and_deleted_package_gates(authorized):
    root, auth = authorized
    altered = dict(auth, proposal_sha256='0' * 64)
    with pytest.raises(investigation.ScopeStop, match='HASH_MISMATCH'):
        investigation.verify_gate(root, altered)
    with pytest.raises(investigation.ScopeStop, match='RETENTION_SCOPE_MISMATCH'):
        investigation.verify_gate(root, dict(auth, retention='indefinite'))
    path = root / 'artifacts/nse_fno_reports/2026-09-09'
    path.mkdir(parents=True)
    with pytest.raises(investigation.ScopeStop, match='DELETED_PACKAGE_UNEXPECTEDLY_PRESENT'):
        investigation.verify_gate(root, auth)


@pytest.mark.parametrize('url', ['http://www.nseindia.com/static/resources/forms-formats-members',
    'https://example.com/', 'https://www.nseindia.com/new-document',
    'https://nsearchives.nseindia.com/content/fo/report.zip', investigation.URLS[0] + '?new=1'])
def test_only_exact_https_document_urls_allowed(url):
    with pytest.raises(investigation.ScopeStop):
        investigation.validate_url(url)


@pytest.mark.parametrize('destination', ['http://www.nseindia.com/', 'https://example.com/',
                                        'https://www.nseindia.com/new-document'])
def test_unsafe_redirect_stops_before_next_request(authorized, destination):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda url, **k:
        Response(url, status=302, headers={'Location': destination}))
    assert result['transactions_attempted'] == 1
    assert result['total_body_bytes_received'] == 0 and not result['documents']


def test_redirect_limit_includes_every_hop(authorized):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda url, **k:
        Response(url, status=302, headers={'Location': investigation.URLS[0]}))
    assert result['stop_reason'] == 'REDIRECT_HOP_LIMIT'
    assert result['transactions_attempted'] == 3


@pytest.mark.parametrize('status', [401, 403, 429, 404])
def test_http_failure_stops_without_retry_or_body_retention(authorized, status):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda url, **k: Response(url, status=status))
    assert result['transactions_attempted'] == 1 and not result['documents']
    assert result['total_body_bytes_received'] == 0


@pytest.mark.parametrize('headers,body,reason', [
    ({'Content-Type':'text/plain'}, b'doc', 'UNEXPECTED_CONTENT_TYPE'),
    ({'Content-Type':'text/html','Content-Length':'4194305'}, b'', 'DECLARED_RESPONSE_BYTE_LIMIT'),
    ({'Content-Type':'text/html','Content-Length':'99'}, b'<html>doc</html>', 'TRUNCATED_OR_LENGTH_MISMATCH'),
    ({'Content-Type':'text/html'}, b'', 'EMPTY_BODY'),
    ({'Content-Type':'text/html'}, b'<html>Access denied</html>', 'ACCESS_CONTROL_BODY'),
    ({'Content-Type':'text/html','Content-Encoding':'gzip'}, b'', 'UNEXPECTED_HTTP_CONTENT_ENCODING'),
])
def test_content_and_response_limits(authorized, headers, body, reason):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda url, **k: Response(url, body, headers=headers))
    assert result['stop_reason'] == reason and not result['documents']


def xlsx(extra=()):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('xl/workbook.xml', '<workbook/>')
        for name, body in extra:
            archive.writestr(name, body)
    return stream.getvalue()


def test_xlsx_validation_no_extraction_and_bounded_bombs():
    assert investigation.validate_xlsx(xlsx())['crc_validation'] == 'PASS'
    for payload in (b'PKbad', xlsx([('../unsafe', 'x')]), xlsx([('bomb', 'x' * 100000)]),
                    xlsx([(str(i), 'x') for i in range(127)])):
        with pytest.raises(investigation.ScopeStop):
            investigation.validate_xlsx(payload)


def test_request_and_session_timeouts_are_sanitized(authorized):
    root, auth = authorized
    def timeout(url, **kwargs):
        raise TimeoutError('sensitive local error')
    result = investigation.fetch_documents(root, auth, send=timeout)
    assert result['stop_reason'] == 'TRANSPORT_FAILURE_NO_RETRY'
    assert result['transactions_attempted'] == 1 and 'sensitive' not in json.dumps(result)
    times = iter([0, 1800, 1800])
    result = investigation.fetch_documents(root, auth, send=timeout, clock=lambda: next(times))
    assert result['stop_reason'] == 'SESSION_TIME_LIMIT' and result['transactions_attempted'] == 0


def test_unresolved_cannot_qualify_or_reacquire(authorized):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda url, **k: Response(url, status=403))
    assert result['source_qualified'] is False and result['raw_packages_absent'] is True
    assert result['review_copies_deleted'] == 0
    assert all(not (root / 'artifacts/nse_fno_reports' / day).exists() for day in investigation.DELETED_DATES)


def test_eight_transactions_includes_successful_redirect_chains(authorized, monkeypatch):
    root, auth = authorized
    monkeypatch.setattr(investigation, 'validate_body', lambda *a: {})
    counts = {}
    def send(url, **kwargs):
        counts[url] = counts.get(url, 0) + 1
        if counts[url] <= 2:
            return Response(url, status=302, headers={'Location': url})
        kind = investigation.XLSX if url.endswith('.xlsx') else ('application/pdf' if url.endswith('.pdf') else 'text/html')
        return Response(url, b'doc', headers={'Content-Type':kind, 'Content-Length':'3'})
    result = investigation.fetch_documents(root, auth, send=send)
    assert result['stop_reason'] == 'HTTP_TRANSACTION_LIMIT'
    assert result['transactions_attempted'] == len(result['requests']) == 8
    assert len(result['documents']) == 2 and not result['source_qualified']


def test_total_eight_mib_and_unknown_length_cap_do_not_overread(authorized, monkeypatch):
    root, auth = authorized
    monkeypatch.setattr(investigation, 'validate_body', lambda *a: {})
    def send(url, **kwargs):
        kind = investigation.XLSX if url.endswith('.xlsx') else ('application/pdf' if url.endswith('.pdf') else 'text/html')
        return Response(url, b'x' * 4194304, headers={'Content-Type':kind, 'Content-Length':'4194304'})
    result = investigation.fetch_documents(root, auth, send=send)
    assert result['stop_reason'] == 'TOTAL_RESPONSE_BYTE_LIMIT'
    assert result['total_body_bytes_received'] == 8388608
    assert result['transactions_attempted'] == 2
    response = Response(investigation.URLS[0], b'x' * 4194305, headers={'Content-Type':'text/html'})
    result = investigation.fetch_documents(root, auth, send=lambda *a, **k: response)
    assert result['stop_reason'] == 'RESPONSE_LIMIT_EOF_UNPROVEN'
    assert result['total_body_bytes_received'] == 4194304 and response.closed


def test_final_url_and_expected_document_type_are_verified(authorized):
    root, auth = authorized
    result = investigation.fetch_documents(root, auth, send=lambda *a, **k: Response('https://example.com/'))
    assert result['stop_reason'] == 'HTTPS_OR_HOST_VIOLATION'
    result = investigation.fetch_documents(root, auth, send=lambda url, **k:
        Response(url, headers={'Content-Type': 'application/pdf'}))
    assert result['stop_reason'] == 'DOCUMENT_FORMAT_CONTENT_TYPE_MISMATCH'


def test_recorded_closeout_budget_provenance_and_unresolved_state():
    ledger = json.loads((EVIDENCE / 'request_ledger.json').read_text())
    assert ledger['transactions_attempted'] == len(ledger['requests']) == 5
    assert sum(item['body_bytes_received'] for item in ledger['requests']) == ledger['total_body_bytes_received'] == 961466
    assert [item['url'] for item in ledger['requests']] == list(investigation.URLS)
    assert all(item['method'] == 'GET' and item['status'] == 200 and item['redirect_hop'] == 0 for item in ledger['requests'])
    assert len(ledger['documents']) == 5 and ledger['source_qualified'] is False
    inventory = json.loads((EVIDENCE / 'document_inventory.json').read_text())
    assert [item['sha256'] for item in inventory['sources']] == [item['sha256'] for item in ledger['documents']]
    for source in inventory['sources']:
        assert source['publisher'] and source['title'] and source['relevant_sections']
        assert source['effective_date'].startswith('NOT_ESTABLISHED')
    matrix = json.loads((EVIDENCE / 'question_results.json').read_text())
    assert len(matrix['questions']) == 3 and matrix['all_questions_resolved'] is False
    assert all(item['missing'] for item in matrix['questions'])
    applicability = json.loads((EVIDENCE / 'applicability_assessment.json').read_text())
    assert applicability['exception_validity_proven'] is False
    assert applicability['raw_package_status'].startswith('ALL_THREE_DELETED')
    lifecycle = json.loads((EVIDENCE / 'lifecycle_and_next_step.json').read_text())
    assert lifecycle['source_qualified'] is False and lifecycle['production_activated'] is False
    assert lifecycle['blocking_codes'] == {'CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS': 2, 'TRADE_STATE_ATTRIBUTION_UNAVAILABLE': 1}
    assert lifecycle['partial_source_qualification_permitted'] is False
    for key in ('adapter_or_diagnostic_changes', 'diagnostic_waivers', 'price_mutation', 'trade_states_inferred',
                'raw_package_reacquisition', 'requalification', 'ingestion', 'research', 'fingerprint_refreshed', 'deletion'):
        assert lifecycle[key] is False


def test_review_copy_retention_is_not_new_deletion_authority():
    retention = json.loads((EVIDENCE / 'review_copy_retention.json').read_text())
    assert retention['retained_copies'] == 5 and retention['full_documents_tracked_in_git'] == 0
    assert retention['owner_closeout_confirmation'] == 'PENDING' and retention['deadline'] == '2026-12-31'
    assert retention['review_copies_deleted'] == 0
    assert all(not (ROOT / 'artifacts/nse_fno_reports' / day).exists() for day in investigation.DELETED_DATES)


def test_investigation_json_report_and_test_support_are_sanitized_hash_bound():
    manifest = json.loads((EVIDENCE / 'root_manifest.json').read_text())
    expected = sorted([path.relative_to(ROOT).as_posix() for path in EVIDENCE.glob('*.json') if path.name != 'root_manifest.json'] + [
        'reports/NSE_FNO_POST_R10NI_INVESTIGATION_CLOSEOUT.md',
        'tests/support_nse_documentation_scope.py', 'tests/test_post_r10ni_documentation_investigation.py'])
    assert [item['path'] for item in manifest['artifacts']] == expected
    for item in manifest['artifacts']:
        assert not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts
        payload = (ROOT / item['path']).read_bytes()
        assert len(payload) == item['byte_length'] and hashlib.sha256(payload).hexdigest() == item['sha256']
    text = '\n'.join(path.read_text(encoding='utf-8') for path in EVIDENCE.glob('*.json')).lower()
    for marker in ('c:\\users\\', '/home/', '/users/', 'cookie:', 'authorization:', 'bearer ',
                   'financial_instrument_id_sha256', 'raw_contract_inventory'):
        assert marker not in text
