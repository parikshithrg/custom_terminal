"""Current-only Kite connection health, inventory, and bounded quotes."""
from __future__ import annotations
from collections import Counter
import requests
import streamlit as st
from market_intel.foundation.kite_connect import (
    KiteSessionState, build_login_url, current_data_scope, disconnect,
    finish_login, invalidate_session,
)
from market_intel.foundation.kite_current_market import (
    MAX_QUOTE_SYMBOLS, KiteCurrentDataError, KiteCurrentMarketClient,
    KiteInvalidSessionError,
)
from market_intel.foundation.current_market import format_quote_rows, search_current_instruments
from views._topbar import render_section_tabs

# Streamlit retains session objects across source hot reloads. Upgrade an old
# in-memory client while preserving its current-only inventory and access
# session, so a UI-only compatibility fix does not force another broker login.
_existing_client=st.session_state.get("kite_client")
_existing_session=st.session_state.get("kite_session")
if (_existing_session and _existing_client and
        getattr(_existing_client,"client_version",None)!=KiteCurrentMarketClient.client_version):
    _upgraded_client=KiteCurrentMarketClient(_existing_session,http=requests)
    _existing_inventory=st.session_state.get("kite_inventory")
    if _existing_inventory:
        _upgraded_client.attach_current_inventory(_existing_inventory)
    st.session_state["kite_client"]=_upgraded_client

def _login() -> None:
    finish_login(st.session_state, http=requests)
    session=st.session_state.get("kite_session")
    if session: st.session_state["kite_client"]=KiteCurrentMarketClient(session,http=requests)

def _disconnect() -> None: disconnect(st.session_state)

def _provider_error(exc: Exception) -> None:
    if isinstance(exc,KiteInvalidSessionError): invalidate_session(st.session_state,expired=True)
    else: st.session_state["kite_ui_error"]=str(exc)

render_section_tabs(active_section="data_library")
st.markdown("## 🌐 Data Coverage")
st.error("Kite current instruments are not a historical universe and cannot validate historical cross-sectional research.")
login_tab,inventory_tab,quotes_tab,scope_tab=st.tabs(["Kite Connection","Current Inventory","Current Quotes","Research Scope"])

state=st.session_state.get("kite_connection_state",KiteSessionState.UNAUTHENTICATED)
with login_tab:
    st.metric("Connection state",str(state))
    if st.session_state.get("kite_ui_error"): st.error(st.session_state.pop("kite_ui_error"))
    if st.session_state.get("kite_ui_message"): st.success(st.session_state.pop("kite_ui_message"))
    session=st.session_state.get("kite_session")
    if not session:
        st.caption("API key is an application identifier. Secret and one-time token inputs are masked and removed from application state after every exchange attempt.")
        api_key=st.text_input("Kite API key",key="kite_api_key")
        st.text_input("Kite API secret",type="password",key="kite_api_secret")
        if api_key.strip(): st.link_button("1. Log in with Zerodha",build_login_url(api_key))
        else: st.button("1. Enter API key to continue",disabled=True)
        st.text_input("2. Paste request_token or complete redirect URL",type="password",key="kite_request_token")
        st.button("3. Create daily session",type="primary",on_click=_login)
    else:
        st.success("Authenticated. Sensitive login inputs have been removed.")
        st.write("Authenticated user:",session.user_id or "Not supplied by token response")
        if st.button("Validate session"):
            try:
                user=st.session_state["kite_client"].validate_session()
                st.session_state["kite_authenticated_user"]=user
                st.session_state["kite_last_request"]="Session validation succeeded"
                st.success("Session is valid.")
            except KiteCurrentDataError as exc: _provider_error(exc); st.rerun()
    if st.session_state.get("kite_last_request"): st.caption(f"Last successful request: {st.session_state['kite_last_request']}")
    st.button("Disconnect and clear Kite values",on_click=_disconnect)
    st.caption("Disconnect removes application references; it does not claim secure erasure of Python process memory.")

with inventory_tab:
    client=st.session_state.get("kite_client")
    if not client: st.info("Authenticate first to load the current instrument inventory.")
    elif st.button("Load current instrument inventory"):
        try:
            snapshot=client.discover_current_instruments(); st.session_state["kite_inventory"]=snapshot
            st.session_state["kite_last_request"]=snapshot.retrieved_at.isoformat()
        except KiteCurrentDataError as exc: _provider_error(exc); st.rerun()
    snapshot=st.session_state.get("kite_inventory")
    if snapshot:
        st.caption(f"Provider: {snapshot.provider} · retrieved: {snapshot.retrieved_at.isoformat()} · scope: {snapshot.scope}")
        by_exchange=Counter(i.exchange for i in snapshot.instruments)
        by_type=Counter(i.instrument_type for i in snapshot.instruments)
        st.write("By exchange",dict(sorted(by_exchange.items())))
        st.write("By instrument type",dict(sorted(by_type.items())))
        st.warning(snapshot.warning)

with quotes_tab:
    snapshot=st.session_state.get("kite_inventory"); client=st.session_state.get("kite_client")
    if not snapshot or not client: st.info("Authenticate and load the current inventory first.")
    else:
        exchanges=sorted({i.exchange for i in snapshot.instruments})
        instrument_types=sorted({i.instrument_type for i in snapshot.instruments})
        exchange=st.selectbox("Exchange",["All"]+exchanges)
        instrument_type=st.selectbox("Instrument type",["All"]+instrument_types)
        query=st.text_input("Search trading symbol",placeholder="Type at least 2 characters, for example INFY")
        options=search_current_instruments(snapshot,query,
            exchange=None if exchange=="All" else exchange,
            instrument_type=None if instrument_type=="All" else instrument_type,
            limit=100)
        if len(query.strip())<2:
            st.info("Enter at least two characters to search the in-session inventory.")
        elif not options:
            st.warning("No current inventory matches the selected filters.")
        elif len(options)==100:
            st.caption("Showing the first 100 matches. Refine the search to narrow the list.")
        selected=st.multiselect(f"Select up to {MAX_QUOTE_SYMBOLS} current instruments",options,max_selections=MAX_QUOTE_SYMBOLS)
        mode=st.selectbox("Snapshot type",["quote","ohlc","ltp"])
        if st.button("Retrieve current snapshot",disabled=not selected):
            try:
                result=client.get_current_quotes(selected,mode=mode); st.session_state["kite_last_request"]=result.retrieved_at.isoformat()
                st.subheader(f"{mode.upper()} snapshot")
                st.caption(f"Endpoint: {result.source_endpoint} · provider: {result.provider} · retrieved: {result.retrieved_at.isoformat()} · {result.cache_status}")
                st.dataframe(format_quote_rows(result,mode),width="stretch")
            except (ValueError,KiteCurrentDataError) as exc: _provider_error(exc); st.rerun()
        st.caption("Snapshots are user-requested, not streaming. In-session quote cache lifetime: 15 seconds.")

with scope_tab:
    scope=current_data_scope(); st.warning(scope["warning"])
    st.write("Implemented endpoints: profile validation, current instruments, LTP, quote, and OHLC snapshot.")
    st.write("No order, GTT, basket, funds-transfer, holdings-mutation, margin-submission, or order-update functionality is implemented.")
    st.caption("The token may have broader account permissions; this application client permits only its declared GET data endpoints.")
