from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

import pytest

from tools.download_nse_fno_reports import (
    DownloadError,
    build_parser,
    build_plan,
    download_package,
    parse_trade_date,
)


class Response:
    def __init__(self, body: bytes, *, url: str, status: int = 200, content_type: str = "application/octet-stream"):
        self.body = body
        self.url = url
        self.status_code = status
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(body)), "ETag": "public-etag"}
        self.closed = False

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.body), max(1, chunk_size // 2)):
            yield self.body[start:start + max(1, chunk_size // 2)]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_exact_single_date_plan_uses_official_https_urls() -> None:
    plan = build_plan(date(2026, 9, 9), "both")
    assert [item.filename for item in plan] == [
        "BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip",
        "NSE_FO_contract_09092026.csv.gz",
    ]
    assert all(item.url.startswith("https://nsearchives.nseindia.com/content/fo/") for item in plan)
    assert {item.key for item in build_plan(date(2026, 9, 9), "udiff")} == {"udiff"}


def test_parser_has_no_date_range_or_bulk_option() -> None:
    parser = build_parser()
    option_strings = {option for action in parser._actions for option in action.option_strings}
    assert "--date" in option_strings
    assert not {"--from", "--to", "--start-date", "--end-date", "--all"} & option_strings
    with pytest.raises(SystemExit):
        parser.parse_args(["--from", "2026-09-01", "--to", "2026-09-09"])


def test_date_parser_rejects_bad_and_future_dates() -> None:
    with pytest.raises(Exception, match="YYYY-MM-DD"):
        parse_trade_date("09-09-2026")
    future = date.today() + timedelta(days=1)
    with pytest.raises(Exception, match="future"):
        parse_trade_date(future.isoformat())


def test_terms_acknowledgement_is_mandatory_before_network(tmp_path: Path) -> None:
    session = Session([])
    with pytest.raises(PermissionError, match="acknowledge-nse-terms"):
        download_package(
            trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
            acknowledge_nse_terms=False, session=session,
        )
    assert session.calls == []


def test_successful_pair_is_atomic_hashed_and_manifested(tmp_path: Path) -> None:
    plan = build_plan(date(2026, 9, 9), "both")
    zip_body = b"PK\x03\x04synthetic-zip"
    gzip_body = b"\x1f\x8bsynthetic-gzip"
    session = Session([
        Response(zip_body, url=plan[0].url, content_type="application/zip"),
        Response(gzip_body, url=plan[1].url, content_type="application/gzip"),
    ])
    manifest = download_package(
        trading_date=date(2026, 9, 9), report="both", output_root=tmp_path,
        acknowledge_nse_terms=True, session=session,
    )
    package = tmp_path / "2026-09-09"
    assert (package / plan[0].filename).read_bytes() == zip_body
    assert (package / plan[1].filename).read_bytes() == gzip_body
    assert (package / "manifest.json").exists()
    assert [row["sha256"] for row in manifest["files"]] == [
        hashlib.sha256(zip_body).hexdigest(), hashlib.sha256(gzip_body).hexdigest(),
    ]
    assert not list(package.glob("*.part"))
    assert all("Cookie" not in str(row) and "Authorization" not in str(row) for row in manifest["files"])
    assert len(session.calls) == 2


def test_access_control_html_wrong_magic_and_redirects_fail_closed(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    cases = [
        Response(b"<html>CAPTCHA</html>", url=spec.url, content_type="text/html"),
        Response(b"not-a-zip", url=spec.url),
        Response(b"PK\x03\x04data", url="https://example.test/file.zip", content_type="application/zip"),
    ]
    for index, response in enumerate(cases):
        target = tmp_path / str(index)
        with pytest.raises(DownloadError):
            download_package(
                trading_date=date(2026, 9, 9), report="udiff", output_root=target,
                acknowledge_nse_terms=True, session=Session([response]),
            )
        assert not list(target.rglob("*.part"))


def test_oversize_and_existing_package_are_rejected(tmp_path: Path) -> None:
    spec = build_plan(date(2026, 9, 9), "udiff")[0]
    with pytest.raises(DownloadError, match="exceeds"):
        download_package(
            trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path,
            acknowledge_nse_terms=True, max_bytes=3,
            session=Session([Response(b"PK-too-large", url=spec.url)]),
        )
    package = tmp_path / "existing" / "2026-09-09"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="overwrite"):
        download_package(
            trading_date=date(2026, 9, 9), report="udiff", output_root=tmp_path / "existing",
            acknowledge_nse_terms=True, session=Session([]),
        )
