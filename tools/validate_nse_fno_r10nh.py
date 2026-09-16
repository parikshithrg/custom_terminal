"""Offline, sanitized R10N-H regression helpers for explicit retained NSE packages.

This module performs no discovery, acquisition, ingestion, research, or
qualification.  Each package directory and trading date must be supplied.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from market_intel.foundation.nse_fno_candidate import (
    adapt_package,
    build_package_descriptor,
)


PRICE_COLUMNS = ("OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric")


def _digest(rows: list[tuple[str, tuple[str, ...]]]) -> str:
    canonical = json.dumps(sorted(rows), separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(b"r10nh-price-immutability-v1\0" + canonical).hexdigest()


def _source_price_digest(package: Path, filename: str) -> str:
    with zipfile.ZipFile(package / filename) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise ValueError("expected one UDiFF member")
        with archive.open(members[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            rows = [
                ((row.get("FinInstrmId") or "").strip(), tuple((row.get(name) or "").strip() for name in PRICE_COLUMNS))
                for row in reader
            ]
    return _digest(rows)


def validate_package(package: Path, trading_date: str) -> dict:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest.setdefault("schema_version", "nse_fno_single_date_download_v1")
    descriptor = build_package_descriptor(package, trading_date=trading_date, manifest=manifest)
    result = adapt_package(descriptor)
    facts = next(item for item in descriptor.files if item.key == "udiff")
    source_digest = _source_price_digest(package, facts.filename)
    normalized_digest = _digest([
        (record.financial_instrument_id, tuple(format(value, "f") for value in (
            record.open, record.high, record.low, record.close, record.settlement_price,
        )))
        for record in result.records
    ])
    quality = result.quality
    return {
        "trading_date": trading_date,
        "manifest_and_archive_validation": "PASS",
        "source_rows": dict(quality["source_rows"]),
        "normalized_rows": quality["normalized_rows"],
        "expiry_agreement": {
            "matched": quality["expiry_encoding"]["agreement"]["matched"],
            "mismatched": quality["expiry_encoding"]["agreement"]["mismatched"],
            "rate": format(quality["expiry_encoding"]["agreement"]["rate"], "f"),
        },
        "diagnostic_counts": dict(quality["diagnostic_counts"]),
        "qualification_blocking_diagnostic_count": quality["qualification"]["blocking_diagnostic_count"],
        "price_immutability": {
            "source_digest": source_digest,
            "normalized_digest": normalized_digest,
            "exact_match": source_digest == normalized_digest,
        },
        "source_qualified": False,
    }


def validate_packages(packages: tuple[tuple[str, Path], ...]) -> dict:
    """Validate exactly three caller-selected packages and return sanitized evidence."""
    if len(packages) != 3 or len({trading_date for trading_date, _ in packages}) != 3:
        raise ValueError("R10N-H regression requires exactly three distinct explicit dates")
    return {
        "schema_version": "r10nh_three_package_regression_v1",
        "milestone": "R.10N-H",
        "packages": [validate_package(path, trading_date) for trading_date, path in packages],
        "network_requests": 0,
        "source_qualified": False,
        "retained_raw_rows_or_identifiers": False,
    }
