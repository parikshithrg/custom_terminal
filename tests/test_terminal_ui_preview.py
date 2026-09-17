"""Presentation-only UI and no-source-access regression checks."""
import ast
import sys
from pathlib import Path

import pytest
from views import _market_preview as preview, _theme

ROOT = Path(__file__).resolve().parents[1]

def test_preview_is_explicitly_synthetic_and_escaped():
    assert "demonstration only" in preview.index_markup()
    assert "synthetic values" in preview.table_markup(preview.DEMO_ROWS)
    assert "&lt;script&gt;" in preview.table_markup([("<script>","1","0","mock")])
    assert "24,850.25" in preview.index_markup()

def test_theme_has_local_fonts_responsive_layout_and_focus():
    assert "@import" not in _theme.CSS and "https://" not in _theme.CSS
    assert "560px" in _theme.CSS and "1000px" in _theme.CSS
    assert "focus-visible" in _theme.CSS and "tabular-nums" in _theme.CSS

def test_static_reference_adaptation_is_visual_only():
    assert "#e9e9e7" in _theme.CSS and "#2563eb" in _theme.CSS
    assert "position:sticky" in _theme.CSS and "tbody tr:hover" in _theme.CSS
    assert "html body .lt-masthead { position:fixed !important" in _theme.CSS
    assert "background:#fff !important; width:240px !important" in _theme.CSS
    assert "a::before" in _theme.CSS and "#eef4ff" in _theme.CSS
    assert "st.html(CSS + REFERENCE_CSS)" in (ROOT/"views/_theme.py").read_text(encoding="utf-8")
    assert "#07bcf5" in _theme.REFERENCE_CSS
    assert "height:52px" in _theme.REFERENCE_CSS
    assert "https://" not in _theme.REFERENCE_CSS and "@import" not in _theme.REFERENCE_CSS
    tree = ast.parse((ROOT/"views/_theme.py").read_text(encoding="utf-8"))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {"html"}
    assert {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} == {"streamlit"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id in {"open", "eval", "exec"} for node in ast.walk(tree))

def test_preview_does_not_load_sources_or_experimental_facts():
    tree=ast.parse((ROOT/"views/_market_preview.py").read_text())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert set(imports)=={"decimal","html"}
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {"open","eval","exec"} for n in ast.walk(tree))
    text=(ROOT/"views/_market_preview.py").read_text()
    assert "experimental outputs are unavailable" in text
    assert "requests" not in text and "sqlite3" not in text

def test_existing_grid_routing_preserved():
    text=(ROOT/"app.py").read_text(encoding="utf-8")
    assert 'position="hidden"' in text
    assert "with st.sidebar:" in text
    assert "_theme.masthead()" in text
    text=(ROOT/"views/home.py").read_text(encoding="utf-8")
    assert "st.page_link(page.file" in text
    assert '_market_preview.readiness()' in text
    assert 'st.expander("Market overview' not in text

def test_requested_cards_hidden_without_deleting_metadata():
    from views._registry import PAGES, ALL_PAGES, PAGES_BY_FILE, HIDDEN_PAGE_FILES
    assert HIDDEN_PAGE_FILES == frozenset({
        "views/td_decision_helper.py", "views/research_options_oi.py",
        "views/td_trade_management.py", "views/inv_risk_protection.py",
    })
    assert not HIDDEN_PAGE_FILES.intersection(p.file for p in PAGES)
    assert HIDDEN_PAGE_FILES.issubset(PAGES_BY_FILE)
    assert len(PAGES) == len(ALL_PAGES) - 4
    merged = PAGES_BY_FILE["views/inv_asset_allocation.py"]
    assert [name for name, _ in merged.subsections] == [
        "Asset Allocation & Rotation", "Risk Dashboard", "Capital Protection",
    ]

def test_home_streamlit_interactions():
    # Reuse installed pure-Python UI dependencies without installing anything.
    site=ROOT/".venv/Lib/site-packages"
    if site.exists() and str(site) not in sys.path:
        sys.path.append(str(site))
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=15).run()
    assert not app.exception
    assert app.radio[0].value=="Equities"
    app.radio[0].set_value("Futures").run()
    assert not app.exception
    rendered=" ".join(m.value for m in app.markdown)
    assert "DEMO FUTURE A" in rendered
    assert "unqualified / evidence deferred" in rendered
