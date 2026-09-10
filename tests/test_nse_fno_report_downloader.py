from __future__ import annotations

import gzip
import hashlib
import io
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest

import tools.download_nse_fno_reports as downloader
from tools.download_nse_fno_reports import (
    ArchiveLimits,
    DownloadError,
    ReportSpec,
    build_parser,
    build_plan,
    download_package,
    main,
    parse_trade_date,
)


def zip_bytes(files: dict[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in (files or {"BhavCopy.csv": b"TradDt,TckrSymb\n2026-09-09,NIFTY\n"}).items():
            archive.writestr(name, body)
    return output.getvalue()


def gzip_bytes(body: bytes = b"FinInstrmId,TckrSymb\n1,NIFTY\n") -> bytes:
    return gzip.compress(body, mtime=0)


class Response:
    def __init__(self, body: bytes, *, url: str, status: int = 200,
                 content_type: str = "application/octet-stream", headers: dict | None = None,
                 history: list | None = None, declared_length: int | None = None):
        self.body = body
        self.url = url
        self.status_code = status
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body) if declared_length is None else declared_length),
            "ETag": "public-etag",
            **(headers or {}),
        }
        self.history = history or []
        self.closed = False

    def iter_content(self, chunk_size: int):
        step = max(1, chunk_size // 2)
        for start in range(0, len(self.body), step):
            yield self.body[start:start + step]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def pair_responses() -> list[Response]:
    plan = build_plan(date(2026, 9, 9), "both")
    return [
        Response(zip_bytes(), url=plan[0].url, content_type="application/zip"),
        Response(gzip_bytes(), url=plan[1].url, content_type="application/gzip"),
    ]


def assert_no_package_or_stage(root: Path) -> None:
    assert not (root / "2026-09-09").exists()
    assert not list(root.glob(".2026-09-09.staging-*"))


def test_exact_single_date_plan_uses_official_https_urls() -> None:
    plan = build_plan(date(2026, 9, 9), "both")
    assert [item.filename for item in plan] == [
        "BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip",
        "NSE_FO_contract_09092026.csv.gz",
    ]
    assert all(item.url.startswith("https://nsearchives.nseindia.com/content/fo/") for item in plan)


def test_parser_has_no_date_range_retry_or_bulk_option() -> None:
    parser = build_parser()
    option_strings = {option for action in parser._actions for option in action.option_strings}
    assert "--date" in option_strings
    assert not {"--from", "--to", "--start-date", "--end-date", "--all", "--retry"} & option_strings
    with pytest.raises(SystemExit):
        parser.parse_args(["--from", "2026-09-01", "--to", "2026-09-09"])


def test_date_parser_rejects_bad_and_future_dates() -> None:
    with pytest.raises(Exception, match="YYYY-MM-DD"):
        parse_trade_date("09-09-2026")
    with pytest.raises(Exception, match="future"):
        parse_trade_date((date.today() + timedelta(days=1)).isoformat())


def test_acknowledgement_is_mandatory_before_request_or_staging(tmp_path: Path) -> None:
    session = Session([])
    with pytest.raises(PermissionError, match="acknowledge-nse-terms"):
        download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                         acknowledge_nse_terms=False, session=session)
    assert session.calls == []
    assert list(tmp_path.iterdir()) == []


def test_dry_run_performs_zero_network_calls_and_retains_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    def forbidden_session():
        raise AssertionError("dry-run attempted to create a network session")

    monkeypatch.setattr(downloader.requests, "Session", forbidden_session)
    assert main(["--date", "2026-09-09", "--report", "both", "--dry-run",
                 "--output-root", str(tmp_path)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["network_requests"] == 0 and plan["payloads_retained"] == 0
    assert plan["downloaded"] is False
    assert list(tmp_path.iterdir()) == []


def test_successful_pair_is_transactional_validated_hashed_and_manifested(tmp_path: Path) -> None:
    responses = pair_responses()
    bodies = [response.body for response in responses]
    manifest = download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                                acknowledge_nse_terms=True, session=Session(responses))
    package = tmp_path / "2026-09-09"
    plan = build_plan(date(2026, 9, 9), "both")
    assert sorted(path.name for path in package.iterdir()) == sorted(
        [plan[0].filename, plan[1].filename, "manifest.json"]
    )
    assert [row["sha256"] for row in manifest["files"]] == [hashlib.sha256(body).hexdigest() for body in bodies]
    assert [row["archive_validation"]["member_count"] for row in manifest["files"]] == [1, 1]
    assert manifest["acquisition_mode"] == "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION"
    assert not list(tmp_path.glob(".*.staging-*"))


@pytest.mark.parametrize("failure_index", [0, 1])
def test_first_or_second_file_failure_leaves_no_final_package(tmp_path: Path, failure_index: int) -> None:
    responses = pair_responses()
    responses[failure_index] = Response(b"failure", url=build_plan(date(2026, 9, 9))[failure_index].url,
                                        status=500)
    with pytest.raises(DownloadError):
        download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session(responses))
    assert_no_package_or_stage(tmp_path)


