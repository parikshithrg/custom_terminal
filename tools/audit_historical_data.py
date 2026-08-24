"""Audit the configured local equity population without external acquisition."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(price_dir: Path, events_path: Path, industry_map_path: Path, output_dir: Path, cutoff: pd.Timestamp) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_path = price_dir / "NIFTY50_DAILY.csv"
    benchmark = pd.read_csv(benchmark_path, parse_dates=["date"])
    benchmark = benchmark[benchmark.date <= cutoff].drop_duplicates("date").sort_values("date")
    calendar = pd.DatetimeIndex(benchmark.date)
    dataset_end = calendar.max()
    rows, discontinuities, annual_presence = [], [], {}
    current_equities = set(pd.read_csv(industry_map_path)["symbol"].astype(str).str.upper())
    paths = sorted(price_dir.glob("*_DAILY.csv"))
    for path in paths:
        symbol = path.stem.removesuffix("_DAILY").upper()
        asset_class = ("EQUITY_CURRENT_MAP" if symbol in current_equities else
                       "BENCHMARK_OR_INDEX" if symbol.startswith(("NIFTY", "INDIA")) else "OTHER_NON_EQUITY_OR_UNRESOLVED")
        raw = pd.read_csv(path)
        date = pd.to_datetime(raw["date"], errors="coerce")
        frame = raw.assign(date=date)
        frame = frame[frame.date.notna() & (frame.date <= cutoff)].sort_values("date", kind="stable")
        duplicates = int(frame.date.duplicated().sum())
        unique = frame.drop_duplicates("date", keep="last").set_index("date")
        if unique.empty:
            continue
        expected = calendar[(calendar >= unique.index.min()) & (calendar <= unique.index.max())]
        missing = expected.difference(unique.index)
        positions = calendar.get_indexer(unique.index.intersection(calendar))
        position_gaps = np.diff(positions)
        large_gaps = position_gaps[position_gaps > 5]
        prices = unique[[c for c in ("open", "high", "low", "close") if c in unique]].apply(pd.to_numeric, errors="coerce")
        volume = pd.to_numeric(unique.get("volume"), errors="coerce")
        returns = pd.to_numeric(unique["close"], errors="coerce").pct_change(fill_method=None)
        jumps = returns[returns.abs() >= 0.40]
        for dt, value in jumps.items():
            discontinuities.append({"symbol": symbol, "date": dt, "close_to_close_return": value,
                                    "classification": "SUSPECTED_CORPORATE_ACTION_OR_DATA_BREAK"})
        active = (dataset_end - unique.index.max()).days <= 10
        rows.append({
            "symbol": symbol, "file": path.name, "asset_class": asset_class, "sha256": _hash(path),
            "earliest_date": unique.index.min(), "latest_date": unique.index.max(),
            "observations": len(unique), "missing_trading_sessions": len(missing),
            "missing_session_pct": 100 * len(missing) / max(1, len(expected)),
            "large_internal_gaps_gt_5_sessions": int(len(large_gaps)),
            "largest_internal_gap_sessions": int(large_gaps.max() - 1) if len(large_gaps) else 0,
            "duplicate_dates": duplicates,
            "zero_or_negative_price_rows": int((prices <= 0).any(axis=1).sum()),
            "zero_volume_rows": int((volume == 0).sum()), "missing_volume_rows": int(volume.isna().sum()),
            "turnover_available": "turnover" in unique.columns,
            "suspected_listing_date": unique.index.min(),
            "suspected_end_date": pd.NaT if active else unique.index.max(),
            "activity_status": "CURRENTLY_ACTIVE" if active else "TERMINATED_OR_SOURCE_ENDED_UNRESOLVED",
            "corporate_action_discontinuities": len(jumps),
        })
        if asset_class == "EQUITY_CURRENT_MAP":
            for year in range(unique.index.min().year, unique.index.max().year + 1):
                annual_presence.setdefault(year, set()).add(symbol)

    inventory = pd.DataFrame(rows).sort_values("symbol")
    events = pd.read_csv(events_path)
    event_symbols = set(events["symbol"].dropna().astype(str).str.upper())
    equity_inventory = inventory[inventory.asset_class == "EQUITY_CURRENT_MAP"].copy()
    local_symbols = set(equity_inventory.symbol)
    missing_reference = events[events["symbol"].astype(str).str.upper().isin(event_symbols - local_symbols)].copy()
    missing_reference["reference_reason"] = "HISTORICAL_INDEX_EVENT_SYMBOL_ABSENT_FROM_LOCAL_PRICE_DIRECTORY"
    missing_reference = missing_reference.sort_values(["effective_date", "symbol"], kind="stable")

    years = sorted(annual_presence)
    annual_rows = []
    for i, year in enumerate(years):
        present = annual_presence[year]
        prior = annual_presence.get(year - 1, set())
        following = annual_presence.get(year + 1, set())
        lengths = equity_inventory[equity_inventory.symbol.isin(present)].observations
        continuing = sum(equity_inventory.set_index("symbol").loc[list(present), "latest_date"] >= dataset_end - pd.Timedelta(days=10))
        annual_rows.append({"year": year, "securities_with_data": len(present),
                            "entering_dataset": len(present - prior),
                            "disappearing_after_year": len(present - following) if i < len(years) - 1 else 0,
                            "median_full_series_observations": float(lengths.median()),
                            "pct_continuing_to_dataset_end": 100 * continuing / max(1, len(present))})
    coverage = pd.DataFrame(annual_rows)

    securities = equity_inventory.assign(
        issuer_id=pd.NA,
        instrument_id=inventory.symbol.map(lambda s: "ins_" + hashlib.sha256(f"NSE|{s}|unknown".encode()).hexdigest()[:16]),
        exchange="NSE", listing_id=pd.NA, isin=pd.NA,
        listing_date=inventory.suspected_listing_date, end_date=inventory.suspected_end_date,
        status=inventory.activity_status, identity_status="UNRESOLVED",
        predecessor_instrument_id=pd.NA, successor_instrument_id=pd.NA,
    )[["issuer_id", "instrument_id", "exchange", "listing_id", "isin", "symbol", "listing_date", "end_date", "status",
       "identity_status", "predecessor_instrument_id", "successor_instrument_id"]]
    aliases = securities[["instrument_id", "exchange", "symbol"]].assign(
        valid_from=pd.NaT, valid_to=pd.NaT, source_id="local_filename_only", identity_status="UNRESOLVED")

    for name, frame in {"symbol_inventory": inventory, "coverage_by_year": coverage,
                        "corporate_action_discontinuities": pd.DataFrame(discontinuities),
                        "historical_reference_symbols_absent": missing_reference,
                        "security_master_provisional": securities,
                        "symbol_aliases_provisional": aliases}.items():
        frame.to_parquet(output_dir / f"{name}.parquet", index=False)
        frame.to_csv(output_dir / f"{name}.csv", index=False)

    summary = {
        "dataset_cutoff": str(cutoff.date()), "dataset_end": str(dataset_end.date()),
        "daily_files": len(inventory), "current_map_equity_files": len(equity_inventory),
        "benchmark_or_index_files": int((inventory.asset_class == "BENCHMARK_OR_INDEX").sum()),
        "other_or_unresolved_files": int((inventory.asset_class == "OTHER_NON_EQUITY_OR_UNRESOLVED").sum()),
        "reference_event_symbols": len(event_symbols),
        "reference_symbols_absent": len(event_symbols - local_symbols),
        "terminated_or_unresolved_equities": int((equity_inventory.activity_status != "CURRENTLY_ACTIVE").sum()),
        "late_start_after_2010_equities": int((equity_inventory.earliest_date >= "2010-01-01").sum()),
        "equities_with_turnover": int(equity_inventory.turnover_available.sum()),
        "equities_with_large_gaps": int((equity_inventory.large_internal_gaps_gt_5_sessions > 0).sum()),
        "equities_with_duplicates": int((equity_inventory.duplicate_dates > 0).sum()),
        "equities_with_nonpositive_prices": int((equity_inventory.zero_or_negative_price_rows > 0).sum()),
        "suspected_discontinuities_all_files": len(discontinuities),
        "benchmark": {"symbol": "NIFTY50", "first": str(calendar.min().date()), "last": str(dataset_end.date()),
                      "columns": list(benchmark.columns), "sha256": _hash(benchmark_path)},
    }
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        commit, status = "NO_GIT_METADATA", "NO_GIT_METADATA"
    outputs = sorted(p for p in output_dir.iterdir() if p.is_file() and p.name != "audit_manifest.json")
    manifest = {
        "audit_version": "local_430_historical_data_audit_v1", "code_commit": commit,
        "dirty_worktree_fingerprint": hashlib.sha256(status.encode()).hexdigest(),
        "source_tree_fingerprint": _hash(Path(__file__)), "python": platform.python_version(),
        "input_snapshot_hashes": {"benchmark": _hash(benchmark_path), "events": _hash(events_path),
                                  "industry_map": _hash(industry_map_path)},
        "output_artifact_hashes": {p.name: _hash(p) for p in outputs},
    }
    (output_dir / "audit_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-dir", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--industry-map", required=True, type=Path)
    parser.add_argument("--output", default=Path("artifacts/data_audit/local_430_v1"), type=Path)
    parser.add_argument("--cutoff", default="2026-08-13")
    args = parser.parse_args()
    audit(args.price_dir, args.events, args.industry_map, args.output, pd.Timestamp(args.cutoff))


if __name__ == "__main__":
    main()
