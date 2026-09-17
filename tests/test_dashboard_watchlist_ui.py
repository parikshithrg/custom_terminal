"""Synthetic-only Dashboard integration and fail-closed presentation checks."""
import ast
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from views import _market_preview
from views._watchlist_contract_view import dashboard_fixture, dashboard_presentation, presentation

ROOT = Path(__file__).resolve().parents[1]


def test_exact_prices_missingness_and_determinism():
    rows, provenance = dashboard_presentation()
    assert (rows, provenance) == dashboard_presentation()
    assert rows[0][1] == "125.500000000000000001"
    assert rows[2][1] == "Unavailable — MISSING_PRICE"
    assert all(row[2] == "Unavailable" for row in rows)
    assert all("SYNTHETIC:WATCHLIST_FIXTURE" in row[3] for row in rows)
    assert "SYNTHETIC_NOT_MARKET_READY" in provenance
    assert "Invented fixture metadata" in provenance
    assert "Not market freshness" in provenance


def test_presentation_performs_no_io(monkeypatch):
    import builtins
    import socket
    import requests
    def denied(*args, **kwargs):
        raise AssertionError("I/O is forbidden for synthetic presentation")
    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    assert len(dashboard_presentation()[0]) == 3


def test_refuses_noncontract_and_tampered_bindings():
    with pytest.raises(ValueError):
        presentation({"mode": "REAL_PROVIDER"})
    envelope = dashboard_fixture(as_of=datetime(2026, 1, 1, 10, tzinfo=timezone.utc))
    original = envelope.to_bytes()
    presentation(envelope)
    assert envelope.to_bytes() == original
    with pytest.raises(ValueError):
        replace(envelope, consumer_id="market_gate")
    object.__setattr__(envelope, "fixture_hash", "0" * 64)
    with pytest.raises(ValueError):
        presentation(envelope)


def test_fail_closed_without_old_price_fallback(monkeypatch):
    import sys
    site = ROOT / ".venv/Lib/site-packages"
    if site.exists() and str(site) not in sys.path:
        sys.path.append(str(site))
    st = pytest.importorskip("streamlit")
    captions, markup = [], []
    monkeypatch.setattr(st, "caption", captions.append)
    monkeypatch.setattr(st, "markdown", lambda value, **kwargs: markup.append(value))
    def invalid():
        raise ValueError("invalid fixture")
    monkeypatch.setattr(_market_preview, "dashboard_presentation", invalid)
    _market_preview.render(use_watchlist_contract=True)
    assert any("No fallback prices" in value for value in captions)
    assert not any("DEMO EQUITY" in value for value in markup)
    _market_preview.render()
    assert any("DEMO EQUITY A" in value for value in markup)


def test_one_consumer_and_pure_boundary():
    assert "render(use_watchlist_contract=True)" in (ROOT / "views/home.py").read_text()
    assert "use_watchlist_contract=True" not in (ROOT / "views/lib_market_gate_home.py").read_text()
    tree = ast.parse((ROOT / "views/_watchlist_contract_view.py").read_text())
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "datetime", "market_intel.dashboard_watchlist_fixtures_v1",
        "market_intel.dashboard_watchlist_read_model_v1"}
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))
    forbidden = {"open", "eval", "exec", "now", "today", "connect", "request", "write_text"}
    assert not any(isinstance(node, ast.Call) and
                   (getattr(node.func, "id", None) in forbidden or
                    getattr(node.func, "attr", None) in forbidden) for node in ast.walk(tree))
