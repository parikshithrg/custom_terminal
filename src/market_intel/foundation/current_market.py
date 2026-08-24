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

@dataclass(frozen=True)
class CurrentQuoteSnapshot:
    provider:str; retrieved_at:datetime; source_endpoint:str; quotes:tuple[CurrentQuote,...]
    cache_status:str="LIVE_PROVIDER_VALUE"; scope:str=CURRENT_SCOPE

class CurrentMarketDataProvider(Protocol):
    def validate_session(self)->str|None: ...
    def discover_current_instruments(self)->CurrentInstrumentSnapshot: ...
    def get_current_quotes(self,instrument_keys:Sequence[str],*,mode:str="quote")->CurrentQuoteSnapshot: ...
