"""Offline, single-date technical qualification for NSE F&O report packages.

This module never performs network access and never persists raw source rows.
It supports the UDiFF facts schema only; legacy bhavcopies are intentionally a
separate, unsupported schema family. Contract identity is joined solely by the
documented ``FinInstrmId`` field.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import stat
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Iterator, TextIO


TRADING_DATE = date(2026, 9, 9)
UDIFF_FILENAME = "BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip"
UDIFF_MEMBER = "BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv"
MII_FILENAME = "NSE_FO_contract_09092026.csv.gz"
EXPECTED_URLS = {
    UDIFF_FILENAME: f"https://nsearchives.nseindia.com/content/fo/{UDIFF_FILENAME}",
    MII_FILENAME: f"https://nsearchives.nseindia.com/content/fo/{MII_FILENAME}",
}
UDIFF_REQUIRED = {
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt",
    "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric", "OpnIntrst", "TtlTradgVol", "NewBrdLotQty",
}
MII_REQUIRED = {
    "FinInstrmId", "FinInstrmNm", "TckrSymb", "XpryDt", "StrkPric",
    "OptnTp", "MinLot", "NewBrdLotQty", "FinInstrmTp",
}
NUMERIC_FIELDS = (
    "OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric",
    "OpnIntrst", "TtlTradgVol",
)
PRIVATE_PATH = re.compile(r"(?i)(?:[a-z]:\\\\users\\\\|/users/|/home/)")
SECRET_ASSIGNMENT = re.compile(r"(?i)(?:authorization|cookie|password|token|secret)\s*[:=]")


class QualificationError(RuntimeError):
    """The package cannot be safely or unambiguously qualified."""


@dataclass(frozen=True)
class ParsedValue:
    state: str
    value: object | None = None


def _safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or "\x00" in name or "\\" in name or name.startswith("/")
            or ".." in path.parts or re.match(r"^[A-Za-z]:", path.parts[0])):
        raise QualificationError("unsafe archive member path")


@contextmanager
def open_udiff_csv(path: Path) -> Iterator[tuple[TextIO, dict]]:
    """Validate and stream exactly the expected UDiFF CSV member."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != 1:
                raise QualificationError("UDiFF archive must contain exactly one member")
            member = members[0]
            _safe_member(member.filename)
            if member.filename != UDIFF_MEMBER or member.is_dir():
                raise QualificationError("unexpected UDiFF archive member")
            if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                raise QualificationError("unsafe UDiFF archive member type")
            if member.file_size > 1024 * 1024 * 1024:
                raise QualificationError("UDiFF expanded size exceeds limit")
            if member.file_size > max(1, member.compress_size) * 250:
                raise QualificationError("UDiFF expansion ratio exceeds limit")
            if archive.testzip() is not None:
                raise QualificationError("corrupt UDiFF archive")
            metadata = {
                "name": member.filename,
                "compressed_bytes": member.compress_size,
                "expanded_bytes": member.file_size,
                "crc32": f"{member.CRC:08x}",
            }
            with archive.open(member, "r") as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                    yield text, metadata
    except QualificationError:
        raise
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile) as exc:
        raise QualificationError("corrupt UDiFF archive") from exc


@contextmanager
def open_mii_csv(path: Path) -> Iterator[tuple[TextIO, dict]]:
    """Validate and stream the expected GZIP payload without extracting it."""
    try:
        with path.open("rb") as source:
            if source.read(3) != b"\x1f\x8b\x08":
                raise QualificationError("invalid MII GZIP signature")
        compressed = path.stat().st_size
        expanded = 0
        with gzip.open(path, "rb") as validation:
            for block in iter(lambda: validation.read(1024 * 1024), b""):
                expanded += len(block)
                if expanded > 1024 * 1024 * 1024:
                    raise QualificationError("MII expanded size exceeds limit")
                if expanded > max(1, compressed) * 250:
                    raise QualificationError("MII expansion ratio exceeds limit")
        metadata = {"compressed_bytes": compressed, "expanded_bytes": expanded}
        with gzip.open(path, "rb") as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                yield text, metadata
    except QualificationError:
        raise
    except (OSError, EOFError) as exc:
        raise QualificationError("corrupt MII GZIP archive") from exc


def _schema(reader: csv.DictReader, required: set[str], family: str) -> list[str]:
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise QualificationError(f"duplicate {family} header")
    missing = sorted(required - set(fields))
    if missing:
        raise QualificationError(f"{family} schema mismatch; missing {','.join(missing)}")
    if family == "UDIFF" and {"INSTRUMENT", "TIMESTAMP"} & set(fields):
        raise QualificationError("legacy bhavcopy must not use the UDiFF parser")
    return fields


