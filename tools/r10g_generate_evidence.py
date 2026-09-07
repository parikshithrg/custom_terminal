"""Generate R.10G synthetic evidence from an exact clean implementation commit."""

from pathlib import Path

from market_intel.application.synthetic_portfolio import run_portfolio_evidence


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run_portfolio_evidence(output_dir=root / "docs/investigations/r10g/run_v1",
                           project_root=root, entrypoint=Path(__file__).resolve())
