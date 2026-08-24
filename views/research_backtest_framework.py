"""Backtesting Framework - stub page. See views/_registry.py for the full description
this page renders; edit metadata there, not here, so the registry stays
the single source of truth."""

from __future__ import annotations

from views._registry import PAGES_BY_FILE
from views._stub import render_stub

meta = PAGES_BY_FILE["views/research_backtest_framework.py"]
render_stub(meta.title, meta.icon, meta.section, meta.description, note=meta.note)
