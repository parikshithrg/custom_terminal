"""Shared renderers for not-yet-wired pages - every page in this app calls
one of these until its own backend data source is decided. Keeps every
stub consistent (same "not wired yet" framing) rather than seventeen
slightly different placeholder pages.

`render_stub` is for a single-topic page. `render_stub_multi` is for a
CONSOLIDATED page (2026-08-18's clubbing pass) - one page covering two
formerly-separate topics, shown as tabs rather than two separate pages,
since the two topics are meant to be read together (a risk reading next
to its own protection trigger, a benchmark next to the return it's
measured against, etc.) - see `_registry.py`'s own docstring for the
reasoning behind each specific consolidation.

No per-page "back to home" link/function here any more (removed
2026-08-18) - `views/_topbar.py`'s own "Main Page" tab is now the single
way back to home from every page, so a second, separate link at the
bottom would just be a redundant affordance.
"""

from __future__ import annotations

import streamlit as st

from views._topbar import render_section_tabs


def _footer() -> None:
    st.markdown(
        "**Not yet wired to real data.** This page is a placeholder - the "
        "backend for it (which local files, which API, which cache) hasn't "
        "been decided yet."
    )


def render_stub(title: str, icon: str, source: str, description: str,
                note: str | None = None) -> None:
    render_section_tabs(active_section=source)
    st.markdown(f"## {icon} {title}")
    st.caption(f"Source: {source}")
    st.info(description)
    if note:
        st.warning(note)
    _footer()


def render_stub_multi(title: str, icon: str, source: str,
                      subsections: tuple[tuple[str, str], ...]) -> None:
    render_section_tabs(active_section=source)
    st.markdown(f"## {icon} {title}")
    st.caption(f"Source: {source}")
    tabs = st.tabs([label for label, _ in subsections])
    for tab, (_, desc) in zip(tabs, subsections):
        with tab:
            st.info(desc)
    _footer()
