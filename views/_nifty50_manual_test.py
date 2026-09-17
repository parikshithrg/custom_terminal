"""Explicit manual NIFTY 50 test; no network merely by visiting this page."""


def render(*, now, manual_refresh, provider_error):
    import requests
    import streamlit as st
    from market_intel.nifty50_manual_test import fetch_constituents, run_test
    from market_intel.foundation.current_market import format_quote_rows
    from market_intel.foundation.kite_current_market import KiteCurrentDataError

    with st.expander("NIFTY 50 · two-batch equity test"):
        st.caption("Official latest published list, not historical membership. Manual only; results stay in memory. Dashboard remains synthetic.")
        if st.button("Load official current NIFTY 50 list") and manual_refresh("nifty50_list"):
            st.session_state.pop("kite_nifty50_constituents", None)
            st.session_state.pop("kite_nifty50_test", None)
            try:
                with requests.Session() as http:
                    st.session_state["kite_nifty50_constituents"] = fetch_constituents(http=http, now=now)
            except Exception:
                st.error("Official list could not be verified within scope. No fallback or retry performed.")
        constituents = st.session_state.get("kite_nifty50_constituents")
        if constituents:
            st.caption(f"50 unique EQ constituents · source {constituents.source_url} · retrieved {constituents.retrieved_at.isoformat()} · SHA-256 {constituents.payload_hash}")
        client, inventory = st.session_state.get("kite_client"), st.session_state.get("kite_inventory")
        if st.button("Test all 50 equities · 2 × 25", disabled=not (constituents and client and inventory)):
            if manual_refresh("nifty50_quotes"):
                st.session_state.pop("kite_nifty50_test", None)
                try:
                    results = run_test(constituents=constituents, inventory=inventory, client=client, as_of=now())
                    st.session_state["kite_nifty50_test"] = (constituents.payload_hash, results)
                except ValueError:
                    st.error("NIFTY 50 test stopped: list/inventory/batch quality checks failed. No partial result displayed.")
                except KiteCurrentDataError as exc:
                    provider_error(exc)
                    st.error("Provider rejected or failed the bounded test. No partial result displayed.")
        stored = st.session_state.get("kite_nifty50_test")
        if stored and constituents and client and inventory and stored[0] == constituents.payload_hash:
            for index, snapshot in enumerate(stored[1], 1):
                st.markdown(f"#### Batch {index} · 25 requested")
                available = sum(row.status == "AVAILABLE" for row in snapshot.quotes)
                st.caption(f"Returned {available} · missing {25-available} · retrieved {snapshot.retrieved_at.isoformat()} · {snapshot.cache_status}")
                rows = [{key: row[key] for key in ("instrument", "status", "last_price", "provider_timestamp", "message")}
                        for row in format_quote_rows(snapshot, "quote")]
                st.dataframe(rows, width="stretch")
            st.warning("Operational observations only, not exact-Decimal or freshness qualification. Two batches are not a simultaneous snapshot. Missingness remains explicit; no research or source promotion.")
