"""Offline synthetic coverage for predicate-level R10N-F diagnosis."""

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
    CandidateAdapterError, adapt_package, build_package_descriptor, expected_package_files,
)
from tools.diagnose_nse_fno_ohlc_r10nf import (
    diagnose_streams, sanitized_identifier,
)


FACT_FIELDS = [
    "TradDt", "FinInstrmTp", "FinInstrmId", "TckrSymb", "XpryDt", "StrkPric", "OptnTp",
    "OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric", "TtlTradgVol", "OpnIntrst",
    "NewBrdLotQty",
]
MII_FIELDS = [
    "FinInstrmId", "XpryDt", "NewBrdLotQty", "MinLot", "StrkPric", "OptnTp",
    "FinInstrmTp", "UndrlygFinInstrmId", "FinInstrmNm", "TckrSymb",
]
DAY = "2026-09-10"


def _fact(**updates) -> dict[str, str]:
    row = {
        "TradDt": DAY, "FinInstrmTp": "STF", "FinInstrmId": "987654321",
        "TckrSymb": "LEAK_TICKER_NEVER_RETAIN", "XpryDt": "2026-09-24",
        "StrkPric": "", "OptnTp": "", "OpnPric": "10", "HghPric": "12",
        "LwPric": "8", "ClsPric": "11", "SttlmPric": "11", "TtlTradgVol": "3",
        "OpnIntrst": "2", "NewBrdLotQty": "25",
    }
    row.update(updates)
    return row


def _contract(**updates) -> dict[str, str]:
    expiry = int((datetime(2026, 9, 24) - datetime(1980, 1, 1)).total_seconds())
    row = {
        "FinInstrmId": "987654321", "XpryDt": str(expiry), "NewBrdLotQty": "25",
        "MinLot": "25", "StrkPric": "", "OptnTp": "XX", "FinInstrmTp": "",
        "UndrlygFinInstrmId": "100", "FinInstrmNm": "SYNTHETIC",
        "TckrSymb": "LEAK_TICKER_NEVER_RETAIN",
    }
    row.update(updates)
    return row


