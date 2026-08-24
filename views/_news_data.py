"""Live data for the News & Event Monitor - News Feed (RSS, no API key)
and Event Calendar (NSE's own unofficial JSON endpoints, no API key).

SOURCES CHOSEN 2026-08-18 after live-probing every candidate rather than
assuming availability: GDELT was rate-limited (429) every attempt,
Trading Economics' free "guest" tier is discontinued (410), FRED needs a
real registered key with no demo option. RSS and NSE's own endpoints were
the two that worked cleanly with zero signup - see
[[project-local-terminal-status]]'s 2026-08-18 entry for the full probe
results, including the ones that didn't pan out.

NSE'S ENDPOINTS ARE UNOFFICIAL AND UNDOCUMENTED. They can require a
warmed-up session (cookies from a prior request to the site itself)
depending on network/IP - confirmed working bare (no session) from this
machine, but that is not guaranteed elsewhere, so every call here still
warms a session first rather than assuming it. Every fetch function
degrades to an empty DataFrame on failure rather than raising - a page
that can't reach NSE or one RSS host today should still render everything
else, not crash.

SENTIMENT (added 2026-08-18): every article's `title` is scored via
`views/_sentiment.py`'s finance-augmented VADER, not plain VADER - see
that module's own docstring for why (plain VADER misreads financial
headlines badly, confirmed on real examples before choosing this).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import feedparser
import pandas as pd
import requests
import streamlit as st

from views._sentiment import score_text

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
REQUEST_TIMEOUT = 12

# (display name, feed URL, region) - each URL confirmed live via a direct
# probe on 2026-08-18, not assumed from documentation.
NEWS_SOURCES: list[tuple[str, str, str]] = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "India"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml", "India"),
    ("Moneycontrol Markets", "https://www.moneycontrol.com/rss/marketreports.xml", "India"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss", "India"),
    ("LiveMint", "https://www.livemint.com/rss/markets", "India"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "Global"),
    ("Dow Jones Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "Global"),
    ("MarketWatch", "https://www.marketwatch.com/rss/topstories", "Global"),
    ("Investing.com", "https://www.investing.com/rss/news.rss", "Global"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", "Global"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "Global"),
]


def _fetch_one_feed(name: str, url: str, region: str) -> list[dict]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception:
        return []

    rows = []
    for entry in parsed.entries:
        published = None
        for key in ("published_parsed", "updated_parsed"):
            t = getattr(entry, key, None)
            if t is not None:
                published = pd.Timestamp(datetime(*t[:6]))
                break
        rows.append({
            "source": name, "region": region,
            "title": getattr(entry, "title", "(no title)"),
            "link": getattr(entry, "link", ""),
            "published": published,
            "summary": getattr(entry, "summary", ""),
        })
    return rows


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news() -> pd.DataFrame:
    """Every source's feed, merged and sorted newest-first. Cached 10
    minutes - these feeds update continuously, but re-fetching eleven
    sources on every single page interaction would be wasteful, not more
    accurate."""
    all_rows: list[dict] = []
    for name, url, region in NEWS_SOURCES:
        all_rows.extend(_fetch_one_feed(name, url, region))

    if not all_rows:
        return pd.DataFrame(columns=["source", "region", "title", "link", "published", "summary", "sentiment"])

    df = pd.DataFrame(all_rows)
    # Scored on the TITLE only, not title+summary - RSS summaries are often
    # the article's opening paragraph (factual scene-setting) rather than
    # more sentiment-bearing text, and mixing the two would dilute a sharp
    # headline's own signal rather than sharpen it.
    df["sentiment"] = df["title"].apply(score_text)
    df = df.sort_values("published", ascending=False, na_position="last").reset_index(drop=True)
    return df


def _nse_session() -> requests.Session:
    """A warmed-up session - visits the site itself first so any cookies
    NSE's bot-protection wants to set exist before the API call. Confirmed
    the bare (no-session) call also works from this machine right now, but
    that is a fact about this network today, not a guarantee - the warm-up
    is cheap insurance against needing it elsewhere."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        s.get("https://www.nseindia.com/", timeout=REQUEST_TIMEOUT)
    except Exception:
        pass
    return s


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_nse_board_meetings(days_ahead: int = 30) -> pd.DataFrame:
    """Forward-looking board meetings NSE-listed companies have
    scheduled - real dated catalysts (results, dividends, buybacks
    considered/approved at a specific future meeting), not news about
    something that already happened."""
    today = datetime.now()
    params = {
        "index": "equities",
        "from_date": today.strftime("%d-%m-%Y"),
        "to_date": (today + timedelta(days=days_ahead)).strftime("%d-%m-%Y"),
    }
    try:
        s = _nse_session()
        r = s.get("https://www.nseindia.com/api/corporate-board-meetings", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return pd.DataFrame(columns=["date", "symbol", "company", "purpose", "description"])

    if not data:
        return pd.DataFrame(columns=["date", "symbol", "company", "purpose", "description"])

    rows = [{
        "date": pd.to_datetime(d.get("bm_date"), format="%d-%b-%Y", errors="coerce"),
        "symbol": d.get("bm_symbol"),
        "company": d.get("sm_name"),
        "purpose": d.get("bm_purpose"),
        "description": d.get("bm_desc"),
    } for d in data]
    df = pd.DataFrame(rows).dropna(subset=["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_nse_corporate_actions(days_ahead: int = 30) -> pd.DataFrame:
    """Dividends, splits, bonuses, buybacks and their ex-dates - already-
    announced corporate actions with a scheduled future ex-date, the other
    half of "what's scheduled" alongside board meetings."""
    try:
        s = _nse_session()
        r = s.get("https://www.nseindia.com/api/corporates-corporateActions",
                  params={"index": "equities"}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return pd.DataFrame(columns=["date", "symbol", "company", "purpose"])

    if not data:
        return pd.DataFrame(columns=["date", "symbol", "company", "purpose"])

    rows = [{
        "date": pd.to_datetime(d.get("exDate"), format="%d-%b-%Y", errors="coerce"),
        "symbol": d.get("symbol"),
        "company": d.get("comp"),
        "purpose": d.get("subject"),
    } for d in data]
    df = pd.DataFrame(rows).dropna(subset=["date"])

    today = pd.Timestamp(datetime.now().date())
    cutoff = today + pd.Timedelta(days=days_ahead)
    df = df[(df["date"] >= today) & (df["date"] <= cutoff)]
    return df.sort_values("date").reset_index(drop=True)
