"""Offline compatibility tests for R10N-B through the shared adapter."""

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
    EXPECTED_URLS, MII_FILENAME, QualificationError, UDIFF_FILENAME,
    UDIFF_MEMBER, qualify_package, write_evidence,
)


UDIFF_FIELDS = [
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt",
    "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric", "OpnIntrst", "TtlTradgVol", "NewBrdLotQty",
]
MII_FIELDS = [
    "FinInstrmId", "UndrlygFinInstrmId", "FinInstrmNm", "TckrSymb",
    "XpryDt", "StrkPric", "OptnTp", "MinLot", "NewBrdLotQty", "FinInstrmTp",
]


def _csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def _fact(**updates) -> dict:
    row = {
        "TradDt": "2026-09-09", "FinInstrmTp": "STF", "FinInstrmId": "101",
        "TckrSymb": "ABC", "XpryDt": "2026-09-24", "StrkPric": "", "OptnTp": "",
        "OpnPric": "10", "HghPric": "12", "LwPric": "9", "ClsPric": "11",
        "SttlmPric": "11", "OpnIntrst": "5", "TtlTradgVol": "7", "NewBrdLotQty": "25",
    }
    row.update(updates)
    return row


def _contract(**updates) -> dict:
    row = {
        "FinInstrmId": "101", "UndrlygFinInstrmId": "9001", "FinInstrmNm": "FUT",
        "TckrSymb": "ABC", "XpryDt": "1789574400", "StrkPric": "", "OptnTp": "XX",
        "MinLot": "25", "NewBrdLotQty": "25", "FinInstrmTp": "",
    }
    row.update(updates)
    return row


def _package(root: Path, *, facts: list[dict] | None = None,
             contracts: list[dict] | None = None, member: str = UDIFF_MEMBER) -> Path:
    root.mkdir()
    zip_path = root / UDIFF_FILENAME
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, _csv_bytes(UDIFF_FIELDS, facts or [_fact()]))
    gzip_path = root / MII_FILENAME
    gzip_path.write_bytes(gzip.compress(_csv_bytes(MII_FIELDS, contracts or [_contract()]), mtime=0))
    files = []
    for path in (zip_path, gzip_path):
        files.append({
            "filename": path.name, "source_url": EXPECTED_URLS[path.name],
            "resolved_url": EXPECTED_URLS[path.name], "byte_length": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": "nse_fno_single_date_download_v2",
        "trading_date": "2026-09-09", "terms_acknowledged_by_operator": True,
        "files": files,
    }), encoding="utf-8")
    return root


def test_valid_package_reconciles_through_shared_adapter(tmp_path: Path) -> None:
    result = qualify_package(_package(tmp_path / "package"))
    assert result["observed_schema.json"]["udiff"]["family"] == "UDIFF"
    assert result["observed_schema.json"]["mii"]["family"] == "MII_CONTRACT"
    assert result["quality_metrics.json"]["identity_join"]["rate"] == 1.0


@pytest.mark.parametrize("member", ["../escape.csv", "wrong.csv"])
def test_archive_member_must_be_safe_and_exact(tmp_path: Path, member: str) -> None:
    with pytest.raises(QualificationError, match="UNSAFE|UNEXPECTED"):
        qualify_package(_package(tmp_path / "package", member=member))


def test_identity_failures_are_closed(tmp_path: Path) -> None:
    conflicting = [_contract(), _contract(XpryDt="1792195200")]
    with pytest.raises(QualificationError, match="AMBIGUOUS_IDENTITY"):
        qualify_package(_package(tmp_path / "duplicate", contracts=conflicting))
    with pytest.raises(QualificationError, match="MALFORMED_VALUE"):
        qualify_package(_package(tmp_path / "missing", facts=[_fact(FinInstrmId="")]))
    with pytest.raises(QualificationError, match="UNRESOLVED_IDENTITY"):
        qualify_package(_package(tmp_path / "unresolved", facts=[_fact(FinInstrmId="999")]))


def test_invalid_numeric_is_rejected_not_coerced(tmp_path: Path) -> None:
    with pytest.raises(QualificationError, match="MALFORMED_VALUE"):
        qualify_package(_package(tmp_path / "package", facts=[_fact(HghPric="bad")]))


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
    assert "c:\\users\\" not in combined and "authorization:" not in combined


def test_manifest_hash_tampering_is_rejected(tmp_path: Path) -> None:
    package = _package(tmp_path / "package")
    with (package / MII_FILENAME).open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(QualificationError, match="PACKAGE_SIZE_MISMATCH|PACKAGE_HASH_MISMATCH"):
        qualify_package(package)