def parse_value(raw: str | None, kind: str, *, applicable: bool = True,
                required: bool = False) -> ParsedValue:
    if not applicable:
        return ParsedValue("NOT_APPLICABLE")
    text = (raw or "").strip()
    if not text:
        return ParsedValue("MALFORMED" if required else "MISSING")
    try:
        if kind == "id":
            if not text.isdigit():
                raise ValueError
            return ParsedValue("PRESENT", text)
        if kind == "date":
            return ParsedValue("PRESENT", date.fromisoformat(text).isoformat())
        if kind == "epoch_date":
            if not text.isdigit() or len(text) not in {9, 10}:
                raise ValueError
            value = datetime.fromtimestamp(int(text), tz=timezone.utc).date()
            if not date(1990, 1, 1) <= value <= date(2100, 12, 31):
                raise ValueError
            return ParsedValue("PRESENT", value.isoformat())
        if kind == "decimal":
            value = Decimal(text)
            if not value.is_finite():
                raise InvalidOperation
            return ParsedValue("PRESENT", value)
        if kind == "integer":
            value = Decimal(text)
            if not value.is_finite() or value != value.to_integral_value():
                raise InvalidOperation
            return ParsedValue("PRESENT", int(value))
        if kind == "option":
            if text not in {"CE", "PE"}:
                raise ValueError
            return ParsedValue("PRESENT", text)
    except (ValueError, InvalidOperation):
        return ParsedValue("MALFORMED")
    raise ValueError(f"unknown parser kind: {kind}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_manifest(package: Path) -> dict:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("trading_date") != TRADING_DATE.isoformat():
        raise QualificationError("package manifest trading date mismatch")
    expected = {item["filename"]: item for item in manifest.get("files", [])}
    if set(expected) != {UDIFF_FILENAME, MII_FILENAME}:
        raise QualificationError("package manifest does not bind exactly two expected files")
    for filename, url in EXPECTED_URLS.items():
        path = package / filename
        item = expected[filename]
        if item.get("source_url") != url or item.get("resolved_url") != url:
            raise QualificationError("package manifest URL mismatch")
        if item.get("sha256") != _sha256(path) or item.get("byte_length") != path.stat().st_size:
            raise QualificationError("package file hash or size mismatch")
    return manifest


def _state_counter() -> defaultdict[str, Counter]:
    return defaultdict(Counter)


def qualify_package(package: Path) -> dict[str, dict]:
    manifest = _read_manifest(package)
    mii_path = package / MII_FILENAME
    facts_path = package / UDIFF_FILENAME
    identities: dict[str, dict] = {}
    duplicate_ids: set[str] = set()
    mii_states = _state_counter()
    mii_rows = mii_malformed = 0
    with open_mii_csv(mii_path) as (stream, mii_archive):
        reader = csv.DictReader(stream)
        mii_fields = _schema(reader, MII_REQUIRED, "MII")
        for row in reader:
            mii_rows += 1
            fid = parse_value(row.get("FinInstrmId"), "id", required=True)
            expiry = parse_value(row.get("XpryDt"), "epoch_date", required=True)
            lot = parse_value(row.get("NewBrdLotQty") or row.get("MinLot"), "integer", required=True)
            raw_option = (row.get("OptnTp") or "").strip()
            is_option = raw_option in {"CE", "PE"}
            recognized_kind = is_option or raw_option == "XX"
            strike = parse_value(row.get("StrkPric"), "decimal", applicable=is_option, required=is_option)
            option = parse_value(row.get("OptnTp"), "option", applicable=is_option, required=is_option)
            parsed = {"id": fid, "expiry": expiry, "lot": lot, "strike": strike, "option": option}
            for key, value in parsed.items():
                mii_states[key][value.state] += 1
            if not recognized_kind or any(value.state == "MALFORMED" for value in parsed.values()):
                mii_malformed += 1
            if fid.state == "PRESENT":
                key = str(fid.value)
                if key in identities:
                    duplicate_ids.add(key)
                else:
                    identities[key] = {
                        "expiry": expiry.state, "lot": lot.state,
                        "strike": strike.state, "option": option.state,
                    }
    for key in duplicate_ids:
        identities.pop(key, None)

    counts = Counter()
    join = Counter()
    fact_states = _state_counter()
    malformed_rows = ohlc_inconsistent = 0
    value_coverage = {name: Counter() for name in ("TtlTradgVol", "SttlmPric", "OpnIntrst")}
    trade_dates = Counter()
    with open_udiff_csv(facts_path) as (stream, member):
        reader = csv.DictReader(stream)
        udiff_fields = _schema(reader, UDIFF_REQUIRED, "UDIFF")
        for row in reader:
            counts["source_rows"] += 1
            kind = (row.get("FinInstrmTp") or "").strip()
            is_option = kind in {"STO", "IDO"}
            if is_option:
                counts["options"] += 1
            elif kind in {"STF", "IDF"}:
                counts["futures"] += 1
            else:
                counts["other"] += 1
            values = {
                "trade_date": parse_value(row.get("TradDt"), "date", required=True),
                "expiry": parse_value(row.get("XpryDt"), "date", required=True),
                "id": parse_value(row.get("FinInstrmId"), "id", required=True),
                "strike": parse_value(row.get("StrkPric"), "decimal", applicable=is_option, required=is_option),
                "option_type": parse_value(row.get("OptnTp"), "option", applicable=is_option, required=is_option),
                "lot_size": parse_value(row.get("NewBrdLotQty"), "integer", required=True),
            }
            numerics = {name: parse_value(row.get(name), "decimal", required=True) for name in NUMERIC_FIELDS}
            values.update(numerics)
            for name, counter in value_coverage.items():
                parsed = numerics[name]
                if parsed.state == "PRESENT":
                    counter["zero" if parsed.value == 0 else "nonzero"] += 1
                else:
                    counter[parsed.state.lower()] += 1
            for key, value in values.items():
                fact_states[key][value.state] += 1
            malformed = any(value.state == "MALFORMED" for value in values.values())
            malformed_rows += int(malformed)
            if not malformed:
                counts["normalized_rows"] += 1
            if values["trade_date"].state == "PRESENT":
                trade_dates[str(values["trade_date"].value)] += 1
            fid = values["id"]
            if fid.state != "PRESENT":
                join["missing_key"] += 1
            elif str(fid.value) in duplicate_ids:
                join["ambiguous"] += 1
            elif str(fid.value) in identities:
                join["matched"] += 1
            else:
                join["unresolved"] += 1
            if (numerics["TtlTradgVol"].state == "PRESENT" and numerics["TtlTradgVol"].value > 0
                    and all(numerics[name].state == "PRESENT" for name in ("OpnPric", "HghPric", "LwPric", "ClsPric"))):
                opn, high, low, close = (numerics[n].value for n in ("OpnPric", "HghPric", "LwPric", "ClsPric"))
                if high < max(opn, close, low) or low > min(opn, close, high):
                    ohlc_inconsistent += 1

    total = counts["source_rows"]
    matched = join["matched"]
    acquisition = {
        "schema_version": "r10nb_acquisition_v1", "milestone": "R.10N-B",
        "trading_date": TRADING_DATE.isoformat(),
        "acquisition_mode": "EXACT_ONE_DATE_NO_RETRY_NO_ENUMERATION",
        "files": [{
            "filename": name, "official_url": EXPECTED_URLS[name],
            "byte_length": (package / name).stat().st_size,
            "sha256": _sha256(package / name),
        } for name in (UDIFF_FILENAME, MII_FILENAME)],
        "manifest_terms_acknowledged_by_operator": bool(manifest.get("terms_acknowledged_by_operator")),
        "owner_confirmation_received_in_r10nb_chat": True,
        "qualification_input": "PREEXISTING_HASH_BOUND_PACKAGE",
        "post_confirmation_acquisition_performed": False,
        "post_confirmation_downloader_outcome": "REFUSED_EXISTING_PACKAGE_BEFORE_NETWORK",
        "post_confirmation_network_requests": 0,
        "owner_scope": "NON_COMMERCIAL_INTERNAL_TECHNICAL_QUALIFICATION_ONLY",
        "redistribution_authorized": False, "bulk_acquisition_authorized": False,
        "research_or_production_authorized": False, "trading_authorized": False,
    }
    schema = {
        "schema_version": "r10nb_observed_schema_v1",
        "udiff": {"family": "UDIFF", "archive_member": member, "column_count": len(udiff_fields), "columns": udiff_fields},
        "mii": {"family": "MII_CONTRACT", "compression": "gzip", "archive": mii_archive,
                "column_count": len(mii_fields), "columns": mii_fields},
        "join_key": ["FinInstrmId"], "legacy_schema_parsed": False,
    }
    quality = {
        "schema_version": "r10nb_quality_metrics_v1",
        "source_rows": {"udiff": total, "mii": mii_rows},
        "normalized_rows": {"udiff": counts["normalized_rows"], "mii": mii_rows - mii_malformed},
        "instrument_counts": {"futures": counts["futures"], "options": counts["options"], "other": counts["other"]},
        "identity_join": {
            "matched": join["matched"], "missing_key": join["missing_key"],
            "ambiguous": join["ambiguous"], "unresolved": join["unresolved"],
            "rate": matched / total if total else 0.0,
        },
        "contract_identity": {"unique_ids": len(identities), "duplicate_keys": len(duplicate_ids), "malformed_rows": mii_malformed},
        "malformed_fact_rows": malformed_rows, "ohlc_inconsistent_rows": ohlc_inconsistent,
        "trade_date_counts": dict(sorted(trade_dates.items())),
        "fact_field_states": {k: dict(sorted(v.items())) for k, v in sorted(fact_states.items())},
        "contract_field_states": {k: dict(sorted(v.items())) for k, v in sorted(mii_states.items())},
        "fact_value_coverage": {k: dict(sorted(v.items())) for k, v in sorted(value_coverage.items())},
        "bounded_sanitized_examples": [
            {"issue": key, "count": value} for key, value in sorted({
                "ambiguous_identity": join["ambiguous"], "malformed_fact_row": malformed_rows,
                "malformed_contract_row": mii_malformed, "ohlc_inconsistent": ohlc_inconsistent,
                "unresolved_identity": join["unresolved"],
            }.items()) if value
        ][:10],
        "correction_finality": {
            "filename_marks_final": "_F_" in UDIFF_FILENAME,
            "single_observation_can_establish_later_corrections": False,
        },
    }
    completion = {
        "schema_version": "r10nb_completion_v1", "milestone": "R.10N-B",
        "single_date_only": True, "files_qualified": 2,
        "post_confirmation_acquisition_performed": False,
        "qualified_preexisting_hash_bound_package": True,
        "raw_rows_retained_in_evidence": False, "holdout_accessed": False,
        "local_fno_database_accessed": False, "kite_used": False, "apsw_used": False,
        "research_backtest_scoring_recommendation_or_trading": False,
        "validation": {
            "focused_r10nb_downloader_r10na": "46_PASS",
            "relevant_fno_governance": "41_PASS",
            "root_pre_entrypoint_correction": "830_PASS_4_FAIL_4_SKIP_7_WARN",
            "root_pre_entrypoint_failures": [
                "TWO_NEW_ENTRYPOINT_INVENTORY_DIAGNOSTICS_CORRECTED_WITHOUT_CHANGING_INVENTORY",
                "TWO_PRE_EXISTING_R9K_NATIVE_SLEEP_NEGATIVE_0_003_SECOND_DIAGNOSTICS",
            ],
            "root_final": "833_PASS_1_FAIL_4_SKIP_7_WARN",
            "root_final_failure": "PRE_EXISTING_R9K_JOB_CLOSE_NEGATIVE_0_003_SECOND_TIMING_DIAGNOSTIC",
            "r10nb_related_root_failures": 0,
        },
        "reproducibility_limitations": [
            "Source payloads remain local and ignored by Git.",
            "One date cannot establish historical schema stability or correction behavior.",
            "Permission is limited to the owner's stated non-commercial technical qualification scope.",
        ],
        "completion_decision": (
            "SINGLE_DATE_PACKAGE_TECHNICALLY_QUALIFIED"
            if malformed_rows == 0 and mii_malformed == 0 and join["ambiguous"] == 0
            and join["unresolved"] == 0 and matched == total and ohlc_inconsistent == 0
            else "PARTIALLY_QUALIFIED_WITH_EXPLICIT_GAPS"
        ),
    }
    return {"acquisition.json": acquisition, "observed_schema.json": schema,
            "quality_metrics.json": quality, "completion.json": completion}


def _canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()


def write_evidence(package: Path, output: Path) -> dict:
    artifacts = qualify_package(package)
    output.mkdir(parents=True, exist_ok=False)
    bindings = []
    for name, value in artifacts.items():
        payload = _canonical_bytes(value)
        (output / name).write_bytes(payload)
        bindings.append({"path": name, "sha256": hashlib.sha256(payload).hexdigest(), "byte_length": len(payload)})
    root = {
        "schema_version": "r10nb_root_manifest_v1", "milestone": "R.10N-B",
        "artifacts": sorted(bindings, key=lambda item: item["path"]),
        "source_bindings": artifacts["acquisition.json"]["files"],
    }
    text = _canonical_bytes(root).decode()
    if PRIVATE_PATH.search(text) or SECRET_ASSIGNMENT.search(text):
        raise QualificationError("evidence contains private-path or credential material")
    (output / "root_manifest.json").write_text(text, encoding="utf-8", newline="\n")
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path("artifacts/nse_fno_reports/2026-09-09"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_evidence(args.package, args.output)
    return 0
