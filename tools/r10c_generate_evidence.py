"""Generate compact R.10C evidence from a clean implementation checkpoint."""

from pathlib import Path

from market_intel.application.synthetic_security_events import run_security_event_evidence


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run_security_event_evidence(
        recipe_path=ROOT / "specs" / "synthetic_security_events_r10c_v1.json",
        output_dir=ROOT / "docs" / "investigations" / "r10c" / "run_v1",
        project_root=ROOT,
        entrypoint=Path(__file__).resolve(),
    )


if __name__ == "__main__":
    main()
