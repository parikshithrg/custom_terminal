"""Offline-only predicate diagnosis for the three retained R10N-F packages.

This module is deliberately separate from the fail-closed candidate adapter.
It has no acquisition code or command-line entry point and never persists raw
rows or contract inventories.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, TextIO

from market_intel.foundation.nse_fno_candidate import (
    CandidateAdapterError,
    adapt_package,
    build_package_descriptor,
    verify_package,
)


APPROVED_DATES = ("2026-09-09", "2026-09-10", "2025-07-08")
TARGET_DATE = "2026-09-10"
MAX_EXAMPLES_PER_DATE = 8
INSTRUMENT_CLASSES = {"STF": "FUTURES", "IDF": "FUTURES", "STO": "OPTIONS", "IDO": "OPTIONS"}
PREDICATES = (
    "high_below_open", "high_below_close", "high_below_low",
    "low_above_open", "low_above_close",
)
PRICE_FIELDS = ("OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric")


class DiagnosticError(RuntimeError):
    pass


def sanitized_identifier(financial_instrument_id: str) -> str:
    """Return a deterministic domain-separated one-way identifier."""
    if not isinstance(financial_instrument_id, str) or not financial_instrument_id.isdigit():
        raise DiagnosticError("FinInstrmId must be a decimal digit string")
    return hashlib.sha256(f"R10N-F|FinInstrmId|{financial_instrument_id}".encode("ascii")).hexdigest()


def _decimal(row: Mapping[str, str], field: str, row_number: int) -> Decimal:
    raw = (row.get(field) or "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise DiagnosticError(f"row {row_number} has malformed required decimal field") from exc
    if not value.is_finite():
        raise DiagnosticError(f"row {row_number} has non-finite required decimal field")
    return value


def _integer(row: Mapping[str, str], field: str, row_number: int) -> int:
    value = _decimal(row, field, row_number)
    if value != value.to_integral_value():
        raise DiagnosticError(f"row {row_number} has malformed required integer field")
    return int(value)


def _expiry_from_mii(raw: str) -> str | None:
    if not raw.isdigit():
        return None
    try:
        return datetime.fromtimestamp(int(raw), timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _contract_fingerprint(row: Mapping[str, str]) -> tuple[str, ...]:
    return tuple((row.get(name) or "").strip() for name in (
        "XpryDt", "NewBrdLotQty", "MinLot", "StrkPric", "OptnTp", "FinInstrmTp",
    ))


def _read_contracts(stream: TextIO) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    reader = csv.DictReader(stream)
    required = {"FinInstrmId", "XpryDt", "NewBrdLotQty", "MinLot", "StrkPric", "OptnTp", "FinInstrmTp"}
    if not required.issubset(reader.fieldnames or ()):
        raise DiagnosticError("MII required diagnostic fields are absent")
    identities: dict[str, dict[str, str]] = {}
    fingerprints: dict[str, tuple[str, ...]] = {}
    duplicate = conflicting = rows = 0
    for row_number, row in enumerate(reader, 2):
        rows += 1
        if None in row:
            raise DiagnosticError(f"MII row {row_number} exceeds schema width")
        fid = (row.get("FinInstrmId") or "").strip()
        if not fid.isdigit():
            raise DiagnosticError(f"MII row {row_number} has malformed identifier")
        fingerprint = _contract_fingerprint(row)
        if fid in identities:
            if fingerprints[fid] == fingerprint:
                duplicate += 1
            else:
                conflicting += 1
            continue
        identities[fid] = {key: (row.get(key) or "").strip() for key in required}
        fingerprints[fid] = fingerprint
    return identities, {
        "total_rows": rows,
        "unique_identifiers": len(identities),
        "duplicate_identifiers": duplicate,
        "conflicting_identifiers": conflicting,
    }


def _predicates(open_: Decimal, high: Decimal, low: Decimal, close: Decimal) -> dict[str, bool]:
    return {
        "high_below_open": high < open_,
        "high_below_close": high < close,
        "high_below_low": high < low,
        "low_above_open": low > open_,
        "low_above_close": low > close,
    }


def _identity_assessment(row: Mapping[str, str], identity: Mapping[str, str] | None) -> dict[str, Any]:
    if identity is None:
        return {"resolved": False, "expiry_agrees": False, "lot_size_agrees": False,
                "strike_semantics_agree": False, "option_type_agrees": False}
    instrument = (row.get("FinInstrmTp") or "").strip()
    is_option = instrument in {"STO", "IDO"}
    mii_lot = identity.get("NewBrdLotQty") or identity.get("MinLot") or ""
    return {
        "resolved": True,
        "expiry_agrees": _expiry_from_mii(identity.get("XpryDt", "")) == (row.get("XpryDt") or "").strip(),
        "lot_size_agrees": mii_lot == (row.get("NewBrdLotQty") or "").strip(),
        "strike_semantics_agree": (
            identity.get("StrkPric", "") == (row.get("StrkPric") or "").strip()
            if is_option else not (row.get("StrkPric") or "").strip()
        ),
        "option_type_agrees": (
            identity.get("OptnTp", "") == (row.get("OptnTp") or "").strip()
            if is_option else not (row.get("OptnTp") or "").strip()
        ),
    }


def diagnose_streams(
    fact_stream: TextIO, contract_stream: TextIO, *, trading_date: str,
    max_examples: int = MAX_EXAMPLES_PER_DATE,
) -> dict[str, Any]:
    """Return aggregate diagnostics and bounded sanitized examples only."""
    if max_examples < 0 or max_examples > MAX_EXAMPLES_PER_DATE:
        raise ValueError("bounded example limit must be between zero and eight")
    identities, identity_metrics = _read_contracts(contract_stream)
    reader = csv.DictReader(fact_stream)
    required = {"TradDt", "FinInstrmTp", "FinInstrmId", "XpryDt", "StrkPric", "OptnTp",
                "OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric", "TtlTradgVol",
                "NewBrdLotQty"}
    if not required.issubset(reader.fieldnames or ()):
        raise DiagnosticError("UDiFF required diagnostic fields are absent")
    totals = Counter()
    predicate_counts = Counter({name: 0 for name in PREDICATES})
    instrument_types = Counter()
    instrument_classes = Counter()
    patterns = Counter()
    patterns_by_volume = Counter()
    examples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_fact_ids = unresolved = cross_file_disagreements = 0

    for row_number, row in enumerate(reader, 2):
        if None in row:
            raise DiagnosticError(f"UDiFF row {row_number} exceeds schema width")
        if (row.get("TradDt") or "").strip() != trading_date:
            raise DiagnosticError(f"UDiFF row {row_number} differs from explicit date")
        fid = (row.get("FinInstrmId") or "").strip()
        if not fid.isdigit():
            raise DiagnosticError(f"UDiFF row {row_number} has malformed identifier")
        if fid in seen_ids:
            duplicate_fact_ids += 1
        seen_ids.add(fid)
        instrument = (row.get("FinInstrmTp") or "").strip()
        instrument_class = INSTRUMENT_CLASSES.get(instrument, "UNKNOWN")
        instrument_types[instrument or "MISSING"] += 1
        instrument_classes[instrument_class] += 1
        open_, high, low, close, settlement = (_decimal(row, field, row_number) for field in PRICE_FIELDS)
        volume = _integer(row, "TtlTradgVol", row_number)
        totals["total_rows"] += 1
        totals["zero_volume_rows" if volume == 0 else "nonzero_volume_rows"] += 1
        if any(value == 0 for value in (open_, high, low, close)) and any(
            value != 0 for value in (open_, high, low, close, settlement)
        ):
            totals["ohlc_zero_while_another_price_nonzero"] += 1
        if close < low or close > high:
            totals["close_outside_low_high"] += 1
        if open_ < low or open_ > high:
            totals["open_outside_low_high"] += 1
        if high < low:
            totals["high_below_low"] += 1
        if settlement < low or settlement > high:
            totals["settlement_outside_low_high"] += 1

        failed = _predicates(open_, high, low, close)
        failed_names = tuple(name for name in PREDICATES if failed[name])
        for name in failed_names:
            predicate_counts[name] += 1
        if failed_names:
            totals["any_ohlc_predicate_violation"] += 1
            totals["violating_zero_volume_rows" if volume == 0 else "violating_nonzero_volume_rows"] += 1
            patterns["+".join(failed_names)] += 1
            patterns_by_volume[("ZERO" if volume == 0 else "NONZERO") + "|" + "+".join(failed_names)] += 1
            identity = identities.get(fid)
            assessment = _identity_assessment(row, identity)
            if not assessment["resolved"]:
                unresolved += 1
            if not all(assessment.values()):
                cross_file_disagreements += int(assessment["resolved"])
            candidate = {
                    "trading_date": trading_date,
                    "csv_row_number": row_number,
                    "financial_instrument_id_sha256": sanitized_identifier(fid),
                    "instrument_class": instrument_class,
                    "instrument_type_group": instrument,
                    "failed_predicates": list(failed_names),
                    "value_states": {name: "PRESENT_EXACT_DECIMAL" for name in (
                        "open", "high", "low", "close", "settlement_price"
                    )} | {"volume": "PRESENT_EXACT_INTEGER"},
                    "exact_differences": {
                        "high_minus_open": format(high - open_, "f"),
                        "high_minus_close": format(high - close, "f"),
                        "high_minus_low": format(high - low, "f"),
                        "low_minus_open": format(low - open_, "f"),
                        "low_minus_close": format(low - close, "f"),
                        "close_minus_settlement": format(close - settlement, "f"),
                    },
                    "volume_state": "ZERO" if volume == 0 else "NONZERO",
                    "identity_assessment": assessment,
                }
            if len(examples) < max_examples:
                examples.append(candidate)
            elif volume != 0:
                zero_index = next(
                    (index for index in range(len(examples) - 1, -1, -1)
                     if examples[index]["volume_state"] == "ZERO"),
                    None,
                )
                if zero_index is not None:
                    examples[zero_index] = candidate

    pattern_counts = dict(sorted(patterns.items()))
    repeated = sum(count for count in patterns.values() if count > 1)
    isolated = sum(count for count in patterns.values() if count == 1)
    return {
        "schema_version": "r10nf_predicate_diagnostics_v1",
        "trading_date": trading_date,
        "totals": {key: totals[key] for key in (
            "total_rows", "zero_volume_rows", "nonzero_volume_rows",
            "ohlc_zero_while_another_price_nonzero", "close_outside_low_high",
            "open_outside_low_high", "high_below_low", "settlement_outside_low_high",
            "any_ohlc_predicate_violation", "violating_zero_volume_rows",
            "violating_nonzero_volume_rows",
        )},
        "predicate_violations": {name: predicate_counts[name] for name in PREDICATES},
        "instrument_types": dict(sorted(instrument_types.items())),
        "instrument_classes": dict(sorted(instrument_classes.items())),
        "violation_patterns": pattern_counts,
        "violation_patterns_by_volume": dict(sorted(patterns_by_volume.items())),
        "pattern_repetition": {"repeated_rows": repeated, "isolated_rows": isolated},
        "identity": identity_metrics | {
            "duplicate_fact_identifiers": duplicate_fact_ids,
            "unresolved_violating_rows": unresolved,
            "cross_file_disagreement_violating_rows": cross_file_disagreements,
        },
        "bounded_examples": examples,
        "sanitization": {
            "identifier": "SHA256_OF_ASCII_R10N-F_PIPE_FinInstrmId_PIPE_RAW_ID",
            "ticker_retained": False,
            "raw_identifier_retained": False,
            "full_row_retained": False,
            "max_examples": max_examples,
        },
    }


def reproduce_adapter_failure(package_dir: Path, *, trading_date: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    descriptor = build_package_descriptor(package_dir, trading_date=trading_date, manifest=manifest)
    try:
        adapt_package(descriptor)
    except CandidateAdapterError as exc:
        return {"trading_date": trading_date, "adapter_error_code": exc.code,
                "sanitized_message": str(exc)}
    return {"trading_date": trading_date, "adapter_error_code": None,
            "sanitized_message": "ADAPTER_COMPLETED_WITHOUT_FAILURE"}


def diagnose_package(package_dir: Path, *, trading_date: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify one explicit package, validate archives, then scan it offline."""
    descriptor = build_package_descriptor(package_dir, trading_date=trading_date, manifest=manifest)
    verify_package(descriptor)
    by_key = {item.key: item for item in descriptor.files}
    udiff = by_key["udiff"]
    mii = by_key["mii"]
    udiff_path = package_dir / udiff.filename
    mii_path = package_dir / mii.filename
    expected_member = udiff.filename.removesuffix(".zip")
    with zipfile.ZipFile(udiff_path) as archive:
        if archive.testzip() is not None:
            raise DiagnosticError("UDiFF CRC validation failed")
        members = archive.namelist()
        if members != [expected_member]:
            raise DiagnosticError("UDiFF archive member mismatch")
        with archive.open(expected_member) as fact_raw, gzip.open(mii_path, "rb") as contract_raw:
            with io.TextIOWrapper(fact_raw, encoding="utf-8-sig", newline="") as facts:
                with io.TextIOWrapper(contract_raw, encoding="utf-8-sig", newline="") as contracts:
                    result = diagnose_streams(facts, contracts, trading_date=trading_date)
    result["archive_integrity"] = {
        "manifest_and_file_hashes": "MATCHED_BEFORE_ROW_ACCESS",
        "udiff_zip_crc": "PASS",
        "udiff_member_count": 1,
        "mii_gzip_complete_decompression_and_crc": "PASS",
    }
    return result


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
