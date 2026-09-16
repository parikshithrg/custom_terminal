"""Bounded documentation-only HTTP review; no market-data or lifecycle adapter.

No CLI entry point: execution requires a caller supplying hash-bound owner
authorization. Failed access stops the entire session, without retries.
"""
from __future__ import annotations

import hashlib
import http.client
import io
import json
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit


PROPOSAL = 'docs/investigations/post_r10ni_policy/decision_v1/investigation_proposal.json'
PROPOSAL_SHA256 = 'a790f565c9641043b8aa3efc6f549859faaa4fe47d546cc2ce518831826ef903'
URLS = (
    'https://www.nseindia.com/static/resources/forms-formats-members',
    'https://nsearchives.nseindia.com/web/sites/default/files/inline-files/UDiFF%20guidance%20document_Ver1.0.pdf',
    'https://nsearchives.nseindia.com/web/mediaattachment/2026-06/Annexure_B_UDiFF_Catalogue_Ver4.0.xlsx_20260630115645.xlsx',
    'https://nsearchives.nseindia.com/web/mediaattachment/2026-06/UDiFF_trade_and_Bhavcopy_file_formats_20260630115803.xlsx',
    'https://www.nseindia.com/static/products-services/equity-derivatives-settlement-price',
)
HOSTS = {'www.nseindia.com', 'nsearchives.nseindia.com'}
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
TYPES = {'text/html', 'application/pdf', XLSX}
DELETED_DATES = ('2026-09-09', '2026-09-10', '2025-07-08')


class ScopeStop(RuntimeError):
    """Only sanitized fixed reason codes are disclosed."""


def transport(url, timeout):
    # Direct TLS: no redirects, proxies, cookies, auth, consent, or retries.
    parsed = urlsplit(url)
    started = time.monotonic()
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=timeout)
    try:
        connection.connect()
        request_socket = connection.sock
        request_socket.settimeout(max(0.001, timeout - (time.monotonic() - started)))
        connection.request('GET', parsed.path, headers={
            'User-Agent': 'custom-terminal-documentation-review/1.0',
            'Accept-Encoding': 'identity',
        })
        request_socket.settimeout(max(0.001, timeout - (time.monotonic() - started)))
        response = connection.getresponse()
    except Exception:
        connection.close()
        raise

    class BoundedResponse:
        status = response.status
        headers = response.headers

        def geturl(self):
            return url

        def read(self, size):
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError('request deadline')
            request_socket.settimeout(remaining)
            return response.read1(size)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            response.close()
            connection.close()

    return BoundedResponse()


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS:
        raise ScopeStop('HTTPS_OR_HOST_VIOLATION')
    if parsed.username or parsed.password or parsed.port not in (None, 443) or url not in URLS:
        raise ScopeStop('EXACT_URL_ALLOWLIST_VIOLATION')


def validate_xlsx(payload):
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if not members or len(members) > 128 or len(names) != len(set(names)):
                raise ScopeStop('XLSX_MEMBER_LIMIT_OR_DUPLICATE')
            declared = sum(item.file_size for item in members)
            if declared > 33554432 or declared > len(payload) * 100:
                raise ScopeStop('XLSX_DECLARED_EXPANSION_LIMIT')
            if '[Content_Types].xml' not in names or 'xl/workbook.xml' not in names:
                raise ScopeStop('NOT_XLSX_WORKBOOK')
            actual = 0
            for member in members:
                path = PurePosixPath(member.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in member.filename
                        or ':' in member.filename or member.flag_bits & 1
                        or (member.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ScopeStop('UNSAFE_XLSX_MEMBER')
                with archive.open(member) as stream:
                    while True:
                        block = stream.read(min(65536, 33554432 - actual + 1))
                        if not block:
                            break
                        actual += len(block)
                        if actual > 33554432 or actual > len(payload) * 100:
                            raise ScopeStop('XLSX_ACTUAL_EXPANSION_LIMIT')
            return {'member_count': len(members), 'declared_expanded_bytes': declared,
                    'actual_expanded_bytes': actual, 'crc_validation': 'PASS'}
    except ScopeStop:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError) as exc:
        raise ScopeStop('CORRUPT_XLSX') from exc


def validate_body(payload, content_type):
    if not payload:
        raise ScopeStop('EMPTY_BODY')
    lowered = payload[:131072].lower()
    if any(marker in lowered for marker in (b'access denied', b'captcha', b'verify you are human',
                                            b'request rejected', b'permission to access', b'login required')):
        raise ScopeStop('ACCESS_CONTROL_BODY')
    if content_type == XLSX:
        return validate_xlsx(payload)
    if content_type == 'application/pdf':
        if not payload.startswith(b'%PDF-') or b'%%EOF' not in payload[-4096:]:
            raise ScopeStop('INVALID_PDF_STRUCTURE')
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(payload), strict=True)
            if reader.is_encrypted or not len(reader.pages):
                raise ScopeStop('ENCRYPTED_OR_EMPTY_PDF')
            return {'pages': len(reader.pages), 'structure': 'PASS'}
        except ScopeStop:
            raise
        except Exception as exc:
            raise ScopeStop('INVALID_PDF_STRUCTURE') from exc
    if b'<html' not in lowered and b'<!doctype html' not in lowered:
        raise ScopeStop('INVALID_HTML_STRUCTURE')
    return {'structure': 'HTML_ENVELOPE_PASS_NOT_YET_SEMANTIC_REVIEWED'}


