"""Strict zero-redirect companion for bounded R10N-E NSE F&O acquisition.

This module deliberately has no command-line entry point.  A later owner-gated
executor must call :func:`download_package_zero_redirects` explicitly after
the amended request budget and exact scope have been approved.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

import requests

from tools import download_nse_fno_reports as base


REDIRECT_POLICY = "ZERO_REDIRECTS"


class _ZeroRedirectSession:
    """Force direct responses and reject redirect evidence before streaming."""

    def __init__(self, session):
        self._session = session

    def get(self, url, **kwargs):
        kwargs["allow_redirects"] = False
        response = self._session.get(url, **kwargs)
        try:
            base._validate_https_url(url)
            if list(getattr(response, "history", ()) or ()):
                raise base.DownloadError("strict zero-redirect mode received redirect history")
            status = getattr(response, "status_code", None)
            if isinstance(status, int) and 300 <= status <= 399:
                raise base.DownloadError(f"strict zero-redirect mode rejected HTTP {status}")
            final_url = getattr(response, "url", None) or url
            base._validate_https_url(final_url)
            if final_url != url:
                raise base.DownloadError("strict zero-redirect mode detected a changed response URL")
            return response
        except Exception:
            close = getattr(response, "close", None)
            if close:
                close()
            raise


def download_package_zero_redirects(
    *, trading_date: date, report: str, output_root: Path,
    acknowledge_nse_terms: bool, max_bytes: int = base.DEFAULT_MAX_BYTES,
    archive_limits: base.ArchiveLimits | None = None, session=None,
) -> dict:
    """Download one explicit date with zero redirects, retries, or discovery."""
    if not acknowledge_nse_terms:
        raise PermissionError(
            "retention is disabled until the owner supplies acknowledgement after exact approval"
        )
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    limits = archive_limits or base.ArchiveLimits()
    limits.validate()
    plan = base.build_plan(trading_date, report)
    if len(plan) > 2:
        raise base.DownloadError("strict acquisition exceeds two-file invocation boundary")
    package_dir = output_root / trading_date.isoformat()
    if os.path.lexists(package_dir):
        raise FileExistsError(f"refusing to overwrite existing package: {package_dir}")

    output_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(
        prefix=f".{trading_date.isoformat()}.staging-", dir=output_root,
    ))
    http = session
    owns_session = session is None
    published = False
    try:
        if http is None:
            http = requests.Session()
        strict = _ZeroRedirectSession(http)
        records: list[dict] = []
        for spec in plan:
            record = base._download_one(
                strict, spec, staging_dir / spec.filename,
                max_bytes=max_bytes, archive_limits=limits,
            )
            record["trading_date"] = trading_date.isoformat()
            records.append(record)
        manifest = {
            "schema_version": "nse_fno_single_date_download_v3",
            "trading_date": trading_date.isoformat(),
            "report_selection": report,
            "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION_ZERO_REDIRECTS",
            "redirect_policy": REDIRECT_POLICY,
            "terms_acknowledged_by_operator": True,
            "policy_urls": [
                base.TERMS_URL, base.COPYRIGHT_URL, base.DATA_POLICY_URL,
                base.LANDING_URL, base.FORMAT_URL,
            ],
            "files": records,
            "production_activation_authorized": False,
            "bulk_acquisition_authorized": False,
        }
        base._write_manifest(staging_dir / "manifest.json", manifest)
        if owns_session:
            http.close()
            http = None
        base._publish_staged_package(staging_dir, package_dir)
        published = True
        return manifest
    finally:
        try:
            if owns_session and http is not None:
                http.close()
        finally:
            if not published and staging_dir.exists():
                shutil.rmtree(staging_dir)
