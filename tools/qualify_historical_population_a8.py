"""Bounded A.8 acquisition for the locked dates; never a full-year crawler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_intel.foundation.nse_population_normalization import normalize_bhavcopy, normalize_mii_security
from market_intel.foundation.official_http import OfficialHttpClient
from market_intel.foundation.population_qualification import (
    AcquisitionProvenance, compare_snapshots, partial_sample_trust, qualify_pair,
)


DATES = ["2016-01-04", "2016-08-24", "2018-02-06", "2018-09-21", "2020-01-02", "2020-03-23",
         "2022-02-24", "2022-06-17", "2024-01-02", "2024-06-04", "2025-01-02", "2025-04-07"]
MII_WEBSITE_START = "2024-02-05"


def bhavcopy_url(value: str) -> tuple[str, tuple[str, ...]]:
    year, month, day = value.split("-")
    months = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    if int(year) <= 2018:
        return (f"https://archives.nseindia.com/content/historical/EQUITIES/{year}/{months[int(month)]}/"
                f"cm{day}{months[int(month)]}{year}bhav.csv.zip", ("application/zip", "application/octet-stream"))
    if int(year) <= 2024:
        return (f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{day}{month}{year}.csv",
                ("text/csv", "application/octet-stream"))
    return (f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{year}{month}{day}_F_0000.csv.zip",
            ("application/zip", "application/octet-stream"))


def provenance(manifest: dict) -> AcquisitionProvenance:
    return AcquisitionProvenance("AUTOMATED", manifest["source_url"], manifest["retrieval_timestamp"],
                                 manifest["content_hash"], manifest["parser_version"], True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("artifacts/population_a8/raw"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/population_a8/v1"))
    parser.add_argument("--access-log", type=Path, default=Path("specs/historical_population_access_log_v1.json"))
    args = parser.parse_args()
    client = OfficialHttpClient(allowed_hosts={"archives.nseindia.com", "nsearchives.nseindia.com"},
        user_agent="custom-terminal-a8-population-qualification/1.0 (bounded official research)",
        minimum_interval_seconds=1.0, retries=2)
    args.output.mkdir(parents=True, exist_ok=True)
    results, snapshots = [], {}
    for date in DATES:
        row = {"date": date, "security_snapshot": {}, "bhavcopy": {}}
        if date < MII_WEBSITE_START:
            row["security_snapshot"] = {"status": "BLOCKED", "reason": "NSE website MII dissemination began 2024-02-05",
                "evidence": "NSE/MSD/60315", "requested": False}
            security = security_manifest = None
        else:
            url = f"https://nsearchives.nseindia.com/content/cm/NSE_CM_security_{date[8:10]}{date[5:7]}{date[:4]}.csv.gz"
            landed = client.retrieve(organization="nse", dataset="security_snapshot", url=url,
                raw_root=args.raw_root, parser_version="a8_router_v1",
                expected_content_types=("application/gzip", "application/x-gzip", "application/octet-stream"))
            security_manifest = json.loads(Path(landed.manifest_path).read_text(encoding="utf-8"))
            row["security_snapshot"] = {"status": "PASS" if landed.outcome == "SUCCEEDED" else "BLOCKED",
                "url": url, "hash": landed.content_hash, "outcome": landed.outcome,
                "quarantine_reason": landed.quarantine_reason, "manifest": landed.manifest_path}
            security = (normalize_mii_security(Path(landed.payload_path), snapshot_date=date,
                        content_hash=landed.content_hash) if landed.outcome == "SUCCEEDED" else None)
        url, types = bhavcopy_url(date)
        landed = client.retrieve(organization="nse", dataset="daily_equity", url=url, raw_root=args.raw_root,
                                 parser_version="a8_router_v1", expected_content_types=types)
        price_manifest = json.loads(Path(landed.manifest_path).read_text(encoding="utf-8"))
        row["bhavcopy"] = {"status": "PASS" if landed.outcome == "SUCCEEDED" else "BLOCKED", "url": url,
                           "hash": landed.content_hash, "outcome": landed.outcome,
                           "quarantine_reason": landed.quarantine_reason, "manifest": landed.manifest_path}
        prices = (normalize_bhavcopy(Path(landed.payload_path), trade_date=date, content_hash=landed.content_hash)
                  if landed.outcome == "SUCCEEDED" else None)
        if security is not None and prices is not None:
            row["qualification"] = qualify_pair(security, prices, cash_series={"EQ"},
                security_provenance=provenance(security_manifest), price_provenance=provenance(price_manifest))
            row["qualification"].update({"total_security_records": len(security),
                "total_bhavcopy_records": len(prices),
                "security_series_counts": {str(k): int(v) for k, v in security.groupby("series", dropna=False).size().items()},
                "bhavcopy_series_counts": {str(k): int(v) for k, v in prices.groupby("series", dropna=False).size().items()},
                "missing_mandatory_fields": int(security[["symbol", "series", "listing_id"]].isna().any(axis=1).sum()),
                "schema_version": "nse_mii_security_v1+nse_bhavcopy_router_v2"})
            snapshots[date] = security
        else:
            row["qualification"] = qualify_pair(None, None, cash_series={"EQ"})
        results.append(row)
    cross = []
    ordered = sorted(snapshots)
    for previous, current in zip(ordered, ordered[1:]):
        left = snapshots[previous][snapshots[previous].series == "EQ"]
        right = snapshots[current][snapshots[current].series == "EQ"]
        changes = compare_snapshots(left, right)
        cross.append({"previous_date": previous, "current_date": current,
                      "additions_count": len(changes["additions"]), "removals_count": len(changes["removals"]),
                      "additions": changes["additions"], "removals": changes["removals"],
                      "causal_transition_status": "UNRESOLVED_WITHOUT_COMPLETE_EVENT_LEDGER"})
    machine = {"result_version": "historical_population_12_dates_result_v1", "dates": results,
               "trust": partial_sample_trust([r["qualification"] for r in results], len(DATES))}
    (args.output / "date_results.json").write_text(json.dumps(machine, indent=2, default=str) + "\n", encoding="utf-8")
    (args.output / "cross_date_reconciliation.json").write_text(json.dumps({"version": "cross_date_v1", "pairs": cross}, indent=2, default=str) + "\n", encoding="utf-8")
    access_objects = []
    for manifest_path in sorted(args.raw_root.glob("**/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        access_objects.append({key: manifest.get(key) for key in ("dataset", "source_url", "retrieval_timestamp",
            "request_parameters", "http_status", "response_metadata", "content_hash", "byte_size",
            "parser_version", "retrieval_outcome", "quarantine_reason")})
    args.access_log.write_text(json.dumps({"version": "historical_population_access_log_v1",
        "objects": access_objects}, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"dates": len(results), "complete_pairs": sum(r["qualification"]["status"] == "QUALIFIED" for r in results),
                      "security_objects": len(snapshots), "trust": machine["trust"]}, default=str))


if __name__ == "__main__":
    main()