def verify_gate(root, authorization):
    if not all(authorization.get(key) is True for key in (
            'execution_approved', 'isolated_review_copy_retention_approved', 'owner_reviewed_permission')):
        raise ScopeStop('OWNER_APPROVAL_REQUIRED')
    raw = (root / PROPOSAL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROPOSAL_SHA256 or authorization.get('proposal_sha256') != PROPOSAL_SHA256:
        raise ScopeStop('APPROVED_PROPOSAL_HASH_MISMATCH')
    proposal = json.loads(raw)
    if tuple(proposal['authoritative_sources_sought']) != URLS:
        raise ScopeStop('PROPOSAL_URL_MISMATCH')
    if authorization.get('retention') != 'EARLIER_OF_OWNER_CLOSEOUT_OR_2026_12_31; SEPARATE_EXACT_PATH_DELETION_AUTHORIZATION':
        raise ScopeStop('RETENTION_SCOPE_MISMATCH')
    if any((root / 'artifacts/nse_fno_reports' / day).exists() for day in DELETED_DATES):
        raise ScopeStop('DELETED_PACKAGE_UNEXPECTEDLY_PRESENT')
    return proposal


def fetch_documents(root, authorization, *, send=None, clock=time.monotonic):
    root = Path(root).resolve()
    proposal = verify_gate(root, authorization)  # before staging or transport
    send = send or transport
    review_parent = root / 'artifacts/nse_documentation_reviews'
    if review_parent.is_symlink():
        raise ScopeStop('REVIEW_PARENT_LINK_REFUSED')
    review_parent.mkdir(parents=True, exist_ok=True)
    review_dir = Path(tempfile.mkdtemp(prefix='post_r10ni_', dir=review_parent))
    started = clock()
    result = {'schema_version': 'post_r10ni_request_ledger_v1',
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'proposal_sha256': PROPOSAL_SHA256, 'requests': [], 'documents': [],
              'transactions_attempted': 0, 'total_body_bytes_received': 0,
              'stop_reason': None, 'source_qualified': False,
              'review_directory_relative': review_dir.relative_to(root).as_posix(),
              'review_copies_deleted': 0, 'raw_packages_absent': True}
    try:
        for index, initial in enumerate(URLS):
            url = initial
            hops = 0
            while True:
                validate_url(url)
                if clock() - started >= 1800:
                    raise ScopeStop('SESSION_TIME_LIMIT')
                if result['transactions_attempted'] >= 8:
                    raise ScopeStop('HTTP_TRANSACTION_LIMIT')
                if result['total_body_bytes_received'] >= 8388608:
                    raise ScopeStop('TOTAL_RESPONSE_BYTE_LIMIT')
                result['transactions_attempted'] += 1
                entry = {'number': result['transactions_attempted'], 'initial_url': initial,
                         'url': url, 'method': 'GET', 'redirect_hop': hops,
                         'status': None, 'body_bytes_received': 0, 'outcome': 'REQUEST_ATTEMPTED'}
                result['requests'].append(entry)
                request_started = clock()
                try:
                    response = send(url, timeout=min(10, 1800 - (clock() - started)))
                except (URLError, TimeoutError, OSError) as exc:
                    entry['outcome'] = 'TRANSPORT_FAILURE_NO_RETRY'
                    raise ScopeStop('TRANSPORT_FAILURE_NO_RETRY') from exc
                with response:
                    validate_url(response.geturl())
                    if response.geturl() != url:
                        raise ScopeStop('UNLEDGERED_REDIRECT')
                    status = entry['status'] = response.status
                    if status in (301, 302, 303, 307, 308):
                        entry['outcome'] = 'REDIRECT_BODY_NOT_READ'
                        if hops >= 2:
                            raise ScopeStop('REDIRECT_HOP_LIMIT')
                        location = response.headers.get('Location')
                        if not location:
                            raise ScopeStop('REDIRECT_WITHOUT_LOCATION')
                        url = urljoin(url, location)
                        validate_url(url)  # destination before another request
                        hops += 1
                        continue
                    if status in (401, 403, 429):
                        raise ScopeStop('ACCESS_CONTROL_HTTP_STATUS')
                    if status != 200:
                        raise ScopeStop('UNEXPECTED_HTTP_STATUS')
                    content_type = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
                    entry['content_type'] = content_type if content_type in TYPES else 'UNEXPECTED'
                    if content_type not in TYPES:
                        raise ScopeStop('UNEXPECTED_CONTENT_TYPE')
                    expected_type = XLSX if url.endswith('.xlsx') else ('application/pdf' if url.endswith('.pdf') else 'text/html')
                    if content_type != expected_type:
                        raise ScopeStop('DOCUMENT_FORMAT_CONTENT_TYPE_MISMATCH')
                    if response.headers.get('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                        raise ScopeStop('UNEXPECTED_HTTP_CONTENT_ENCODING')
                    cap = min(4194304, 8388608 - result['total_body_bytes_received'])
                    if cap <= 0:
                        raise ScopeStop('TOTAL_RESPONSE_BYTE_LIMIT')
                    length = response.headers.get('Content-Length')
                    if length is not None:
                        if not length.isascii() or not length.isdigit():
                            raise ScopeStop('INVALID_CONTENT_LENGTH')
                        length = int(length)
                        if length > cap:
                            raise ScopeStop('DECLARED_RESPONSE_BYTE_LIMIT')
                    body = bytearray()
                    while True:
                        if clock() - request_started >= 10 or clock() - started >= 1800:
                            raise ScopeStop('REQUEST_OR_SESSION_TIME_LIMIT')
                        remaining = cap - len(body)
                        if remaining <= 0:
                            if length == len(body):
                                break
                            raise ScopeStop('RESPONSE_LIMIT_EOF_UNPROVEN')
                        block = response.read(min(65536, remaining))
                        if not block:
                            break
                        body.extend(block)
                        entry['body_bytes_received'] += len(block)
                        result['total_body_bytes_received'] += len(block)
                    if length is not None and length != len(body):
                        raise ScopeStop('TRUNCATED_OR_LENGTH_MISMATCH')
                    structure = validate_body(bytes(body), content_type)
                    suffix = {XLSX: '.xlsx', 'application/pdf': '.pdf', 'text/html': '.html'}[content_type]
                    document_path = review_dir / (f'document_{index + 1}' + suffix)
                    with document_path.open('xb') as output:
                        output.write(body)
                    result['documents'].append({'url': url, 'initial_url': initial,
                        'review_copy_relative_path': document_path.relative_to(root).as_posix(),
                        'byte_length': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                        'content_type': content_type, 'structure': structure})
                    entry['outcome'] = 'VALIDATED_ISOLATED_REVIEW_COPY_RETAINED'
                break
        result['stop_reason'] = 'FIXED_URL_SET_COMPLETE_PENDING_SEMANTIC_REVIEW'
    except ScopeStop as exc:
        result['stop_reason'] = str(exc)
        if result['requests'] and result['requests'][-1]['outcome'] == 'REQUEST_ATTEMPTED':
            result['requests'][-1]['outcome'] = str(exc)
    except Exception:
        # Never disclose exception bodies/URLs/credentials/private paths.
        result['stop_reason'] = 'UNEXPECTED_LOCAL_OR_RESPONSE_FAILURE_NO_RETRY'
    result['unattempted_initial_urls'] = [url for url in URLS if url not in {
        entry['initial_url'] for entry in result['requests']}]
    result['elapsed_seconds'] = round(clock() - started, 3)
    return result
