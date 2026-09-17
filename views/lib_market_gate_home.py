"""Market Gate Home - stub page (consolidated, 2 tabs). See views/_registry.py
for the full description this page renders; edit metadata there, not
here, so the registry stays the single source of truth."""

from __future__ import annotations

from views._registry import PAGES_BY_FILE
import streamlit as st
from views._topbar import render_section_tabs
from views import _market_preview

meta = PAGES_BY_FILE["views/lib_market_gate_home.py"]
render_section_tabs(active_section=meta.section)
st.markdown(f"## {meta.icon} {meta.title}")
st.caption("Presentation preview — no market-data adapter connected")
_market_preview.render()
_market_preview.readiness()
