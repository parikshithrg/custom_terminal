"""Offline presentation filtering does not alter source snapshots or gates."""
from datetime import datetime, timezone
from pathlib import Path
from market_intel.foundation.current_market import (
    CurrentInstrument, CurrentInstrumentSnapshot, CurrentQuote, CurrentQuoteSnapshot,
)
from views._cash_scope import cash_inventory, cash_quotes


def test_cash_subset_preserves_originals_and_provenance():
    now = datetime(2026, 9, 17, tzinfo=timezone.utc)
    items = tuple(CurrentInstrument(n, None, str(n), ex, ex, kind, None, None, None, None)
                  for n, ex, kind in [(1,"NSE","EQ"),(2,"NSE","INDICES"),
                                      (3,"NFO","FUT"),(4,"NFO","CE"),(5,"MCX","FUT")])
    inventory = CurrentInstrumentSnapshot("fixture",now,"2026-09-17","fixture","v1",items)
    quotes = CurrentQuoteSnapshot("fixture",now,"fixture",tuple(
        CurrentQuote(item.provider_key,"AVAILABLE",10,None,None) for item in items))
    displayed = cash_inventory(inventory)
    filtered = cash_quotes(quotes, inventory)
    assert len(displayed.instruments)==2 and len(filtered.quotes)==2
    assert len(inventory.instruments)==5 and len(quotes.quotes)==5
    assert displayed.retrieved_at==inventory.retrieved_at and displayed.scope==inventory.scope
    assert filtered.source_endpoint==quotes.source_endpoint and filtered.scope==quotes.scope
    assert cash_inventory(displayed)==displayed
    assert cash_inventory(None) is None and cash_quotes(quotes,None) is None


def test_derivative_paths_hidden_with_code_retained():
    from views._registry import HIDDEN_PAGE_FILES, PAGES
    root = Path(__file__).resolve().parents[1]
    assert all((root/path).is_file() for path in HIDDEN_PAGE_FILES)
    assert not set(p.file for p in PAGES).intersection(HIDDEN_PAGE_FILES)
    preview=(root/"views/_market_preview.py").read_text(encoding="utf-8")
    assert "DEMO_FUTURES =" in preview  # retained, never rendered
    assert "st.radio" not in preview
