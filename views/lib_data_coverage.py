"""Ephemeral Kite connection, coverage health, inventory, and bounded quotes."""
from __future__ import annotations

from datetime import datetime, timezone

import requests
import streamlit as st

from market_intel.foundation.current_market import format_quote_rows, search_current_instruments
from market_intel.foundation.current_market_health import (
    IST, build_health, claim_refresh, inventory_diagnostics, sanitized_error_category,
    sanitized_health_json,
)
from market_intel.foundation.kite_connect import (
    KiteSessionState, build_login_url, current_data_scope, disconnect,
    finish_login, invalidate_session,
)
from market_intel.foundation.kite_current_market import (
    MAX_QUOTE_SYMBOLS, KiteCurrentDataError, KiteCurrentMarketClient,
    KiteInvalidSessionError,
)
from views._topbar import render_section_tabs

REFRESH_COOLDOWN_SECONDS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _login() -> None:
    finish_login(st.session_state, http=requests)
    session = st.session_state.get("kite_session")
    if session:
        st.session_state["kite_client"] = KiteCurrentMarketClient(session, http=requests)
        st.session_state["kite_validation_state"] = "NOT_VALIDATED"
        st.session_state.pop("kite_last_failure_category", None)


def _disconnect() -> None:
    disconnect(st.session_state)


def _provider_error(exc: Exception) -> None:
    category = sanitized_error_category(exc)
    st.session_state["kite_last_failure_category"] = category
    if isinstance(exc, KiteInvalidSessionError):
        invalidate_session(st.session_state, expired=True)
    else:
        st.session_state["kite_ui_error"] = f"Current-data request failed ({category})."


def _manual_refresh(action: str) -> bool:
    allowed, remaining = claim_refresh(
        st.session_state, action, _now(), seconds=REFRESH_COOLDOWN_SECONDS
    )
    if not allowed:
        st.warning(f"Manual refresh cooldown: wait {remaining:.1f} seconds.")
    return allowed


# Upgrade pre-A.12 clients retained by Streamlit hot reload without persisting
# or re-downloading their in-memory current-only inventory.
_existing_client = st.session_state.get("kite_client")
_existing_session = st.session_state.get("kite_session")
if (_existing_session and _existing_client and
        getattr(_existing_client, "client_version", None) != KiteCurrentMarketClient.client_version):
    _upgraded_client = KiteCurrentMarketClient(_existing_session, http=requests)
    if st.session_state.get("kite_inventory"):
        _upgraded_client.attach_current_inventory(st.session_state["kite_inventory"])
    st.session_state["kite_client"] = _upgraded_client

render_section_tabs(active_section="data_library")
st.markdown("## 🌐 Data Coverage")
st.error(
    "Kite current instruments are not a historical universe and cannot "
    "validate historical cross-sectional research."
)

connection_tab, health_tab, inventory_tab, quotes_tab, scope_tab = st.tabs([
    "Kite Connection", "Coverage Health", "Current Inventory",
    "Current Quotes", "Research Scope",
])

state = st.session_state.get("kite_connection_state", KiteSessionState.UNAUTHENTICATED)

