"""Invented minimal JSON, not retained provider data."""
from datetime import datetime, timezone
from .offline_equity_quote_parser_v1 import SyntheticTarget

FIXTURE_VERSION = "full_quote_fixture_v1"
AS_OF = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
RETRIEVAL = datetime(2026, 1, 1, 9, 59, 59, tzinfo=timezone.utc)
TARGETS = (SyntheticTarget("SYNTHETIC:EQUITY_A", 1),)
PAYLOAD = (b'{"status":"success","data":{"SYNTHETIC:EQUITY_A":{'
           b'"instrument_token":1,"last_price":125.500000000000000001,'
           b'"timestamp":"2026-01-01T09:59:58+00:00",'
           b'"last_trade_time":"2026-01-01T09:59:00+00:00"}}}')
