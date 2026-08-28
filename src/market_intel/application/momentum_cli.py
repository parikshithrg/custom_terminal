"""CLI for the non-actionable Slice A momentum experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from market_intel.application.runner import load_spec, run_momentum
from market_intel.foundation.prices import load_symbol_csvs


def main() -> int:
    print(
        "DEPRECATED: the Slice A momentum CLI is not an R.4 governed entry point. "
        "No research was executed. Use the governed preflight and obtain a run-specific approval.",
        file=sys.stderr,
    )
    return 2
    # The parser is retained below as historical command documentation; this
    # entry point intentionally fails closed before loading any data.
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default="specs/momentum_12_1_v1.json")
    parser.add_argument("--price-dir", required=True)
    parser.add_argument("--benchmark-file", required=True)
    parser.add_argument("--industry-map")
    parser.add_argument("--output-root", default="artifacts/runs")
    parser.add_argument("--survivorship-safe", action="store_true")
    args = parser.parse_args()
    project_root = Path.cwd()
    spec = load_spec(args.spec)
    include_symbols = None
    if args.industry_map:
        industry = pd.read_csv(args.industry_map)
        include_symbols = set(industry["symbol"].astype(str).str.strip().str.upper())
    retrieved_at = pd.Timestamp("2026-08-24T00:00:00Z")
    panels = load_symbol_csvs(
        args.price_dir, as_of=pd.Timestamp(spec["research_end"]),
        retrieved_at=retrieved_at, survivorship_safe=args.survivorship_safe,
        include_symbols=include_symbols,
    )
    benchmark = pd.read_csv(args.benchmark_file, parse_dates=["date"]).set_index("date").sort_index()
    run_dir = run_momentum(
        panels=panels, benchmark_open=benchmark["open"].reindex(panels.open.index).ffill(),
        spec=spec, output_root=args.output_root, project_root=project_root,
    )
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
