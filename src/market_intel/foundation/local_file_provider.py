"""Dry-run adapter for the already-audited local files; no network access."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .canonical_schemas import (BENCHMARK_SCHEMA, CORPORATE_ACTION_SCHEMA, COST_SCHEDULE_SCHEMA,
                                DAILY_EQUITY_SCHEMA, SECURITY_MASTER_SCHEMA, TERMINAL_OUTCOME_SCHEMA)
from .providers import AcquisitionRequest, DatasetKind, ProviderObject
from .raw_ingestion import RawObjectManifest


class LocalAuditedFileProvider:
    provider_id = "local_audited_files_v1"

    def __init__(self, price_dir: Path, industry_map: Path):
        self.price_dir, self.industry_map = Path(price_dir), Path(industry_map)
        self.equity_symbols = set(pd.read_csv(industry_map)["symbol"].astype(str).str.upper())

    def discover(self, request: AcquisitionRequest) -> list[ProviderObject]:
        if request.dataset == DatasetKind.DAILY_EQUITY:
            paths = [p for p in sorted(self.price_dir.glob("*_DAILY.csv"))
                     if p.stem.removesuffix("_DAILY").upper() in self.equity_symbols]
        elif request.dataset == DatasetKind.SECURITY_MASTER:
            paths = [self.industry_map]
        elif request.dataset == DatasetKind.BENCHMARK_HISTORY:
            paths = [self.price_dir / "NIFTY50_DAILY.csv"]
        else:
            paths = []
        return [ProviderObject(self.provider_id, request.dataset, str(path.resolve()), path,
                               request.parameters, request.expected_event_date,
                               "Existing local files; upstream license and retention terms unknown") for path in paths]

    def parser_version(self, dataset: DatasetKind) -> str:
        return f"local_{dataset.value}_parser_v1"

    def normalize(self, dataset: DatasetKind, items: list[tuple[Path, RawObjectManifest]]) -> pd.DataFrame:
        if dataset == DatasetKind.DAILY_EQUITY:
            frames = []
            for path, manifest in items:
                symbol = Path(manifest.source_identity).stem.removesuffix("_DAILY").upper()
                raw = pd.read_csv(path, parse_dates=["date"])
                instrument = "UNRESOLVED:" + hashlib.sha256(f"NSE|{symbol}|unknown".encode()).hexdigest()[:16]
                frame = pd.DataFrame({"trade_date": raw.date, "instrument_id": instrument,
                                      "listing_id": f"UNRESOLVED:NSE:{symbol}", "exchange_symbol": symbol,
                                      "series": "UNKNOWN", "open": raw.open, "high": raw.high, "low": raw.low,
                                      "close": raw.close, "previous_close": pd.NA, "volume": raw.volume,
                                      "exchange_turnover": pd.NA, "trade_count": pd.NA, "published_at": pd.NaT,
                                      "retrieved_at": pd.Timestamp(manifest.retrieval_timestamp).tz_localize(None),
                                      "source_id": self.provider_id, "raw_payload_hash": manifest.content_hash})
                frames.append(frame)
            return DAILY_EQUITY_SCHEMA.validate(pd.concat(frames, ignore_index=True))
        if dataset == DatasetKind.SECURITY_MASTER:
            source = pd.read_csv(items[0][0])
            rows = []
            for symbol in source.symbol.astype(str).str.upper():
                instrument = "UNRESOLVED:" + hashlib.sha256(f"NSE|{symbol}|unknown".encode()).hexdigest()[:16]
                rows.append({"issuer_id": pd.NA, "instrument_id": instrument, "listing_id": f"UNRESOLVED:NSE:{symbol}",
                             "exchange": "NSE", "segment_series": "UNKNOWN", "symbol": symbol, "isin": pd.NA,
                             "valid_from": pd.Timestamp("2000-01-01"), "valid_to": pd.NaT, "listing_date": pd.NaT,
                             "end_date": pd.NaT, "status": "UNRESOLVED_IDENTITY_CURRENT_MAP"})
            return SECURITY_MASTER_SCHEMA.validate(pd.DataFrame(rows))
        if dataset == DatasetKind.BENCHMARK_HISTORY:
            raw = pd.read_csv(items[0][0], parse_dates=["date"])
            frame = pd.DataFrame({"date": raw.date, "index_id": "NIFTY50", "return_classification": "PRI",
                                  "open": raw.open, "close": raw.close, "methodology_version": pd.NA,
                                  "source_id": self.provider_id})
            return BENCHMARK_SCHEMA.validate(frame)
        raise ValueError(f"local dry-run provider has no {dataset.value} dataset")


def empty_canonical(schema) -> pd.DataFrame:
    return schema.validate(pd.DataFrame({name: pd.Series(dtype=dtype) for name, dtype in schema.columns.items()}))


def local_missing_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    costs = pd.DataFrame([{"component": "COMPATIBILITY_ALL_IN", "effective_from": "2026-08-13",
                           "effective_to": pd.NaT, "rate": 0.0, "rate_base": "COMPATIBILITY_MODEL",
                           "source_reference": "Slice A compatibility model", "schedule_version": "india_delivery_2026_08_13_slippage_5bps_v1"}])
    return (empty_canonical(CORPORATE_ACTION_SCHEMA), empty_canonical(TERMINAL_OUTCOME_SCHEMA),
            COST_SCHEDULE_SCHEMA.validate(costs))
