"""Download one explicitly selected NSE F&O daily-report package.

This is a bounded acquisition utility, not an archive crawler.  It accepts
exactly one ISO trading date and downloads the requested UDiFF bhavcopy, MII
contract master, or both from allowlisted official NSE HTTPS hosts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterable
from urllib.parse import urlparse

import requests


LANDING_URL = "https://www.nseindia.com/all-reports-derivatives"
TERMS_URL = "https://www.nseindia.com/static/nse-terms-of-use"
COPYRIGHT_URL = "https://www.nseindia.com/static/nse-copyright"
DATA_POLICY_URL = "https://www.nseindia.com/static/market-data/nse-data-policy"
ARCHIVE_ROOT = "https://nsearchives.nseindia.com/content/fo"
ALLOWED_HOSTS = {"www.nseindia.com", "nsearchives.nseindia.com", "archives.nseindia.com"}
USER_AGENT = "custom-terminal-nse-fno-downloader/1.0 (single-date official-data utility)"
DEFAULT_MAX_BYTES = 256 * 1024 * 1024
CHUNK_BYTES = 128 * 1024


class DownloadError(RuntimeError):
    """A report could not be safely retained."""


@dataclass(frozen=True)
class ReportSpec:
    key: str
    role: str
    filename: str
    url: str
    compression: str
    magic: bytes
    accepted_content_types: tuple[str, ...]


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
            key="udiff",
            role="DAILY_DERIVATIVES_FACTS",
            filename=facts_name,
            url=f"{ARCHIVE_ROOT}/{facts_name}",
            compression="zip",
            magic=b"PK",
            accepted_content_types=("application/zip", "application/x-zip-compressed", "application/octet-stream"),
        ),
        "mii": ReportSpec(
            key="mii",
            role="CONTRACT_IDENTITY",
            filename=contract_name,
            url=f"{ARCHIVE_ROOT}/{contract_name}",
            compression="gzip",
            magic=b"\x1f\x8b",
            accepted_content_types=("application/gzip", "application/x-gzip", "application/octet-stream"),
        ),
    }
    if report == "both":
        return available["udiff"], available["mii"]
    try:
        return (available[report],)
    except KeyError as exc:
        raise ValueError("report must be one of: udiff, mii, both") from exc


def _validate_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise DownloadError(f"non-allowlisted download URL: {url}")


def _stream_response(response, destination: BinaryIO, *, max_bytes: int) -> tuple[int, str, bytes]:
    declared = response.headers.get("Content-Length")
    if declared:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise DownloadError("invalid Content-Length") from exc
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
    if declared and size != int(declared):
        raise DownloadError(f"truncated response: expected {declared} bytes, received {size}")
    if size == 0:
        raise DownloadError("empty response")
    return size, digest.hexdigest(), prefix


def _download_one(session, spec: ReportSpec, part_path: Path, *, max_bytes: int) -> dict:
    _validate_https_url(spec.url)
    response = session.get(
        spec.url,
        headers={"User-Agent": USER_AGENT, "Accept": ", ".join(spec.accepted_content_types)},
        timeout=(10, 90),
        stream=True,
        allow_redirects=True,
    )
    try:
        final_url = getattr(response, "url", spec.url) or spec.url
        _validate_https_url(final_url)
        if response.status_code in {401, 403, 429}:
            raise DownloadError(f"NSE access control returned HTTP {response.status_code}; no bypass attempted")
        if response.status_code != 200:
            raise DownloadError(f"NSE returned HTTP {response.status_code}")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type and content_type not in spec.accepted_content_types:
            raise DownloadError(f"unexpected Content-Type: {content_type}")
        with part_path.open("xb") as destination:
            size, digest, prefix = _stream_response(response, destination, max_bytes=max_bytes)
        lowered = prefix.lower()
        if b"captcha" in lowered or b"access denied" in lowered or b"enable javascript" in lowered:
            raise DownloadError("access-control page detected; no bypass attempted")
        if not prefix.startswith(spec.magic):
            raise DownloadError(f"{spec.compression} signature missing")
        return {
            "key": spec.key,
            "role": spec.role,
            "trading_date": None,
            "landing_page_url": LANDING_URL,
            "source_url": spec.url,
            "resolved_url": final_url,
            "filename": spec.filename,
            "compression": spec.compression,
            "content_type": content_type or "NOT_SUPPLIED",
            "byte_length": size,
            "sha256": digest,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response_metadata": {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower() in {"content-length", "content-type", "last-modified", "etag"}
            },
        }
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def download_package(
    *,
    trading_date: date,
    report: str,
    output_root: Path,
    acknowledge_nse_terms: bool,
    max_bytes: int = DEFAULT_MAX_BYTES,
    session=None,
) -> dict:
    """Download a single-date package and return its sanitized manifest."""

    if not acknowledge_nse_terms:
        raise PermissionError(
            "retention is disabled until --acknowledge-nse-terms is supplied after reviewing NSE policy pages"
        )
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    plan = build_plan(trading_date, report)
    package_dir = output_root / trading_date.isoformat()
    manifest_path = package_dir / "manifest.json"
    targets = [package_dir / spec.filename for spec in plan]
    parts = [target.with_name(f".{target.name}.part") for target in targets]
    if manifest_path.exists() or any(path.exists() for path in (*targets, *parts)):
        raise FileExistsError(f"refusing to overwrite existing package: {package_dir}")

    package_dir.mkdir(parents=True, exist_ok=True)
    http = session or requests.Session()
    records: list[dict] = []
    try:
        for spec, part in zip(plan, parts, strict=True):
            record = _download_one(http, spec, part, max_bytes=max_bytes)
            record["trading_date"] = trading_date.isoformat()
            records.append(record)
        for part, target in zip(parts, targets, strict=True):
            os.replace(part, target)
        manifest = {
            "schema_version": "nse_fno_single_date_download_v1",
            "trading_date": trading_date.isoformat(),
            "report_selection": report,
            "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION",
            "terms_acknowledged_by_operator": True,
            "policy_urls": [TERMS_URL, COPYRIGHT_URL, DATA_POLICY_URL],
            "files": records,
            "production_activation_authorized": False,
            "bulk_acquisition_authorized": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        for part in parts:
            part.unlink(missing_ok=True)
        raise


def _plan_json(specs: Iterable[ReportSpec], trading_date: date) -> dict:
    return {
        "trading_date": trading_date.isoformat(),
        "landing_page_url": LANDING_URL,
        "files": [
            {"key": spec.key, "role": spec.role, "filename": spec.filename, "url": spec.url}
            for spec in specs
        ],
        "downloaded": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=parse_trade_date, help="one trading date in YYYY-MM-DD")
    parser.add_argument("--report", choices=("udiff", "mii", "both"), default="both")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/nse_fno_reports"))
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="maximum bytes allowed per file")
    parser.add_argument("--dry-run", action="store_true", help="print the exact plan without network access")
    parser.add_argument(
        "--acknowledge-nse-terms",
        action="store_true",
        help="confirm the operator reviewed NSE terms/copyright/data-policy pages and has retention authority",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(args.date, args.report)
    if args.dry_run:
        print(json.dumps(_plan_json(plan, args.date), indent=2, sort_keys=True))
        return 0
    manifest = download_package(
        trading_date=args.date,
        report=args.report,
        output_root=args.output_root,
        acknowledge_nse_terms=args.acknowledge_nse_terms,
        max_bytes=args.max_bytes,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0
