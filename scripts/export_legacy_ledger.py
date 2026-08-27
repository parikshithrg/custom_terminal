"""Generate the deterministic R.2 neutral ledger from explicit boundaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--family-mapping", type=Path, required=True)
    parser.add_argument("--repository-runs", type=Path, required=True)
    parser.add_argument("--sibling-runs", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path, required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "Data test"))
    from dtest.evaluate.legacy_export import export_legacy_ledger, write_neutral_ledger

    ledger = export_legacy_ledger(
        snapshot_path=args.snapshot,
        snapshot_manifest_path=args.snapshot_manifest,
        family_mapping_path=args.family_mapping,
        artifact_boundaries={
            "repository_local_runs": args.repository_runs,
            "sibling_source_runs": args.sibling_runs,
        },
    )
    json_hash, csv_hash = write_neutral_ledger(
        ledger, json_path=args.json_output, csv_path=args.csv_output
    )
    print(f"json_sha256={json_hash}")
    print(f"csv_sha256={csv_hash}")
    print(f"rows={ledger['source_row_count']}")


if __name__ == "__main__":
    main()
