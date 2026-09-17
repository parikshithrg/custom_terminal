"""Local, presentation-only styling informed by TradingQnA and the static reference.

No reference data, scripts, or generated panels are imported.
"""
from html import escape

CSS = """
<style>
:root { --lt-ink:#222222; --lt-muted:#767676; --lt-rule:#e9e9e7; --lt-border:#e9e9e7; --lt-accent:#2563eb; --lt-hover:#f6f6f5; }
[data-testid="stAppViewContainer"], [data-testid="stHeader"] { background:#fff; color:var(--lt-ink); }
[data-testid="stHeader"] { background:transparent; pointer-events:none; }
[data-testid="stHeader"] button { pointer-events:auto; }
[data-testid="stMainBlockContainer"] { padding:76px 28px 48px !important; }
[data-testid="stSidebar"] { width:240px !important; min-width:240px !important; max-width:240px !important; background:#fff; border-right:1px solid var(--lt-rule); margin-top:56px; height:calc(100vh - 56px); }
[data-testid="stSidebarContent"] { padding-top:16px; }
[data-testid="stSidebarUserContent"] { padding:0 !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { padding:16px 20px 6px; font-size:12px; font-weight:700; letter-spacing:.04em; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a { padding:9px 20px; border-radius:0; font-size:14px; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background:var(--lt-hover); }
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] { background:#eef4ff; color:var(--lt-accent); font-weight:600; }
[data-testid="stMarkdownContainer"] h2 { font-size:19px !important; line-height:1.3; padding:0 0 4px !important; }
[data-testid="stMarkdownContainer"] h3 { font-size:17px !important; }
[data-testid="stMarkdownContainer"] h4 { font-size:14.5px !important; }
[data-testid="stCaptionContainer"] p { font-size:12.5px; line-height:1.5; }
.lt-masthead { position:fixed; top:0; left:0; right:0; height:56px; min-height:56px; z-index:999; padding:0 20px; margin:0; background:#fff; }
.lt-table, .lt-market-card { font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif; }
.lt-table caption { text-align:left; color:var(--lt-muted); font-size:12px; padding:6px 10px; }
[data-testid="stMainBlockContainer"] { max-width:1600px; padding-top:64px; padding-bottom:48px; }
h1,h2,h3,h4,h5,p,label { font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif; }
h2 { font-size:21px; letter-spacing:normal; }
h3 { font-size:19px; } h4 { font-size:14.5px; }
[data-testid="stCaptionContainer"] { color:var(--lt-muted); }
[data-testid="stMetricValue"], .lt-number { font-family:"IBM Plex Mono",Consolas,monospace; font-variant-numeric:tabular-nums; }
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stLayoutWrapper"] > div[class*="st-key-card-"] { border-color:var(--lt-border); border-radius:8px; }
.lt-masthead { display:flex; align-items:center; justify-content:space-between; gap:16px; border-bottom:1px solid var(--lt-rule); }
.lt-brand { display:flex; align-items:center; gap:8px; font-size:16px; font-weight:700; }
.lt-logo { display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:7px; background:var(--lt-accent); color:#fff; font-size:14px; }
.lt-tag { display:inline-block; padding:4px 9px; border:1px solid var(--lt-rule); border-radius:6px; font-size:11px; letter-spacing:.04em; background:#fff; color:var(--lt-muted); }
.lt-kicker { font-size:11px; letter-spacing:.10em; text-transform:uppercase; color:var(--lt-muted); margin-bottom:7px; }
.lt-market-grid { display:grid; grid-template-columns:repeat(4,minmax(110px,180px)); gap:14px; margin:0 0 22px; }
.lt-market-card { padding:12px 18px; border:1px solid var(--lt-border); border-radius:8px; }
.lt-number { font-size:21px; font-weight:700; }
.lt-up { color:#15803d; } .lt-down { color:#b91c1c; }
.lt-change { font-size:12px; margin-top:6px; }
.lt-table-wrap { overflow:auto; max-height:420px; border:1px solid var(--lt-border); border-radius:6px; margin-top:10px; }
.lt-table { border-collapse:collapse; width:100%; font-size:13px; min-width:510px; }
.lt-table th { position:sticky; top:0; z-index:1; background:#fff; color:var(--lt-muted); font-size:12px; text-align:left; padding:8px 10px; font-weight:600; border-bottom:1px solid var(--lt-rule); }
.lt-table td { padding:8px 10px; white-space:nowrap; border-bottom:1px solid var(--lt-rule); }
.lt-table tbody tr:hover { background:var(--lt-hover); }
.lt-table tr:last-child td { border-bottom:0; }
.lt-table th:nth-child(2), .lt-table th:nth-child(3), .lt-table td:nth-child(2), .lt-table td:nth-child(3) { text-align:right; font-variant-numeric:tabular-nums; }
.lt-empty { border:1px dashed var(--lt-rule); padding:22px; color:var(--lt-muted); border-radius:4px; }
.lt-topbar { flex-wrap:wrap; }
.lt-topbar a:focus-visible, [data-testid="stPageLink"] a:focus-visible { outline:2px solid var(--lt-accent); outline-offset:3px; }
div[class*="st-key-card-"] { border-color:var(--lt-border) !important; border-radius:8px; transition:background .15s; }
div[class*="st-key-card-"]:hover { background:var(--lt-hover); }
@media(max-width:1000px) {
 .lt-market-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
 [data-testid="stHorizontalBlock"]:has(div[class*="st-key-card-"]) { flex-wrap:wrap; }
 [data-testid="stHorizontalBlock"]:has(div[class*="st-key-card-"]) > [data-testid="stColumn"] { min-width:calc(50% - 1rem); flex:1 1 calc(50% - 1rem); }
}
@media(max-width:560px) {
 .lt-tag { display:none; }
 .lt-brand { font-size:14px; }
 [data-testid="stSidebar"] { width:220px !important; min-width:220px !important; max-width:220px !important; }
 [data-testid="stMainBlockContainer"] { padding-left:16px; padding-right:16px; }
 .lt-market-grid { grid-template-columns:1fr; }
 [data-testid="stHorizontalBlock"]:has(div[class*="st-key-card-"]) > [data-testid="stColumn"] { min-width:100%; flex-basis:100%; }
 .lt-number { font-size:22px; }
}
/* Final high-specificity shell overrides: beat Streamlit's generated rules. */
html body [data-testid="stAppViewContainer"], html body [data-testid="stMain"] { background:#fff !important; color:#222 !important; }
html body [data-testid="stMainBlockContainer"] { padding:76px 28px 48px !important; max-width:none !important; }
html body [data-testid="stSidebar"] { background:#fff !important; width:240px !important; min-width:240px !important; max-width:240px !important; flex-basis:240px !important; border-right:1px solid #e9e9e7 !important; top:56px !important; margin-top:0 !important; height:calc(100vh - 56px) !important; }
html body [data-testid="stSidebarContent"] { background:#fff !important; padding:16px 0 !important; }
html body [data-testid="stSidebarUserContent"] { padding:0 !important; }
html body [data-testid="stSidebarHeader"] { display:none !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] { padding:0 !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a { display:flex !important; align-items:center !important; gap:10px !important; min-height:37px; margin:0 !important; padding:9px 20px !important; border-radius:0 !important; font-size:14px !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a::before { content:""; width:10px; height:10px; flex:none; border-radius:2px; background:#2563eb; }
html body [data-testid="stSidebar"] [data-testid="stElementContainer"]:nth-child(3n) a::before { background:#15803d; }
html body [data-testid="stSidebar"] [data-testid="stElementContainer"]:nth-child(3n+1) a::before { background:#9333ea; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"], html body [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-selected="true"] { background:#eef4ff !important; color:#2563eb !important; }
html body [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#767676 !important; font-size:12px !important; font-weight:700; letter-spacing:.04em; }
html body .lt-masthead { position:fixed !important; top:0 !important; left:0 !important; right:0 !important; width:100vw !important; height:56px !important; padding:0 20px !important; margin:0 !important; background:#fff !important; border-bottom:1px solid #e9e9e7 !important; z-index:999999 !important; }
html body h2, html body [data-testid="stMarkdownContainer"] h2 { font-size:19px !important; line-height:1.3 !important; margin:0 !important; padding:0 0 4px !important; }
html body h3 { font-size:17px !important; } html body h4 { font-size:14.5px !important; }
html body [data-testid="stMain"] [data-testid="stVerticalBlock"] { gap:8px !important; }
html body [data-testid="stCaptionContainer"] p { color:#767676 !important; font-size:12.5px !important; }
html body .lt-number { font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif !important; font-size:21px !important; }
html body .lt-market-grid { margin:0 0 18px !important; }
@media(max-width:560px) { html body [data-testid="stMainBlockContainer"] { padding:76px 16px 32px !important; } }
</style>
"""

