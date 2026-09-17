"""Default page execution remains offline even with purported approval flags."""
import ast
from dataclasses import replace
from pathlib import Path
import sys
import pytest
from market_intel.news_readiness_v1 import REQUIRED_BINDINGS, assess_news_readiness

ROOT = Path(__file__).resolve().parents[1]


def test_missing_partial_and_complete_metadata_cannot_activate():
    state = assess_news_readiness()
    assert state.missing_prerequisites == REQUIRED_BINDINGS
    assert not state.can_fetch and not state.can_score
    partial = {REQUIRED_BINDINGS[0]:"a"*64}
    before = partial.copy()
    assert len(assess_news_readiness(partial).missing_prerequisites)==9
    assert partial == before
    complete=assess_news_readiness({key:"a"*64 for key in REQUIRED_BINDINGS})
    assert complete.status=="METADATA_BOUND_NOT_VERIFIED_EXECUTION_DISABLED"
    assert not complete.can_fetch and not complete.can_score
    for kwargs in ({"can_fetch":True},{"can_score":True}):
        with pytest.raises(ValueError):
            replace(complete,**kwargs)


@pytest.mark.parametrize("evidence",[{"approved":True},[],{"publisher_binding":"private/path"}, {"publisher_binding":True}])
def test_invalid_bindings_fail_closed(evidence):
    if type(evidence) is not dict or set(evidence)-set(REQUIRED_BINDINGS):
        with pytest.raises(ValueError):
            assess_news_readiness(evidence)
    else:
        assert "publisher_binding" in assess_news_readiness(evidence).missing_prerequisites


def test_page_load_no_legacy_import_request_or_persistence(monkeypatch):
    site=ROOT/".venv/Lib/site-packages"
    if str(site) not in sys.path:
        sys.path.append(str(site))
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import requests
    import socket
    import pandas as pd
    def forbidden(*args,**kwargs):
        raise AssertionError("External or market file access prohibited")
    monkeypatch.setattr(requests.sessions.Session,"request",forbidden)
    monkeypatch.setattr(socket,"create_connection",forbidden)
    monkeypatch.setattr(pd,"read_csv",forbidden)
    monkeypatch.setattr(pd.DataFrame,"to_csv",forbidden)
    real_import=__import__
    def guarded_import(name,*args,**kwargs):
        if name in {"views._news_data","views._sentiment","views._blackswan_data","views._legacy_news_calendar","yfinance","feedparser","sqlite3","duckdb"}:
            raise AssertionError("Legacy/source import prohibited")
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr("builtins.__import__",guarded_import)
    app=AppTest.from_file(str(ROOT/"views/news_feed_calendar.py")).run()
    assert not app.exception and len(app.tabs)==2
    assert len(app.button)==0 and len(app.radio)==0
    app.session_state["news_execution_approved"]=True
    app.session_state["news_source_ready"]=True
    app.run()
    assert not app.exception
    assert any("UNAVAILABLE_MISSING_PREREQUISITES" in c.value for c in app.caption)


def test_new_modules_have_no_io_or_scoring_imports():
    allowed={"streamlit","market_intel.news_readiness_v1","views._registry","views._theme","dataclasses","re"}
    for path in (ROOT/"views/news_feed_calendar.py",ROOT/"src/market_intel/news_readiness_v1.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert node.module in allowed
            if isinstance(node,ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            if isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
                assert name not in {"open","read_csv","to_csv","write_text","request","fetch_news","score_text","now","today"}
    assert (ROOT/"views/_legacy_news_calendar.py").is_file()
