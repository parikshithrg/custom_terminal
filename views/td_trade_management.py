"""Trade Management - Position Sizing & Risk (still a stub) and Tradebook
(real data, 2026-08-18's first wired page).

Tradebook reads market_gate's own trade data STRICTLY READ-ONLY - same
discipline the `Data test` project already established for reusing
market_gate's data (see that project's own config.toml: "read STRICTLY
read-only... content-hashed every run"). Nothing here calls any of
market_gate.tradebook's save_* functions. This is real financial data
(currently ~835 closed trades from imported Console P&L workbooks, plus
any hand-logged trades) - not a demo file, per market_gate's own
tradebook.py docstring history.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from views._registry import PAGES_BY_FILE
from views._topbar import render_section_tabs

# Local Terminal and Dashboard/market_gate are separate project folders -
# this reaches across to Dashboard's own package the same way market_gate's
# OWN view files reach up to their shared ROOT (sys.path.insert), just
# crossing a project boundary instead of a views/ subfolder.
DASHBOARD_ROOT = Path(r"C:\Users\parik\OneDrive\Desktop\Dashboard")
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

meta = PAGES_BY_FILE["views/td_trade_management.py"]

render_section_tabs(active_section=meta.section)
st.markdown(f"## {meta.icon} {meta.title}")
st.caption(f"Source: {meta.section}")

tab_sizing, tab_journal = st.tabs([label for label, _ in meta.subsections])

with tab_sizing:
    st.info(meta.subsections[0][1])
    st.markdown(
        "**Not yet wired to real data.** This tab is a placeholder - the "
        "backend for it hasn't been decided yet."
    )

with tab_journal:
    try:
        from market_gate import tradebook as tb
    except Exception as e:
        st.error(f"Couldn't reach market_gate's tradebook module: {e}")
    else:
        pl_trades = tb.load_manual_trades(path=tb.PL_TRADES_PATH)
        manual = tb.load_manual_trades()
        all_closed = pd.concat([pl_trades, manual], ignore_index=True)

        if all_closed.empty:
            st.info("No trades found in Market Gate's tradebook data.")
        else:
            # Same stable sort market_gate's own Tradebook page uses - many
            # P&L-derived trades within one FY share an identical placeholder
            # timestamp, and an unstable sort's tie-break among those is
            # undefined, which would silently reorder them between runs.
            all_closed = all_closed.sort_values("exit_time", kind="stable").reset_index(drop=True)
            # Per-row "commission" is 0 for every P&L-workbook-derived trade -
            # those charges were never allocated per-trade, only itemized in
            # aggregate by segment+FY (tb.load_pl_charges). Using the
            # per-row column for the headline Net P/L would silently show
            # gross P/L as if it were net - matching market_gate's own
            # Tradebook page, which computes net the same aggregate way.
            pl_charges = tb.load_pl_charges()
            total_charges = tb.total_pl_charges(pl_charges)
            gross_pnl = all_closed["pnl"].sum()
            net_pnl = gross_pnl - total_charges
            row_net_pnl = all_closed["pnl"] - all_closed["commission"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Closed trades", f"{len(all_closed):,}")
            c2.metric("Realized P/L", f"₹{gross_pnl:,.0f}")
            c3.metric("Charges", f"₹{total_charges:,.0f}")
            c4.metric("Net P/L", f"₹{net_pnl:,.0f}")
            st.caption(
                f"Win rate {100 * (row_net_pnl > 0).mean():.1f}% (by trade, "
                "before the aggregate charges above) · source: Market "
                "Gate's tradebook (imported P&L workbooks + hand-logged "
                "trades), read-only. Per-trade charges below are 0 for "
                "P&L-workbook trades - charges are itemized in aggregate "
                "only, not per trade; the Charges/Net P/L KPIs above "
                "account for them, the table's own Charges/Net P/L columns "
                "don't."
            )

            is_long = all_closed["direction"] == "LONG"
            buy_price = all_closed["entry_price"].where(is_long, all_closed["exit_price"])
            sell_price = all_closed["exit_price"].where(is_long, all_closed["entry_price"])
            trade_log = pd.DataFrame({
                "Trade no.": all_closed.index + 1,
                "Instrument": all_closed["instrument"],
                "Scrip": all_closed["symbol"],
                "Long/Short": all_closed["direction"],
                "Entry Date": pd.to_datetime(all_closed["entry_time"]).dt.strftime("%Y-%m-%d"),
                "Exit Date": pd.to_datetime(all_closed["exit_time"]).dt.strftime("%Y-%m-%d"),
                "Quantity": all_closed["quantity"],
                "Buy Price": buy_price.round(2),
                "Buy Value": (buy_price * all_closed["quantity"]).round(2),
                "Sell Price": sell_price.round(2),
                "Sell Value": (sell_price * all_closed["quantity"]).round(2),
                "P/L": all_closed["pnl"].round(2),
                "Charges": all_closed["commission"].round(2),
                "Net P/L": row_net_pnl.round(2),
            })
            st.dataframe(trade_log, width="stretch", height=420, hide_index=True)
