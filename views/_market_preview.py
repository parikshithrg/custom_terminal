"""Static, explicitly synthetic UI fixtures; no provider or local data access."""
from decimal import Decimal
from html import escape
from views._watchlist_contract_view import dashboard_presentation

# Illustrative values, not captured exchange observations.
DEMO_INDICES = (
    ("NIFTY 50","24850.25","+0.42%"),
    ("NIFTY BANK","53120.50","-0.18%"),
    ("NIFTY IT","38240.75","+0.63%"),
    ("INDIA VIX","13.20","-1.04%"),
)
DEMO_ROWS = (
    ("DEMO EQUITY A","125.50","+0.80%","Mock / no feed"),
    ("DEMO EQUITY B","840.25","-0.35%","Mock / no feed"),
    ("DEMO EQUITY C","312.00","+0.22%","Mock / no feed"),
)
DEMO_FUTURES = (
    ("DEMO FUTURE A","25100.00","+0.15%","Synthetic contract"),
    ("DEMO FUTURE B","53400.00","-0.20%","Synthetic contract"),
)

def index_markup():
    cards = []
    for name, value, change in DEMO_INDICES:
        cls = "lt-down" if change.startswith("-") else "lt-up"
        cards.append(f'<div class="lt-market-card"><div class="lt-kicker">{escape(name)}</div><div class="lt-number">{Decimal(value):,.2f}</div><div class="lt-change {cls}">{escape(change)} · demonstration only</div></div>')
    return '<div class="lt-market-grid">'+"".join(cards)+'</div>'

def table_markup(rows):
    body = "".join("<tr>"+"".join(f"<td>{escape(str(v))}</td>" for v in row)+"</tr>" for row in rows)
    return '<div class="lt-table-wrap"><table class="lt-table"><caption>Illustrative watchlist — synthetic values, not live market data</caption><thead><tr><th scope="col">Instrument</th><th scope="col">Demo price</th><th scope="col">Demo change</th><th scope="col">Source status</th></tr></thead><tbody>'+body+'</tbody></table></div>'

def render(*, use_watchlist_contract=False):
    import streamlit as st
    st.caption("DEMONSTRATION ONLY — all prices and changes below are static synthetic fixtures, not current or historical market observations.")
    st.markdown(index_markup(),unsafe_allow_html=True)
    st.markdown("Illustrative equity watchlist")
    if use_watchlist_contract:
        try:
            rows, provenance = dashboard_presentation()
        except ValueError:
            st.caption("Synthetic watchlist unavailable — contract validation failed. No fallback prices.")
        else:
            st.markdown(table_markup(rows),unsafe_allow_html=True)
            st.caption(provenance)
    else:
        st.markdown(table_markup(DEMO_ROWS),unsafe_allow_html=True)
    st.caption("View selection changes presentation only. No data is fetched, refreshed, saved or used to calculate signals.")

def readiness():
    import streamlit as st
    with st.container(border=True,key="terminal-readiness"):
        st.markdown("#### Data readiness")
        st.markdown("**This preview · synthetic fixtures**")
        st.caption("No real market source is connected to the preview. Existing manual current-data controls remain on Data Coverage.")
        st.caption("Deferred experimental outputs are unavailable to production and research.")
