"""Offline-only News & Calendar shell; legacy execution is not imported."""
import streamlit as st
from market_intel.news_readiness_v1 import assess_news_readiness
from views._registry import PAGES_BY_FILE
from views._theme import empty_panel

meta = PAGES_BY_FILE["views/news_feed_calendar.py"]
readiness = assess_news_readiness()  # Session flags cannot enable a source.
st.markdown(f"## {meta.icon} {meta.title}")
st.caption("Offline readiness view · no news provider or calendar source activated")
tabs = st.tabs([label for label, _ in meta.subsections])
for tab in tabs:
    with tab:
        with st.container(border=True):
            empty_panel("Source unavailable — approval and qualification pending")
        st.caption("No automatic fetch, retry, headline scoring, local file read or write is performed.")
st.markdown("#### Source readiness")
st.caption(readiness.status)
st.write({"missing_prerequisites": readiness.missing_prerequisites})
st.caption("Hash bindings alone do not verify rights, semantics or execution approval. Live activation requires a separate milestone.")
