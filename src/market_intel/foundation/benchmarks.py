"""Explicit benchmark identity metadata."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    version: str
    symbol: str
    return_type: str
    adjustment_status: str
    source_id: str
    evidence: str


LOCAL_NIFTY50_V1 = BenchmarkDefinition(
    benchmark_id="nifty_50_local_daily",
    version="nifty_50_local_daily_v1",
    symbol="NIFTY50",
    return_type="PRICE_RETURN_INDEX",
    adjustment_status="INDEX_LEVEL_NOT_TOTAL_RETURN",
    source_id="local_dashboard_csv_unknown_upstream_vendor",
    evidence="Filename/fields identify NIFTY 50 OHLC index levels; no TRI or dividend field is present.",
)
