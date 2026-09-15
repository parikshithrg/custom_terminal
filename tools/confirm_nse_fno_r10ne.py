"""Strict bounded HEAD confirmation for the owner-approved R10N-E pairs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from tools import download_nse_fno_reports as base


MAX_DATES = 2
FILES_PER_DATE = 2
MAX_HEAD_REQUESTS = 4
APPROVED_DATES = (date(2026, 9, 10), date(2025, 7, 8))


@dataclass(frozen=True)
class Confirmation:
    trading_date: str
    key: str
    filename: str
    url: str
    status_code: int
    response_metadata: dict[str, str]

    def sanitized(self) -> dict[str, Any]:
        return {
            "trading_date": self.trading_date,
            "key": self.key,
            "filename": self.filename,
            "url": self.url,
            "status_code": self.status_code,
            "response_metadata": dict(self.response_metadata),
        }


def _confirm_one(session, trading_date: date, spec: base.ReportSpec) -> Confirmation:
    base._validate_https_url(spec.url)
    response = session.head(
        spec.url,
        headers={"User-Agent": base.USER_AGENT, "Accept": ", ".join(spec.accepted_content_types)},
        timeout=(10, 90),
        allow_redirects=False,
    )
    try:
        if list(getattr(response, "history", ()) or ()):
            raise base.DownloadError("strict confirmation received redirect history")
        status = getattr(response, "status_code", None)
        if isinstance(status, int) and 300 <= status <= 399:
            raise base.DownloadError(f"strict confirmation rejected HTTP {status}")
        if status != 200:
            raise base.DownloadError(f"strict confirmation expected HTTP 200, received {status}")
        final_url = getattr(response, "url", None) or spec.url
        base._validate_https_url(final_url)
        if final_url != spec.url:
            raise base.DownloadError("strict confirmation detected a changed response URL")
        return Confirmation(
            trading_date.isoformat(), spec.key, spec.filename, spec.url, status,
            base._safe_response_metadata(getattr(response, "headers", {})),
        )
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def confirm_exact_pairs(
    trading_dates: tuple[date, date], *, session=None,
) -> tuple[Confirmation, Confirmation, Confirmation, Confirmation]:
    """Confirm exactly two complete pairs with four direct HEADs and no retry."""
    if not isinstance(trading_dates, tuple) or len(trading_dates) != MAX_DATES:
        raise ValueError("exactly two explicit trading dates are required")
    if any(not isinstance(value, date) for value in trading_dates):
        raise TypeError("trading dates must be datetime.date values")
    if len(set(trading_dates)) != MAX_DATES:
        raise ValueError("trading dates must be distinct")
    if trading_dates != APPROVED_DATES:
        raise ValueError("trading dates must match the ordered owner-approved R10N-E scope")

    plans = tuple((value, base.build_plan(value, "both")) for value in trading_dates)
    if any(len(plan) != FILES_PER_DATE for _, plan in plans):
        raise base.DownloadError("each confirmation plan must contain exactly two files")

    http = session
    owns_session = session is None
    try:
        if http is None:
            http = requests.Session()
        results: list[Confirmation] = []
        for trading_date, plan in plans:
            for spec in plan:
                if len(results) >= MAX_HEAD_REQUESTS:
                    raise base.DownloadError("confirmation request budget exceeded")
                results.append(_confirm_one(http, trading_date, spec))
        if len(results) != MAX_HEAD_REQUESTS:
            raise base.DownloadError("all four exact files were not confirmed")
        return tuple(results)  # type: ignore[return-value]
    finally:
        if owns_session and http is not None:
            http.close()
