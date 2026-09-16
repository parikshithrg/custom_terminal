"""Fully synthetic tests for the date-agnostic NSE F&O candidate adapter."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import socket
import zipfile
from datetime import date, datetime
from pathlib import Path

import pytest

from market_intel.foundation.nse_fno_candidate import (
    LIFECYCLE_STATE,
    OHLC_SEMANTICS_VERSION,
    CandidateAdapterError,
    ValueState,
    adapt_package,
    build_package_descriptor,
    decode_mii_expiry,
    expected_package_files,
)


FACT_FIELDS = [
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt",
    "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
    "SttlmPric", "OpnIntrst", "TtlTradgVol", "NewBrdLotQty",
]
MII_FIELDS = [
    "FinInstrmId", "UndrlygFinInstrmId", "FinInstrmNm", "TckrSymb",
    "XpryDt", "StrkPric", "OptnTp", "MinLot", "NewBrdLotQty", "FinInstrmTp",
]


def _csv(fields: list[str], rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _epoch(day: str) -> str:
    parsed = date.fromisoformat(day)
    return str(int((datetime(parsed.year, parsed.month, parsed.day) - datetime(1980, 1, 1)).total_seconds()))


def _future(day: str, fid: str = "101", **updates) -> dict:
    row = {
        "TradDt": day, "FinInstrmTp": "STF", "FinInstrmId": fid,
        "TckrSymb": "ALPHA", "XpryDt": day, "StrkPric": "", "OptnTp": "",
        "OpnPric": "10.10", "HghPric": "12.20", "LwPric": "9.05", "ClsPric": "11.15",
        "SttlmPric": "0", "OpnIntrst": "0", "TtlTradgVol": "0", "NewBrdLotQty": "25",
    }
    row.update(updates)
    return row


def _option(day: str, fid: str = "202", **updates) -> dict:
    row = _future(day, fid, FinInstrmTp="IDO", TckrSymb="INDEX", StrkPric="123.45",
                  OptnTp="CE", SttlmPric="1.25", OpnIntrst="10", TtlTradgVol="3")
    row.update(updates)
    return row


def _contract(day: str, fid: str = "101", *, option: bool = False, **updates) -> dict:
    row = {
        "FinInstrmId": fid, "UndrlygFinInstrmId": "9001", "FinInstrmNm": "SYNTHETIC",
        "TckrSymb": "INDEX" if option else "ALPHA", "XpryDt": _epoch(day),
        "StrkPric": "123.45" if option else "", "OptnTp": "CE" if option else "XX",
        "MinLot": "25", "NewBrdLotQty": "25", "FinInstrmTp": "",
    }
    row.update(updates)
    return row


def _package(
    root: Path, day: str, *, facts: list[dict] | None = None,
    contracts: list[dict] | None = None, fact_fields: list[str] | None = None,
    mii_fields: list[str] | None = None, member: str | None = None,
    raw_zip: bytes | None = None, raw_gzip: bytes | None = None,
    manifest_mutator=None,
):
    root.mkdir(parents=True)
    plan = expected_package_files(date.fromisoformat(day))
    facts_name, contracts_name = plan[0][1], plan[1][1]
    zip_path, gzip_path = root / facts_name, root / contracts_name
    if raw_zip is None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(member or facts_name.removesuffix(".zip"), _csv(
                fact_fields or FACT_FIELDS,
                facts if facts is not None else [_future(day), _option(day)],
            ))
        raw_zip = buffer.getvalue()
    if raw_gzip is None:
        raw_gzip = gzip.compress(_csv(
            mii_fields or MII_FIELDS,
            contracts if contracts is not None else [_contract(day), _contract(day, "202", option=True)],
        ), mtime=0)
    zip_path.write_bytes(raw_zip)
    gzip_path.write_bytes(raw_gzip)
    rows = []
    for key, filename, url, _ in plan:
        path = root / filename
        rows.append({
            "key": key, "filename": filename, "source_url": url, "resolved_url": url,
            "byte_length": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest = {"schema_version": "nse_fno_single_date_download_v2", "trading_date": day, "files": rows}
    if manifest_mutator:
        manifest_mutator(manifest)
    descriptor = build_package_descriptor(root, trading_date=day, manifest=manifest)
    return descriptor, manifest


@pytest.mark.parametrize("day", ["2026-09-09", "2026-10-14"])
def test_two_dates_prove_no_fixed_date_and_network_is_never_used(tmp_path: Path, monkeypatch, day: str) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    result = adapt_package(_package(tmp_path / day, day)[0])
    assert result.lifecycle_state == LIFECYCLE_STATE == "CANDIDATE_NOT_PRODUCTION_AUTHORIZED"
    assert {record.trading_date.isoformat() for record in result.records} == {day}
    assert result.quality["instrument_counts"] == {"futures": 1, "options": 1}


def test_exact_decimal_zero_coverage_and_missing_vs_not_applicable(tmp_path: Path) -> None:
    day = "2026-09-09"
    facts = [_future(day, TckrSymb="")]
    contracts = [_contract(day, TckrSymb="", UndrlygFinInstrmId="")]
    record = adapt_package(_package(tmp_path / "package", day, facts=facts, contracts=contracts)[0]).records[0]
    assert str(record.open) == "10.10" and isinstance(record.open.as_tuple().digits, tuple)
    assert record.volume == record.open_interest == 0 and str(record.settlement_price) == "0"
    assert record.strike.state == record.option_type.state == ValueState.NOT_APPLICABLE
    assert record.ticker.state == record.underlying_financial_instrument_id.state == ValueState.MISSING


@pytest.mark.parametrize("field,value", [
    ("OpnPric", "bad"), ("TtlTradgVol", "1.5"), ("TradDt", "09-09-2026"),
    ("XpryDt", "not-a-date"), ("NewBrdLotQty", "2.5"), ("OptnTp", "XX"),
])
def test_malformed_fact_values_fail_closed(tmp_path: Path, field: str, value: str) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError, match="MALFORMED_VALUE"):
        adapt_package(_package(tmp_path / field, day, facts=[_option(day, **{field: value})])[0])


def test_duplicate_and_conflicting_contract_identities_are_distinct_failures(tmp_path: Path) -> None:
    day = "2026-09-09"
    duplicate = [_contract(day), _contract(day)]
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / "duplicate", day, facts=[_future(day)], contracts=duplicate)[0])
    assert caught.value.code == "DUPLICATE_IDENTITY"
    conflict = [_contract(day), _contract(day, NewBrdLotQty="50")]
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / "conflict", day, facts=[_future(day)], contracts=conflict)[0])
    assert caught.value.code == "AMBIGUOUS_IDENTITY"


def test_duplicate_fact_identity_and_malformed_contract_value_fail_closed(tmp_path: Path) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / "facts", day, facts=[_future(day), _future(day)])[0])
    assert caught.value.code == "DUPLICATE_FACT_IDENTITY"
    with pytest.raises(CandidateAdapterError, match="MALFORMED_VALUE"):
        adapt_package(_package(tmp_path / "contract", day,
                               facts=[_option(day)], contracts=[_contract(day, "202", option=True, StrkPric="bad")])[0])


def test_missing_and_unresolved_join_keys_fail_closed(tmp_path: Path) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError, match="MALFORMED_VALUE"):
        adapt_package(_package(tmp_path / "missing", day, facts=[_future(day, FinInstrmId="")])[0])
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / "unresolved", day, facts=[_future(day, "999")])[0])
    assert caught.value.code == "UNRESOLVED_IDENTITY"


def test_legacy_schema_is_explicitly_rejected(tmp_path: Path) -> None:
    day = "2026-09-09"
    fields = ["INSTRUMENT", "TIMESTAMP"]
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / "legacy", day, fact_fields=fields,
                               facts=[{"INSTRUMENT": "FUT", "TIMESTAMP": day}])[0])
    assert caught.value.code == "LEGACY_SCHEMA_REJECTED"


def test_filename_date_and_manifest_hash_mismatch_fail_before_parsing(tmp_path: Path) -> None:
    day = "2026-09-09"
    descriptor, manifest = _package(tmp_path / "filename", day)
    manifest["trading_date"] = "2026-09-10"
    with pytest.raises(CandidateAdapterError, match="MANIFEST_DATE_MISMATCH"):
        build_package_descriptor(descriptor.package_dir, trading_date=day, manifest=manifest)
    descriptor, manifest = _package(tmp_path / "wrong-name", day)
    manifest["files"][0]["filename"] = "BhavCopy_NSE_FO_0_0_0_20260910_F_0000.csv.zip"
    with pytest.raises(CandidateAdapterError, match="FILENAME_DATE_MISMATCH"):
        build_package_descriptor(descriptor.package_dir, trading_date=day, manifest=manifest)
    descriptor, _ = _package(tmp_path / "hash", day)
    (descriptor.package_dir / descriptor.files[0].filename).write_bytes(b"changed")
    with pytest.raises(CandidateAdapterError, match="PACKAGE_SIZE_MISMATCH|PACKAGE_HASH_MISMATCH"):
        adapt_package(descriptor)


def test_unsafe_and_corrupt_archives_fail_closed(tmp_path: Path) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError, match="UNSAFE_ARCHIVE"):
        adapt_package(_package(tmp_path / "unsafe", day, member="../escape.csv")[0])
    with pytest.raises(CandidateAdapterError, match="CORRUPT_ARCHIVE"):
        adapt_package(_package(tmp_path / "corrupt", day, raw_gzip=b"not-gzip")[0])


def test_schema_additions_and_reordered_columns_are_accepted(tmp_path: Path) -> None:
    day = "2026-09-09"
    fact_fields = ["SyntheticAddition", *reversed(FACT_FIELDS)]
    mii_fields = [*reversed(MII_FIELDS), "SyntheticAddition"]
    result = adapt_package(_package(tmp_path / "package", day,
                                   fact_fields=fact_fields, mii_fields=mii_fields)[0])
    assert len(result.records) == 2
    assert "SyntheticAddition" in result.quality["schemas"]["udiff_columns"]


@pytest.mark.parametrize("family", ["udiff", "mii"])
def test_missing_required_columns_are_rejected(tmp_path: Path, family: str) -> None:
    day = "2026-09-09"
    kwargs = {"fact_fields": FACT_FIELDS[:-1]} if family == "udiff" else {"mii_fields": MII_FIELDS[:-1]}
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(tmp_path / family, day, **kwargs)[0])
    assert caught.value.code == "MISSING_REQUIRED_COLUMNS"


def test_manifest_must_be_sanitized_and_extra_files_are_not_discovered(tmp_path: Path) -> None:
    day = "2026-09-09"
    descriptor, manifest = _package(tmp_path / "dirty", day)
    manifest["request_headers"] = {"Authorization": "secret"}
    with pytest.raises(CandidateAdapterError) as caught:
        build_package_descriptor(descriptor.package_dir, trading_date=day, manifest=manifest)
    assert caught.value.code == "UNSANITIZED_MANIFEST"
    descriptor, manifest = _package(tmp_path / "private-path", day)
    manifest["local_path"] = "D:\\private\\package.zip"
    with pytest.raises(CandidateAdapterError, match="UNSANITIZED_MANIFEST"):
        build_package_descriptor(descriptor.package_dir, trading_date=day, manifest=manifest)
    descriptor, _ = _package(tmp_path / "explicit", day)
    (descriptor.package_dir / "unrelated.zip").write_bytes(b"ignored")
    assert len(adapt_package(descriptor).records) == 2


def test_normalized_records_are_deterministic_and_provenance_bound(tmp_path: Path) -> None:
    day = "2026-09-09"
    descriptor, _ = _package(tmp_path / "package", day)
    left = adapt_package(descriptor).deterministic_records()
    right = adapt_package(descriptor).deterministic_records()
    assert left == right
    assert [row["financial_instrument_id"] for row in left] == ["101", "202"]
    assert all(row["source_family"] == "NSE_FO_PAIRED_REPORTS" for row in left)
    assert all(row["provenance"]["facts_sha256"] == descriptor.files[0].sha256 for row in left)
    assert adapt_package(descriptor).deterministic_quality() == adapt_package(descriptor).deterministic_quality()
    assert adapt_package(descriptor).deterministic_quality()["identity_join"]["rate"] == "1"


def test_nse_1980_expiry_decoder_is_exact_timezone_free_and_leap_safe() -> None:
    for expected in (date(2000, 2, 29), date(2026, 9, 24), date(2100, 12, 31)):
        seconds = int((datetime.combine(expected, datetime.min.time()) - datetime(1980, 1, 1)).total_seconds())
        assert decode_mii_expiry(str(seconds)) == expected
        assert decode_mii_expiry(str(seconds + 86399)) == expected
    for invalid in ("", "0", "-1", "+1", "1.0", "１２３", "999999999999999999999"):
        with pytest.raises(ValueError):
            decode_mii_expiry(invalid)


def test_expiry_agreement_is_required_for_every_joined_record(tmp_path: Path) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(
            tmp_path / "mismatch", day, facts=[_future(day)],
            contracts=[_contract("2026-09-10")],
        )[0])
    assert caught.value.code == "MII_EXPIRY_MISMATCH"


def test_versioned_ohlc_diagnostics_are_countable_and_do_not_mutate_prices(tmp_path: Path) -> None:
    day = "2026-09-09"
    fact = _future(day, OpnPric="13.00", HghPric="12.00", LwPric="9.00",
                   ClsPric="8.00", SttlmPric="14.00", TtlTradgVol="7")
    result = adapt_package(_package(
        tmp_path / "diagnostics", day, facts=[fact], contracts=[_contract(day)],
    )[0])
    assert result.quality["semantics_contract"]["version"] == OHLC_SEMANTICS_VERSION
    assert result.quality["diagnostic_counts"] == {
        "CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS": 1,
        "OPEN_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS": 1,
        "SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS": 1,
        "TRADE_STATE_ATTRIBUTION_UNAVAILABLE": 1,
    }
    assert result.quality["qualification"] == {
        "source_qualified": False,
        "blocking_diagnostic_count": 3,
        "informational_diagnostic_count": 1,
    }
    record = result.records[0]
    assert tuple(map(str, (record.open, record.high, record.low, record.close, record.settlement_price))) == (
        "13.00", "12.00", "9.00", "8.00", "14.00",
    )


@pytest.mark.parametrize(("updates", "code"), [
    ({"HghPric": "8", "LwPric": "9"}, "HIGH_BELOW_LOW"),
    ({"TtlTradgVol": "-1"}, "NEGATIVE_TOTAL_TRADED_QUANTITY"),
])
def test_structural_price_and_volume_errors_remain_fatal(
    tmp_path: Path, updates: dict, code: str,
) -> None:
    day = "2026-09-09"
    with pytest.raises(CandidateAdapterError) as caught:
        adapt_package(_package(
            tmp_path / code, day, facts=[_future(day, **updates)], contracts=[_contract(day)],
        )[0])
    assert caught.value.code == code


@pytest.mark.parametrize("close", ["13.00", "8.00"])
def test_close_above_high_and_below_low_are_blocking_diagnostics(tmp_path: Path, close: str) -> None:
    day = "2026-09-09"
    result = adapt_package(_package(
        tmp_path / close, day,
        facts=[_future(day, ClsPric=close, SttlmPric="10", TtlTradgVol="1")],
        contracts=[_contract(day)],
    )[0])
    assert result.quality["diagnostic_counts"]["CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS"] == 1
    assert result.quality["qualification"]["blocking_diagnostic_count"] == 2


@pytest.mark.parametrize(("open_price", "high", "low", "close", "settlement"), [
    ("0", "0", "0", "0", "0"),
    ("0", "0", "0", "7.25", "7.25"),
    ("8", "12", "7", "11", "10"),
])
def test_zero_volume_is_one_visible_state_not_a_traded_range(
    tmp_path: Path, open_price: str, high: str, low: str, close: str, settlement: str,
) -> None:
    day = "2026-09-09"
    result = adapt_package(_package(
        tmp_path / f"zero-{close}", day,
        facts=[_future(day, OpnPric=open_price, HghPric=high, LwPric=low, ClsPric=close,
                       SttlmPric=settlement, TtlTradgVol="0")],
        contracts=[_contract(day)],
    )[0])
    assert result.quality["diagnostic_counts"] == {"ZERO_VOLUME_PRICE_STATE": 1}
    assert result.quality["qualification"]["blocking_diagnostic_count"] == 0


def test_diagnostic_order_is_exact_and_deterministic(tmp_path: Path) -> None:
    day = "2026-09-09"
    descriptor, _ = _package(
        tmp_path / "ordered", day,
        facts=[_future(day, OpnPric="13", HghPric="12", LwPric="9", ClsPric="8",
                       SttlmPric="14", TtlTradgVol="1")],
        contracts=[_contract(day)],
    )
    expected = [
        "OPEN_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS",
        "CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS",
        "SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS",
        "TRADE_STATE_ATTRIBUTION_UNAVAILABLE",
    ]
    assert [item["code"] for item in adapt_package(descriptor).quality["diagnostics"]] == expected
    assert adapt_package(descriptor).deterministic_quality() == adapt_package(descriptor).deterministic_quality()
