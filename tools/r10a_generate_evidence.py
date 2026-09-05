"""Generate the one fixed, noncanonical R.10A synthetic evidence package."""
from pathlib import Path

from market_intel.application.synthetic_pipeline import run_synthetic_pipeline


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run_synthetic_pipeline(
        recipe_path=root / "specs" / "synthetic_research_fixture_r10a_v1.json",
        output_dir=root / "docs" / "investigations" / "r10a" / "run_v1",
        project_root=root,
    )


if __name__ == "__main__":
    main()
