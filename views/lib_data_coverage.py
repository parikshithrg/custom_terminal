"""Data coverage and memory-only Kite Connect login."""

from __future__ import annotations

import requests
import streamlit as st

from market_intel.foundation.kite_connect import (
    KiteAuthenticationError,
    build_login_url,
    current_data_scope,
    exchange_request_token,
)
from views._topbar import render_section_tabs

render_section_tabs(active_section="data_library")
st.markdown("## 🌐 Data Coverage")

inventory, kite_tab, scope_tab = st.tabs(
    ["Market Data Inventory", "Kite Connect Login", "Research Scope"]
)
with inventory:
    st.info("Provider coverage will be shown here as approved adapters are connected.")

with kite_tab:
    st.subheader("Daily Kite login")
    st.caption("Credentials stay in this running session and are never written to disk.")
    api_key = st.text_input("Kite API key", key="kite_api_key")
    api_secret = st.text_input("Kite API secret", type="password", key="kite_api_secret")
    if api_key.strip():
        st.link_button("1. Log in with Zerodha", build_login_url(api_key))
    else:
        st.button("1. Enter API key to continue", disabled=True)
    request_value = st.text_input(
        "2. Paste request_token or the complete redirect URL",
        type="password",
        key="kite_request_token",
        help="Kite returns this after login. It is short-lived and single-use.",
    )
    if st.button("3. Create daily session", type="primary"):
        try:
            session = exchange_request_token(api_key, api_secret, request_value, http=requests)
            st.session_state["kite_session"] = session
            suffix = f" for {session.user_id}" if session.user_id else ""
            st.success(f"Kite session active{suffix}.")
        except (ValueError, KiteAuthenticationError) as exc:
            st.error(str(exc))
    if st.session_state.get("kite_session"):
        st.success("Authenticated for current-market data. Kite tokens expire daily.")
        if st.button("Clear Kite session"):
            del st.session_state["kite_session"]
            st.rerun()
    st.warning("Read-only connector: no trade execution and no credentials saved to disk.")

with scope_tab:
    scope = current_data_scope()
    st.info("Delisted securities are excluded from live screens and current analysis.")
    st.warning(scope["warning"])
    st.caption(
        "Historical backtests still require point-in-time inactive membership to avoid "
        "survivorship bias. Kite's current instrument list is not used for that purpose."
    )
