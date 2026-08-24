"""Build the small historical Slice A compatibility fixture once.

The committed fixture is self-contained. This script documents its provenance;
normal tests never read the external Dashboard directory.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "Data test"))

from dtest.config import load_config
from dtest.engine.simulate import ExitRule, simulate_trades, trades_to_frame
from dtest.signals.momentum import momentum_signal
from dtest.universe import build_universe
from market_intel.foundation.artifacts import frame_hash, sha256_file
from market_intel.research.momentum import MomentumFeatureDefinition, calculate_momentum, rank_at_decisions
from market_intel.research.outcomes import OutcomeDefinition, materialize_outcomes
from market_intel.research.universe import UniverseDefinition, materialize_liquidity_universe
from market_intel.simulation.costs import DeliveryCostDefinition


SYMBOLS = ["ASIANPAINT", "HDFCBANK", "HINDUNILVR", "ICICIBANK", "INFY", "ITC", "RELIANCE", "TCS"]
START, END = pd.Timestamp("2013-01-01"), pd.Timestamp("2016-12-31")


def main() -> int:
    source = Path("C:/Users/parik/OneDrive/Desktop/Dashboard/data")
    out = ROOT / "tests" / "fixtures" / "momentum_golden_v1"
    out.mkdir(parents=True, exist_ok=True)
    long_rows, hashes = [], []
    panels = {field: {} for field in ("open", "high", "low", "close", "volume", "turnover")}
    for symbol in SYMBOLS:
        path = source / f"{symbol}_DAILY.csv"
        frame = pd.read_csv(path, parse_dates=["date"])
        frame = frame[(frame["date"] >= START) & (frame["date"] <= END)].sort_values("date")
        frame["turnover"] = frame["close"] * frame["volume"]
        hashes.append(f"{path.name}:{sha256_file(path)}")
        for field in panels:
            panels[field][symbol] = frame.set_index("date")[field]
        for record in frame.to_dict("records"):
            long_rows.append({"instrument_id": symbol, **record})
    panels = {name: pd.DataFrame(values).sort_index() for name, values in panels.items()}
    prices = pd.DataFrame(long_rows)
    benchmark_path = source / "NIFTY50_DAILY.csv"
    benchmark = pd.read_csv(benchmark_path, parse_dates=["date"])
    benchmark = benchmark[(benchmark["date"] >= START) & (benchmark["date"] <= END)].sort_values("date")
    hashes.append(f"{benchmark_path.name}:{sha256_file(benchmark_path)}")

    cfg = load_config()
    legacy_universe = build_universe(panels["close"], panels["turnover"], cfg)
    decisions = [d for d in legacy_universe.rebalance_dates if d >= pd.Timestamp("2014-02-01")]
    legacy_feature = panels["close"].shift(21) / panels["close"].shift(273) - 1.0
    legacy_signals = momentum_signal(panels["close"], legacy_universe.membership, decisions)
    legacy_trades = trades_to_frame(simulate_trades(
        legacy_signals, "long", ExitRule(max_hold_days=21, atr_stop_multiple=None, risk_reward=None),
        open_=panels["open"], high=panels["high"], low=panels["low"], close=panels["close"],
        volume=panels["volume"], atr_panel=None, target_value_per_trade=10_000, cfg=cfg,
    ))

    new_universe = materialize_liquidity_universe(
        panels["close"], panels["turnover"], UniverseDefinition(), "golden_prices_v1"
    )
    new_feature = calculate_momentum(panels["close"], MomentumFeatureDefinition(), END)
    ranked = rank_at_decisions(new_feature, new_universe.membership, decisions, 0.2)
    new_outcomes = materialize_outcomes(
        ranked, panels["open"], panels["high"], panels["low"], benchmark.set_index("date")["open"],
        OutcomeDefinition(), DeliveryCostDefinition(), 10_000,
    )

    prices.to_parquet(out / "prices.parquet", index=False)
    benchmark.to_parquet(out / "benchmark.parquet", index=False)
    legacy_universe.decisions if hasattr(legacy_universe, "decisions") else None
    pd.DataFrame({"date": legacy_universe.membership.index,
                  "members": legacy_universe.membership.apply(lambda r: "|".join(r.index[r]), axis=1)}).to_parquet(out / "legacy_universe.parquet", index=False)
    legacy_feature.stack(future_stack=True).rename("feature_value").reset_index().to_parquet(out / "legacy_feature.parquet", index=False)
    legacy_signals.stack(future_stack=True).rename("selected").reset_index().query("selected").to_parquet(out / "legacy_signals.parquet", index=False)
    legacy_trades.to_parquet(out / "legacy_trades.parquet", index=False)
    ranked.to_parquet(out / "new_ranks.parquet", index=False)
    new_outcomes.to_parquet(out / "new_outcomes.parquet", index=False)

    resolved = legacy_trades[legacy_trades["net_pnl_pct"].notna()]
    expected = {
        "fixture_version": "momentum_golden_v1",
        "source_file_hashes": hashes,
        "date_start": str(START.date()), "date_end": str(END.date()), "symbols": SYMBOLS,
        "legacy": {"signals": int(legacy_signals.to_numpy().sum()), "trades": len(legacy_trades),
                   "resolved": len(resolved), "mean_net_pct": float(resolved["net_pnl_pct"].mean())},
        "hashes": {"legacy_feature": frame_hash(legacy_feature), "legacy_signals": frame_hash(legacy_signals)},
    }
    (out / "expected.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
