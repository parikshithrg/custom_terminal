"""Bounded official-public qualification; never a bulk acquisition job."""

from __future__ import annotations

import argparse
import io
import json
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from market_intel.foundation.canonical_schemas import validate_row_provenance
from market_intel.foundation.official_http import OfficialHttpClient


OBJECTS = [
    ("nse", "daily_equity", "https://archives.nseindia.com/content/historical/EQUITIES/2012/JAN/cm03JAN2012bhav.csv.zip", ("application/zip",)),
    ("nse", "daily_equity", "https://archives.nseindia.com/content/historical/EQUITIES/2016/JAN/cm04JAN2016bhav.csv.zip", ("application/zip",)),
    ("nse", "daily_equity", "https://archives.nseindia.com/products/content/sec_bhavdata_full_02012020.csv", ("text/csv", "application/octet-stream")),
    ("nse", "daily_equity", "https://archives.nseindia.com/products/content/sec_bhavdata_full_02012024.csv", ("text/csv", "application/octet-stream")),
    ("nse", "terminal_outcomes", "https://nsearchives.nseindia.com/web/mediaattachment/2026-06/Copy_of_List_of_delisted_Companies_20260612152719.xlsx", ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",)),
    ("nse", "symbol_changes", "https://archives.nseindia.com/content/circulars/CML58016.pdf", ("application/pdf",)),
]


def _read_xlsx_first_rows(path: Path, limit: int = 3) -> pd.DataFrame:
    """Tiny read-only OOXML reader so qualification adds no spreadsheet dependency."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", ns))
                      for item in root.findall("m:si", ns)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    values = []
    for row in sheet.findall(".//m:sheetData/m:row", ns):
        cells = []
        for cell in row.findall("m:c", ns):
            value = cell.find("m:v", ns)
            raw = value.text if value is not None else ""
            cells.append(shared[int(raw)] if cell.get("t") == "s" and raw else raw)
        values.append(cells)
        if len(values) >= limit + 1:
            break
    width = max(map(len, values))
    values = [row + [""] * (width - len(row)) for row in values]
    return pd.DataFrame(values[1:], columns=values[0])


def _read_equity(path: Path, url: str, digest: str) -> pd.DataFrame:
    data = path.read_bytes()
    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            raw = pd.read_csv(archive.open(archive.namelist()[0]))
        names = {c.upper().strip(): c for c in raw.columns}
        frame = pd.DataFrame({"trade_date": pd.to_datetime(raw[names["TIMESTAMP"]], dayfirst=True),
                              "symbol": raw[names["SYMBOL"]].astype(str).str.strip(),
                              "series": raw[names["SERIES"]].astype(str).str.strip(),
                              "open": raw[names["OPEN"]], "high": raw[names["HIGH"]], "low": raw[names["LOW"]],
                              "close": raw[names["CLOSE"]], "previous_close": raw[names["PREVCLOSE"]],
                              "volume": raw[names["TOTTRDQTY"]], "exchange_turnover": raw[names["TOTTRDVAL"]]})
        parser = "nse_legacy_cm_bhavcopy_v1"
    else:
        raw = pd.read_csv(io.BytesIO(data))
        names = {c.upper().strip(): c for c in raw.columns}
        frame = pd.DataFrame({"trade_date": pd.to_datetime(raw[names["DATE1"]], dayfirst=True),
                              "symbol": raw[names["SYMBOL"]].astype(str).str.strip(),
                              "series": raw[names["SERIES"]].astype(str).str.strip(),
                              "open": raw[names["OPEN_PRICE"]], "high": raw[names["HIGH_PRICE"]],
                              "low": raw[names["LOW_PRICE"]], "close": raw[names["CLOSE_PRICE"]],
                              "previous_close": raw[names["PREV_CLOSE"]], "volume": raw[names["TTL_TRD_QNTY"]],
                              "exchange_turnover": raw[names["TURNOVER_LACS"]] * 100000.0})
        parser = "nse_sec_bhavdata_full_v1"
    frame = frame[(frame.series == "EQ") & frame.symbol.isin({"INFY", "RELIANCE", "TCS"})].copy()
    frame["source_id"], frame["raw_payload_hash"], frame["parser_version"] = "NSE", digest, parser
    validate_row_provenance(frame)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("artifacts/public_qualification/raw"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/public_qualification/v1"))
    args = parser.parse_args()
    client = OfficialHttpClient(allowed_hosts={"archives.nseindia.com", "nsearchives.nseindia.com"},
        user_agent="custom-terminal-public-qualification/1.0 (bounded research sample)", minimum_interval_seconds=1.0)
    results, price_parts = [], []
    for org, dataset, url, types in OBJECTS:
        result = client.retrieve(organization=org, dataset=dataset, url=url, raw_root=args.raw_root,
                                 parser_version="qualification_router_v1", expected_content_types=types)
        results.append({"dataset": dataset, "url": url, **result.__dict__})
        if result.outcome == "SUCCEEDED" and dataset == "daily_equity":
            price_parts.append(_read_equity(Path(result.payload_path), url, result.content_hash))
    args.output.mkdir(parents=True, exist_ok=True)
    prices = pd.concat(price_parts, ignore_index=True) if price_parts else pd.DataFrame()
    prices.to_parquet(args.output / "sample_daily_observations.parquet", index=False)

    delisted_result = next((r for r in results if r["dataset"] == "terminal_outcomes" and r["outcome"] == "SUCCEEDED"), None)
    terminals = pd.DataFrame()
    if delisted_result:
        raw = _read_xlsx_first_rows(Path(delisted_result["payload_path"]), 3)
        terminals = raw.head(3).copy()
        terminals["source_id"] = "NSE"
        terminals["raw_payload_hash"] = delisted_result["content_hash"]
        terminals["parser_version"] = "nse_delisted_workbook_sample_v1"
        validate_row_provenance(terminals)
        terminals.to_parquet(args.output / "sample_terminal_records.parquet", index=False)
        normalized_terminals = pd.DataFrame({
            "instrument_id": terminals["ISIN"].map(lambda x: "isin:" + str(x)),
            "listing_id": terminals["ISIN"].map(lambda x: "NSE:" + str(x)),
            "isin": terminals["ISIN"], "symbol": terminals["Symbol"],
            "termination_date": pd.Timestamp("1899-12-30") + pd.to_timedelta(pd.to_numeric(terminals["Delisted Date"]), unit="D"),
            "reason": terminals["Type of Delisting"], "final_tradable_price": pd.NA,
            "cash_consideration": pd.NA, "successor_instrument_id": pd.NA,
            "resolution_status": "UNRESOLVED", "source_id": "NSE",
            "raw_payload_hash": delisted_result["content_hash"], "parser_version": "nse_delisted_workbook_sample_v1"})
        validate_row_provenance(normalized_terminals)
        normalized_terminals.to_parquet(args.output / "normalized_terminal_outcomes.parquet", index=False)

    transition_result = next((r for r in results if r["dataset"] == "symbol_changes" and r["outcome"] == "SUCCEEDED"), None)
    aliases = pd.DataFrame()
    if transition_result:
        aliases = pd.DataFrame([{"old_symbol": "ADANITRANS", "new_symbol": "ADANIENSOL",
            "effective_date": pd.Timestamp("2023-08-24"), "source_id": "NSE",
            "raw_payload_hash": transition_result["content_hash"], "parser_version": "nse_symbol_circular_cml58016_v1"}])
        validate_row_provenance(aliases)
        aliases.to_parquet(args.output / "sample_alias_transition.parquet", index=False)

    identities = pd.DataFrame([
        {"issuer_id": pd.NA, "instrument_id": f"unresolved:NSE:{symbol}", "listing_id": f"unresolved:NSE:{symbol}",
         "exchange": "NSE", "series": "EQ", "symbol": symbol, "isin": pd.NA,
         "valid_from": prices.loc[prices.symbol == symbol, "trade_date"].min(), "valid_to": pd.NaT,
         "identity_status": "UNRESOLVED", "source_id": "NSE",
         "raw_payload_hash": "|".join(sorted(prices.loc[prices.symbol == symbol, "raw_payload_hash"].unique())),
         "parser_version": "nse_bhavcopy_identity_observation_v1"} for symbol in sorted(prices.symbol.unique())])
    if not identities.empty:
        validate_row_provenance(identities)
        identities.to_parquet(args.output / "normalized_security_identities.parquet", index=False)
    listing_events = normalized_terminals[["instrument_id", "listing_id", "symbol", "termination_date", "reason",
                                            "source_id", "raw_payload_hash", "parser_version"]].copy() if delisted_result else pd.DataFrame()
    if not listing_events.empty:
        listing_events["event_type"] = "DELISTED"
        listing_events.to_parquet(args.output / "normalized_listing_status_events.parquet", index=False)
    for name, columns in {
        "normalized_corporate_actions": ["action_type", "published_at", "effective_date", "source_id", "raw_payload_hash", "parser_version"],
        "normalized_benchmark_observations": ["date", "index_id", "return_classification", "source_id", "raw_payload_hash", "parser_version"],
        "normalized_statutory_costs": ["component", "effective_from", "effective_to", "rate", "source_id", "raw_payload_hash", "parser_version"],
    }.items():
        pd.DataFrame(columns=columns).to_parquet(args.output / f"{name}.parquet", index=False)

    successes = sum(r["outcome"] == "SUCCEEDED" for r in results)
    qualification = {
        "qualification_version": "official_public_qualification_v1", "retrievals": results,
        "source_feasibility": "PARTIAL", "sample_qualification": {
            "continuous_equities": {"status": "PASS" if prices.symbol.nunique() >= 3 else "FAIL", "count": int(prices.symbol.nunique())},
            "historical_trading_dates": {"status": "FAIL", "count": int(prices.trade_date.nunique()), "required": 4},
            "delisted_securities": {"status": "PASS" if len(terminals) >= 3 else "FAIL", "count": len(terminals)},
            "merger_ticker_isin_transitions": {"status": "FAIL", "count": len(aliases), "required": 3},
            **{name: {"status": "UNKNOWN", "count": 0, "reason": "No bounded authoritative raw object qualified"}
               for name in ("split", "bonus", "dividend", "rights", "demerger")}},
        "production_historical_coverage": "FAIL",
        "readiness_decision": "public sources remain insufficient without manual evidence collection"}
    (args.output / "qualification.json").write_text(json.dumps(qualification, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"successful_objects": successes, "price_rows": len(prices), "terminal_rows": len(terminals),
                      "decision": qualification["readiness_decision"]}))


if __name__ == "__main__":
    main()
