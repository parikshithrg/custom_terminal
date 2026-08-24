"""Typed normalization for the bounded NSE historical-population sample."""

from __future__ import annotations

import gzip
import io
import zipfile
from pathlib import Path

import pandas as pd


def normalize_mii_security(path: Path, *, snapshot_date: str, content_hash: str,
                           parser_version: str = "nse_mii_security_v1") -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(gzip.decompress(path.read_bytes())), low_memory=False)
    required = {"FinInstrmId", "TckrSymb", "SctySrs", "ISIN", "Xchg", "Sts"}
    missing = required - set(raw)
    if missing:
        raise ValueError(f"unrecognized MII security schema: {sorted(missing)}")
    exchange = raw.Xchg.astype("string").str.strip().fillna("NSE").replace("", "NSE")
    frame = pd.DataFrame({"snapshot_date": pd.Timestamp(snapshot_date), "exchange": exchange,
                          "symbol": raw.TckrSymb.astype("string").str.strip(),
                          "series": raw.SctySrs.astype("string").str.strip(),
                          "isin": raw.ISIN.astype("string").str.strip(),
                          "listing_id": "NSE:" + raw.FinInstrmId.astype("string").str.strip(),
                          "instrument_name": raw.FinInstrmNm.astype("string").str.strip(),
                          "trading_status": raw.Sts.astype("string").str.strip(),
                          "source_id": "NSE_MII_SECURITY", "raw_payload_hash": content_hash,
                          "parser_version": parser_version})
    return frame


def normalize_bhavcopy(path: Path, *, trade_date: str, content_hash: str,
                       parser_version: str = "nse_bhavcopy_router_v2") -> pd.DataFrame:
    body = path.read_bytes()
    if body[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            raw = pd.read_csv(archive.open(archive.namelist()[0]), low_memory=False)
    else:
        raw = pd.read_csv(io.BytesIO(body), low_memory=False)
    names = {str(c).strip().upper(): c for c in raw.columns}
    symbol = names.get("SYMBOL") or names.get("TCKRSYMB")
    series = names.get("SERIES") or names.get("SCTYSRS")
    if not symbol or not series:
        raise ValueError(f"unrecognized bhavcopy schema: {sorted(names)}")
    isin_col = names.get("ISIN")
    frame = pd.DataFrame({"trade_date": pd.Timestamp(trade_date), "exchange": "NSE",
                          "exchange_symbol": raw[symbol].astype("string").str.strip(),
                          "series": raw[series].astype("string").str.strip(),
                          "isin": raw[isin_col].astype("string").str.strip() if isin_col else pd.NA,
                          "source_id": "NSE_BHAVCOPY", "raw_payload_hash": content_hash,
                          "parser_version": parser_version})
    return frame
