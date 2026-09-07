"""Generate compact R.10E evidence from a clean implementation checkpoint."""

from pathlib import Path

from market_intel.application.synthetic_scoring import run_scoring_evidence


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    run_scoring_evidence(
        recipe_path=ROOT / "specs/synthetic_multi_feature_score_r10e_v1.json",
        output_dir=ROOT / "docs/investigations/r10e/run_v1",
        project_root=ROOT,
        entrypoint=Path(__file__).resolve(),
    )
