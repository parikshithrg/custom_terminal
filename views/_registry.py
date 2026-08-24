"""Single source of truth for every page this app knows about - both
`app.py`'s `st.navigation` call and `home.py`'s grid read from this same
list, so a page's title/icon/description can never drift between the two.

HISTORY, in order:
1. First pass grouped pages by WHICH SOURCE PROJECT they came from.
2. Restructured same day once the user explained the actual purpose (three
   jobs - trading decisions, long-only investment decisions, news/event
   risk - sitting on a shared data foundation): 26 pages across 4
   job-oriented sections (`trading_desk`, `investment_desk`, `news_events`,
   `data_library`).
3. CONSOLIDATED 2026-08-18, later same day: asked for a viewpoint on which
   pages could club together, then asked to implement it. 26 pages -> 17.
   Nine pairs of pages that were really the same JOB split across two
   screens got merged into one page with two tabs (`subsections` below) -
   e.g. a risk reading and its own protection trigger, or a benchmark next
   to the return measured against it. Two pages (Lab, Backtesting
   Framework) were flagged rather than merged - they're two DIFFERENT
   ENGINES that both "configure and run a backtest," which is an open
   architecture question (consolidate to one engine? keep both?), not a
   page-layout one - merging their PAGES would have hidden that question,
   not resolved it. `note` on both surfaces the flag on the page itself.

SECTIONS:
  trading_desk    - the decision helper a professional trader uses, both
                    directions. Built to remove the mental burden of
                    holding every signal in your head at once.
  investment_desk - long-only, goal-oriented family capital: asset
                    rotation, capital protection, risk, alpha.
  news_events     - news, an event calendar, and the Black Swan Radar -
                    explicitly a similarity check against past black
                    swans' shared structural traits, not a forecast.
  data_library    - NOT a decision surface. The foundation both desks
                    above pull from - raw market data/reference pages.

DESCRIPTION CONVENTION: one short fragment, target 55-80 characters, no
parenthetical asides. For a consolidated page, `description` is the
home-grid card's own short unifying line (what the two tabs share), and
`subsections` holds each tab's own (label, description) pair at the same
length target. `home.py` gives every card a fixed height - a description
that runs long gets clipped rather than resizing its card.

Existing pages were RE-SECTIONED and now CONSOLIDATED, not renamed - the
surviving `file` paths still carry their original mg_/global_/research_
prefixes where applicable, recording provenance even where the grouping
or page count has moved on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTIONS = {
    "trading_desk": "Trading Desk",
    "investment_desk": "Investment Desk",
    "news_events": "News & Event Monitor",
    "data_library": "Markets Data Library",
}

# Shown under the Data Library header only - it's the one section that
# isn't a decision surface, worth saying once rather than leaving implicit.
SECTION_SUBTITLES = {
    "data_library": "Foundation, not a decision surface - raw data/reference pages the two desks above draw from.",
}


@dataclass(frozen=True)
class PageMeta:
    file: str
    title: str
    icon: str
    section: str
    description: str
    # (tab_label, tab_description) pairs - non-empty ONLY for a
    # consolidated page, rendered as tabs by render_stub_multi.
    subsections: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    # An architectural flag shown ON the page itself (render_stub's
    # optional st.warning) - for something worth surfacing to whoever
    # lands on the page, not just this source file's own comments.
    note: str | None = None


PAGES: list[PageMeta] = [
    # ============================== TRADING DESK ==============================
    PageMeta(
        "views/td_decision_helper.py", "Trade Decision Helper", "🎯", "trading_desk",
        "Synthesized long/short trade read - regime, setups, rotation, "
        "positioning.",
    ),
    PageMeta(
        "views/td_market_sector_context.py", "Market & Sector Context", "📊", "trading_desk",
        "Overall regime and sector-level rotation, read together.",
        subsections=(
            ("Market Regime", "Bull/Choppy/Bear regime classifier with "
             "per-sector capital deployment."),
            ("Sector Rotation", "Short-horizon read on which sectors are "
             "strengthening or weakening."),
        ),
    ),
    PageMeta(
        "views/mg_screener.py", "Setup Scanner", "🔍", "trading_desk",
        "Screens the tracked universe for candidate long and short setups.",
    ),
    PageMeta(
        "views/research_options_oi.py", "Options & Positioning", "🧭", "trading_desk",
        "Max pain, put-call ratio, and ATM strike reads for "
        "NIFTY/BANKNIFTY.",
    ),
    PageMeta(
        "views/td_trade_management.py", "Trade Management", "⚖️", "trading_desk",
        "Position sizing going in, the trade record coming out.",
        subsections=(
            ("Position Sizing & Risk", "Per-trade risk calculator - stop "
             "distance and open-position exposure."),
            ("Tradebook", "Trade history, P&L, streaks, and performance "
             "versus NIFTY50."),
        ),
    ),

    # ============================= INVESTMENT DESK =============================
    PageMeta(
        "views/inv_asset_allocation.py", "Asset Allocation & Rotation", "🧮", "investment_desk",
        "Long-horizon rotation across equity, debt, gold, and cash.",
    ),
    PageMeta(
        "views/inv_risk_protection.py", "Risk & Capital Protection", "🛡️", "investment_desk",
        "Risk exposure and the triggers that act on it, together.",
        subsections=(
            ("Risk Dashboard", "Concentration and correlation risk across "
             "the investment book."),
            ("Capital Protection", "Drawdown triggers and de-risking "
             "rules for long-term capital."),
        ),
    ),
    PageMeta(
        "views/inv_performance_benchmarks.py", "Performance & Benchmarks", "📐", "investment_desk",
        "Portfolio returns next to the benchmarks they're measured "
        "against.",
        subsections=(
            ("Alpha & Performance Tracking", "Performance versus "
             "benchmark and each goal's required return."),
            ("Index YTD", "Year-to-date performance across tracked "
             "benchmark indices."),
        ),
    ),
    PageMeta(
        "views/inv_goal_tracker.py", "Goal Tracker", "🎯", "investment_desk",
        "Progress against each family goal's own timeline and corpus.",
    ),

    # =========================== NEWS & EVENT MONITOR ===========================
    PageMeta(
        "views/news_feed_calendar.py", "News & Calendar", "📰", "news_events",
        "What's happening now and what's scheduled next, in one place.",
        subsections=(
            ("News Feed", "Aggregated global and local news relevant to "
             "both books."),
            ("Event Calendar", "Scheduled catalysts - earnings, central "
             "bank meetings, elections, expiries."),
        ),
    ),
    PageMeta(
        "views/news_event_risk.py", "Event Risk Assessment", "🦢", "news_events",
        "Whether an event is dangerous, and whether it hits your "
        "positions.",
        subsections=(
            ("Black Swan Radar", "Scores current conditions against past "
             "black swans' shared traits."),
            ("Portfolio Impact Mapper", "Maps a news event to exactly "
             "which positions it actually exposes."),
        ),
    ),

    # ============================ MARKETS DATA LIBRARY ============================
    # Foundation, not a decision surface - see SECTION_SUBTITLES above.
    PageMeta(
        "views/lib_correlation_explorer.py", "Correlation Explorer", "🔗", "data_library",
        "Cross-market and cross-asset correlations in one selector.",
        subsections=(
            ("Global Market Correlations", "Cross-market equity index "
             "correlations over rolling windows."),
            ("Global Asset & Commodity Correlations", "Cross-asset "
             "correlations across commodities, currencies, and rates."),
        ),
    ),
    PageMeta(
        "views/lib_data_coverage.py", "Data Coverage", "🌐", "data_library",
        "What data exists globally, and the gap versus local India data.",
        subsections=(
            ("Market Data Inventory", "Yahoo Finance coverage - global "
             "indices, ETFs, FX, commodities, rates."),
            ("India vs. Global Data", "Coverage map of local NSE data "
             "versus what needs Yahoo."),
        ),
    ),
    PageMeta(
        "views/lib_market_gate_home.py", "Market Gate Home", "🏠", "data_library",
        "Composite market score and pipeline health, together.",
        subsections=(
            ("Market Gate Dashboard", "Composite deployment-gate score "
             "for the Indian market."),
            ("Status", "Data health and pipeline diagnostics for Market "
             "Gate."),
        ),
    ),
    PageMeta(
        "views/mg_lab.py", "Lab", "🧪", "data_library",
        "Configure and run a backtest against Market Gate's strategies.",
        note="Overlaps with Backtesting Framework - both configure and "
             "run a backtest, via different engines. Whether these stay "
             "two engines or consolidate to one is an open question.",
    ),
    PageMeta(
        "views/research_backtest_framework.py", "Backtesting Framework", "⚙️", "data_library",
        "Config-driven strategy backtesting engine with HTML reports.",
        note="Overlaps with Lab - both configure and run a backtest, via "
             "different engines. Whether these stay two engines or "
             "consolidate to one is an open question.",
    ),
    PageMeta(
        "views/mg_seasonality.py", "Seasonality", "🗓", "data_library",
        "Seasonal and calendar-based patterns across the tracked universe.",
    ),
    PageMeta(
        "views/lib_reports.py", "Reports", "📄", "data_library",
        "Written research reports, rendered in-app - Data test's "
        "hypothesis testing report and any added later.",
    ),
]

PAGES_BY_FILE: dict[str, PageMeta] = {p.file: p for p in PAGES}
