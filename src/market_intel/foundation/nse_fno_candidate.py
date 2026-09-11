"""Offline NSE F&O paired-report adapter candidate.

The adapter is intentionally isolated from acquisition and application code.
It performs no discovery or network access and is not a production provider.

Date semantics:
* UDiFF trading and expiry dates are exchange-calendar dates without a time
  zone. They are represented as :class:`datetime.date`.
* MII expiry values are Unix seconds and are interpreted as UTC before taking
  the calendar date, matching the qualified R10N-B sample convention.

Market prices and strikes use :class:`decimal.Decimal`; volume, open interest,
and lot size are exact integers. Binary floating point is never introduced.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import re
import stat
import zipfile
import zlib
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterator, Mapping, TextIO
from urllib.parse import urlparse


LIFECYCLE_STATE = "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
SOURCE_FAMILY = "NSE_FO_PAIRED_REPORTS"
SOURCE_VERSION = "UDIFF_V1_MII_CONTRACT_V1"
ARCHIVE_ROOT = "https://nsearchives.nseindia.com/content/fo"
ALLOWED_HOSTS = frozenset({"nsearchives.nseindia.com", "archives.nseindia.com"})
MAX_ARCHIVE_MEMBERS = 8
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_EXPANSION_RATIO = Decimal("250")
CHUNK_BYTES = 128 * 1024

UDIFF_REQUIRED = frozenset({
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt",
    "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric", "OpnIntrst", "TtlTradgVol", "NewBrdLotQty",
})
MII_REQUIRED = frozenset({
    "FinInstrmId", "UndrlygFinInstrmId", "FinInstrmNm", "TckrSymb",
    "XpryDt", "StrkPric", "OptnTp", "MinLot", "NewBrdLotQty",
    "FinInstrmTp",
})
LEGACY_MARKERS = frozenset({"INSTRUMENT", "TIMESTAMP", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP"})
PRICE_FIELDS = ("OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric")
_SENSITIVE_KEYS = (
    "authorization", "cookie", "credential", "password", "secret", "token",
    "request_header", "response_body", "stored_payload",
)
_ABSOLUTE_WINDOWS_PATH = re.compile(r"(?i)^[a-z]:[\\/]")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CandidateAdapterError(RuntimeError):
    """A candidate package failed a closed adapter boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class ValueState(StrEnum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MALFORMED = "MALFORMED"


@dataclass(frozen=True)
class FieldValue:
    state: ValueState
    value: str | int | Decimal | date | None = None

    def deterministic(self) -> dict[str, Any]:
        value = self.value
        if isinstance(value, Decimal):
            value = format(value, "f")
        elif isinstance(value, date):
            value = value.isoformat()
        return {"state": self.state.value, "value": value}


@dataclass(frozen=True)
class PackageFileDescriptor:
    key: str
    filename: str
    official_url: str
    byte_length: int
    sha256: str
    compression: str


@dataclass(frozen=True)
class PackageDescriptor:
    package_dir: Path
    trading_date: date
    manifest_schema_version: str
    files: tuple[PackageFileDescriptor, PackageFileDescriptor]


@dataclass(frozen=True)
class ProvenanceBinding:
    manifest_schema_version: str
    facts_filename: str
    facts_sha256: str
    contracts_filename: str
    contracts_sha256: str

    def deterministic(self) -> dict[str, str]:
        return {
            "manifest_schema_version": self.manifest_schema_version,
            "facts_filename": self.facts_filename,
            "facts_sha256": self.facts_sha256,
            "contracts_filename": self.contracts_filename,
            "contracts_sha256": self.contracts_sha256,
        }


@dataclass(frozen=True)
class ContractIdentity:
    financial_instrument_id: str
    ticker: FieldValue
    underlying_financial_instrument_id: FieldValue
    expiry: date
    strike: FieldValue
    option_type: FieldValue
    lot_size: int


@dataclass(frozen=True)
class NormalizedFnoRecord:
    trading_date: date
    financial_instrument_id: str
    instrument_type: str
    ticker: FieldValue
    underlying_financial_instrument_id: FieldValue
    expiry: date
    strike: FieldValue
    option_type: FieldValue
    lot_size: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    settlement_price: Decimal
    volume: int
    open_interest: int
    source_family: str
    source_version: str
    provenance: ProvenanceBinding

    def deterministic(self) -> dict[str, Any]:
        return {
            "trading_date": self.trading_date.isoformat(),
            "financial_instrument_id": self.financial_instrument_id,
            "instrument_type": self.instrument_type,
            "ticker": self.ticker.deterministic(),
            "underlying_financial_instrument_id": self.underlying_financial_instrument_id.deterministic(),
            "expiry": self.expiry.isoformat(),
            "strike": self.strike.deterministic(),
            "option_type": self.option_type.deterministic(),
            "lot_size": self.lot_size,
            "open": format(self.open, "f"),
            "high": format(self.high, "f"),
            "low": format(self.low, "f"),
            "close": format(self.close, "f"),
            "settlement_price": format(self.settlement_price, "f"),
            "volume": self.volume,
            "open_interest": self.open_interest,
            "source_family": self.source_family,
            "source_version": self.source_version,
            "provenance": self.provenance.deterministic(),
        }


@dataclass(frozen=True)
class AdapterResult:
    lifecycle_state: str
    descriptor: PackageDescriptor
    records: tuple[NormalizedFnoRecord, ...]
    quality: Mapping[str, Any]

    def deterministic_records(self) -> list[dict[str, Any]]:
        return [record.deterministic() for record in self.records]

    def deterministic_quality(self) -> dict[str, Any]:
        return _deterministic_value(self.quality)


def _error(code: str, message: str) -> CandidateAdapterError:
    return CandidateAdapterError(code, message)


def _deterministic_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _deterministic_value(child) for key, child in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_deterministic_value(child) for child in value]
    return value


