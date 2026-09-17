"""Local Terminal - entrypoint. `st.navigation(position="hidden")` wires
up real multi-page routing (so `st.page_link`/`st.switch_page` work) but
suppresses Streamlit's automatic navigation. An explicitly grouped sidebar
and shared fixed header reproduce the owner's chosen static-reference shell.
"""

from __future__ import annotations

import streamlit as st

from views._registry import PAGES, SECTIONS
from views import _theme

st.set_page_config(page_title="Local Terminal", page_icon="🖥️", layout="wide", initial_sidebar_state="expanded")
_theme.apply()

pages = [st.Page("views/home.py", title="Local Terminal", icon="🖥️", default=True)]
pages += [st.Page(p.file, title=p.title, icon=p.icon) for p in PAGES]

pg = st.navigation(pages, position="hidden")
_theme.masthead()
with st.sidebar:
    st.page_link("views/home.py", label="Dashboard")
    for section, title in SECTIONS.items():
        st.caption(title)
        for page in PAGES:
            if page.section == section:
                st.page_link(page.file, label=page.title)
pg.run()
