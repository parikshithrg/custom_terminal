"""Home - a grid of boxes, one per page, grouped by JOB (trading decisions,
investment decisions, news/events) with the shared data foundation last.
Explicitly NOT tabs and NOT a sidebar nav (ruled out when this was scoped
2026-08-18) - every page is reachable from this one screen."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from views._registry import PAGES, SECTION_SUBTITLES, SECTIONS

# Arriving from another page's section tab (views/_topbar.py) via
# ?section=<key> - jump to that section instead of landing at the top.
# Anchors are plain <div id=...> (below); the scroll itself needs real JS
# to run AFTER Streamlit's async render (an anchor in the URL at initial
# load fires the browser's native scroll-to-fragment too early, before the
# element exists, so nothing happens) - `st.markdown` does not execute
# <script> tags at all, only `components.html`'s iframe does, and that
# iframe can still reach the main document via `window.parent.document`
# since it's same-origin. Retries for ~1.5s in case the target section's
# DOM hasn't painted yet either.
_requested_section = st.query_params.get("section")

# `st.container(key=...)` is the DOCUMENTED, version-stable way to target a
# specific container with custom CSS (it emits a fixed `st-key-<key>` class)
# - unlike Streamlit's own internal `st-emotion-cache-*` classes, which are
# content-hashed and can change on any Streamlit upgrade. Every card below
# shares the "card-" key prefix so one selector reaches all of them.
st.markdown(
    """<style>
    /* Same value and same real testid market_gate uses
    (Dashboard/market_gate/theme.py) - `.block-container` (used here at
    first) doesn't reliably match this Streamlit version's actual DOM. */
    div[data-testid="stMainBlockContainer"] { padding-top: 64px !important; }
    div[class*="st-key-card-"] {
        padding: 0.5rem 0.75rem !important;
        gap: 0.15rem !important;
    }
    /* Defensive sizing for narrow viewports: a flex item's default
    min-height/min-width is "auto", which under a squeezed column can force
    the caption text into a near-zero-width column and wrap it into dozens
    of lines instead of shrinking normally - confirmed at a 607px viewport
    during testing (16px-wide caption, 761px tall as a result), gone at a
    normal desktop width. Pinning min-height:0 keeps that failure mode from
    recurring on a phone-width browser instead of just hiding it here. */
    div[class*="st-key-card-"] > [data-testid="stElementContainer"] {
        flex: 0 0 auto !important;
        min-height: 0 !important;
    }
    div[class*="st-key-card-"] [data-testid="stCaptionContainer"],
    div[class*="st-key-card-"] [data-testid="stMarkdown"] {
        min-height: 0 !important;
        height: auto !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

st.markdown("## 🖥️ Local Terminal")
st.caption(
    "A complete information & analytics terminal for Indian and global "
    "markets - deliberately no trade execution. Every box below is a page; "
    "none are wired to real data yet."
)

N_COLS = 5

# ONE fixed height for every card, in every section, forever - this is what
# makes the grid uniform "whenever added" rather than something re-tuned by
# hand each time a page is added. Sized for the description length range
# _registry.py's own docstring asks new entries to stay inside (55-80 chars,
# wraps to at most 2 caption lines under a one-line title).
CARD_HEIGHT = 122

for section_key, section_title in SECTIONS.items():
    section_pages = [p for p in PAGES if p.section == section_key]
    if not section_pages:
        continue

    st.markdown(f'<div id="section-{section_key}"></div>', unsafe_allow_html=True)
    subtitle = SECTION_SUBTITLES.get(section_key)
    header = f"#### {section_title}" + (f" — *{subtitle}*" if subtitle else "")
    st.markdown(header)

    cols = st.columns(N_COLS, gap="small")
    for i, page in enumerate(section_pages):
        card_key = f"card-{section_key}-{i}"
        with cols[i % N_COLS].container(border=True, key=card_key, height=CARD_HEIGHT):
            st.page_link(page.file, label=page.title, icon=page.icon)
            st.caption(page.description)

if _requested_section in SECTIONS:
    # NOT el.scrollIntoView(), and NOT scrollTo({behavior:"smooth"}) -
    # both confirmed via live testing to run without error and find the
    # right elements, but silently fail to move anything, because this
    # script executes inside `components.html`'s own iframe while the
    # target belongs to the PARENT document - smooth/animated scrolling
    # across that frame boundary does not reliably take effect in this
    # browser. A plain, INSTANT `scrollTop =` assignment on Streamlit's own
    # scroll container (`[data-testid="stMain"]`) sidesteps that entirely -
    # confirmed working live (jumps to the right section every time).
    components.html(
        f"""<script>
        (function() {{
            function tryScroll(attempts) {{
                var mainEl = window.parent.document.querySelector('[data-testid="stMain"]');
                var target = window.parent.document.getElementById('section-{_requested_section}');
                if (mainEl && target) {{
                    var targetRect = target.getBoundingClientRect();
                    var mainRect = mainEl.getBoundingClientRect();
                    var offset = mainEl.scrollTop + (targetRect.top - mainRect.top);
                    mainEl.scrollTop = Math.max(0, offset - 8);
                    return;
                }}
                if (attempts > 0) setTimeout(function() {{ tryScroll(attempts - 1); }}, 150);
            }}
            tryScroll(15);
        }})();
        </script>""",
        height=0,
    )
