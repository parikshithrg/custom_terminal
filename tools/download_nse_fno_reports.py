"""Safely download one explicitly selected NSE F&O daily-report package."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
import zlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable
from urllib.parse import urljoin, urlparse

import requests


LANDING_URL = "https://www.nseindia.com/all-reports-derivatives"
TERMS_URL = "https://www.nseindia.com/static/nse-terms-of-use"
COPYRIGHT_URL = "https://www.nseindia.com/static/nse-copyright"
DATA_POLICY_URL = "https://www.nseindia.com/static/market-data/nse-data-policy"
FORMAT_URL = "https://www.nseindia.com/static/resources/forms-formats-members"
ARCHIVE_ROOT = "https://nsearchives.nseindia.com/content/fo"
ALLOWED_HOSTS = {"www.nseindia.com", "nsearchives.nseindia.com", "archives.nseindia.com"}
USER_AGENT = "custom-terminal-nse-fno-downloader/1.1 (single-date official-data utility)"
DEFAULT_MAX_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_ARCHIVE_MEMBERS = 8
DEFAULT_MAX_EXPANSION_RATIO = 250.0
MAX_REDIRECT_HOPS = 5
CHUNK_BYTES = 128 * 1024
_ACCESS_CONTROL_MARKERS = (
    b"captcha", b"access denied", b"enable javascript",
    b"request blocked", b"too many requests",
)


class DownloadError(RuntimeError):
    """A report could not be safely retained."""


@dataclass(frozen=True)
class ReportSpec:
    key: str
    role: str
    filename: str
    url: str
    compression: str
    accepted_content_types: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveLimits:
    max_members: int = DEFAULT_MAX_ARCHIVE_MEMBERS
    max_expanded_bytes: int = DEFAULT_MAX_EXPANDED_BYTES
    max_expansion_ratio: float = DEFAULT_MAX_EXPANSION_RATIO

    def validate(self) -> None:
        if self.max_members <= 0:
            raise ValueError("max_members must be positive")
        if self.max_expanded_bytes <= 0:
            raise ValueError("max_expanded_bytes must be positive")
        if self.max_expansion_ratio <= 0:
            raise ValueError("max_expansion_ratio must be positive")


def parse_trade_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc
    if parsed > date.today():
        raise argparse.ArgumentTypeError("future dates are not allowed")
    return parsed


def build_plan(trading_date: date, report: str = "both") -> tuple[ReportSpec, ...]:
    yyyymmdd = trading_date.strftime("%Y%m%d")
    ddmmyyyy = trading_date.strftime("%d%m%Y")
    facts_name = f"BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip"
    contract_name = f"NSE_FO_contract_{ddmmyyyy}.csv.gz"
    available = {
        "udiff": ReportSpec(
            "udiff", "DAILY_DERIVATIVES_FACTS", facts_name,
            f"{ARCHIVE_ROOT}/{facts_name}", "zip",
            ("application/zip", "application/x-zip-compressed", "application/octet-stream"),
        ),
        "mii": ReportSpec(
            "mii", "CONTRACT_IDENTITY", contract_name,
            f"{ARCHIVE_ROOT}/{contract_name}", "gzip",
            ("application/gzip", "application/x-gzip", "application/octet-stream"),
        ),
    }
    if report == "both":
        return available["udiff"], available["mii"]
    try:
        return (available[report],)
    except KeyError as exc:
        raise ValueError("report must be one of: udiff, mii, both") from exc


def _validate_https_url(url: str) -> None:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise DownloadError("malformed download URL") from exc
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() not in ALLOWED_HOSTS
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise DownloadError(f"non-allowlisted download URL: {url}")


def _validate_redirect_chain(response, initial_url: str) -> str:
    """Validate the source and destination of every followed redirect."""
    _validate_https_url(initial_url)
    history = list(getattr(response, "history", ()) or ())
    if len(history) > MAX_REDIRECT_HOPS:
        raise DownloadError(f"redirect chain exceeds {MAX_REDIRECT_HOPS} hops")
    current = initial_url
    for hop in history:
        hop_url = getattr(hop, "url", None) or current
        _validate_https_url(hop_url)
        location = getattr(hop, "headers", {}).get("Location")
        if not location:
            raise DownloadError("redirect response omitted Location")
        current = urljoin(hop_url, location)
        _validate_https_url(current)
    final_url = getattr(response, "url", None) or current
    _validate_https_url(final_url)
    return final_url


def _stream_response(response, destination: BinaryIO, *, max_bytes: int) -> tuple[int, str, bytes]:
    declared = response.headers.get("Content-Length")
    declared_size: int | None = None
    if declared:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise DownloadError("invalid Content-Length") from exc
        if declared_size < 0:
            raise DownloadError("negative Content-Length")
        if declared_size > max_bytes:
            raise DownloadError(f"declared response exceeds {max_bytes} bytes")

    digest = hashlib.sha256()
    size = 0
    prefix = b""
    for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
        if not chunk:
            continue
        size += len(chunk)
        if size > max_bytes:
            raise DownloadError(f"streamed response exceeds {max_bytes} bytes")
        if len(prefix) < 4096:
            prefix = (prefix + chunk)[:4096]
        digest.update(chunk)
        destination.write(chunk)
    if declared_size is not None and size != declared_size:
        raise DownloadError(f"truncated response: expected {declared_size} bytes, received {size}")
    if size == 0:
        raise DownloadError("empty response")
    return size, digest.hexdigest(), prefix


def _validate_member_path(name: str) -> None:
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        raise DownloadError("archive contains an unsafe member path")
    path = PurePosixPath(name)
    if ".." in path.parts or (path.parts and re.match(r"^[A-Za-z]:", path.parts[0])):
        raise DownloadError("archive contains an unsafe member path")


def _check_expansion(expanded: int, compressed: int, limits: ArchiveLimits) -> None:
    if expanded > limits.max_expanded_bytes:
        raise DownloadError("archive declared or produced excessive expanded data")
    if expanded > max(1, compressed) * limits.max_expansion_ratio:
        raise DownloadError("archive expansion ratio exceeds the configured limit")


def _validate_zip(path: Path, limits: ArchiveLimits) -> dict:
    compressed_total = declared_total = actual_total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > limits.max_members:
                raise DownloadError("ZIP member count is empty or excessive")
            files = [member for member in members if not member.is_dir()]
            if not files:
                raise DownloadError("ZIP contains no files")
            for member in members:
                _validate_member_path(member.filename)
                if member.flag_bits & 0x1:
                    raise DownloadError("encrypted ZIP members are not accepted")
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise DownloadError("ZIP symbolic-link members are not accepted")
                compressed_total += member.compress_size
                declared_total += member.file_size
                _check_expansion(declared_total, compressed_total, limits)
            for member in files:
                member_size = 0
                with archive.open(member, "r") as source:
                    while True:
                        chunk = source.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        member_size += len(chunk)
                        actual_total += len(chunk)
                        _check_expansion(actual_total, compressed_total, limits)
                if member_size != member.file_size:
                    raise DownloadError("ZIP member length differs from its declaration")
    except DownloadError:
        raise
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise DownloadError("corrupt ZIP archive") from exc
    return {
        "member_count": len(members),
        "declared_expanded_bytes": declared_total,
        "validated_expanded_bytes": actual_total,
    }


def _read_c_string(source: BinaryIO, *, limit: int = 4096) -> bytes:
    value = bytearray()
    while len(value) <= limit:
        byte = source.read(1)
        if not byte:
            raise DownloadError("truncated GZIP header")
        if byte == b"\x00":
            return bytes(value)
        value.extend(byte)
    raise DownloadError("GZIP header field exceeds the configured limit")


def _validate_gzip_header(path: Path) -> None:
    with path.open("rb") as source:
        header = source.read(10)
        if len(header) != 10 or header[:3] != b"\x1f\x8b\x08":
            raise DownloadError("invalid GZIP header")
        flags = header[3]
        if flags & 0xE0:
            raise DownloadError("GZIP header uses reserved flags")
        if flags & 0x04:
            raw_length = source.read(2)
            if len(raw_length) != 2:
                raise DownloadError("truncated GZIP extra header")
            extra_length = int.from_bytes(raw_length, "little")
            if extra_length > 4096 or len(source.read(extra_length)) != extra_length:
                raise DownloadError("unsafe or truncated GZIP extra header")
        if flags & 0x08:
            _validate_member_path(_read_c_string(source).decode("latin-1"))
        if flags & 0x10:
            _read_c_string(source)
        if flags & 0x02 and len(source.read(2)) != 2:
            raise DownloadError("truncated GZIP header checksum")


def _validate_gzip(path: Path, limits: ArchiveLimits) -> dict:
    try:
        _validate_gzip_header(path)
        compressed = path.stat().st_size
        expanded = 0
        with gzip.open(path, "rb") as source:
            while True:
                chunk = source.read(CHUNK_BYTES)
                if not chunk:
                    break
                expanded += len(chunk)
                _check_expansion(expanded, compressed, limits)
        if expanded == 0:
            raise DownloadError("GZIP expands to an empty file")
    except DownloadError:
        raise
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
        raise DownloadError("corrupt GZIP archive") from exc
    return {"member_count": 1, "validated_expanded_bytes": expanded}


def _validate_archive(path: Path, spec: ReportSpec, limits: ArchiveLimits) -> dict:
    if spec.compression == "zip":
        return _validate_zip(path, limits)
    if spec.compression == "gzip":
        return _validate_gzip(path, limits)
    raise DownloadError(f"unsupported archive type: {spec.compression}")


def _safe_response_metadata(headers) -> dict[str, str]:
    """Retain only non-sensitive, bounded transport metadata."""
    result: dict[str, str] = {}
    for key in ("Content-Length", "Content-Type", "Last-Modified"):
        value = headers.get(key)
        if value is not None:
            result[key.lower()] = str(value).replace("\r", "").replace("\n", "")[:512]
    return result


def _download_one(session, spec: ReportSpec, destination: Path, *, max_bytes: int,
                  archive_limits: ArchiveLimits) -> dict:
    _validate_https_url(spec.url)
    response = session.get(
        spec.url,
        headers={"User-Agent": USER_AGENT, "Accept": ", ".join(spec.accepted_content_types)},
        timeout=(10, 90), stream=True, allow_redirects=True,
    )
    try:
        final_url = _validate_redirect_chain(response, spec.url)
        if response.status_code in {401, 403, 407, 429}:
            raise DownloadError(f"NSE access control returned HTTP {response.status_code}; no bypass attempted")
        if response.status_code != 200:
            raise DownloadError(f"NSE returned HTTP {response.status_code}")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type and content_type not in spec.accepted_content_types:
            raise DownloadError(f"unexpected Content-Type: {content_type}")
        with destination.open("xb") as output:
            size, digest, prefix = _stream_response(response, output, max_bytes=max_bytes)
            output.flush()
            os.fsync(output.fileno())
        if any(marker in prefix.lower() for marker in _ACCESS_CONTROL_MARKERS):
            raise DownloadError("access-control page detected; no bypass attempted")
        archive = _validate_archive(destination, spec, archive_limits)
        return {
            "key": spec.key, "role": spec.role, "trading_date": None,
            "landing_page_url": LANDING_URL, "source_url": spec.url,
            "resolved_url": final_url, "filename": spec.filename,
            "compression": spec.compression,
            "content_type": content_type or "NOT_SUPPLIED",
            "byte_length": size, "sha256": digest,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "archive_validation": archive,
            "response_metadata": _safe_response_metadata(response.headers),
        }
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def _write_manifest(path: Path, manifest: dict) -> None:
    body = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(body)
        output.flush()
        os.fsync(output.fileno())


def _publish_staged_package(staging_dir: Path, package_dir: Path) -> None:
    if os.path.lexists(package_dir):
        raise FileExistsError(f"refusing to overwrite existing package: {package_dir}")
    os.rename(staging_dir, package_dir)


def download_package(*, trading_date: date, report: str, output_root: Path,
                     acknowledge_nse_terms: bool, max_bytes: int = DEFAULT_MAX_BYTES,
                     archive_limits: ArchiveLimits | None = None, session=None) -> dict:
    """Download one date into an isolated stage and publish it transactionally."""
    if not acknowledge_nse_terms:
        raise PermissionError(
            "retention is disabled until --acknowledge-nse-terms is supplied after reviewing NSE policy pages"
        )
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    limits = archive_limits or ArchiveLimits()
    limits.validate()
    plan = build_plan(trading_date, report)
    package_dir = output_root / trading_date.isoformat()
    if os.path.lexists(package_dir):
        raise FileExistsError(f"refusing to overwrite existing package: {package_dir}")

    output_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{trading_date.isoformat()}.staging-", dir=output_root))
    http = session
    owns_session = session is None
    session_closed = False
    published = False
    try:
        if http is None:
            http = requests.Session()
        records: list[dict] = []
        for spec in plan:
            record = _download_one(http, spec, staging_dir / spec.filename,
                                   max_bytes=max_bytes, archive_limits=limits)
            record["trading_date"] = trading_date.isoformat()
            records.append(record)
        manifest = {
            "schema_version": "nse_fno_single_date_download_v2",
            "trading_date": trading_date.isoformat(),
            "report_selection": report,
            "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION",
            "terms_acknowledged_by_operator": True,
            "policy_urls": [TERMS_URL, COPYRIGHT_URL, DATA_POLICY_URL, LANDING_URL, FORMAT_URL],
            "files": records,
            "production_activation_authorized": False,
            "bulk_acquisition_authorized": False,
        }
        _write_manifest(staging_dir / "manifest.json", manifest)
        if owns_session:
            http.close()
            session_closed = True
        _publish_staged_package(staging_dir, package_dir)
        published = True
        return manifest
    finally:
        try:
            if owns_session and http is not None and not session_closed:
                http.close()
        finally:
            if not published and staging_dir.exists():
                shutil.rmtree(staging_dir)


def _plan_json(specs: Iterable[ReportSpec], trading_date: date) -> dict:
    return {
        "schema_version": "nse_fno_single_date_dry_run_v1",
        "trading_date": trading_date.isoformat(),
        "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION",
        "landing_page_url": LANDING_URL,
        "files": [
            {"key": spec.key, "role": spec.role, "filename": spec.filename, "url": spec.url}
            for spec in specs
        ],
        "network_requests": 0,
        "payloads_retained": 0,
        "downloaded": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=parse_trade_date, help="one trading date in YYYY-MM-DD")
    parser.add_argument("--report", choices=("udiff", "mii", "both"), default="both")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/nse_fno_reports"))
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="maximum bytes allowed per file")
    parser.add_argument("--dry-run", action="store_true", help="print the exact plan without network access")
    parser.add_argument("--acknowledge-nse-terms", action="store_true",
                        help="confirm the operator reviewed NSE policy pages and has retention authority")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(args.date, args.report)
    if args.dry_run:
        print(json.dumps(_plan_json(plan, args.date), indent=2, sort_keys=True))
        return 0
    manifest = download_package(
        trading_date=args.date, report=args.report, output_root=args.output_root,
        acknowledge_nse_terms=args.acknowledge_nse_terms, max_bytes=args.max_bytes,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