def apply():
    import streamlit as st
    # Style-only HTML enters Streamlit's event container, avoiding blank layout
    # blocks and allowing app-wide CSS rather than markdown content styling.
    st.html(CSS + REFERENCE_CSS)


# Measured against the live reference. No remote CSS, scripts, logos, fonts,
# forum content, or market data are fetched by the terminal.
REFERENCE_CSS = """
<style>
html body { font-family:"Open Sans",Helvetica,"Segoe UI",sans-serif; color:#222; background:#fff; }
html body [data-testid="stAppViewContainer"], html body [data-testid="stMain"], html body [data-testid="stSidebar"], html body [data-testid="stSidebarContent"] { background:#fff !important; }
html body [data-testid="stHeader"] { height:52px; background:transparent !important; }
html body [data-testid="stMainBlockContainer"] { padding:76px 28px 48px !important; }
html body .lt-masthead { height:52px !important; min-height:52px !important; padding-left:48px !important; border-bottom:1px solid #e9e9e9 !important; box-shadow:0 1px 2px #00000006; }
html body [data-testid="stHeader"] { z-index:1000000; }
html body [data-testid="stSidebarHeader"] { display:flex !important; position:fixed; top:6px; left:4px; padding:0; width:36px; height:40px; z-index:1000001; }
html body [data-testid="stLogoSpacer"] { display:none; }
html body .lt-brand { font-family:"Open Sans",Helvetica,"Segoe UI",sans-serif; font-size:20px; color:#444; }
html body .lt-logo { background:#07bcf5; border-radius:3px; }
html body .lt-tag { color:#767676; border:0; font-size:12px; letter-spacing:0; }
html body [data-testid="stSidebar"] { top:52px !important; width:240px !important; min-width:240px !important; max-width:240px !important; height:calc(100vh - 52px) !important; border-color:#e9e9e9 !important; }
html body [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0 !important; }
html body [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { padding:18px 16px 5px !important; border-bottom:1px solid #e9e9e9; margin:0 8px 4px; }
html body [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { font-weight:400 !important; color:#666 !important; letter-spacing:0 !important; font-size:13px !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a { padding:8px 16px !important; min-height:36px; font-family:"Open Sans",Helvetica,"Segoe UI",sans-serif; color:#444; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a p { font-size:14px !important; line-height:20px; white-space:normal !important; overflow:visible !important; text-overflow:clip !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background:#f6f6f5 !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"], html body [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-selected="true"] { background:#f2f2f2 !important; color:#222 !important; }
html body .lt-market-card, html body .lt-table-wrap { border-color:#e9e9e9; }
html body .lt-table th { color:#919191; border-bottom:2px solid #e9e9e9; }
html body .lt-table td { border-bottom:1px solid #e9e9e9; padding:10px; }
html body .lt-table tbody tr { border-bottom:1px solid #e9e9e9; }
html body .lt-table-wrap { margin-bottom:26px; }
html body .lt-market-grid { margin:0 0 22px !important; }
html body h1, html body h2, html body h3, html body h4, html body p, html body label { font-family:"Open Sans",Helvetica,"Segoe UI",sans-serif !important; }
html body [data-testid="stCaptionContainer"] p { color:#767676 !important; }
html body [data-testid="stMain"] [data-testid="stVerticalBlock"] { gap:8px !important; }
html body [data-testid="stSidebar"] [data-testid="stPageLink"] a:focus-visible { outline:2px solid #07bcf5; outline-offset:-2px; }
@media(max-width:760px) {
 html body .lt-brand { font-size:16px; }
 html body .lt-masthead { padding-left:48px !important; }
 html body [data-testid="stHeader"] { z-index:1000000; }
 html body [data-testid="stSidebar"] { z-index:1000001; }
}
</style>
"""

def masthead():
    import streamlit as st
    st.markdown('<div class="lt-masthead"><div class="lt-brand"><span class="lt-logo" aria-hidden="true">M</span>Local Terminal / Market workspace</div><div><span class="lt-tag">MOCK-FIRST INTERFACE</span> <span class="lt-tag">NO TRADE EXECUTION</span></div></div>', unsafe_allow_html=True)

def empty_panel(label="Data unavailable"):
    import streamlit as st
    st.markdown(f'<div class="lt-empty"><strong>{escape(label)}</strong><br>No qualified data source is connected to this panel. No signal or estimate is generated.</div>', unsafe_allow_html=True)
