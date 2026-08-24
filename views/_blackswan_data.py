"""Live data for the Black Swan Radar - a composite cross-asset stress
score, 0-100 (100 = most stressed), built from 7 dimensions: India VIX,
US VIX, market breadth (inverted - low breadth = high stress), USDINR's
own 20-session rate of change, DXY level, gold's own 20-session return,
and (added 2026-08-18) aggregate news sentiment (inverted - negative
tone = high stress).

NOT A PREDICTOR. Scoped 2026-08-18 on the premise the user stated: black
swans can't be predicted individually, but hindsight shows they share
structural traits (vol spikes, breadth deterioration, flight to safety,
currency stress). This measures how stressed CURRENT conditions look
across those traits, relative to history - it has NOT been backtested
against real historical crisis windows (2008, 2020, etc.) to confirm the
composite actually tracks past black swans. That would be a separate,
real research undertaking (matching the `Data test` project's own
train/val discipline), not assumed here just because the ingredients
sound plausible. Equal-weighted across all 7 dimensions, deliberately -
no weight has been fit or validated, so none is presented as mattering
more than another.

Market breadth is READ-ONLY REUSE of market_gate's own universe loader
and breadth function (`universe.load_universe_symbols`,
`universe.read_local_daily`, `signals.breadth.pct_above_sma`) - the exact
functions Market Gate's own Market Regime page calls, not a
reimplementation that could quietly drift from how market_gate itself
defines breadth. The 5 market series come from Yahoo Finance via
yfinance - India VIX (`^INDIAVIX`) is directly queryable there, confirmed
live 2026-08-18, so this needed no dependency on market_gate's own (as
of writing, not locally cached) VIX data at all.

SENTIMENT IS METHODOLOGICALLY DIFFERENT FROM THE OTHER 6, stated
plainly rather than blended in silently: every other dimension
percentile-ranks today against a real ~1-year history that already
existed (Yahoo's own price history). Aggregate news sentiment has never
been computed before today, so there IS no year of history to
percentile-rank against yet - one only exists from this point forward.
`data/sentiment_history.csv` (this project's own, new, append-only log -
the first piece of state Local Terminal persists itself, everything
else so far has been either live-fetched or read-only from market_gate)
records one row per calendar day, upserted if the page runs more than
once the same day. Until MIN_HISTORY_DAYS (30) rows exist, sentiment
uses a PROVISIONAL fixed linear scale instead of a percentile - bounds
hand-picked from the one real reading available at build time (today's
aggregate was +0.12; -0.20 was set as the "clearly downbeat" anchor and
+0.30 as the "clearly upbeat" one) and NOT validated against a real
range of days, since no such range exists yet. Once 30+ days accumulate,
scoring switches to the same percentile convention as every other
dimension automatically - no code change needed, just time passing.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(r"C:\Users\parik\OneDrive\Desktop\Dashboard")
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

LOCAL_TERMINAL_ROOT = Path(__file__).resolve().parent.parent
SENTIMENT_LOG_PATH = LOCAL_TERMINAL_ROOT / "data" / "sentiment_history.csv"
MIN_HISTORY_DAYS = 30
# Provisional-scale bounds - see module docstring for why these are a
# stated placeholder, not a fitted range.
SENTIMENT_STRESSED_ANCHOR = -0.20   # aggregate mean at/below this -> stress 100
SENTIMENT_CALM_ANCHOR = 0.30        # aggregate mean at/above this -> stress 0

YAHOO_TICKERS = {
    "india_vix": "^INDIAVIX",
    "us_vix": "^VIX",
    "usdinr": "INR=X",
    "dxy": "DX-Y.NYB",
    "gold": "GC=F",
}

# High score = high stress, throughout. Cutoffs are round, hand-set
# anchors (same spirit as market_gate's own BAND scale) - not fitted.
BANDS = [(80, "Crisis-level"), (60, "Stressed"), (40, "Elevated"), (20, "Normal"), (0, "Calm")]


def band_for_score(score: float) -> str:
    for cutoff, label in BANDS:
        if score >= cutoff:
            return label
    return "Calm"


def _percentile_rank(series: pd.Series) -> float | None:
    """Where the LAST value sits (0-100) versus every PRIOR value in the
    series - today is never compared against itself."""
    clean = series.dropna()
    if len(clean) < 30:
        return None
    return float((clean.iloc[:-1] < clean.iloc[-1]).mean() * 100.0)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yahoo_stress_inputs() -> dict[str, pd.Series]:
    import yfinance as yf
    out: dict[str, pd.Series] = {}
    for key, ticker in YAHOO_TICKERS.items():
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
            s = df["Close"]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            out[key] = s.dropna()
        except Exception:
            out[key] = pd.Series(dtype=float)
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_breadth() -> pd.Series:
    """% of the NIFTY 500 universe above its own 200-day SMA, daily."""
    try:
        from market_gate import universe as mg_universe
        from market_gate.config import DATA_DIR as MG_DATA_DIR
        from market_gate.config import PROJECT_DATA_DIR
        from market_gate.signals import breadth as mg_breadth

        symbols = mg_universe.load_universe_symbols(MG_DATA_DIR / "nifty500.csv", "", None)
        cutoff = pd.Timestamp(datetime.now()) - pd.Timedelta(days=400)
        cols = {}
        for sym in symbols:
            df = mg_universe.read_local_daily(sym, PROJECT_DATA_DIR, cutoff, columns=("close",))
            if df is not None:
                cols[sym] = df["close"]
        if not cols:
            return pd.Series(dtype=float)
        prices = pd.DataFrame(cols)
        pct, _coverage = mg_breadth.pct_above_sma(prices, window=200, min_coverage=50)
        return pct.dropna()
    except Exception:
        return pd.Series(dtype=float)


def _record_and_load_sentiment_history(today_mean: float, n_articles: int) -> pd.DataFrame:
    """Upserts today's aggregate sentiment into the local log and returns
    the full history. Upsert (not append) because this can run more than
    once in a day (every page load, subject to the cache TTL) - a second
    run today must replace today's row, not duplicate it."""
    SENTIMENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    today = pd.Timestamp(datetime.now().date())

    if SENTIMENT_LOG_PATH.exists():
        log = pd.read_csv(SENTIMENT_LOG_PATH, parse_dates=["date"])
    else:
        log = pd.DataFrame(columns=["date", "mean_sentiment", "n_articles"])

    log = log[log["date"] != today]
    new_row = pd.DataFrame([{"date": today, "mean_sentiment": today_mean, "n_articles": n_articles}])
    log = pd.concat([log, new_row], ignore_index=True).sort_values("date").reset_index(drop=True)
    log.to_csv(SENTIMENT_LOG_PATH, index=False)
    return log


