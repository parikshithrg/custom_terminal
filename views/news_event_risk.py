"""Event Risk Assessment - Black Swan Radar (real data, 2026-08-18) and
Portfolio Impact Mapper (still a stub - needs actual position data before
it can map anything). See views/_blackswan_data.py for the full
methodology and its stated limits.
"""

from __future__ import annotations

import streamlit as st

from views._blackswan_data import band_for_score, compute_stress_score
from views._registry import PAGES_BY_FILE
from views._topbar import render_section_tabs

meta = PAGES_BY_FILE["views/news_event_risk.py"]

render_section_tabs(active_section=meta.section)
st.markdown(f"## {meta.icon} {meta.title}")
st.caption(f"Source: {meta.section}")

tab_radar, tab_impact = st.tabs([label for label, _ in meta.subsections])

with tab_radar:
    st.info(
        "**Not a predictor.** Black swans can't be forecast individually - "
        "this scores CURRENT conditions against the structural traits "
        "(vol spikes, breadth deterioration, flight to safety, currency "
        "stress) that past crises shared in hindsight. It has not been "
        "tested against actual historical crisis windows to confirm the "
        "composite would have flagged them - that's real, unstarted "
        "research, not assumed here."
    )

    result = compute_stress_score()

    if result["composite"] is None:
        st.warning("Couldn't compute a score right now - no dimension had enough live data.")
    else:
        band_colors = {
            "Calm": "🟢", "Normal": "🟢", "Elevated": "🟡",
            "Stressed": "🟠", "Crisis-level": "🔴",
        }
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("Composite stress score", f"{result['composite']:.0f} / 100")
        c2.metric("Band", f"{band_colors.get(result['band'], '')} {result['band']}")
        c3.caption(
            f"Equal-weighted across {result['n_available']}/{result['n_total']} "
            "dimensions - 6 percentile-ranked against ~1-year history, "
            "News Sentiment on a provisional scale until its own history "
            "log builds up (see its own card below) · refreshes every 30 min"
        )

        st.markdown("#### Dimension breakdown")
        cols = st.columns(3)
        for i, d in enumerate(result["dimensions"]):
            with cols[i % 3].container(border=True):
                if d["score"] is None:
                    st.markdown(f"**{d['label']}**")
                    st.caption(d["detail"])
                else:
                    st.markdown(
                        f"**{d['label']}** — {d['score']:.0f}/100 "
                        f"({band_for_score(d['score'])})"
                    )
                    st.caption(f"{d['value']} · {d['detail']}")

with tab_impact:
    st.info(meta.subsections[1][1])
    st.markdown(
        "**Not yet wired to real data.** This tab is a placeholder - it "
        "needs real position data (from the Trading Desk / Investment "
        "Desk) to map an event against, which isn't connected yet."
    )
