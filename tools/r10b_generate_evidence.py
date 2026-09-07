"""Generate R.10B evidence from a clean implementation checkpoint."""

from pathlib import Path

from market_intel.application.synthetic_incremental import run_incremental_evidence


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run_incremental_evidence(
        recipe_path=ROOT / "specs" / "synthetic_incremental_sequence_r10b_v1.json",
        output_dir=ROOT / "docs" / "investigations" / "r10b" / "run_v1",
        project_root=ROOT,
        entrypoint=Path(__file__).resolve(),
    )


if __name__ == "__main__":
    main()