def test_manifest_failure_cleans_only_unique_stage(tmp_path: Path, monkeypatch) -> None:
    sibling = tmp_path / ".2026-09-09.staging-do-not-touch"
    sibling.mkdir()
    marker = sibling / "owner.txt"
    marker.write_text("preserve", encoding="utf-8")

    def fail_manifest(path, manifest):
        raise OSError("simulated manifest failure")

    monkeypatch.setattr(downloader, "_write_manifest", fail_manifest)
    with pytest.raises(OSError, match="manifest"):
        download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session(pair_responses()))
    assert not (tmp_path / "2026-09-09").exists()
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert list(tmp_path.iterdir()) == [sibling]


def test_publication_failure_leaves_no_final_package_or_stage(tmp_path: Path, monkeypatch) -> None:
    def fail_publish(stage, final):
        raise OSError("simulated publication failure")

    monkeypatch.setattr(downloader, "_publish_staged_package", fail_publish)
    with pytest.raises(OSError, match="publication"):
        download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session(pair_responses()))
    assert_no_package_or_stage(tmp_path)


def test_existing_package_is_never_overwritten_and_no_request_occurs(tmp_path: Path) -> None:
    package = tmp_path / "2026-09-09"
    package.mkdir()
    marker = package / "owner.txt"
    marker.write_text("preserve", encoding="utf-8")
    session = Session([])
    with pytest.raises(FileExistsError, match="overwrite"):
        download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=session)
    assert marker.read_text(encoding="utf-8") == "preserve" and session.calls == []


def test_internal_session_is_closed_but_injected_session_remains_caller_owned(tmp_path: Path, monkeypatch) -> None:
    internal = Session(pair_responses())
    monkeypatch.setattr(downloader.requests, "Session", lambda: internal)
    download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path / "internal",
                     acknowledge_nse_terms=True)
    assert internal.closed

    injected = Session(pair_responses())
    download_package(trading_date=date(2026, 9, 9), report="both", output_root=tmp_path / "injected",
                     acknowledge_nse_terms=True, session=injected)
    assert not injected.closed


@pytest.mark.parametrize("location", ["http://nsearchives.nseindia.com/file.zip", "https://example.test/file.zip"])
def test_redirect_hop_rejects_downgrade_and_off_domain(tmp_path: Path, location: str) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    hop = Response(b"", url=spec.url, status=302, headers={"Location": location})
    final = Response(zip_bytes(), url=location, content_type="application/zip", history=[hop])
    with pytest.raises(DownloadError, match="allowlisted"):
        download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session([final]))
    assert_no_package_or_stage(tmp_path)


def test_valid_same_domain_redirect_chain_is_accepted(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    redirected = spec.url.replace("nsearchives", "archives")
    hop = Response(b"", url=spec.url, status=302, headers={"Location": redirected})
    final = Response(zip_bytes(), url=redirected, content_type="application/zip", history=[hop])
    download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                     acknowledge_nse_terms=True, session=Session([final]))
    assert (tmp_path / "2026-09-09" / spec.filename).exists()


def test_initial_url_and_redirect_source_are_independently_validated(tmp_path: Path) -> None:
    good = build_plan(date(2026, 9, 9), "udiff")[0]
    bad_initial = ReportSpec(good.key, good.role, good.filename,
                             "http://nsearchives.nseindia.com/file.zip",
                             good.compression, good.accepted_content_types)
    with pytest.raises(DownloadError, match="allowlisted"):
        downloader._download_one(Session([]), bad_initial, tmp_path / "never.zip",
                                 max_bytes=1000, archive_limits=ArchiveLimits())

    hop = Response(b"", url="https://example.test/source.zip", status=302,
                   headers={"Location": good.url})
    final = Response(zip_bytes(), url=good.url, content_type="application/zip", history=[hop])
    with pytest.raises(DownloadError, match="allowlisted"):
        download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session([final]))
    assert_no_package_or_stage(tmp_path)


