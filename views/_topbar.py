"""Section top bar - rendered on every page EXCEPT home.py (the grid IS
the navigation there; a second nav bar on top of it would be redundant,
which is why the user asked for it excluded specifically).

"Main Page" (plain link to home, no section scroll) plus one tab per
section on the home grid. Clicking a section tab jumps to home.py
scrolled to that section, so any section heading is reachable from
wherever you currently are, not just from the top of home. "Main Page"
is the sole way back to home now - the standalone "Back to Local
Terminal" link every page's footer used to have was removed 2026-08-18
in favour of this, so there is exactly one home-navigation affordance
per page, not two.

PLAIN <a> TAGS, NOT st.page_link - deliberately. `st.page_link` uses
Streamlit's client-side routing, which was not confirmed to carry a
query string through to the target page. A plain anchor with
target="_self" does a full navigation instead, which reliably lands on
home.py with `?section=...` in the URL for `home.py`'s own reader
(see there) to act on - a full reload is heavier but predictable, which
matters more here than speed for a local tool.
"""

from __future__ import annotations

import streamlit as st

from views._registry import SECTIONS


def render_section_tabs(active_section: str | None = None) -> None:
    st.markdown(
        """<style>
        /* Streamlit's default top clearance is a generous ~96px under its
        own 60px header - market_gate (Dashboard/market_gate/theme.py)
        already tightened this app-wide to 64px via the real testid
        (`stMainBlockContainer`, not the `.block-container` class this
        project used at first, which doesn't reliably match in this
        Streamlit version). Matched here rather than picking a new value,
        so a page with the top bar reads at the same density as market_gate
        itself. */
        div[data-testid="stMainBlockContainer"] { padding-top: 64px !important; }
        .lt-topbar {
            display: flex; gap: 4px; margin: 0 0 1.25rem;
            border-bottom: 1px solid rgba(128,128,128,0.35);
        }
        .lt-topbar a {
            padding: 8px 16px; font-size: 14px; font-weight: 500;
            text-decoration: none; color: inherit; opacity: 0.6;
            border-bottom: 2px solid transparent; margin-bottom: -1px;
        }
        .lt-topbar a:hover { opacity: 1; }
        .lt-topbar a.active {
            opacity: 1; font-weight: 700; border-bottom-color: currentColor;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    home_link = '<a href="/" target="_self">Main Page</a>'
    section_links = "".join(
        f'<a class="{"active" if key == active_section else ""}" '
        f'href="/?section={key}" target="_self">{label}</a>'
        for key, label in SECTIONS.items()
    )
    st.markdown(f'<div class="lt-topbar">{home_link}{section_links}</div>', unsafe_allow_html=True)
