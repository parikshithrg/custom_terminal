"""Validate and append an R.2 ledger to the non-production evidence catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from market_intel.foundation.legacy_evidence import (
    LegacyEvidenceCatalog,
    validate_legacy_import,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--family-mapping", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--imported-at")
    args = parser.parse_args()
    validation = validate_legacy_import(
        ledger_path=args.ledger,
        snapshot_path=args.snapshot,
        snapshot_manifest_path=args.snapshot_manifest,
        family_mapping_path=args.family_mapping,
    )
    record, appended = LegacyEvidenceCatalog(args.catalog).register(
        validation, imported_at=args.imported_at
    )
    print(f"validation={record['validation_result']}")
    print(f"classification={record['registration_classification']}")
    print(f"appended={str(appended).lower()}")
    print(f"ledger_sha256={record['ledger_sha256']}")


if __name__ == "__main__":
    main()