def _linear_map(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    t = (x - x0) / (x1 - x0) if x1 != x0 else 0.0
    t = max(0.0, min(1.0, t))
    return y0 + t * (y1 - y0)


def _sentiment_dimension(news_df: pd.DataFrame | None) -> dict:
    if news_df is None or news_df.empty or "sentiment" not in news_df.columns:
        return {"key": "sentiment", "label": "News Sentiment", "score": None,
               "detail": "data unavailable", "value": None}

    today_mean = float(news_df["sentiment"].mean())
    n_articles = int(len(news_df))
    log = _record_and_load_sentiment_history(today_mean, n_articles)

    if len(log) >= MIN_HISTORY_DAYS:
        pct = _percentile_rank(log["mean_sentiment"])
        score = (100.0 - pct) if pct is not None else None
        detail = f"percentile vs {len(log)}-day accumulated history, inverted"
    else:
        # Negative sentiment -> high stress, so the map runs stressed-anchor
        # -> 100 down to calm-anchor -> 0 (an inverted range on purpose).
        score = _linear_map(today_mean, SENTIMENT_STRESSED_ANCHOR, SENTIMENT_CALM_ANCHOR, 100.0, 0.0)
        detail = f"provisional fixed scale (only {len(log)}/{MIN_HISTORY_DAYS} days logged so far)"

    return {
        "key": "sentiment", "label": "News Sentiment",
        "score": round(score, 1) if score is not None else None,
        "detail": detail, "value": f"{today_mean:+.2f} avg ({n_articles} articles)",
    }


def _dimension(key, label, series, detail, value_fmt, *, invert=False, pct_change_days=None) -> dict:
    if series is None or series.empty:
        return {"key": key, "label": label, "score": None, "detail": "data unavailable", "value": None}

    s = series
    if pct_change_days:
        s = ((s / s.shift(pct_change_days) - 1.0) * 100.0).dropna()

    pct = _percentile_rank(s)
    if pct is None:
        return {"key": key, "label": label, "score": None, "detail": "insufficient history", "value": None}

    score = (100.0 - pct) if invert else pct
    raw_val = float(s.dropna().iloc[-1])
    return {
        "key": key, "label": label, "score": round(score, 1),
        "detail": detail, "value": value_fmt.format(raw_val),
    }


def compute_stress_score() -> dict:
    yahoo = fetch_yahoo_stress_inputs()
    breadth = fetch_breadth()

    try:
        from views._news_data import fetch_news
        news_df = fetch_news()
    except Exception:
        news_df = None

    dims = [
        _dimension("india_vix", "India VIX", yahoo.get("india_vix"),
                  "percentile of level, ~1y", "{:.1f}"),
        _dimension("us_vix", "US VIX", yahoo.get("us_vix"),
                  "percentile of level, ~1y", "{:.1f}"),
        _dimension("breadth", "Market Breadth", breadth,
                  "percentile of % above 200DMA, inverted", "{:.0f}% above 200DMA", invert=True),
        _dimension("usdinr", "USDINR (20-session change)", yahoo.get("usdinr"),
                  "percentile of 20-session % change", "{:+.2f}%", pct_change_days=20),
        _dimension("dxy", "US Dollar Index", yahoo.get("dxy"),
                  "percentile of level, ~1y", "{:.1f}"),
        _dimension("gold", "Gold (20-session return)", yahoo.get("gold"),
                  "percentile of 20-session return", "{:+.2f}%", pct_change_days=20),
        _sentiment_dimension(news_df),
    ]

    valid = [d["score"] for d in dims if d["score"] is not None]
    composite = round(sum(valid) / len(valid), 1) if valid else None

    return {
        "composite": composite,
        "band": band_for_score(composite) if composite is not None else "Unavailable",
        "dimensions": dims,
        "n_available": len(valid),
        "n_total": len(dims),
    }
