"""Local Terminal - entrypoint. `st.navigation(position="hidden")` wires
up real multi-page routing (so `st.page_link`/`st.switch_page` work) but
suppresses Streamlit's own sidebar nav entirely - navigation happens only
through `views/home.py`'s grid, per how this was scoped (grid boxes,
explicitly not tabs or a sidebar).
"""

from __future__ import annotations

import streamlit as st

from views._registry import PAGES

st.set_page_config(page_title="Local Terminal", page_icon="🖥️", layout="wide")

pages = [st.Page("views/home.py", title="Local Terminal", icon="🖥️", default=True)]
pages += [st.Page(p.file, title=p.title, icon=p.icon) for p in PAGES]

pg = st.navigation(pages, position="hidden")
pg.run()
