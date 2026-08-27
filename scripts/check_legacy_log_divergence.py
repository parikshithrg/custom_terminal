"""Emit a sanitized ID-only comparison against the frozen 32-row ledger."""

from __future__ import annotations

import argparse
from pathlib import Path

from research_contracts.divergence import compare_legacy_logs, write_divergence_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--governed-manifest", type=Path, action="append", default=[])
    args = parser.parse_args()
    report = compare_legacy_logs(
        frozen_path=args.frozen,
        live_path=args.live,
        governed_manifest_paths=args.governed_manifest,
    )
    print(f"sha256={write_divergence_report(report, args.output)}")
    print(f"live_rows={report['live']['row_count']}")
    print(f"added_rows={len(report['added_row_ids'])}")
    print(f"classification={report['added_row_classification']}")


if __name__ == "__main__":
    main()
