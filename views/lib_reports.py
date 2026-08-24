"""Reports - native, in-app rendering of the reports produced so far, not a
PDF embed. Currently one: the Data test Hypothesis Testing Report
(2026-08-19), read directly from `Data test/runs/` - that folder is a real
subtree-merged subfolder of THIS repo (see project memory's 2026-08-19
entries), so no cross-project sys.path hack is needed, just a relative path.

Same underlying facts/figures as `Data test/scripts/build_hypothesis_report_
pdf.py`'s PDF (kept in sync by hand, not auto-generated from it) - narrative
text is the same, tables render as real HTML/`st.dataframe`s instead of
paginated print pages. The diagnosis matrix (23 hypotheses x 17 metrics)
needed 4 landscape pages in the PDF; here it's one scrollable table,
transposed to one row per hypothesis with wrapped row labels and column
headers (a real HTML table, not `st.dataframe`, which truncates long
headers/labels instead of wrapping them).

Structured as a small `REPORTS` list + one render function each, so a
second report can be added later without redesigning the page.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from views._registry import PAGES_BY_FILE
from views._topbar import render_section_tabs

meta = PAGES_BY_FILE["views/lib_reports.py"]

DATA_TEST_RUNS = Path(__file__).resolve().parent.parent / "Data test" / "runs"

SIGNAL_CATALOG = [
    ("mean_reversion", "A stock pushed 1.5+ std devs below its own 50-day average in a short "
     "window is disproportionately a forced/panicked seller (margin calls, index rebalancing, "
     "tax-loss selling) rather than new information about impaired value - expected to partially "
     "correct once the selling pressure exhausts. The only predecessor-project strategy that "
     "survived a genuine walk-forward test; re-tested here under honest execution."),
    ("delivery_breakout", "A price breakout on ordinary/low delivery is disproportionately intraday "
     "speculation that unwinds overnight. A breakout with delivery meaningfully above its own "
     "recent normal is disproportionately real buyers converting the move into settled positions."),
    ("oi_momentum", "A breakout on falling/average open interest is disproportionately short-covering "
     "with no fresh leveraged conviction. A breakout with open interest rising meaningfully faster "
     "than normal means participants are opening new leveraged positions into the move."),
    ("participant_tilt", "A mean-reversion dip bought while FII net index-futures positioning sits "
     "above its own recent trend is a normal pullback inside continued institutional accumulation; "
     "the identical dip bought while FII positioning trends down is the early stage of a real "
     "breakdown. Market-wide gate only (no per-stock FII breakdown exists) - it decides WHETHER a "
     "dip is bought that day, not WHICH stock."),
    ("vol_squeeze_breakout", "A breakout following a genuine contraction (short-term range compressed "
     "well below its own longer-run normal) is the first real re-pricing after a quiet period, not "
     "noise inside an already-active range. A delay=2 variant was also tested, entering two "
     "sessions after the signal fires, to isolate whether buying at the peak of the dislocation "
     "explained the rejection."),
    ("price_action (LONG)", "A session that is BOTH unusually wide-range AND closes pinned at one "
     "extreme, on volume well above normal, is disproportionately genuine new information or real "
     "institutional participation - unlike vol_squeeze_breakout, needs no prior contraction."),
    ("pairs_reversion (correlation-screened)", "Two same-sector, historically correlated stocks whose "
     "log-price spread drifts unusually wide are disproportionately showing a temporary, idiosyncratic "
     "dislocation rather than a genuine re-rating - market-neutral by construction."),
    ("same_sector_pairing", "A looser version of the pairs premise: shared sector membership alone is "
     "claimed to be enough linkage for a wide relative-price dislocation to be temporary. Tested with "
     "both a random-draw and a liquidity-ranked pair-selection rule."),
    ("momentum (12-1 month)", "A stock that outperformed over the trailing ~12 months (skipping the "
     "most recent month, to exclude a known short-term reversal window) is more likely still "
     "mid-diffusion of genuine improving information than already fully priced."),
    ("cross-asset stress-regime gate", "Gates the 6 core reactive signals above by a 6-dimension "
     "systemic-stress composite (India VIX, US VIX, breadth-inverted, USDINR 20d change, DXY, gold "
     "20d return) - the same construction this app's own Black Swan Radar uses, tested here as a "
     "real entry filter rather than a live dashboard read."),
]

METRIC_ROWS = [
    ("Number of trades", "n_trades", True, 0),
    ("Win rate", "win_rate_pct", True, 1),
    ("Avg winner", "avg_winner_pct", True, 2),
    ("Avg loser", "avg_loser_pct", True, 2),
    ("Profit factor", "profit_factor", False, 2),
    ("Gross expectancy", "gross_expectancy_pct", True, 3),
    ("Net expectancy", "net_expectancy_pct", True, 3),
    ("Avg holding period (days)", "avg_holding_days", False, 1),
    ("Max drawdown", "max_drawdown_pct", True, 1),
    ("CAGR", "cagr_pct", True, 2),
    ("Sharpe", "sharpe", False, 3),
    ("Costs as % of |gross P&L|", "costs_pct_of_abs_gross", True, 1),
    ("Long-only result", "long_only_result_pct", True, 3),
    ("Short-only result", "short_only_result_pct", True, 3),
    ("Bull-market result", "bull_result_pct", True, 3),
    ("Bear-market result", "bear_result_pct", True, 3),
    ("Sideways-market result", "sideways_result_pct", True, 3),
]


def _fmt(v, pct: bool, dp: int) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    s = f"{v:,.{dp}f}"
    return f"{s}%" if pct else s


def _short_title(t: str) -> str:
    return (t.replace(" (honest execution)", "").replace(" (honest fills + costs)", "")
             .replace(", long-only", "").replace(" (random draw)", " – random")
             .replace(" (liquidity-ranked)", " – liquidity"))


@st.cache_data(ttl=3600)
def _load_hypothesis_report_data():
    log = pd.read_csv(DATA_TEST_RUNS / "hypothesis_log.csv")
    mc = pd.read_csv(DATA_TEST_RUNS / "monte_carlo_hypotheses" / "summary.csv")
    matrix = pd.read_csv(DATA_TEST_RUNS / "hypothesis_report" / "diagnosis_matrix.csv")
    return log, mc, matrix


def render_hypothesis_testing_report() -> None:
    try:
        log, mc, matrix = _load_hypothesis_report_data()
    except FileNotFoundError as exc:
        st.error(f"Report data not found - {exc}")
        return

    n_total = len(log)
    n_rejected = int((log["decision"] == "rejected").sum())
    n_accepted = int((log["decision"] == "accepted").sum())

    st.markdown(f"""