with connection_tab:
    st.metric("Connection state", str(state))
    if st.session_state.get("kite_ui_error"):
        st.error(st.session_state.pop("kite_ui_error"))
    if st.session_state.get("kite_ui_message"):
        st.success(st.session_state.pop("kite_ui_message"))
    session = st.session_state.get("kite_session")
    if not session:
        st.caption(
            "API key is an application identifier. Secret and one-time token "
            "inputs are masked and removed after every exchange attempt."
        )
        api_key = st.text_input("Kite API key", key="kite_api_key")
        st.text_input("Kite API secret", type="password", key="kite_api_secret")
        if api_key.strip():
            st.link_button("1. Log in with Zerodha", build_login_url(api_key))
        else:
            st.button("1. Enter API key to continue", disabled=True)
        st.text_input(
            "2. Paste request_token or complete redirect URL",
            type="password", key="kite_request_token",
        )
        st.button("3. Create daily session", type="primary", on_click=_login)
    else:
        st.success("Authenticated. Sensitive login inputs have been removed.")
        st.write("Authenticated user:", session.user_id or "Not supplied by token response")
        if st.button("Validate session", help="User-triggered; no background validation"):
            if _manual_refresh("validation"):
                try:
                    st.session_state["kite_client"].validate_session()
                    st.session_state["kite_validation_state"] = "VALID"
                    st.session_state["kite_last_request"] = _now().isoformat()
                    st.session_state.pop("kite_last_failure_category", None)
                    st.success("Session is valid.")
                except KiteCurrentDataError as exc:
                    st.session_state["kite_validation_state"] = "INVALID"
                    _provider_error(exc)
                    st.rerun()
    if st.session_state.get("kite_last_request"):
        st.caption(f"Last successful request: {st.session_state['kite_last_request']}")
    if st.session_state.get("kite_last_failure_category"):
        st.caption(f"Last sanitized failure: {st.session_state['kite_last_failure_category']}")
    st.button("Disconnect and clear Kite values", on_click=_disconnect)
    st.caption(
        "Disconnect removes application references; it does not claim secure "
        "erasure of Python process memory."
    )

with inventory_tab:
    client = st.session_state.get("kite_client")
    if not client:
        st.info("Authenticate first to load the current instrument inventory.")
    elif st.button("Refresh current inventory", help="Manual, five-second cooldown"):
        if _manual_refresh("inventory"):
            try:
                snapshot = client.discover_current_instruments()
                st.session_state["kite_inventory"] = snapshot
                st.session_state["kite_last_request"] = snapshot.retrieved_at.isoformat()
                st.session_state.pop("kite_last_failure_category", None)
            except KiteCurrentDataError as exc:
                _provider_error(exc)
                st.rerun()
    snapshot = st.session_state.get("kite_inventory")
    if snapshot:
        diagnostics = inventory_diagnostics(snapshot, as_of=_now().astimezone(IST).date())
        st.caption(
            f"Provider: {snapshot.provider} · retrieved: {snapshot.retrieved_at.isoformat()} "
            f"· session date: {snapshot.session_date} · scope: {snapshot.scope}"
        )
        total, equities, indices, futures, options = st.columns(5)
        total.metric("Total", diagnostics.total_instruments)
        equities.metric("Equities", diagnostics.equities)
        indices.metric("Indices", diagnostics.indices)
        futures.metric("Futures", diagnostics.futures)
        options.metric("Options", diagnostics.options)
        st.write("By exchange", diagnostics.counts_by_exchange)
        with st.expander("Segment and integrity diagnostics"):
            st.write("By segment", diagnostics.counts_by_segment)
            st.write("By instrument type", diagnostics.counts_by_instrument_type)
            st.write({
                "incomplete_rows": diagnostics.incomplete_rows,
                "expired_derivatives": diagnostics.expired_derivatives,
                "duplicate_provider_keys": diagnostics.duplicate_provider_keys,
                "duplicate_exchange_symbols": diagnostics.duplicate_exchange_symbols,
            })
        st.warning(snapshot.warning)

