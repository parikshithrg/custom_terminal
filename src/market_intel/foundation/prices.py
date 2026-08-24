"""Typed daily-price ingestion for Slice A; acquisition remains external."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .artifacts import sha256_file
from .contracts import DatasetSnapshot, stable_instrument_id


PRICE_COLUMNS = ("date", "open", "high", "low", "close", "volume", "turnover")


@dataclass(frozen=True)
class PricePanels:
    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    turnover: pd.DataFrame
    aliases: pd.DataFrame
    provenance: pd.DataFrame
    snapshot: DatasetSnapshot


def load_symbol_csvs(
    price_dir: str | Path,
    *,
    as_of: pd.Timestamp,
    retrieved_at: pd.Timestamp,
    survivorship_safe: bool,
    source_id: str = "local_daily_csv",
    include_symbols: set[str] | None = None,
) -> PricePanels:
    """Load dataset-specific OHLCV CSVs with explicit provenance.

    `survivorship_safe` must be supplied by the caller; the loader never infers
    that a directory of current ticker files is historically complete.
    """
    import hashlib

    paths = sorted(Path(price_dir).glob("*_DAILY.csv"), key=lambda p: p.name)
    if not paths:
        raise FileNotFoundError(f"no *_DAILY.csv files under {price_dir}")
    fields: dict[str, dict[str, pd.Series]] = {k: {} for k in PRICE_COLUMNS[1:]}
    aliases = []
    provenance = []
    file_hashes = []
    for path in paths:
        symbol = path.stem.removesuffix("_DAILY").upper()
        if include_symbols is not None and symbol not in include_symbols:
            continue
        instrument_id = stable_instrument_id("NSE", symbol)
        frame = pd.read_csv(path, parse_dates=["date"]).sort_values("date", kind="stable")
        frame = frame[frame["date"] <= pd.Timestamp(as_of)].drop_duplicates("date", keep="last")
        if frame.empty:
            continue
        if "turnover" not in frame.columns:
            frame["turnover"] = pd.to_numeric(frame["close"], errors="coerce") * pd.to_numeric(frame["volume"], errors="coerce")
        frame = frame.set_index("date")
        for field in fields:
            fields[field][instrument_id] = pd.to_numeric(frame[field], errors="coerce")
        aliases.append({
            "instrument_id": instrument_id, "source_id": source_id, "symbol": symbol,
            "effective_from": frame.index.min(), "effective_to": pd.NaT,
        })
        payload_hash = sha256_file(path)
        file_hashes.append(f"{path.name}:{payload_hash}")
        provenance.append({
            "instrument_id": instrument_id, "event_time_start": frame.index.min(),
            "event_time_end": frame.index.max(),
            "published_at_policy": "NSE_SESSION_CLOSE_DATE; exact archive publication timestamp unavailable",
            "retrieved_at": pd.Timestamp(retrieved_at), "source_id": source_id,
            "revision_number": 1, "raw_payload_hash": payload_hash,
            "parser_version": "daily_csv_v1", "quality_flags": "TURNOVER_DERIVED_CLOSE_TIMES_VOLUME" if "turnover" not in pd.read_csv(path, nrows=0).columns else "",
        })
    panels = {name: pd.DataFrame(values).sort_index() for name, values in fields.items()}
    calendar = panels["close"].index
    panels = {name: frame.reindex(calendar) for name, frame in panels.items()}
    content_hash = hashlib.sha256("|".join(file_hashes).encode()).hexdigest()
    flags_list = [] if survivorship_safe else ["SURVIVORSHIP_SAFETY_UNPROVEN"]
    if any("turnover" not in pd.read_csv(path, nrows=0).columns for path in paths[:1]):
        flags_list.append("TURNOVER_DERIVED_CLOSE_TIMES_VOLUME")
    flags = tuple(flags_list)
    snapshot = DatasetSnapshot(
        dataset_id="nse_cash_daily", version=f"sha256:{content_hash[:16]}",
        source_id=source_id, knowledge_cutoff=pd.Timestamp(as_of),
        retrieved_at=pd.Timestamp(retrieved_at), content_hash=content_hash,
        parser_version="daily_csv_v1", survivorship_safe=survivorship_safe,
        paths=tuple(str(p) for p in paths), quality_flags=flags,
    )
    return PricePanels(**panels, aliases=pd.DataFrame(aliases), provenance=pd.DataFrame(provenance), snapshot=snapshot)
