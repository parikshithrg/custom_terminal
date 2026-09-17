"""Dashboard's explicitly manual daily login panel; no page-load requests."""


def render():
    import streamlit as st
    from market_intel.foundation.kite_connect import build_login_url, disconnect

    def login(method):
        import requests
        from market_intel.dashboard_kite_login import connect
        connect(st.session_state, method=method, http=requests)

    if st.button("Kite API login", key="dashboard_kite_login_button"):
        st.session_state["dashboard_kite_login_open"] = not st.session_state.get("dashboard_kite_login_open", False)
    if not st.session_state.get("dashboard_kite_login_open"):
        if st.session_state.get("kite_session"):
            st.caption("Kite session available in memory · Dashboard prices remain synthetic")
        return
    with st.container(border=True):
        st.markdown("#### Daily Kite connection")
        st.caption("Local private use only. No automatic validation, data pull or trading. Never paste credentials into chat.")
        if st.session_state.get("kite_ui_error"):
            st.error(st.session_state.pop("kite_ui_error"))
        if st.session_state.get("kite_ui_message"):
            st.success(st.session_state.pop("kite_ui_message"))
        if st.session_state.get("kite_session"):
            st.info("Session available in memory. Use Data Coverage for manual validation and existing current-data controls.")
            st.page_link("views/lib_data_coverage.py", label="Open Data Coverage")
        else:
            key = st.text_input("Kite API key", type="password", key="kite_api_key", max_chars=128)
            browser, existing = st.tabs(["Log in with Zerodha", "Paste existing access token"])
            with browser:
                st.text_input("Kite API secret", type="password", key="kite_api_secret", max_chars=1024)
                if key.strip():
                    st.link_button("1. Open Zerodha API login", build_login_url(key))
                else:
                    st.caption("Enter your API key to show the official login link.")
                st.text_input("2. Paste request_token or complete redirect URL", type="password",
                              key="kite_request_token", max_chars=8192)
                st.button("3. Create daily Kite session", on_click=login, args=("request_token",))
                st.caption("The browser returns request_token, not access_token. The app exchanges it once; no retry.")
            with existing:
                st.text_input("Daily access token", type="password", key="kite_access_token_input", max_chars=4096)
                st.button("Attach access token", on_click=login, args=("access_token",))
                st.caption("API secret is not needed here. Attaching does not verify the token or contact Kite.")
        st.button("Disconnect Kite and clear values", on_click=disconnect, args=(st.session_state,))
        st.caption("Secrets and token inputs clear after every attempt. Sessions survive reruns only—not a server restart or new browser session. Disconnect removes references, not guaranteed secure memory erasure.")
