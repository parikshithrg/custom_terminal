"""Offline tests for the bounded R.10N-B technical qualification."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from tools.qualify_nse_fno_single_date import (
    EXPECTED_URLS,
    MII_FILENAME,
    QualificationError,
    UDIFF_FILENAME,
    UDIFF_MEMBER,
    open_mii_csv,
    open_udiff_csv,
    parse_value,
    qualify_package,
    write_evidence,
)


UDIFF_FIELDS = [
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt",
    "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric", "OpnIntrst", "TtlTradgVol", "NewBrdLotQty",
]
MII_FIELDS = [
    "FinInstrmId", "FinInstrmNm", "TckrSymb", "XpryDt", "StrkPric",
    "OptnTp", "MinLot", "NewBrdLotQty", "FinInstrmTp",
]


def _csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _facts(rows: list[dict] | None = None) -> bytes:
    return _csv_bytes(UDIFF_FIELDS, rows or [{
        "TradDt": "2026-09-09", "FinInstrmTp": "STF", "FinInstrmId": "101",
        "TckrSymb": "ABC", "XpryDt": "2026-09-24", "StrkPric": "",
        "OptnTp": "", "OpnPric": "10", "HghPric": "12", "LwPric": "9",
        "ClsPric": "11", "SttlmPric": "11", "OpnIntrst": "5",
        "TtlTradgVol": "7", "NewBrdLotQty": "25",
    }])


def _contracts(rows: list[dict] | None = None) -> bytes:
    return _csv_bytes(MII_FIELDS, rows or [{
        "FinInstrmId": "101", "FinInstrmNm": "FUT", "TckrSymb": "ABC",
        "XpryDt": "1789574400", "StrkPric": "", "OptnTp": "XX",
        "MinLot": "25", "NewBrdLotQty": "25", "FinInstrmTp": "STF",
    }])


def _package(root: Path, *, facts: bytes | None = None, contracts: bytes | None = None,
             member: str = UDIFF_MEMBER) -> Path:
    root.mkdir()
    zip_path = root / UDIFF_FILENAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, facts or _facts())
    gzip_path = root / MII_FILENAME
    gzip_path.write_bytes(gzip.compress(contracts or _contracts(), mtime=0))
    files = []
    for path in (zip_path, gzip_path):
        files.append({
            "filename": path.name, "source_url": EXPECTED_URLS[path.name],
            "resolved_url": EXPECTED_URLS[path.name], "byte_length": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    (root / "manifest.json").write_text(json.dumps({
        "trading_date": "2026-09-09", "terms_acknowledged_by_operator": True,
        "files": files,
    }), encoding="utf-8")
    return root


def test_field_parser_preserves_missing_not_applicable_and_malformed() -> None:
    assert parse_value("", "decimal").state == "MISSING"
    assert parse_value("", "decimal", applicable=False).state == "NOT_APPLICABLE"
    assert parse_value("not-a-number", "decimal").state == "MALFORMED"
    assert parse_value("1.5", "integer").state == "MALFORMED"
    assert parse_value("XX", "option").state == "MALFORMED"
    assert parse_value("09-09-2026", "date").state == "MALFORMED"
    assert parse_value("not-an-epoch", "epoch_date").state == "MALFORMED"


def test_udiff_and_mii_are_parsed_independently(tmp_path: Path) -> None:
    result = qualify_package(_package(tmp_path / "package"))
    assert result["observed_schema.json"]["udiff"]["family"] == "UDIFF"
    assert result["observed_schema.json"]["mii"]["family"] == "MII_CONTRACT"
    assert result["observed_schema.json"]["legacy_schema_parsed"] is False


def test_legacy_facts_schema_is_rejected_by_udiff_parser(tmp_path: Path) -> None:
    legacy = _csv_bytes(["INSTRUMENT", "TIMESTAMP"], [{"INSTRUMENT": "FUT", "TIMESTAMP": "09-SEP-2026"}])
    with pytest.raises(QualificationError, match="schema mismatch|legacy"):
        qualify_package(_package(tmp_path / "package", facts=legacy))


@pytest.mark.parametrize("member", ["../escape.csv", "wrong.csv"])
def test_archive_member_must_be_safe_and_exact(tmp_path: Path, member: str) -> None:
    package = _package(tmp_path / "package", member=member)
    with pytest.raises(QualificationError, match="unsafe|unexpected"):
        with open_udiff_csv(package / UDIFF_FILENAME):
            pass


def test_corrupt_and_excessive_gzip_fail_closed(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.gz"
    corrupt.write_bytes(b"\x1f\x8b\x08broken")
    with pytest.raises(QualificationError, match="corrupt"):
        with open_mii_csv(corrupt):
            pass
    bomb = tmp_path / "bomb.gz"
    bomb.write_bytes(gzip.compress(b"A" * 100_000, mtime=0))
    with pytest.raises(QualificationError, match="expansion ratio"):
        with open_mii_csv(bomb):
            pass


def test_missing_duplicate_and_ambiguous_identity_fail_closed(tmp_path: Path) -> None:
    duplicates = _contracts([
        {"FinInstrmId": "101", "FinInstrmNm": "FUT", "TckrSymb": "ABC", "XpryDt": "1789574400",
         "StrkPric": "", "OptnTp": "XX", "MinLot": "25", "NewBrdLotQty": "25", "FinInstrmTp": ""},
        {"FinInstrmId": "101", "FinInstrmNm": "FUT", "TckrSymb": "ABC", "XpryDt": "1792195200",
         "StrkPric": "", "OptnTp": "XX", "MinLot": "25", "NewBrdLotQty": "25", "FinInstrmTp": ""},
    ])
    quality = qualify_package(_package(tmp_path / "package", contracts=duplicates))["quality_metrics.json"]
    assert quality["contract_identity"]["duplicate_keys"] == 1
    assert quality["identity_join"]["ambiguous"] == 1
    assert quality["identity_join"]["matched"] == 0

    base = next(csv.DictReader(io.StringIO(_facts().decode())))
    missing = dict(base, FinInstrmId="")
    unresolved = dict(base, FinInstrmId="999")
    quality = qualify_package(_package(
        tmp_path / "missing-unresolved", facts=_facts([missing, unresolved])
    ))["quality_metrics.json"]
    assert quality["identity_join"]["missing_key"] == 1
    assert quality["identity_join"]["unresolved"] == 1
    assert quality["identity_join"]["matched"] == 0


def test_invalid_numeric_is_counted_not_coerced(tmp_path: Path) -> None:
    row = next(csv.DictReader(io.StringIO(_facts().decode())))
    row["HghPric"] = "bad"
    result = qualify_package(_package(tmp_path / "package", facts=_facts([row])))
    quality = result["quality_metrics.json"]
    assert quality["malformed_fact_rows"] == 1
    assert quality["normalized_rows"]["udiff"] == 0
    assert quality["fact_field_states"]["HghPric"] == {"MALFORMED": 1}


def test_evidence_is_deterministic_sanitized_and_hash_bound(tmp_path: Path) -> None:
    package = _package(tmp_path / "package")
    left, right = tmp_path / "left", tmp_path / "right"
    write_evidence(package, left)
    write_evidence(package, right)
    assert {p.name: p.read_bytes() for p in left.iterdir()} == {p.name: p.read_bytes() for p in right.iterdir()}
    manifest = json.loads((left / "root_manifest.json").read_text())
    for item in manifest["artifacts"]:
        payload = (left / item["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
    combined = "\n".join(path.read_text() for path in left.iterdir()).lower()
    assert "c:\\users\\" not in combined and "/users/" not in combined
    assert not any(word in combined for word in ("authorization:", "cookie:", "password="))


def test_manifest_hash_tampering_is_rejected(tmp_path: Path) -> None:
    package = _package(tmp_path / "package")
    with (package / MII_FILENAME).open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(QualificationError, match="hash or size"):
        qualify_package(package)