with quotes_tab:
    snapshot = st.session_state.get("kite_inventory")
    client = st.session_state.get("kite_client")
    if not snapshot or not client:
        st.info("Authenticate and load the current inventory first.")
    else:
        exchanges = sorted({item.exchange for item in snapshot.instruments if item.exchange})
        instrument_types = sorted({item.instrument_type for item in snapshot.instruments if item.instrument_type})
        exchange = st.selectbox("Exchange", ["All"] + exchanges)
        instrument_type = st.selectbox("Instrument type", ["All"] + instrument_types)
        query = st.text_input(
            "Search trading symbol",
            placeholder="Type at least 2 characters, for example INFY",
        )
        options = search_current_instruments(
            snapshot, query,
            exchange=None if exchange == "All" else exchange,
            instrument_type=None if instrument_type == "All" else instrument_type,
            limit=100,
        )
        if len(query.strip()) < 2:
            st.info("Enter at least two characters to search the in-session inventory.")
        elif not options:
            st.warning("No current inventory matches the selected filters.")
        elif len(options) == 100:
            st.caption("Showing the first 100 matches. Refine the search to narrow the list.")
        selected = st.multiselect(
            f"Select up to {MAX_QUOTE_SYMBOLS} current instruments",
            options, max_selections=MAX_QUOTE_SYMBOLS,
        )
        mode = st.selectbox("Snapshot type", ["quote", "ohlc", "ltp"])
        if st.button("Refresh selected snapshot", disabled=not selected,
                     help="Manual, five-second cooldown"):
            if _manual_refresh("quotes"):
                try:
                    result = client.get_current_quotes(selected, mode=mode)
                    st.session_state["kite_last_quote_snapshot"] = result
                    st.session_state["kite_last_quote_mode"] = mode
                    st.session_state["kite_last_requested_count"] = len(selected)
                    st.session_state["kite_last_request"] = result.retrieved_at.isoformat()
                    st.session_state.pop("kite_last_failure_category", None)
                except (ValueError, KiteCurrentDataError) as exc:
                    _provider_error(exc)
                    st.rerun()
        result = st.session_state.get("kite_last_quote_snapshot")
        result_mode = st.session_state.get("kite_last_quote_mode", mode)
        if result:
            returned = sum(item.status == "AVAILABLE" for item in result.quotes)
            missing = len(result.quotes) - returned
            st.subheader(f"{result_mode.upper()} snapshot")
            st.caption(
                f"Endpoint: {result.source_endpoint} · provider: {result.provider} · "
                f"retrieved: {result.retrieved_at.isoformat()} · {result.cache_status}"
            )
            requested_col, returned_col, missing_col = st.columns(3)
            requested_col.metric("Requested", st.session_state.get("kite_last_requested_count", 0))
            returned_col.metric("Returned", returned)
            missing_col.metric("Missing", missing)
            if not any(item.provider_timestamp for item in result.quotes):
                st.info("Provider timestamps are unavailable; age is based only on local retrieval time.")
            st.dataframe(format_quote_rows(result, result_mode), width="stretch")
        st.caption(
            "Snapshots are user-requested, not streaming. Quote cache lifetime: "
            "15 seconds; no background polling is used."
        )

with health_tab:
    now = _now()
    health = build_health(
        now=now,
        session_state=str(st.session_state.get("kite_connection_state", KiteSessionState.UNAUTHENTICATED)),
        validation_state=st.session_state.get("kite_validation_state", "NOT_VALIDATED"),
        inventory=st.session_state.get("kite_inventory"),
        quotes=st.session_state.get("kite_last_quote_snapshot"),
        requested_count=st.session_state.get("kite_last_requested_count", 0),
        last_error=st.session_state.get("kite_last_failure_category"),
        calendar=None,
    )
    session_col, market_col, freshness_col, entitlement_col = st.columns(4)
    session_col.metric("Session", health.session_state)
    market_col.metric("Market session", health.market_session)
    freshness_col.metric("Freshness", health.freshness)
    entitlement_col.metric("Entitlement", health.entitlement_status)
    st.caption(
        f"Calendar: {health.calendar_version} · timezone: {health.calendar_timezone}. "
        "No maintained current NSE holiday calendar is configured, so session is UNKNOWN."
    )
    st.write({
        "inventory_age_seconds": health.inventory_age_seconds,
        "quote_age_seconds": health.quote_age_seconds,
        "provider_quote_age_seconds": health.provider_quote_age_seconds,
        "provider_time_known": health.provider_time_known,
        "stale_cache": health.stale_cache,
        "last_sanitized_provider_error": health.last_sanitized_provider_error,
    })
    st.download_button(
        "Download sanitized health summary",
        data=sanitized_health_json(health),
        file_name="kite_current_health.json",
        mime="application/json",
        help="Generated in memory; excludes credentials, account details and raw rows.",
    )

with scope_tab:
    scope = current_data_scope()
    st.warning(scope["warning"])
    st.write(
        "Implemented endpoints: profile validation, current instruments, LTP, "
        "quote and OHLC snapshot."
    )
    st.write(
        "No order, GTT, basket, funds-transfer, holdings-mutation, "
        "margin-submission or order-update functionality is implemented."
    )
    st.caption(
        "The token may have broader account permissions; this application "
        "permits only its declared GET data endpoints."
    )
