"""Explicit contracts for ephemeral current-market provider snapshots."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence
CURRENT_SCOPE="CURRENT_TRADABLE_ONLY"

@dataclass(frozen=True)
class CurrentInstrument:
    provider_instrument_token:int; exchange_token:int|None; trading_symbol:str; exchange:str
    segment:str; instrument_type:str; expiry:str|None; strike:float|None; tick_size:float|None; lot_size:int|None
    quality_flags:tuple[str,...]=()
    @property
    def provider_key(self)->str: return f"{self.exchange}:{self.trading_symbol}"

@dataclass(frozen=True)
class CurrentInstrumentSnapshot:
    provider:str; retrieved_at:datetime; session_date:str; source_endpoint:str; parser_version:str
    instruments:tuple[CurrentInstrument,...]; scope:str=CURRENT_SCOPE
    warning:str="Inactive and delisted instruments may be absent."
    def as_historical_universe(self)->None:
        raise TypeError("Current instrument snapshots cannot be used as historical universes")

@dataclass(frozen=True)
class CurrentQuote:
    instrument_key:str; status:str; last_price:float|None; ohlc:dict[str,float]|None
    provider_timestamp:str|None; message:str|None=None
    details:dict[str,float|int|None]|None=None

@dataclass(frozen=True)
class CurrentQuoteSnapshot:
    provider:str; retrieved_at:datetime; source_endpoint:str; quotes:tuple[CurrentQuote,...]
    cache_status:str="LIVE_PROVIDER_VALUE"; scope:str=CURRENT_SCOPE

class CurrentMarketDataProvider(Protocol):
    def validate_session(self)->str|None: ...
    def discover_current_instruments(self)->CurrentInstrumentSnapshot: ...
    def get_current_quotes(self,instrument_keys:Sequence[str],*,mode:str="quote")->CurrentQuoteSnapshot: ...


def search_current_instruments(
    snapshot: CurrentInstrumentSnapshot,
    query: str,
    *,
    exchange: str | None = None,
    instrument_type: str | None = None,
    limit: int = 100,
) -> tuple[str, ...]:
    """Return a bounded set of provider keys without rendering the full dump."""
    needle = query.strip().casefold()
    if len(needle) < 2:
        return ()
    if limit < 1 or limit > 500:
        raise ValueError("Search limit must be between 1 and 500")
    matches = []
    for instrument in snapshot.instruments:
        if exchange and instrument.exchange != exchange:
            continue
        if instrument_type and instrument.instrument_type != instrument_type:
            continue
        if needle not in instrument.trading_symbol.casefold():
            continue
        matches.append(instrument.provider_key)
        if len(matches) >= limit:
            break
    return tuple(sorted(matches))


def format_quote_rows(
    snapshot: CurrentQuoteSnapshot,
    mode: str,
) -> list[dict[str, object]]:
    """Produce mode-specific UI rows without exposing raw provider payloads."""
    if mode not in {"ltp", "ohlc", "quote"}:
        raise ValueError("Unsupported quote display mode")
    rows: list[dict[str, object]] = []
    for quote in snapshot.quotes:
        row: dict[str, object] = {
            "instrument": quote.instrument_key,
            "status": quote.status,
            "last_price": quote.last_price,
        }
        if mode in {"ohlc", "quote"}:
            ohlc = quote.ohlc or {}
            row.update({
                "open": ohlc.get("open"),
                "high": ohlc.get("high"),
                "low": ohlc.get("low"),
                "close": ohlc.get("close"),
            })
        if mode == "quote":
            row["provider_timestamp"] = quote.provider_timestamp
            # Streamlit can retain instances created before a hot-reloaded
            # dataclass gains this optional field.
            row.update(getattr(quote, "details", None) or {})
        row["message"] = quote.message
        rows.append(row)
    return rows
