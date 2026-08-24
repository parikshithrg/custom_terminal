"""End-to-end local-provider dry run: adapter -> raw -> canonical -> acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from market_intel.foundation.acceptance import CanonicalDatasetBundle, write_acceptance_report
from market_intel.foundation.artifacts import write_parquet_immutable
from market_intel.foundation.local_file_provider import LocalAuditedFileProvider, local_missing_frames
from market_intel.foundation.providers import AcquisitionRequest, DatasetKind
from market_intel.foundation.raw_ingestion import acquire_immutable


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a provider dataset against canonical trust gates")
    parser.add_argument("--provider", choices=["local-files"], required=True)
    parser.add_argument("--price-dir", type=Path, required=True)
    parser.add_argument("--industry-map", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=Path("artifacts/raw"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/acceptance/local_audited_files_v1"))
    args = parser.parse_args()

    provider = LocalAuditedFileProvider(args.price_dir, args.industry_map)
    normalized, manifests = {}, []
    for kind in (DatasetKind.DAILY_EQUITY, DatasetKind.SECURITY_MASTER, DatasetKind.BENCHMARK_HISTORY):
        acquired = []
        for obj in provider.discover(AcquisitionRequest(kind)):
            path, manifest = acquire_immutable(obj, raw_root=args.raw_root, parser_version=provider.parser_version(kind))
            acquired.append((path, manifest))
            manifests.append(manifest)
        normalized[kind] = provider.normalize(kind, acquired)

    prices = normalized[DatasetKind.DAILY_EQUITY]
    master = normalized[DatasetKind.SECURITY_MASTER]
    first_dates = prices.groupby("exchange_symbol")["trade_date"].min()
    master["listing_date"] = master["symbol"].map(first_dates)
    aliases = master[["instrument_id", "exchange", "symbol", "valid_from", "valid_to"]].copy()
    actions, terminals, costs = local_missing_frames()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    frames = {"daily_equity": prices, "security_master": master, "aliases": aliases,
              "corporate_actions": actions, "terminal_outcomes": terminals,
              "benchmark_history": normalized[DatasetKind.BENCHMARK_HISTORY], "cost_schedules": costs}
    hashes = {f"{name}.parquet": write_parquet_immutable(frame, output / f"{name}.parquet") for name, frame in frames.items()}
    version_input = "|".join(sorted(m.content_hash for m in manifests))
    version = "sha256:" + hashlib.sha256(version_input.encode()).hexdigest()[:16]
    bundle = CanonicalDatasetBundle("local_audited_equity_history", version, prices, master, aliases,
                                    actions, terminals, frames["benchmark_history"], costs,
                                    population_reference_complete=False, raw_manifest_count=len(manifests))
    write_acceptance_report(bundle, output)
    root_manifest = {"manifest_version": "normalized_dataset_manifest_v1", "provider": provider.provider_id,
                     "dataset_id": bundle.dataset_id, "dataset_version": version,
                     "raw_object_hashes": sorted(m.content_hash for m in manifests),
                     "raw_manifest_count": len(manifests), "canonical_schema_versions": {
                         "daily_equity": "daily_equity_v1", "security_master": "security_master_v1",
                         "corporate_actions": "corporate_actions_v1", "terminal_outcomes": "terminal_outcomes_v1",
                         "benchmark_history": "benchmark_history_v1", "cost_schedules": "cost_schedules_v1"},
                     "canonical_artifact_hashes": hashes}
    (output / "dataset_manifest.json").write_text(json.dumps(root_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output / "acceptance_report.md")


if __name__ == "__main__":
    main()