def parse_iso_trading_date(value: str) -> date:
    if not isinstance(value, str):
        raise _error("INVALID_TRADING_DATE", "trading date must be an explicit ISO string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _error("INVALID_TRADING_DATE", "trading date must use YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise _error("INVALID_TRADING_DATE", "trading date must use canonical YYYY-MM-DD")
    return parsed


def expected_package_files(trading_date: date) -> tuple[tuple[str, str, str, str], ...]:
    yyyymmdd = trading_date.strftime("%Y%m%d")
    ddmmyyyy = trading_date.strftime("%d%m%Y")
    facts = f"BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip"
    contracts = f"NSE_FO_contract_{ddmmyyyy}.csv.gz"
    return (
        ("udiff", facts, f"{ARCHIVE_ROOT}/{facts}", "zip"),
        ("mii", contracts, f"{ARCHIVE_ROOT}/{contracts}", "gzip"),
    )


def _validate_official_url(url: str) -> None:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise _error("MANIFEST_URL_INVALID", "malformed source URL") from exc
    if (parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS
            or port not in (None, 443) or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise _error("MANIFEST_URL_INVALID", "source URL is not allowlisted official HTTPS")


def _validate_sanitized(value: Any, path: str = "manifest") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(marker in normalized for marker in _SENSITIVE_KEYS):
                raise _error("UNSANITIZED_MANIFEST", f"sensitive field at {path}.{key}")
            _validate_sanitized(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str) and not value.lower().startswith("https://"):
        if _ABSOLUTE_WINDOWS_PATH.match(value) or value.startswith(("/", "\\")):
            raise _error("UNSANITIZED_MANIFEST", f"absolute private path at {path}")


def build_package_descriptor(
    package_dir: Path, *, trading_date: str, manifest: Mapping[str, Any],
) -> PackageDescriptor:
    """Build an explicit descriptor; never reads or discovers a manifest."""
    parsed_date = parse_iso_trading_date(trading_date)
    if not isinstance(manifest, Mapping):
        raise _error("MANIFEST_INVALID", "manifest must be a mapping supplied by the caller")
    _validate_sanitized(manifest)
    if manifest.get("trading_date") != trading_date:
        raise _error("MANIFEST_DATE_MISMATCH", "manifest trading date differs from requested date")
    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.startswith("nse_fno_single_date_download_v"):
        raise _error("MANIFEST_SCHEMA_UNSUPPORTED", "unsupported acquisition manifest schema")
    rows = manifest.get("files")
    if not isinstance(rows, list) or len(rows) != 2 or not all(isinstance(row, Mapping) for row in rows):
        raise _error("MANIFEST_FILE_SET_MISMATCH", "manifest must bind exactly two files")
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        name = row.get("filename")
        if not isinstance(name, str) or name in by_name:
            raise _error("MANIFEST_FILE_SET_MISMATCH", "manifest filenames must be unique strings")
        by_name[name] = row
    descriptors: list[PackageFileDescriptor] = []
    expected = expected_package_files(parsed_date)
    if set(by_name) != {item[1] for item in expected}:
        raise _error("FILENAME_DATE_MISMATCH", "manifest filenames do not match the explicit date")
    for key, filename, official_url, compression in expected:
        row = by_name[filename]
        source_url = row.get("source_url") or row.get("official_url")
        resolved_url = row.get("resolved_url", source_url)
        if source_url != official_url or resolved_url != official_url:
            raise _error("MANIFEST_URL_MISMATCH", "manifest URL differs from the exact official URL")
        _validate_official_url(source_url)
        length = row.get("byte_length")
        digest = row.get("sha256")
        if not isinstance(length, int) or isinstance(length, bool) or length <= 0:
            raise _error("MANIFEST_SIZE_INVALID", "manifest byte length must be a positive integer")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise _error("MANIFEST_HASH_INVALID", "manifest SHA-256 must be lowercase hexadecimal")
        descriptors.append(PackageFileDescriptor(key, filename, official_url, length, digest, compression))
    return PackageDescriptor(Path(package_dir), parsed_date, schema_version, tuple(descriptors))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise _error("PACKAGE_FILE_UNREADABLE", "expected package file cannot be read") from exc
    return digest.hexdigest()


def verify_package(descriptor: PackageDescriptor) -> None:
    if not descriptor.package_dir.is_dir():
        raise _error("PACKAGE_DIRECTORY_INVALID", "explicit package directory does not exist")
    for item in descriptor.files:
        path = descriptor.package_dir / item.filename
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise _error("PACKAGE_FILE_UNREADABLE", f"expected {item.key} file is absent") from exc
        if size != item.byte_length:
            raise _error("PACKAGE_SIZE_MISMATCH", f"{item.key} byte length differs from manifest")
        if _sha256(path) != item.sha256:
            raise _error("PACKAGE_HASH_MISMATCH", f"{item.key} SHA-256 differs from manifest")


def _safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or "\x00" in name or "\\" in name or name.startswith("/")
            or ".." in path.parts or (path.parts and re.match(r"^[A-Za-z]:", path.parts[0]))):
        raise _error("UNSAFE_ARCHIVE", "unsafe archive member path")


def _check_expansion(expanded: int, compressed: int) -> None:
    if expanded > MAX_EXPANDED_BYTES:
        raise _error("ARCHIVE_EXPANSION_LIMIT", "expanded bytes exceed the bounded limit")
    if Decimal(expanded) > Decimal(max(1, compressed)) * MAX_EXPANSION_RATIO:
        raise _error("ARCHIVE_EXPANSION_LIMIT", "archive expansion ratio exceeds the bounded limit")


@contextmanager
def _open_udiff(path: Path, expected_member: str) -> Iterator[tuple[TextIO, dict[str, Any]]]:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_ARCHIVE_MEMBERS:
                raise _error("ARCHIVE_MEMBER_COUNT", "UDiFF member count is empty or excessive")
            if len(members) != 1:
                raise _error("UNEXPECTED_ARCHIVE_MEMBER", "UDiFF ZIP must contain exactly one member")
            member = members[0]
            _safe_member(member.filename)
            if member.filename != expected_member or member.is_dir():
                raise _error("UNEXPECTED_ARCHIVE_MEMBER", "UDiFF ZIP member does not match the date")
            if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                raise _error("UNSAFE_ARCHIVE", "encrypted or symbolic-link ZIP member")
            _check_expansion(member.file_size, member.compress_size)
            if archive.testzip() is not None:
                raise _error("CORRUPT_ARCHIVE", "UDiFF CRC validation failed")
            metadata = {
                "member_count": 1, "member_name": member.filename,
                "compressed_bytes": member.compress_size,
                "expanded_bytes": member.file_size, "crc32": f"{member.CRC:08x}",
            }
            with archive.open(member, "r") as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                    yield text, metadata
    except CandidateAdapterError:
        raise
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise _error("CORRUPT_ARCHIVE", "invalid UDiFF ZIP") from exc


def _read_c_string(source, limit: int = 4096) -> bytes:
    value = bytearray()
    while len(value) <= limit:
        byte = source.read(1)
        if not byte:
            raise _error("CORRUPT_ARCHIVE", "truncated GZIP header")
        if byte == b"\x00":
            return bytes(value)
        value.extend(byte)
    raise _error("UNSAFE_ARCHIVE", "GZIP header field exceeds bounded limit")


def _validate_gzip_header(path: Path) -> None:
    with path.open("rb") as source:
        header = source.read(10)
        if len(header) != 10 or header[:3] != b"\x1f\x8b\x08":
            raise _error("CORRUPT_ARCHIVE", "invalid GZIP header")
        flags = header[3]
        if flags & 0xE0:
            raise _error("CORRUPT_ARCHIVE", "reserved GZIP flags")
        if flags & 0x04:
            raw_length = source.read(2)
            if len(raw_length) != 2:
                raise _error("CORRUPT_ARCHIVE", "truncated GZIP extra header")
            extra_length = int.from_bytes(raw_length, "little")
            if extra_length > 4096 or len(source.read(extra_length)) != extra_length:
                raise _error("UNSAFE_ARCHIVE", "unsafe GZIP extra header")
        if flags & 0x08:
            try:
                _safe_member(_read_c_string(source).decode("latin-1"))
            except UnicodeError as exc:
                raise _error("UNSAFE_ARCHIVE", "invalid GZIP member name") from exc
        if flags & 0x10:
            _read_c_string(source)
        if flags & 0x02 and len(source.read(2)) != 2:
            raise _error("CORRUPT_ARCHIVE", "truncated GZIP header checksum")


@contextmanager
def _open_mii(path: Path) -> Iterator[tuple[TextIO, dict[str, int]]]:
    try:
        _validate_gzip_header(path)
        compressed = path.stat().st_size
        expanded = 0
        with gzip.open(path, "rb") as validation:
            for block in iter(lambda: validation.read(CHUNK_BYTES), b""):
                expanded += len(block)
                _check_expansion(expanded, compressed)
        if expanded == 0:
            raise _error("CORRUPT_ARCHIVE", "MII GZIP expands to an empty file")
        metadata = {"member_count": 1, "compressed_bytes": compressed, "expanded_bytes": expanded}
        with gzip.open(path, "rb") as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                yield text, metadata
    except CandidateAdapterError:
        raise
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
        raise _error("CORRUPT_ARCHIVE", "invalid MII GZIP") from exc


def _schema(reader: csv.DictReader, required: frozenset[str], family: str) -> tuple[str, ...]:
    fields = tuple(reader.fieldnames or ())
    if family == "UDIFF" and LEGACY_MARKERS & set(fields):
        raise _error("LEGACY_SCHEMA_REJECTED", "legacy bhavcopy cannot use the UDiFF adapter")
    if len(fields) != len(set(fields)):
        raise _error("DUPLICATE_COLUMNS", f"duplicate {family} header")
    missing = sorted(required - set(fields))
    if missing:
        raise _error("MISSING_REQUIRED_COLUMNS", f"{family} is missing {','.join(missing)}")
    return fields


def _value(raw: str | None, kind: str, *, required: bool = False,
           applicable: bool = True) -> FieldValue:
    if not applicable:
        return FieldValue(ValueState.NOT_APPLICABLE)
    text = (raw or "").strip()
    if not text:
        return FieldValue(ValueState.MALFORMED if required else ValueState.MISSING)
    try:
        if kind == "id":
            if not text.isdigit():
                raise ValueError
            return FieldValue(ValueState.PRESENT, text)
        if kind == "text":
            return FieldValue(ValueState.PRESENT, text)
        if kind == "date":
            parsed = date.fromisoformat(text)
            if parsed.isoformat() != text:
                raise ValueError
            return FieldValue(ValueState.PRESENT, parsed)
        if kind == "epoch_date":
            if not text.isdigit() or len(text) not in {9, 10}:
                raise ValueError
            parsed = datetime.fromtimestamp(int(text), timezone.utc).date()
            if not date(1990, 1, 1) <= parsed <= date(2100, 12, 31):
                raise ValueError
            return FieldValue(ValueState.PRESENT, parsed)
        if kind == "decimal":
            parsed = Decimal(text)
            if not parsed.is_finite():
                raise InvalidOperation
            return FieldValue(ValueState.PRESENT, parsed)
        if kind == "integer":
            parsed = Decimal(text)
            if not parsed.is_finite() or parsed != parsed.to_integral_value():
                raise InvalidOperation
            return FieldValue(ValueState.PRESENT, int(parsed))
        if kind == "option":
            if text not in {"CE", "PE"}:
                raise ValueError
            return FieldValue(ValueState.PRESENT, text)
    except (ValueError, InvalidOperation, OSError, OverflowError):
        return FieldValue(ValueState.MALFORMED)
    raise ValueError(f"unknown candidate parser kind: {kind}")


def _require_present(value: FieldValue, *, field: str, row_number: int, family: str) -> Any:
    if value.state != ValueState.PRESENT:
        raise _error("MALFORMED_VALUE", f"{family} row {row_number} has {value.state.value} {field}")
    return value.value


def _parse_contracts(stream: TextIO) -> tuple[dict[str, ContractIdentity], tuple[str, ...], dict[str, Any]]:
    reader = csv.DictReader(stream)
    fields = _schema(reader, MII_REQUIRED, "MII")
    identities: dict[str, ContractIdentity] = {}
    fingerprints: dict[str, tuple[Any, ...]] = {}
    states: defaultdict[str, Counter] = defaultdict(Counter)
    rows = 0
    for row_number, row in enumerate(reader, 2):
        rows += 1
        if None in row:
            raise _error("ROW_WIDTH_MISMATCH", f"MII row {row_number} exceeds schema width")
        fid = _value(row.get("FinInstrmId"), "id", required=True)
        expiry = _value(row.get("XpryDt"), "epoch_date", required=True)
        lot = _value(row.get("NewBrdLotQty") or row.get("MinLot"), "integer", required=True)
        raw_option = (row.get("OptnTp") or "").strip()
        if raw_option not in {"CE", "PE", "XX"}:
            raise _error("MALFORMED_VALUE", f"MII row {row_number} has invalid option type")
        is_option = raw_option in {"CE", "PE"}
        strike = _value(row.get("StrkPric"), "decimal", required=is_option, applicable=is_option)
        option = _value(row.get("OptnTp"), "option", required=is_option, applicable=is_option)
        ticker = _value(row.get("TckrSymb"), "text")
        underlying = _value(row.get("UndrlygFinInstrmId"), "id")
        parsed = {"id": fid, "expiry": expiry, "lot_size": lot, "strike": strike,
                  "option_type": option, "ticker": ticker, "underlying_id": underlying}
        for name, value in parsed.items():
            states[name][value.state.value] += 1
        malformed_identity = sorted(
            name for name in ("id", "expiry", "lot_size", "strike", "option_type")
            if parsed[name].state == ValueState.MALFORMED
        )
        if malformed_identity:
            raise _error(
                "MALFORMED_VALUE",
                f"MII row {row_number} has malformed {','.join(malformed_identity)}",
            )
        identity = ContractIdentity(
            str(_require_present(fid, field="FinInstrmId", row_number=row_number, family="MII")),
            ticker, underlying,
            _require_present(expiry, field="XpryDt", row_number=row_number, family="MII"),
            strike, option,
            _require_present(lot, field="lot size", row_number=row_number, family="MII"),
        )
        fingerprint = (
            identity.ticker, identity.underlying_financial_instrument_id, identity.expiry,
            identity.strike, identity.option_type, identity.lot_size,
        )
        key = identity.financial_instrument_id
        if key in identities:
            code = "DUPLICATE_IDENTITY" if fingerprints[key] == fingerprint else "AMBIGUOUS_IDENTITY"
            raise _error(code, f"MII identifier {key} is not unique")
        identities[key] = identity
        fingerprints[key] = fingerprint
    if not rows:
        raise _error("EMPTY_SOURCE", "MII contains no records")
    return identities, fields, {
        "source_rows": rows,
        "field_states": {key: dict(sorted(value.items())) for key, value in sorted(states.items())},
    }


def _parse_facts(
    stream: TextIO, *, trading_date: date, identities: Mapping[str, ContractIdentity],
    provenance: ProvenanceBinding,
) -> tuple[tuple[NormalizedFnoRecord, ...], tuple[str, ...], dict[str, Any]]:
    reader = csv.DictReader(stream)
    fields = _schema(reader, UDIFF_REQUIRED, "UDIFF")
    records: list[NormalizedFnoRecord] = []
    states: defaultdict[str, Counter] = defaultdict(Counter)
    instrument_counts = Counter()
    coverage = {name: Counter() for name in ("volume", "settlement_price", "open_interest")}
    seen_fact_ids: set[str] = set()
    for row_number, row in enumerate(reader, 2):
        if None in row:
            raise _error("ROW_WIDTH_MISMATCH", f"UDIFF row {row_number} exceeds schema width")
        raw_type = (row.get("FinInstrmTp") or "").strip()
        if raw_type not in {"STF", "IDF", "STO", "IDO"}:
            raise _error("MALFORMED_VALUE", f"UDIFF row {row_number} has invalid instrument type")
        is_option = raw_type in {"STO", "IDO"}
        parsed = {
            "trading_date": _value(row.get("TradDt"), "date", required=True),
            "financial_instrument_id": _value(row.get("FinInstrmId"), "id", required=True),
            "expiry": _value(row.get("XpryDt"), "date", required=True),
            "strike": _value(row.get("StrkPric"), "decimal", required=is_option, applicable=is_option),
            "option_type": _value(row.get("OptnTp"), "option", required=is_option, applicable=is_option),
            "lot_size": _value(row.get("NewBrdLotQty"), "integer", required=True),
            "ticker": _value(row.get("TckrSymb"), "text"),
            **{name: _value(row.get(source), kind, required=True) for name, source, kind in (
                ("open", "OpnPric", "decimal"), ("high", "HghPric", "decimal"),
                ("low", "LwPric", "decimal"), ("close", "ClsPric", "decimal"),
                ("settlement_price", "SttlmPric", "decimal"),
                ("volume", "TtlTradgVol", "integer"),
                ("open_interest", "OpnIntrst", "integer"),
            )},
        }
        for name, value in parsed.items():
            states[name][value.state.value] += 1
        malformed_fields = sorted(name for name, value in parsed.items() if value.state == ValueState.MALFORMED)
        if malformed_fields:
            raise _error(
                "MALFORMED_VALUE",
                f"UDIFF row {row_number} has malformed {','.join(malformed_fields)}",
            )
        required = ("trading_date", "financial_instrument_id", "expiry", "lot_size", "open", "high",
                    "low", "close", "settlement_price", "volume", "open_interest")
        values = {name: _require_present(parsed[name], field=name, row_number=row_number, family="UDIFF")
                  for name in required}
        if values["trading_date"] != trading_date:
            raise _error("FACT_DATE_MISMATCH", f"UDIFF row {row_number} differs from explicit date")
        fid = str(values["financial_instrument_id"])
        if fid in seen_fact_ids:
            raise _error("DUPLICATE_FACT_IDENTITY", f"UDIFF identifier {fid} is duplicated")
        seen_fact_ids.add(fid)
        identity = identities.get(fid)
        if identity is None:
            raise _error("UNRESOLVED_IDENTITY", f"UDIFF identifier {fid} is absent from MII")
        if values["volume"] > 0:
            if values["high"] < max(values["open"], values["close"], values["low"]):
                raise _error("OHLC_INCONSISTENT", f"UDIFF row {row_number} high is outside range")
            if values["low"] > min(values["open"], values["close"], values["high"]):
                raise _error("OHLC_INCONSISTENT", f"UDIFF row {row_number} low is outside range")
        for name in coverage:
            value = values[name]
            coverage[name]["zero" if value == 0 else "nonzero"] += 1
        instrument_counts["options" if is_option else "futures"] += 1
        records.append(NormalizedFnoRecord(
            trading_date=trading_date, financial_instrument_id=fid, instrument_type=raw_type,
            ticker=parsed["ticker"], underlying_financial_instrument_id=identity.underlying_financial_instrument_id,
            expiry=values["expiry"], strike=parsed["strike"], option_type=parsed["option_type"],
            lot_size=values["lot_size"], open=values["open"], high=values["high"], low=values["low"],
            close=values["close"], settlement_price=values["settlement_price"],
            volume=values["volume"], open_interest=values["open_interest"],
            source_family=SOURCE_FAMILY, source_version=SOURCE_VERSION, provenance=provenance,
        ))
    if not records:
        raise _error("EMPTY_SOURCE", "UDIFF contains no records")
    records.sort(key=lambda item: (int(item.financial_instrument_id), item.instrument_type))
    return tuple(records), fields, {
        "source_rows": len(records), "normalized_rows": len(records),
        "instrument_counts": {key: instrument_counts[key] for key in ("futures", "options")},
        "field_states": {key: dict(sorted(value.items())) for key, value in sorted(states.items())},
        "value_coverage": {key: dict(sorted(value.items())) for key, value in sorted(coverage.items())},
    }


def adapt_package(descriptor: PackageDescriptor) -> AdapterResult:
    """Verify and normalize one explicit paired package without side effects."""
    if not isinstance(descriptor, PackageDescriptor):
        raise _error("DESCRIPTOR_REQUIRED", "caller must supply a PackageDescriptor")
    verify_package(descriptor)
    by_key = {item.key: item for item in descriptor.files}
    facts = by_key["udiff"]
    contracts = by_key["mii"]
    provenance = ProvenanceBinding(
        descriptor.manifest_schema_version, facts.filename, facts.sha256,
        contracts.filename, contracts.sha256,
    )
    with _open_mii(descriptor.package_dir / contracts.filename) as (stream, mii_archive):
        identities, mii_columns, mii_quality = _parse_contracts(stream)
    expected_member = facts.filename.removesuffix(".zip")
    with _open_udiff(descriptor.package_dir / facts.filename, expected_member) as (stream, udiff_archive):
        records, udiff_columns, facts_quality = _parse_facts(
            stream, trading_date=descriptor.trading_date, identities=identities, provenance=provenance,
        )
    quality = MappingProxyType({
        "lifecycle_state": LIFECYCLE_STATE,
        "trading_date": descriptor.trading_date.isoformat(),
        "source_rows": {"udiff": facts_quality["source_rows"], "mii": mii_quality["source_rows"]},
        "normalized_rows": facts_quality["normalized_rows"],
        "identity_join": {"matched": len(records), "missing": 0, "duplicate": 0,
                          "unresolved": 0, "ambiguous": 0, "rate": Decimal("1")},
        "instrument_counts": facts_quality["instrument_counts"],
        "fact_field_states": facts_quality["field_states"],
        "contract_field_states": mii_quality["field_states"],
        "fact_value_coverage": facts_quality["value_coverage"],
        "schemas": {"udiff_columns": udiff_columns, "mii_columns": mii_columns},
        "archives": {"udiff": udiff_archive, "mii": mii_archive},
    })
    return AdapterResult(LIFECYCLE_STATE, descriptor, records, quality)
