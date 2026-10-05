from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from market_intel.foundation.artifacts import Catalog, normalize_logical_path
from market_intel.foundation.prices import load_symbol_csvs


def test_logical_catalog_paths_are_posix_and_historical_rows_are_normalized(tmp_path: Path):
    catalog = Catalog(tmp_path / "catalog.sqlite")
    row = {
        "run_id": "new",
        "experiment_id": "portable",
        "state": "RESEARCHING",
        "manifest_path": r"artifacts\runs\new\manifest.json",
        "manifest_hash": "a" * 64,
        "created_at": "2026-10-05T00:00:00+00:00",
    }
    catalog.record_run(row)
    catalog.db.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?)",
        ("old", "portable", "RESEARCHING", r"artifacts\runs\old\manifest.json", "b" * 64,
         "2026-10-04T00:00:00+00:00"),
    )
    catalog.db.commit()

    records = catalog.runs()
    catalog.close()

    assert [record["manifest_path"] for record in records] == [
        "artifacts/runs/new/manifest.json",
        "artifacts/runs/old/manifest.json",
    ]
    with pytest.raises(ValueError):
        normalize_logical_path(r"C:\private\manifest.json")
    with pytest.raises(ValueError):
        normalize_logical_path("../manifest.json")


def test_price_snapshot_identity_does_not_include_host_root(tmp_path: Path):
    roots = [tmp_path / "windows-like", tmp_path / "linux-like"]
    for root in roots:
        root.mkdir()
        pd.DataFrame(
            {
                "date": ["2026-10-01"],
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [1000],
            }
        ).to_csv(root / "TEST_DAILY.csv", index=False)

    snapshots = [
        load_symbol_csvs(
            root,
            as_of=pd.Timestamp("2026-10-01"),
            retrieved_at=pd.Timestamp("2026-10-02", tz="UTC"),
            survivorship_safe=False,
        ).snapshot
        for root in roots
    ]

    assert snapshots[0].content_hash == snapshots[1].content_hash
    assert snapshots[0].paths == snapshots[1].paths == ("TEST_DAILY.csv",)
    assert str(tmp_path) not in json.dumps(snapshots[0].paths)


def test_snapshot_manifest_has_no_absolute_paths():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "data_snapshot_manifest.json").read_text()
    )
    rendered = json.dumps(manifest)
    assert "C:\\" not in rendered
    assert "/home/" not in rendered
    assert set(manifest["datasets"]) == {
        "nse_cash_daily",
        "nse_fno_sqlite",
        "nifty500_industry_map",
    }