def _csv(fields: list[str], rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _diagnose(facts: list[dict[str, str]], contracts: list[dict[str, str]] | None = None) -> dict:
    return diagnose_streams(
        io.StringIO(_csv(FACT_FIELDS, facts)),
        io.StringIO(_csv(MII_FIELDS, contracts or [_contract()])),
        trading_date=DAY,
    )


@pytest.mark.parametrize(("updates", "predicate"), [
    ({"OpnPric": "11", "HghPric": "10", "LwPric": "9", "ClsPric": "9.5"}, "high_below_open"),
    ({"OpnPric": "9", "HghPric": "10", "LwPric": "8", "ClsPric": "11"}, "high_below_close"),
    ({"OpnPric": "9", "HghPric": "12", "LwPric": "10", "ClsPric": "11"}, "low_above_open"),
    ({"OpnPric": "11", "HghPric": "12", "LwPric": "10", "ClsPric": "9"}, "low_above_close"),
])
def test_each_endpoint_predicate_can_fail_alone(updates: dict[str, str], predicate: str) -> None:
    result = _diagnose([_fact(**updates)])
    assert result["predicate_violations"][predicate] == 1
    assert sum(result["predicate_violations"].values()) == 1


def test_high_below_low_is_counted_independently() -> None:
    result = _diagnose([_fact(OpnPric="9.5", HghPric="9", LwPric="10", ClsPric="9.5")])
    assert result["predicate_violations"]["high_below_low"] == 1
    assert result["totals"]["high_below_low"] == 1


def test_zero_volume_and_nonzero_volume_are_separate() -> None:
    result = _diagnose([
        _fact(TtlTradgVol="0", OpnPric="11", HghPric="10", LwPric="9", ClsPric="9.5"),
        _fact(FinInstrmId="123456789", TtlTradgVol="2", OpnPric="11", HghPric="10",
              LwPric="9", ClsPric="9.5"),
    ], [_contract(), _contract(FinInstrmId="123456789")])
    assert result["totals"]["zero_volume_rows"] == 1
    assert result["totals"]["nonzero_volume_rows"] == 1
    assert result["totals"]["violating_zero_volume_rows"] == 1
    assert result["totals"]["violating_nonzero_volume_rows"] == 1
    assert result["violation_patterns_by_volume"] == {
        "NONZERO|high_below_open": 1, "ZERO|high_below_open": 1,
    }


def test_bounded_examples_reserve_space_for_late_nonzero_violations() -> None:
    facts = [
        _fact(FinInstrmId=str(100000000 + index), TtlTradgVol="0", OpnPric="11",
              HghPric="10", LwPric="9", ClsPric="9.5")
        for index in range(8)
    ]
    facts.append(_fact(FinInstrmId="200000000", TtlTradgVol="2", OpnPric="11",
                       HghPric="10", LwPric="9", ClsPric="9.5"))
    contracts = [_contract(FinInstrmId=row["FinInstrmId"]) for row in facts]
    examples = _diagnose(facts, contracts)["bounded_examples"]
    assert len(examples) == 8
    assert sum(item["volume_state"] == "NONZERO" for item in examples) == 1


def test_nonzero_volume_with_zero_ohlc_and_other_price_is_aggregated() -> None:
    result = _diagnose([_fact(OpnPric="0", HghPric="0", LwPric="0", ClsPric="0",
                                    SttlmPric="1.25", TtlTradgVol="2")])
    assert result["totals"]["ohlc_zero_while_another_price_nonzero"] == 1
    assert result["totals"]["any_ohlc_predicate_violation"] == 0


def test_close_settlement_divergence_and_settlement_range_are_separate() -> None:
    result = _diagnose([_fact(SttlmPric="20")])
    assert result["totals"]["settlement_outside_low_high"] == 1
    assert result["bounded_examples"] == []


def test_sub_paise_precision_is_exact_not_binary_float() -> None:
    result = _diagnose([_fact(OpnPric="1.0001", HghPric="1.0000", LwPric="0.9999", ClsPric="1.0000")])
    example = result["bounded_examples"][0]
    assert example["exact_differences"]["high_minus_open"] == "-0.0001"


def test_futures_and_options_are_aggregated_without_tickers() -> None:
    option = _fact(FinInstrmId="123456789", FinInstrmTp="IDO", StrkPric="100", OptnTp="CE")
    contracts = [_contract(), _contract(FinInstrmId="123456789", StrkPric="100", OptnTp="CE")]
    result = _diagnose([_fact(), option], contracts)
    assert result["instrument_classes"] == {"FUTURES": 1, "OPTIONS": 1}
    assert "LEAK_TICKER_NEVER_RETAIN" not in json.dumps(result)


def test_identifier_hash_is_deterministic_domain_separated_and_sanitized() -> None:
    value = sanitized_identifier("987654321")
    assert value == sanitized_identifier("987654321")
    assert len(value) == 64 and value != hashlib.sha256(b"987654321").hexdigest()
    assert "987654321" not in value


def test_diagnostics_are_deterministic_and_do_not_leak_raw_rows() -> None:
    fact = _fact(OpnPric="11", HghPric="10", LwPric="9", ClsPric="9.5")
    left = _diagnose([fact])
    right = _diagnose([fact])
    assert left == right
    encoded = json.dumps(left, sort_keys=True)
    assert "987654321" not in encoded
    assert "LEAK_TICKER_NEVER_RETAIN" not in encoded
    assert "TckrSymb" not in encoded


def test_diagnostic_path_has_no_network_access(monkeypatch) -> None:
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert _diagnose([_fact()])["totals"]["total_rows"] == 1


def _adapter_package(root: Path, fact: dict[str, str]):
    root.mkdir()
    plan = expected_package_files(date.fromisoformat(DAY))
    zip_path, gzip_path = root / plan[0][1], root / plan[1][1]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(plan[0][1].removesuffix(".zip"), _csv(FACT_FIELDS, [fact]))
    gzip_path.write_bytes(gzip.compress(_csv(MII_FIELDS, [_contract()]).encode(), mtime=0))
    files = []
    for key, filename, url, _ in plan:
        path = root / filename
        files.append({"key": key, "filename": filename, "source_url": url, "resolved_url": url,
                      "byte_length": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"schema_version": "nse_fno_single_date_download_v3", "trading_date": DAY, "files": files}
    return build_package_descriptor(root, trading_date=DAY, manifest=manifest)


def test_r10nh_adapter_classifies_range_anomalies_without_price_mutation(tmp_path: Path) -> None:
    invalid = _fact(OpnPric="11", HghPric="10", LwPric="9", ClsPric="9.5")
    result = adapt_package(_adapter_package(tmp_path / "nonzero", invalid))
    assert result.quality["diagnostic_counts"] == {
        "OPEN_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS": 1,
        "SETTLEMENT_OUTSIDE_DAILY_RANGE_SEPARATE_BASIS": 1,
        "TRADE_STATE_ATTRIBUTION_UNAVAILABLE": 1,
    }
    assert str(result.records[0].open) == "11" and str(result.records[0].high) == "10"
    invalid["TtlTradgVol"] = "0"
    result = adapt_package(_adapter_package(tmp_path / "zero", invalid))
    assert result.quality["diagnostic_counts"] == {"ZERO_VOLUME_PRICE_STATE": 1}


def test_r10nf_historical_adapter_hash_remains_bound_in_sealed_evidence() -> None:
    evidence = Path(__file__).resolve().parents[1] / "docs" / "investigations" / "r10n_f" / "diagnosis_v1" / "failure_reproduction.json"
    assert "93780824f87bd80b67269636fe22b7c11fa2379fbda85537d07565f942e0a6af" in evidence.read_text()
