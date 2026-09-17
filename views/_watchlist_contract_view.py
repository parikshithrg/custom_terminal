"""Pure Dashboard presentation boundary for synthetic in-memory evidence only."""
from datetime import datetime, timezone

from market_intel.dashboard_watchlist_fixtures_v1 import FIXTURE_VERSION, equity_records
from market_intel.dashboard_watchlist_read_model_v1 import WatchlistEnvelope, build_watchlist


def dashboard_fixture(*, as_of):
    return build_watchlist(mode="SYNTHETIC", as_of=as_of,
                          fixture_version=FIXTURE_VERSION, records=equity_records())


def presentation(envelope):
    """Validate before exposing rows; never repair values or derive absent fields."""
    if type(envelope) is not WatchlistEnvelope:
        raise ValueError("Dashboard synthetic envelope required")
    envelope.to_bytes()  # Rechecks scope, identity, timestamps and content binding.
    rows = tuple((record.display_symbol,
                  str(record.last_price) if record.last_price is not None
                  else "Unavailable — MISSING_PRICE",
                  "Unavailable",
                  f"Synthetic / no feed · {record.currency} · {record.source_id} · {record.source_record_id}")
                 for record in envelope.records)
    provenance = (f"Invented fixture metadata — {envelope.fixture_version} · "
                  f"as-of {envelope.as_of.isoformat()} · SHA-256 {envelope.fixture_hash} · "
                  f"{envelope.readiness_state}. Not market freshness. "
                  "Demo change unavailable: contract v1 defines no change field.")
    return rows, provenance


def dashboard_presentation():
    # Fixed synthetic cutoff, never the wall clock or a claimed provider time.
    return presentation(dashboard_fixture(
        as_of=datetime(2026, 1, 1, 10, tzinfo=timezone.utc)))
