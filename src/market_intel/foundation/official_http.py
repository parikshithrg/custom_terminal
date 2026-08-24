"""Conservative official-source HTTP landing with quarantine."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class HttpLandingResult:
    outcome: str
    payload_path: str | None
    manifest_path: str
    content_hash: str | None
    quarantine_reason: str | None


class OfficialHttpClient:
    def __init__(self, *, allowed_hosts: set[str], user_agent: str,
                 minimum_interval_seconds: float = 1.0, max_bytes: int = 10_000_000,
                 retries: int = 2, session=None):
        self.allowed_hosts = allowed_hosts
        self.user_agent = user_agent
        self.minimum_interval_seconds = minimum_interval_seconds
        self.max_bytes = max_bytes
        self.retries = retries
        self.session = session or requests.Session()
        self._last_request = 0.0

    def retrieve(self, *, organization: str, dataset: str, url: str, raw_root: Path,
                 parser_version: str, parameters: dict[str, str] | None = None,
                 expected_content_types: tuple[str, ...] = ()) -> HttpLandingResult:
        host = urlparse(url).hostname or ""
        if host not in self.allowed_hosts:
            raise PermissionError(f"host is not allowlisted: {host}")
        cache_root = raw_root / organization / dataset
        if cache_root.exists():
            for cached_manifest in cache_root.glob("*/manifest.json"):
                cached = json.loads(cached_manifest.read_text(encoding="utf-8"))
                if cached.get("source_url") == url and cached.get("request_parameters", {}) == (parameters or {}):
                    payload = cached_manifest.parent / ("quarantine.bin" if cached["retrieval_outcome"] == "QUARANTINED" else "payload.bin")
                    if payload.exists() and hashlib.sha256(payload.read_bytes()).hexdigest() == cached.get("content_hash"):
                        return HttpLandingResult(cached["retrieval_outcome"], str(payload), str(cached_manifest),
                                                 cached.get("content_hash"), cached.get("quarantine_reason"))
        history, response, error = [], None, None
        for attempt in range(self.retries + 1):
            delay = self.minimum_interval_seconds - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            try:
                response = self.session.get(url, params=parameters or {}, headers={"User-Agent": self.user_agent}, timeout=30)
                self._last_request = time.monotonic()
                history.append(f"attempt={attempt + 1};status={response.status_code}")
                if response.status_code == 200:
                    break
                if response.status_code in {401, 403, 429}:
                    error = f"ACCESS_CONTROL_HTTP_{response.status_code}"
                    break
                error = f"HTTP_{response.status_code}"
            except requests.RequestException as exc:
                error = type(exc).__name__
                history.append(f"attempt={attempt + 1};error={error}")
        body = response.content if response is not None else b""
        content_type = (response.headers.get("Content-Type", "") if response is not None else "").split(";")[0].lower()
        reason = error
        lowered = body[:4096].lower()
        declared_length = int(response.headers.get("Content-Length", len(body))) if response is not None else len(body)
        if len(body) > self.max_bytes or declared_length > len(body):
            reason = "TRUNCATED_OR_OVERSIZE"
        elif any(token in lowered for token in (b"captcha", b"access denied", b"enable javascript")):
            reason = "CAPTCHA_OR_ACCESS_CONTROL"
        elif expected_content_types and content_type not in expected_content_types:
            reason = f"UNEXPECTED_CONTENT_TYPE:{content_type or 'missing'}"
        elif content_type in {"text/html", "application/xhtml+xml"} and dataset not in {"landing_page", "terms"}:
            reason = "HTML_ERROR_OR_SCHEMA_CHANGE"
        digest = hashlib.sha256(body).hexdigest() if body else None
        retrieval_id = (digest or hashlib.sha256(url.encode()).hexdigest())[:24]
        base = raw_root / organization / dataset / retrieval_id
        base.mkdir(parents=True, exist_ok=True)
        outcome = "QUARANTINED" if reason else "SUCCEEDED"
        payload_path = base / ("quarantine.bin" if reason else "payload.bin")
        if not payload_path.exists():
            payload_path.write_bytes(body)
        elif hashlib.sha256(payload_path.read_bytes()).hexdigest() != digest:
            raise FileExistsError(f"content-addressed payload mutated: {payload_path}")
        manifest = {"manifest_version": "official_http_raw_v1", "source_organization": organization,
                    "dataset": dataset, "source_url": url, "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_parameters": parameters or {}, "http_status": response.status_code if response is not None else None,
                    "response_metadata": {k.lower(): v for k, v in (response.headers.items() if response is not None else [])
                                          if k.lower() in {"content-type", "content-length", "last-modified", "etag"}},
                    "content_hash": digest, "byte_size": len(body), "parser_version": parser_version,
                    "retry_history": history, "retrieval_outcome": outcome, "quarantine_reason": reason}
        manifest_path = base / "manifest.json"
        if not manifest_path.exists():
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return HttpLandingResult(outcome, str(payload_path), str(manifest_path), digest, reason)
