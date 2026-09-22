"""Explicit manual NIFTY 50 test; no network merely by visiting this page."""


def render(*, now, manual_refresh, provider_error):
    import requests
    import streamlit as st
    from market_intel.nifty50_manual_test import (
        OFFICIAL_URL, IST, accept_uploaded_constituents, fetch_constituents, run_test,
    )
    from market_intel.kite_exact_preflight_v1 import (
        confirm_preflight, preflight_is_current, prepare_preflight,
    )
    from market_intel.foundation.current_market import format_quote_rows
    from market_intel.foundation.kite_current_market import KiteCurrentDataError

    with st.expander("NIFTY 50 · two-batch equity test"):
        def clear_exact_preflight():
            for key in ("kite_exact_binding", "kite_exact_approval",
                        "kite_exact_binding_confirmed"):
                st.session_state.pop(key, None)

        st.caption("Official latest published list, not historical membership. Manual only; results stay in memory. Dashboard remains synthetic.")
        if st.button("Load official current NIFTY 50 list") and manual_refresh("nifty50_list"):
            st.session_state.pop("kite_nifty50_constituents", None)
            st.session_state.pop("kite_nifty50_test", None)
            clear_exact_preflight()
            try:
                with requests.Session() as http:
                    st.session_state["kite_nifty50_constituents"] = fetch_constituents(http=http, now=now)
            except Exception:
                st.error("Official list could not be verified within scope. No fallback or retry performed.")
        st.markdown("**Or upload your official CSV copy**")
        st.link_button("Open official NIFTY 50 constituent CSV", OFFICIAL_URL)
        st.caption("Download through the official site yourself, then upload that unedited file here. Your source/date declaration is recorded, not independently authenticated. No alternative source is accepted.")
        uploaded = st.file_uploader("Official NIFTY 50 CSV · maximum 64 KiB", type=["csv"],
                                    key="kite_nifty50_upload", max_upload_size=1)
        download_date = st.date_input("Date downloaded from official site (your declaration)",
                                      value=now().astimezone(IST).date(), key="kite_nifty50_upload_date")
        confirmed = st.checkbox("I downloaded this unedited CSV from the official NIFTY 50 constituent link today.",
                                key="kite_nifty50_upload_confirmed")
        if st.button("Validate and use uploaded official list", disabled=not (uploaded and confirmed)):
            st.session_state.pop("kite_nifty50_constituents", None)
            st.session_state.pop("kite_nifty50_test", None)
            clear_exact_preflight()
            try:
                if uploaded.size > 65536:
                    raise ValueError("CSV exceeds 64 KiB")
                st.session_state["kite_nifty50_constituents"] = accept_uploaded_constituents(
                    uploaded.getvalue(), official_source_confirmed=confirmed,
                    download_date=download_date, uploaded_at=now())
                st.success("Uploaded CSV structure validated: 50 unique EQ constituents. Source remains owner-declared.")
            except ValueError:
                st.error("Upload rejected: confirm today's official unedited CSV, maximum 64 KiB, with 50 unique EQ symbols and ISINs.")
        constituents = st.session_state.get("kite_nifty50_constituents")
        if constituents:
            st.caption(f"50 unique EQ constituents · source {constituents.source_url} · acquisition {constituents.acquisition_method} · owner download date {constituents.owner_download_date or 'not applicable'} · received {constituents.retrieved_at.isoformat()} · SHA-256 {constituents.payload_hash}")
        client, inventory = st.session_state.get("kite_client"), st.session_state.get("kite_inventory")

        st.markdown("#### Exact-price local preflight")
        st.caption(
            "This step computes a private in-memory target binding. It makes no "
            "quote request and displays no symbols, tokens, credentials or prices."
        )
        missing_preflight = []
        if not constituents:
            missing_preflight.append("today's validated official NIFTY 50 list")
        if not inventory:
            missing_preflight.append("the current Kite instrument inventory")
        if missing_preflight:
            st.info("Before preparing the binding, load " + " and ".join(missing_preflight) + ".")
        else:
            st.success("Preflight inputs are ready. Preparing the binding makes no quote request.")
        binding = st.session_state.get("kite_exact_binding")
        if binding and not preflight_is_current(
                binding=binding, constituents=constituents, inventory=inventory):
            clear_exact_preflight()
            binding = None
            st.warning("The list or inventory changed. Prepare and review a new binding.")
        if st.button(
                "Prepare exact 50-equity binding · no request",
                disabled=bool(missing_preflight),
                key="kite_exact_prepare_binding"):
            clear_exact_preflight()
            try:
                binding = prepare_preflight(
                    constituents=constituents, inventory=inventory, prepared_at=now())
                st.session_state["kite_exact_binding"] = binding
            except ValueError:
                st.error(
                    "Exact preflight stopped: use today's validated list and current "
                    "unique NSE EQ inventory. No request was made."
                )
        binding = st.session_state.get("kite_exact_binding")
        if binding:
            summary = binding.sanitized_summary()
            st.write({
                "target_count": summary["target_count"],
                "batch_sizes": summary["batch_sizes"],
                "exchange": summary["exchange"],
                "instrument_class": summary["instrument_class"],
            })
            st.caption("Review and confirm this exact local binding hash:")
            st.code(binding.binding_hash, language="text")
            checked = st.checkbox(
                "I confirm this exact 50-equity local binding for the bounded test.",
                key="kite_exact_binding_confirmed",
            )
            if st.button(
                    "Confirm exact binding · still no request",
                    disabled=not checked,
                    key="kite_exact_confirm_binding"):
                try:
                    approval = confirm_preflight(
                        binding=binding, constituents=constituents, inventory=inventory,
                        confirmed_hash=binding.binding_hash,
                        confirmation_checked=checked, confirmed_at=now())
                    st.session_state["kite_exact_approval"] = approval
                except ValueError:
                    st.session_state.pop("kite_exact_binding", None)
                    st.session_state.pop("kite_exact_approval", None)
                    st.error("Confirmation expired or inputs changed. Prepare a new binding.")
            approval = st.session_state.get("kite_exact_approval")
            if approval and approval.binding_hash == binding.binding_hash:
                st.success(
                    "Exact binding confirmed locally. No quote request has run. "
                    f"Confirmation expires {approval.expires_at.isoformat()}."
                )
        else:
            st.info("Load today's validated list and current Kite inventory to prepare the binding.")

        st.markdown("#### Legacy operational coverage check")
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
