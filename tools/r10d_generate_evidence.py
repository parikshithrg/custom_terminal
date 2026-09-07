"""Generate compact R.10D evidence from a clean implementation checkpoint."""

from pathlib import Path

from market_intel.application.synthetic_calendar import run_calendar_evidence


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run_calendar_evidence(
        recipe_path=ROOT / "specs" / "synthetic_exchange_calendar_r10d_v1.json",
        output_dir=ROOT / "docs" / "investigations" / "r10d" / "run_v1",
        project_root=ROOT,
        entrypoint=Path(__file__).resolve(),
    )


if __name__ == "__main__":
    main()
