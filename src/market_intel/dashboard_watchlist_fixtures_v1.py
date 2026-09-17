"""Independent in-memory synthetic fixtures; no approved UI fixture changes."""
from datetime import datetime, timezone
from decimal import Decimal
from .dashboard_watchlist_read_model_v1 import WatchlistRecord

FIXTURE_VERSION = "equity_watchlist_fixture_v1"


def equity_records():
    """All dates, identifiers and values are invented fixture metadata."""
    event = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    publication = datetime(2026, 1, 1, 9, 1, tzinfo=timezone.utc)
    retrieval = datetime(2026, 1, 1, 9, 2, tzinfo=timezone.utc)
    return tuple(WatchlistRecord(
        f"SYNTHETIC:EQUITY_{label}", "SIMULATED", "DEMO_EQUITY", f"DEMO EQUITY {label}",
        "INR", price, "SYNTHETIC:WATCHLIST_FIXTURE", f"SYNTHETIC:RECORD_{label}",
        event, publication, retrieval, None, "MISSING" if price is None else "AVAILABLE",
        ("MISSING_PRICE",) if price is None else (),
    ) for label, price in (("A", Decimal("125.500000000000000001")),
                           ("B", Decimal("840.25")), ("C", None)))