@pytest.mark.parametrize("response, match", [
    (Response(b"", url=build_plan(date(2026, 9, 9), "udiff")[0].url), "empty"),
    (Response(zip_bytes(), url=build_plan(date(2026, 9, 9), "udiff")[0].url, declared_length=9999), "truncated"),
    (Response(b"<html>captcha</html>", url=build_plan(date(2026, 9, 9), "udiff")[0].url,
              content_type="application/octet-stream"), "access-control"),
    (Response(zip_bytes(), url=build_plan(date(2026, 9, 9), "udiff")[0].url,
              content_type="text/html"), "Content-Type"),
])
def test_empty_truncated_access_control_and_content_type_fail_closed(tmp_path: Path, response: Response, match: str) -> None:
    with pytest.raises(DownloadError, match=match):
        download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session([response]))
    assert_no_package_or_stage(tmp_path)


def test_download_size_limit_is_enforced(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    with pytest.raises(DownloadError, match="exceeds"):
        download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                         acknowledge_nse_terms=True, max_bytes=3,
                         session=Session([Response(zip_bytes(), url=spec.url)]))
    assert_no_package_or_stage(tmp_path)


@pytest.mark.parametrize("report, body", [
    ("udiff", b"PK\x03\x04not-a-valid-zip"),
    ("mii", b"\x1f\x8b\x08corrupt-gzip"),
])
def test_corrupt_archives_are_rejected(tmp_path: Path, report: str, body: bytes) -> None:
    spec = build_plan(date(2026, 9, 9), report)[0]
    with pytest.raises(DownloadError, match="corrupt|invalid|reserved"):
        download_package(trading_date=date(2026, 9, 9), report=report, output_root=tmp_path,
                         acknowledge_nse_terms=True, session=Session([Response(body, url=spec.url)]))
    assert_no_package_or_stage(tmp_path)


def test_unsafe_zip_member_and_excessive_member_count_are_rejected(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    for index, (body, limits) in enumerate([
        (zip_bytes({"../escape.csv": b"x"}), ArchiveLimits()),
        (zip_bytes({"one.csv": b"1", "two.csv": b"2"}), ArchiveLimits(max_members=1)),
    ]):
        root = tmp_path / str(index)
        with pytest.raises(DownloadError, match="unsafe|member count"):
            download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=root,
                             acknowledge_nse_terms=True, archive_limits=limits,
                             session=Session([Response(body, url=spec.url)]))
        assert_no_package_or_stage(root)


@pytest.mark.parametrize("report, body", [
    ("udiff", zip_bytes({"large.csv": b"A" * 10_000})),
    ("mii", gzip_bytes(b"A" * 10_000)),
])
def test_compressed_expansion_limits_reject_bombs(tmp_path: Path, report: str, body: bytes) -> None:
    spec = build_plan(date(2026, 9, 9), report)[0]
    with pytest.raises(DownloadError, match="expanded|expansion"):
        download_package(trading_date=date(2026, 9, 9), report=report, output_root=tmp_path,
                         acknowledge_nse_terms=True,
                         archive_limits=ArchiveLimits(max_expanded_bytes=1000, max_expansion_ratio=5),
                         session=Session([Response(body, url=spec.url)]))
    assert_no_package_or_stage(tmp_path)


def test_manifest_is_sanitized_and_contains_no_body_or_private_path(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    secret = "should-not-appear"
    private_path = "C:" + chr(92) + "Users" + chr(92) + "private" + chr(92) + "report.zip"
    response = Response(zip_bytes(), url=spec.url, content_type="application/zip", headers={
        "Cookie": f"session={secret}", "Authorization": f"Bearer {secret}",
        "X-Private-Path": private_path, "X-Body": secret,
    })
    download_package(trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
                     acknowledge_nse_terms=True, session=Session([response]))
    text = (tmp_path / "2026-09-09" / "manifest.json").read_text(encoding="utf-8")
    lowered = text.lower()
    assert secret not in text and "authorization" not in lowered and "cookie" not in lowered
    assert private_path.lower() not in lowered
    assert response.body.hex() not in text