##### Data test – Hypothesis Testing Report
*A deterministic, point-in-time rebuild of India-equity systematic signal testing – NSE
bhavcopy 2004–2026, real T+1 execution and costs, 30-seed placebo floor, train/val
discipline, and a 10,000-path Monte Carlo bootstrap.*
""")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hypotheses tested", n_total)
    c2.metric("Rejected", n_rejected)
    c3.metric("Accepted-on-train", n_accepted)
    c4.metric("Survived confirmation", 0)

    st.markdown("---")
    st.markdown("#### Executive summary")
    st.markdown(
        f"Between 2026-08-14 and 2026-08-19, this project tested {n_total} logged hypotheses "
        "built on 10 distinct economic ideas, each tested on one or both of two data splits "
        "(`primary`: 2004–2016 train / 2017–2021 val / 2022–2026 test, untouched; "
        "`delivery`: 2019–2023 train / 2023–2025 val / 2025–2026 test, untouched - "
        "shorter history, higher evidence bar) and, where a result looked promising on train, "
        "re-tested on a held-out val window."
    )
    st.markdown(
        f"**{n_rejected} of {n_total} were rejected outright** – the real mean return was "
        "either negative, or positive but ranked below the placebo band (blind selection from the "
        f"same eligible pool on the same dates). **{n_accepted} were mechanically “accepted”** "
        "by this project's own logging rule (beats every placebo seed, and positive portfolio "
        "Sharpe where a portfolio simulation exists) – **none have survived independent "
        "scrutiny**: both same_sector_pairing variants failed their own val confirmation and then "
        "flipped sign entirely on the delivery split; momentum's delivery/train acceptance is "
        "undercut by its own delivery/val result, which rests on only 9 weekly buckets, a t-stat "
        "of 0.98, and a mean (+6.55%) driven by a handful of outliers against a negative median "
        "(-3.21%); participant_tilt's calm-tercile stress-gated variant (t=2.20, the strongest "
        "reading of 36 stress-gate variants tested) still didn't beat its own best placebo seed."
    )
    st.markdown(
        "Plain NIFTY50 buy-and-hold (CAGR ~12.8%, Sharpe ~0.62–0.66) beat every mechanical "
        "rule tested on every window. A pure time-based holding-period test (no ATR stop, no "
        "target, 1–12 month exits) confirmed this holds even with the exit rule removed "
        "entirely - 7 of 8 signals still underperformed NIFTY50, by a widening margin the longer "
        "they were held, on both full history and two genuine out-of-sample val windows."
    )
    st.info(
        "The defensible conclusion, unchanged since this project's own working notes: "
        "short-horizon technical reaction to a visible price/delivery/OI/flow/volatility/stress "
        "dislocation does not survive real execution and costs on this universe, at retail cost "
        "structure – not that nothing works, full stop. Longer-horizon momentum constructions, "
        "fundamentals/valuation, and calendar/seasonality effects remain under-explored."
    )

    with st.expander("Methodology", expanded=False):
        st.markdown("""
