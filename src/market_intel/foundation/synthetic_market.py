"""Deterministic fictional market provider used only for synthetic machinery tests."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd

from .providers import AcquisitionRequest, DatasetKind, ProviderObject


SYNTHETIC_PROVIDER_ID = "synthetic_formula_provider"


@dataclass
class SyntheticResearchProvider:
    """Provider-neutral adapter that emits only user-independent recipe objects."""

    recipe: dict
    staging_root: Path
    provider_id: str = SYNTHETIC_PROVIDER_ID

    def discover(self, request: AcquisitionRequest) -> list[ProviderObject]:
        if request.dataset not in {
            DatasetKind.DAILY_EQUITY, DatasetKind.SECURITY_MASTER,
            DatasetKind.CORPORATE_ACTIONS, DatasetKind.BENCHMARK_HISTORY,
        }:
            return []
        self.staging_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "fixture_id": self.recipe["fixture_id"],
            "classification": self.recipe["classification"],
            "calendar": self.recipe["calendar"],
            "versions": self.recipe["versions"],
            "dataset": request.dataset.value,
            "instruments": self.recipe["instruments"] if request.dataset in {
                DatasetKind.DAILY_EQUITY, DatasetKind.SECURITY_MASTER,
            } else [],
            "controlled_cases": self.recipe["controlled_cases"],
            "benchmark": self.recipe["benchmark"] if request.dataset == DatasetKind.BENCHMARK_HISTORY else None,
        }
        path = self.staging_root / f"{request.dataset.value}.synthetic.json"
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != encoded:
            raise FileExistsError("synthetic source object rewrite conflict")
        path.write_text(encoded, encoding="utf-8")
        return [ProviderObject(
            provider=self.provider_id, dataset=request.dataset,
            source_identity=f"{self.recipe['fixture_id']}:{request.dataset.value}",
            local_path=path, request_parameters={"fixture_id": self.recipe["fixture_id"]},
            expected_event_date=self.recipe["calendar"]["end"],
            licensing_notes="GENERATED_SYNTHETIC_RETAINABLE",
            retention_classification="GENERATED_SYNTHETIC_RETAINABLE",
            data_classification="SYNTHETIC_ONLY_NONCANONICAL",
        )]

    def parser_version(self, dataset: DatasetKind) -> str:
        return self.recipe["versions"]["parser"]


@dataclass(frozen=True)
class SyntheticResearchNormalizer:
    """DatasetNormalizer implementation for generated recipe objects."""

    provider_id: str = SYNTHETIC_PROVIDER_ID

    def normalize(self, dataset: DatasetKind, raw_paths: list[Path]) -> object:
        if len(raw_paths) != 1:
            raise ValueError("synthetic normalizer requires exactly one raw object")
        payload = json.loads(raw_paths[0].read_text(encoding="utf-8"))
        if payload.get("classification") != "SYNTHETIC_ONLY_NONCANONICAL":
            raise ValueError("non-synthetic payload rejected")
        if dataset == DatasetKind.DAILY_EQUITY:
            return generate_daily_rows(payload)
        if dataset == DatasetKind.SECURITY_MASTER:
            return generate_security_master(payload)
        if dataset == DatasetKind.CORPORATE_ACTIONS:
            return generate_actions(payload)
        if dataset == DatasetKind.BENCHMARK_HISTORY:
            return generate_benchmark(payload)
        raise ValueError("unsupported synthetic dataset")


def _calendar(recipe: dict) -> pd.DatetimeIndex:
    return pd.bdate_range(recipe["calendar"]["start"], recipe["calendar"]["end"])


def _instant(day: pd.Timestamp, hour: int, minute: int = 0) -> pd.Timestamp:
    return (pd.Timestamp(day).tz_localize("Asia/Kolkata") + pd.Timedelta(hours=hour, minutes=minute)).tz_convert("UTC")


def generate_security_master(recipe: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    securities = []
    for item in recipe["instruments"]:
        securities.append({
            "issuer_id": "SYN_ISSUER_" + item["instrument_id"].split("_")[-1],
            "instrument_id": item["instrument_id"], "listing_id": item["listing_id"],
            "exchange": "SYNTHETIC_EXCHANGE", "series": "SYN_EQ",
            "valid_from": pd.Timestamp(item["start"], tz="UTC"),
            "valid_to": pd.Timestamp(item["end"], tz="UTC") + pd.Timedelta(days=1) if item["end"] else pd.NaT,
            "listing_date": pd.Timestamp(item["start"]),
            "end_date": pd.Timestamp(item["end"]) if item["end"] else pd.NaT,
            "status": "TERMINATED_UNRESOLVED" if item["end"] else "ACTIVE",
        })
    aliases = []
    rename = recipe["controlled_cases"]["rename"]
    for item in recipe["instruments"]:
        if item["instrument_id"] == rename["instrument_id"]:
            aliases.extend([
                {"instrument_id": item["instrument_id"], "listing_id": item["listing_id"],
                 "symbol": rename["old_symbol"], "valid_from": pd.Timestamp(item["start"], tz="UTC"),
                 "valid_to": pd.Timestamp(rename["effective_at"]), "source_id": SYNTHETIC_PROVIDER_ID},
                {"instrument_id": item["instrument_id"], "listing_id": item["listing_id"],
                 "symbol": rename["new_symbol"], "valid_from": pd.Timestamp(rename["effective_at"]),
                 "valid_to": pd.NaT, "source_id": SYNTHETIC_PROVIDER_ID},
            ])
        else:
            aliases.append({"instrument_id": item["instrument_id"], "listing_id": item["listing_id"],
                            "symbol": item["symbol"], "valid_from": pd.Timestamp(item["start"], tz="UTC"),
                            "valid_to": (pd.Timestamp(item["end"], tz="UTC") + pd.Timedelta(days=1)) if item["end"] else pd.NaT,
                            "source_id": SYNTHETIC_PROVIDER_ID})
    terminal = pd.DataFrame([{
        "instrument_id": "SYN_I004", "listing_id": "SYN_L004",
        "termination_date": pd.Timestamp("2018-07-10"), "reason": "SYNTHETIC_DISAPPEARANCE",
        "economic_value": pd.NA, "resolution_status": "UNRESOLVED",
    }])
    return pd.DataFrame(securities), pd.DataFrame(aliases), terminal


def generate_daily_rows(recipe: dict) -> list[dict]:
    calendar = _calendar(recipe)
    cases = recipe["controlled_cases"]
    rows: list[dict] = []
    for instrument_index, item in enumerate(recipe["instruments"], start=1):
        start = pd.Timestamp(item["start"]); end = pd.Timestamp(item["end"]) if item["end"] else calendar[-1]
        active = calendar[(calendar >= start) & (calendar <= end)]
        for global_position, day in enumerate(calendar):
            if day not in active:
                continue
            date_text = str(day.date())
            if ((item["instrument_id"], date_text) in {
                (cases["missing_session"]["instrument_id"], cases["missing_session"]["session_date"]),
                (cases["missing_entry"]["instrument_id"], cases["missing_entry"]["session_date"]),
                (cases["missing_exit"]["instrument_id"], cases["missing_exit"]["session_date"]),
            }):
                continue
            close = round(item["base"] + item["slope"] * global_position + ((global_position + instrument_index) % 7) * 0.02, 4)
            if item["instrument_id"] == cases["invalid_price"]["instrument_id"] and date_text == cases["invalid_price"]["session_date"]:
                close = float(cases["invalid_price"]["close"])
            open_ = round(close * 0.999, 4)
            high = round(max(open_, close) * 1.003, 4)
            low = round(min(open_, close) * 0.997, 4)
            volume = item["volume"] + ((global_position + instrument_index) % 11) * 1000
            published = _instant(day, 18)
            if item["instrument_id"] == cases["publication_delay"]["instrument_id"] and date_text == cases["publication_delay"]["session_date"]:
                published += pd.Timedelta(days=cases["publication_delay"]["delay_days"])
            base_id = f"{item['instrument_id']}:{date_text}:r1"
            row = {
                "instrument_id": item["instrument_id"], "listing_id": item["listing_id"],
                "event_time": _instant(day, 15, 30), "session_date": day,
                "published_at": published, "available_at": published,
                "retrieved_at": published + pd.Timedelta(hours=1),
                "open": open_, "high": high, "low": low, "close": close,
                "volume": float(volume), "turnover": round(close * volume, 4),
                "source_id": SYNTHETIC_PROVIDER_ID, "source_record_id": base_id,
                "revision_number": 1, "supersedes_record_id": None,
            }
            rows.append(row)
            if item["instrument_id"] == cases["duplicate_source_row"]["instrument_id"] and date_text == cases["duplicate_source_row"]["session_date"]:
                rows.append(dict(row))
            if item["instrument_id"] == cases["revision"]["instrument_id"] and date_text == cases["revision"]["session_date"]:
                corrected = dict(row)
                corrected_close = round(close * cases["revision"]["close_multiplier"], 4)
                corrected.update(source_record_id=base_id.removesuffix("r1") + "r2", revision_number=2,
                                 supersedes_record_id=base_id,
                                 published_at=pd.Timestamp(cases["revision"]["revision_2_published_at"]),
                                 available_at=pd.Timestamp(cases["revision"]["revision_2_published_at"]),
                                 retrieved_at=pd.Timestamp(cases["revision"]["revision_2_published_at"]) + pd.Timedelta(hours=1),
                                 close=corrected_close, high=round(max(open_, corrected_close) * 1.003, 4),
                                 turnover=round(corrected_close * volume, 4))
                rows.append(corrected)
    return rows


def generate_benchmark(recipe: dict) -> pd.DataFrame:
    rows = []
    for position, day in enumerate(_calendar(recipe)):
        close = recipe["benchmark"]["base"] + recipe["benchmark"]["slope"] * position
        published = _instant(day, 18)
        rows.append({"event_time": _instant(day, 15, 30), "session_date": day,
                     "published_at": published, "available_at": published,
                     "index_id": recipe["benchmark"]["index_id"],
                     "return_classification": recipe["benchmark"]["return_classification"],
                     "open": close * 0.999, "close": close, "source_id": SYNTHETIC_PROVIDER_ID})
    return pd.DataFrame(rows)


def generate_actions(recipe: dict) -> pd.DataFrame:
    item = recipe["controlled_cases"]["corporate_action"]
    return pd.DataFrame([{**item, "published_at": pd.Timestamp("2016-06-01T12:30:00Z"),
                          "record_date": pd.Timestamp("2016-07-04"),
                          "source_id": SYNTHETIC_PROVIDER_ID,
                          "resolution_status": "DECLARED_NO_PRICE_ADJUSTMENT"}])
