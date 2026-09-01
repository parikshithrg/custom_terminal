"""Print a side-effect-free governed-run preview. This command never executes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_contracts import GovernanceCatalog, preview_governed_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--governance-catalog", type=Path, required=True)
    parser.add_argument("--attempts-root", type=Path, required=True)
    parser.add_argument("--canonical-catalog", type=Path, required=True)
    parser.add_argument("--runner-entry-point", action="append", default=[])
    parser.add_argument("--repository-root", type=Path,
                        help="Required for market research state-fingerprint validation")
    parser.add_argument("--review-record", type=Path,
                        help="Approved status-PDF review record required for market research")
    parser.add_argument("--evaluated-at", required=True,
                        help="Explicit timezone-aware ISO-8601 time for reproducible expiry evaluation")
    args = parser.parse_args()
    result = preview_governed_run(
        family_path=args.family, preregistration_path=args.preregistration,
        input_declaration_path=args.inputs, approval_path=args.approval,
        catalog=GovernanceCatalog(args.governance_catalog),
        attempts_root=args.attempts_root, canonical_catalog_path=args.canonical_catalog,
        registered_runner_entry_points=args.runner_entry_point,
        evaluated_at=args.evaluated_at,
        repository_root=args.repository_root,
        review_record_path=args.review_record,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["execution_permitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