Five rules, each enforced by code and tests, not convention alone:

| Rule | What it means |
|---|---|
| **Deterministic** | Seeds, content hashes, run manifests. An AST scan fails the build if any module reads the wall clock outside two allow-listed metadata timestamps. |
| **Point-in-time** | No datum reaches a decision before it existed. The universe is a recomputable rule (monthly-rebalanced, banded top-200-by-turnover), never today's index membership. |
| **Executable** | Every fill is at the next session's open (T+1), never same-bar. |
| **Benchmark-relative** | Every headline number is compared against NIFTY50 buy-and-hold, after real costs, on the same capital and dates. |
| **Counted** | Every hypothesis tried is logged, append-only, whether it wins or loses. |

**Trade simulation**: sizing-independent (fixed capital per trade) trade-level results, separate
from portfolio-level results (Rs 50,000 capital, 5 concurrent slots, real drawdown). Confirmation-
style signals use a 7-day max hold / 2.0x-ATR stop / 1:2.5 risk-reward exit; momentum uses a pure
~1-month calendar hold. Every result is checked against 30 placebo seeds (same signal dates/counts,
names drawn blindly from that date's eligible pool), and significance is read off a non-overlapping
entry-week bucket t-stat.

**Monte Carlo (2026-08-19)**: a circular block-bootstrap over the same weekly buckets the t-stat is
built on, 10,000 resamples per hypothesis, reporting the probability the resampled mean stays
positive - a bootstrap uncertainty read layered on top of the t-stat/placebo pipeline, not a
replacement for it.
""")

    with st.expander("Data foundation", expanded=False):
        st.markdown("""
| Source | What | Coverage |
|---|---|---|
| NSE bhavcopy archive | Rebuilt fresh per-year parquet store | 5,588 trading days, 2004-01-01–2026-08-13 |
| fno.db | Per-stock futures/OI, read-only, content-hashed every run | 48+ GB; OI/futures data from 2008 |
| Corporate actions | Detected and adjusted directly from the price series | Full history |
| Delivery / participant-flow data | Per-stock delivery %, FII net index-futures positioning | From 2019-06-27 |
| NIFTY50 index level | Benchmark yardstick | Full history |
| Macro stress series | India VIX, US VIX, USDINR, DXY, gold - the cross-asset stress composite | India VIX from 2009-03; others earlier |
| Universe | Point-in-time, monthly-rebalanced, banded top-200-by-turnover | Recomputed every run |
""")

    with st.expander("Signals tested (10 distinct economic ideas)", expanded=False):
        for name, desc in SIGNAL_CATALOG:
            st.markdown(f"**{name}**")
            st.caption(desc)

    st.markdown("#### Full test log – all hypotheses")
    log_display = log.copy()
    log_display["title"] = log_display["title"].apply(_short_title)
    log_display["placebo_delta"] = log_display["real_value"] - log_display["placebo_mean"]
    log_display = log_display.rename(columns={
        "title": "Signal", "split": "Split", "window": "Window", "n_trades": "n",
        "n_buckets": "Buckets", "real_value": "Mean %", "t_stat": "t-stat",
        "placebo_delta": "Δ placebo", "decision": "Decision",
    })
    st.dataframe(
        log_display[["Signal", "Split", "Window", "n", "Buckets", "Mean %", "t-stat",
                      "Δ placebo", "Decision"]],
        width="stretch", height=420, hide_index=True,
        column_config={
            "Mean %": st.column_config.NumberColumn(format="%.3f%%"),
            "t-stat": st.column_config.NumberColumn(format="%.3f"),
            "Δ placebo": st.column_config.NumberColumn(format="%.3f%%"),
        },
    )
    st.caption("cdd796d6e171 (an earlier pairs_reversion primary/train run, superseded same-day "
               "after a rollforward-at-entry fix) is not shown - its raw trades were overwritten "
               "on disk by the re-run and are not separately recoverable.")

    st.markdown("#### Monte Carlo block-bootstrap results")
    st.caption("prob(mean>0) is the share of 10,000 resampled histories where the mean stays "
               "positive - the bootstrap uncertainty around the real mean, not an independent "
               "probability the strategy is “truly” profitable.")
    mc_display = mc.copy()
    mc_display["title"] = mc_display["title"].apply(_short_title)
    mc_display["window"] = mc_display["split"] + "/" + mc_display["window"]
    mc_display = mc_display.rename(columns={
        "title": "Signal", "window": "Split/Window",
        "prob_mean_positive_pct": "prob(mean>0)",
        "mean_ci_lo_pct": "CI low", "mean_ci_hi_pct": "CI high",
        "prob_compounded_positive_pct": "prob(compounded>0)",
    })
    st.dataframe(
        mc_display[["Signal", "Split/Window", "prob(mean>0)", "CI low", "CI high",
                     "prob(compounded>0)"]],
        width="stretch", height=420, hide_index=True,
        column_config={
            "prob(mean>0)": st.column_config.NumberColumn(format="%.1f%%"),
            "CI low": st.column_config.NumberColumn(format="%.2f%%"),
            "CI high": st.column_config.NumberColumn(format="%.2f%%"),
            "prob(compounded>0)": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.markdown("#### Hypothesis diagnosis matrix")
    st.caption(
        "Every metric computed directly from the real saved trade files - no estimation. "
        "CAGR/Sharpe/max-drawdown are blank for pairs trades (no portfolio-level simulation "
        "exists for them). Short-only result is blank for long-only single-leg signals by "
        "design. Costs shown against absolute gross P&L so it stays interpretable when gross "
        "is negative. Bull/bear/sideways use NIFTY50's own trailing 63-session return with a "
        "+/-5% deadband, a descriptive convention for this report, not a re-fitted parameter. "
        "One row per hypothesis, scroll down for more; the metric columns scroll right - one "
        "continuous table, not paginated like the PDF."
    )
    id_to_title = dict(zip(log["hypothesis_id"], log["title"].apply(_short_title)))
    matrix_disp = matrix.set_index("hypothesis_id")
    ordered_ids = [h for h in log["hypothesis_id"] if h in matrix_disp.index]
    matrix_disp = matrix_disp.loc[ordered_ids]
    row_labels = [f"{i+1}. {id_to_title.get(h, h)} ({row['split']}/{row['window']})"
                  for i, (h, row) in enumerate(matrix_disp.iterrows())]
    matrix_disp = matrix_disp.assign(_row_label=row_labels)

    sort_col, dir_col = st.columns([3, 1])
    all_metric_labels = [label for label, _, _, _ in METRIC_ROWS]
    with sort_col:
        sort_by = st.selectbox(
            "Sort rows by", ["Hypothesis (default order)"] + all_metric_labels,
            key="lt_matrix_sort_by",
        )
    with dir_col:
        direction = st.radio(
            "Direction", ["Ascending", "Descending"], horizontal=True,
            key="lt_matrix_sort_dir",
        )

    if sort_by == "Hypothesis (default order)":
        sorted_matrix = matrix_disp if direction == "Ascending" else matrix_disp.iloc[::-1]
    else:
        sort_key = next(key for label, key, _, _ in METRIC_ROWS if label == sort_by)
        sorted_matrix = matrix_disp.sort_values(
            sort_key, ascending=(direction == "Ascending"), na_position="last")

    # Transposed - one row per HYPOTHESIS, one column per METRIC - and a
    # real HTML table (not st.dataframe, which truncates long headers/labels
    # instead of wrapping them) so both the row labels and the metric
    # headers wrap onto multiple lines, same injected-HTML-table pattern
    # `news_feed_calendar.py` already uses for the same reason (fine control
    # `st.dataframe` doesn't give).
    header_cells = "".join(
        f'<th style="min-width:92px;">{html.escape(label)}</th>' for label, _, _, _ in METRIC_ROWS
    )
    body_rows = []
    for _, row in sorted_matrix.iterrows():
        cells = "".join(
            f'<td>{html.escape(_fmt(row.get(key), pct, dp))}</td>' for _, key, pct, dp in METRIC_ROWS
        )
        body_rows.append(
            f'<tr><td class="lt-matrix-rowlabel">{html.escape(row["_row_label"])}</td>{cells}</tr>'
        )
    matrix_html = f"""
    <style>
    .lt-matrix-wrap {{ overflow-x:auto; overflow-y:auto; max-height:700px; border:1px solid rgba(128,128,128,0.25); }}
    .lt-matrix-table {{ border-collapse:collapse; font-size:13px; width:100%; }}
    .lt-matrix-table th, .lt-matrix-table td {{
        white-space:normal; word-wrap:break-word; overflow-wrap:break-word;
        padding:6px 8px; text-align:right; vertical-align:top;
        border-bottom:1px solid rgba(128,128,128,0.18);
    }}
    .lt-matrix-table th {{
        position:sticky; top:0; background:var(--background-color, #fff);
        text-align:right; font-size:11px; text-transform:uppercase; letter-spacing:0.03em;
        opacity:0.75; font-weight:600; border-bottom:1px solid rgba(128,128,128,0.4);
    }}
    .lt-matrix-rowlabel, .lt-matrix-table th:first-child {{
        text-align:left; min-width:220px; max-width:280px; font-weight:600;
        position:sticky; left:0; background:var(--background-color, #fff);
    }}
    .lt-matrix-table tr:last-child td {{ border-bottom:none; }}
    </style>
    <div class="lt-matrix-wrap">
    <table class="lt-matrix-table">
        <thead><tr><th>Hypothesis</th>{header_cells}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
    </table>
    </div>
    """
    st.markdown(matrix_html, unsafe_allow_html=True)

    st.markdown("#### Synthesis")
    st.markdown("""
- **Every confirmation-style signal failed the same way** – mean_reversion, delivery_breakout,
  oi_momentum, participant_tilt, vol_squeeze_breakout, and price_action all react to an
  already-visible dislocation, and all show an inflated stop-hit rate vs. placebo (confirmed via a
  delay sweep: mean_net_pct improved monotonically with entry delay, but portfolio drawdown got
  WORSE, not better – entry timing alone doesn't create a tradeable edge).
- **"Smarter" filters did no better, sometimes worse** – correlation-screened pairs lost to
  random same-sector pairs; delivery/OI/flow overlays underperformed simpler variants.
- **Costs are usually the difference between "looks real" and "isn't"** – correlation-screened
  pairs' gross t-stat of 2.65 collapsed to 0.18 once honestly filled and costed.
- **Large-n, high-t-stat single-window results are not enough on their own** –
  same_sector_pairing's t=3.49–3.70 on 3,400+ trades still collapsed on val and flipped sign
  on the delivery split.
- **Removing the exit rule entirely doesn't rescue anything** – a pure 1–12 month
  time-based hold (no ATR stop, no target) still underperformed NIFTY50 for 7 of 8 signals,
  confirmed on full history AND two genuine out-of-sample val windows.
- **A dedicated cross-asset stress-regime gate found a real, mechanistically coherent pattern**
  (stressed-gating hurt every signal, calm-gating roughly neutralized most) but zero of 36
  screened variants – including the one promoted to a real test – beat their own placebo band.
- **Plain NIFTY50 buy-and-hold beat every mechanical rule tested**, on every window.
""")

    with st.expander("Known limitations", expanded=False):
        st.markdown("""
- No portfolio-level simulation exists for pairs trades – CAGR/Sharpe/max-drawdown cells are
  blank by design, not missing data.
- price_action's SHORT side was only ever screened (no cost model, approximate fills) –
  excluded from the diagnosis matrix entirely.
- The bull/bear/sideways split is a description built after the fact for this report – never
  used to gate or select a real hypothesis.
- "Accepted" always means "cleared this project's own mechanical logging bar", never
  "confirmed" – every acceptance has either failed its own val test or remains too thin to
  trade on.
""")

    st.caption("Generated 2026-08-19 · source data: `Data test/runs/` in this same repo "
               "· full PDF version: `Data test/runs/hypothesis_report/"
               "Data_Test_Hypothesis_Report.pdf`")


REPORTS = [
    ("Data test – Hypothesis Testing Report", "2026-08-19", render_hypothesis_testing_report),
]

render_section_tabs(active_section=meta.section)
st.markdown(f"## {meta.icon} {meta.title}")
st.caption(f"Source: {meta.section} · {len(REPORTS)} report"
           f"{'s' if len(REPORTS) != 1 else ''} on file")

if len(REPORTS) == 1:
    render_hypothesis_testing_report()
else:
    labels = [f"{title} ({date})" for title, date, _ in REPORTS]
    choice = st.selectbox("Report", labels)
    idx = labels.index(choice)
    REPORTS[idx][2]()
