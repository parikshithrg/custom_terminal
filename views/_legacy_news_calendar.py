"""News & Calendar - News Feed (live RSS, 11 India/global sources) and
Event Calendar (live NSE board meetings + corporate actions), both real
data as of 2026-08-18 - see views/_news_data.py for the full sourcing
story and why each was chosen over the alternatives that didn't pan out.
"""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from views._news_data import fetch_news, fetch_nse_board_meetings, fetch_nse_corporate_actions
from views._registry import PAGES_BY_FILE
from views._sentiment import sentiment_emoji, sentiment_label
from views._topbar import render_section_tabs

meta = PAGES_BY_FILE["views/news_feed_calendar.py"]

render_section_tabs(active_section=meta.section)
st.markdown(f"## {meta.icon} {meta.title}")
st.caption(f"Source: {meta.section}")

tab_news, tab_calendar = st.tabs([label for label, _ in meta.subsections])

with tab_news:
    news = fetch_news()
    if news.empty:
        st.warning("Couldn't reach any news source right now - try again shortly.")
    else:
        region = st.radio("Region", ["All", "India", "Global"], horizontal=True, key="news_region")
        shown = news if region == "All" else news[news["region"] == region]
        st.caption(f"{len(shown)} articles from {shown['source'].nunique()} sources · refreshes every 10 min")

        st.markdown("#### Sentiment by source")
        st.caption(
            "Headline sentiment, finance-augmented VADER (not plain VADER - "
            "see views/_sentiment.py for why) - a directional read, not a "
            "precise score, especially on genuinely mixed headlines."
        )
        by_source = (
            shown.groupby("source")["sentiment"]
            .agg(mean="mean", n="count")
            .sort_values("mean", ascending=False)
        )

        # FIXED small size (not st.columns, which sizes each square to
        # column-width and blew up to ~300px on a wide screen) - a flex-wrap
        # grid instead, each card pinned to SENT_CARD_SIZE regardless of
        # viewport, with as many per row as actually fit.
        #
        # REAL BUG, found by inspecting the live DOM after the user reported
        # every card stacking in one column: `st.container(key=...)` is NOT
        # a direct child of its parent - Streamlit wraps each one in its own
        # `stLayoutWrapper` div first, and THAT wrapper (not the card) is
        # the actual flex item my "sent-grid" row sees. Left unstyled, the
        # wrapper defaults to the full row width, so every "row" in the wrap
        # filled up with exactly one (mostly-empty) wrapper before the
        # 120px card inside it could ever matter - confirmed by checking
        # `grid.children` directly, not assumed from the card's own
        # (correctly-120px, but irrelevant) computed style. Fix: constrain
        # the DIRECT CHILDREN of the grid (`> div`, i.e. the wrappers
        # themselves), not just the cards nested inside them.
        SENT_CARD_SIZE = 120
        st.markdown(
            f"""<style>
            div[class*="st-key-sent-grid"] {{
                display: flex !important; flex-direction: row !important;
                flex-wrap: wrap; gap: 0.5rem;
            }}
            div[class*="st-key-sent-grid"] > div {{
                width: {SENT_CARD_SIZE}px !important; flex: 0 0 {SENT_CARD_SIZE}px !important;
            }}
            div[class*="st-key-sent-card-"] {{
                width: {SENT_CARD_SIZE}px; aspect-ratio: 1 / 1;
                display: flex; flex-direction: column; justify-content: center;
                align-items: center; text-align: center; gap: 0.2rem;
                padding: 0.4rem !important; overflow: hidden;
            }}
            div[class*="st-key-sent-card-"] p {{ font-size: 0.8rem; line-height: 1.15; margin: 0; }}
            div[class*="st-key-sent-card-"] [data-testid="stCaptionContainer"] p {{ font-size: 0.68rem; }}
            </style>""",
            unsafe_allow_html=True,
        )
        with st.container(key="sent-grid"):
            for i, (source, row_s) in enumerate(by_source.iterrows()):
                with st.container(border=True, key=f"sent-card-{i}"):
                    st.markdown(f"**{sentiment_emoji(row_s['mean'])} {source}**")
                    st.caption(f"{row_s['mean']:+.2f} · {sentiment_label(row_s['mean'])} · n={int(row_s['n'])}")
        st.divider()

        # A single injected HTML table, not one st.markdown()+st.divider()
        # per article - the previous version's empty space came from each
        # article carrying its own Streamlit block spacing (~60 of them);
        # one table has none of that overhead. `border-collapse: collapse`
        # plus a border only on <tr> (not the <table> itself) is what gives
        # "no outer border, thin line between rows" rather than a boxed grid.
        rows_html = []
        for _, row in shown.head(60).iterrows():
            when = (
                row["published"].strftime("%b %d, %H:%M")
                if row["published"] is not None and pd.notna(row["published"]) else "—"
            )
            title = html.escape(str(row["title"]))
            link = html.escape(str(row["link"]), quote=True)
            source = html.escape(str(row["source"]))
            emoji = sentiment_emoji(row["sentiment"])
            rows_html.append(
                "<tr>"
                f'<td style="padding:6px 10px 6px 0;white-space:nowrap;opacity:0.65;">{when}</td>'
                f'<td style="padding:6px 10px;white-space:nowrap;opacity:0.65;">{source}</td>'
                f'<td style="padding:6px 10px;">{emoji} <a href="{link}" target="_blank" '
                f'style="color:inherit;text-decoration:none;">{title}</a></td>'
                "</tr>"
            )

        table_html = f"""
        <style>
        .lt-news-table {{ width:100%; border-collapse:collapse; font-size:14px; }}
        .lt-news-table th {{
            text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.04em;
            opacity:0.6; font-weight:600; padding:4px 10px 6px 0;
            border-bottom:1px solid rgba(128,128,128,0.35);
        }}
        .lt-news-table td {{ border-bottom:1px solid rgba(128,128,128,0.18); }}
        .lt-news-table tr:last-child td {{ border-bottom:none; }}
        .lt-news-table a:hover {{ text-decoration:underline !important; }}
        </style>
        <table class="lt-news-table">
            <thead><tr><th>Time</th><th>Source</th><th>News</th></tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

with tab_calendar:
    board = fetch_nse_board_meetings()
    actions = fetch_nse_corporate_actions()

    if board.empty and actions.empty:
        st.warning("Couldn't reach NSE's calendar data right now - try again shortly.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Board meetings (30d)", len(board))
        c2.metric("Corporate actions (30d)", len(actions))

        st.markdown("#### Board meetings")
        if board.empty:
            st.caption("None scheduled in the next 30 days.")
        else:
            st.dataframe(
                board.rename(columns={
                    "date": "Date", "symbol": "Symbol", "company": "Company",
                    "purpose": "Purpose", "description": "Description",
                })[["Date", "Symbol", "Company", "Purpose", "Description"]],
                width="stretch", height=300, hide_index=True,
            )

        st.markdown("#### Corporate actions (dividends, splits, bonuses...)")
        if actions.empty:
            st.caption("None scheduled in the next 30 days.")
        else:
            st.dataframe(
                actions.rename(columns={
                    "date": "Ex-Date", "symbol": "Symbol", "company": "Company", "purpose": "Action",
                })[["Ex-Date", "Symbol", "Company", "Action"]],
                width="stretch", height=300, hide_index=True,
            )
        st.caption("Source: NSE's own unofficial endpoints, read-only · refreshes every 30 min")
