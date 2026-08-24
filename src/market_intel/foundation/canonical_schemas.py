"""Typed, dataset-specific canonical schemas; deliberately not EAV."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FrameSchema:
    name: str
    version: str
    columns: dict[str, str]
    nullable: frozenset[str] = frozenset()

    def validate(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = set(self.columns) - set(frame.columns)
        if missing:
            raise ValueError(f"{self.name} missing columns: {sorted(missing)}")
        result = frame[list(self.columns)].copy()
        for column, dtype in self.columns.items():
            if dtype == "datetime64[ns]":
                result[column] = pd.to_datetime(result[column], errors="coerce").astype("datetime64[ns]")
            elif dtype == "string":
                result[column] = result[column].astype("string")
            else:
                result[column] = pd.to_numeric(result[column], errors="coerce").astype(dtype)
        bad_nulls = [c for c in self.columns if c not in self.nullable and result[c].isna().any()]
        if bad_nulls:
            raise ValueError(f"{self.name} non-nullable columns contain nulls: {bad_nulls}")
        return result


DAILY_EQUITY_SCHEMA = FrameSchema("daily_equity", "daily_equity_v1", {
    "trade_date": "datetime64[ns]", "instrument_id": "string", "listing_id": "string",
    "exchange_symbol": "string", "series": "string", "open": "float64", "high": "float64",
    "low": "float64", "close": "float64", "previous_close": "float64", "volume": "float64",
    "exchange_turnover": "float64", "trade_count": "float64", "published_at": "datetime64[ns]",
    "retrieved_at": "datetime64[ns]", "source_id": "string", "raw_payload_hash": "string",
}, frozenset({"previous_close", "exchange_turnover", "trade_count", "published_at"}))

SECURITY_MASTER_SCHEMA = FrameSchema("security_master", "security_master_v1", {
    "issuer_id": "string", "instrument_id": "string", "listing_id": "string", "exchange": "string",
    "segment_series": "string", "symbol": "string", "isin": "string", "valid_from": "datetime64[ns]",
    "valid_to": "datetime64[ns]", "listing_date": "datetime64[ns]", "end_date": "datetime64[ns]",
    "status": "string",
}, frozenset({"issuer_id", "isin", "valid_to", "listing_date", "end_date"}))

CORPORATE_ACTION_SCHEMA = FrameSchema("corporate_actions", "corporate_actions_v1", {
    "action_id": "string", "action_type": "string", "instrument_id": "string",
    "announcement_date": "datetime64[ns]", "published_at": "datetime64[ns]",
    "ex_date": "datetime64[ns]", "record_date": "datetime64[ns]", "effective_date": "datetime64[ns]",
    "ratio": "float64", "cash_amount": "float64", "old_identifier": "string",
    "new_identifier": "string", "predecessor_instrument_id": "string", "successor_instrument_id": "string",
}, frozenset({"announcement_date", "published_at", "ex_date", "record_date", "effective_date", "ratio",
              "cash_amount", "old_identifier", "new_identifier", "predecessor_instrument_id", "successor_instrument_id"}))

TERMINAL_OUTCOME_SCHEMA = FrameSchema("terminal_outcomes", "terminal_outcomes_v1", {
    "instrument_id": "string", "listing_id": "string", "suspension_date": "datetime64[ns]",
    "termination_date": "datetime64[ns]", "reason": "string", "final_tradable_price": "float64",
    "cash_consideration": "float64", "security_consideration": "string", "successor_instrument_id": "string",
    "resolution_status": "string",
}, frozenset({"suspension_date", "termination_date", "final_tradable_price", "cash_consideration",
              "security_consideration", "successor_instrument_id"}))

BENCHMARK_SCHEMA = FrameSchema("benchmark_history", "benchmark_history_v1", {
    "date": "datetime64[ns]", "index_id": "string", "return_classification": "string",
    "open": "float64", "close": "float64", "methodology_version": "string", "source_id": "string",
}, frozenset({"open", "methodology_version"}))

COST_SCHEDULE_SCHEMA = FrameSchema("cost_schedules", "cost_schedules_v1", {
    "component": "string", "effective_from": "datetime64[ns]", "effective_to": "datetime64[ns]",
    "rate": "float64", "rate_base": "string", "source_reference": "string", "schedule_version": "string",
}, frozenset({"effective_to"}))
