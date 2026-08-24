"""Market & Sector Context - stub page (consolidated, 2 tabs). See views/_registry.py
for the full description this page renders; edit metadata there, not
here, so the registry stays the single source of truth."""

from __future__ import annotations

from views._registry import PAGES_BY_FILE
from views._stub import render_stub_multi

meta = PAGES_BY_FILE["views/td_market_sector_context.py"]
render_stub_multi(meta.title, meta.icon, meta.section, meta.subsections)
