"""Generate compact R.10F publication evidence from a clean checkpoint."""

from pathlib import Path

from market_intel.application.synthetic_publication import run_publication_evidence


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    run_publication_evidence(
        output_dir=ROOT / "docs/investigations/r10f/run_v1",
        project_root=ROOT,
        entrypoint=Path(__file__).resolve(),
    )
