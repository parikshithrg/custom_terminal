"""Allowlisted, GET-only Kite current-market client."""
from __future__ import annotations
import csv, io
from datetime import datetime, timezone
from typing import Any, Callable, Sequence
from .current_market import CurrentInstrument,CurrentInstrumentSnapshot,CurrentQuote,CurrentQuoteSnapshot
from .kite_connect import KiteSession
API_ROOT="https://api.kite.trade"
ALLOWED_ENDPOINTS={"profile":("GET","/user/profile"),"instruments":("GET","/instruments"),
    "ltp":("GET","/quote/ltp"),"quote":("GET","/quote"),"ohlc":("GET","/quote/ohlc")}
MAX_QUOTE_SYMBOLS=25; QUOTE_CACHE_SECONDS=15
class KiteCurrentDataError(RuntimeError): pass
class KiteInvalidSessionError(KiteCurrentDataError): pass
class KiteReadOnlyViolation(KiteCurrentDataError): pass

class KiteCurrentMarketClient:
    provider_id="kite_connect"
    client_version="kite_current_market_v2"
    def __init__(self,session:KiteSession,*,http:Any,now:Callable[[],datetime]|None=None):
        self._session,self._http=session,http; self._now=now or (lambda:datetime.now(timezone.utc))
        self._inventory=None; self._quote_cache={}
    def __repr__(self)->str: return "KiteCurrentMarketClient(session=<redacted>, mode=read-only)"
    def attach_current_inventory(self,snapshot:CurrentInstrumentSnapshot)->None:
        if snapshot.provider!="kite_connect" or snapshot.scope!="CURRENT_TRADABLE_ONLY":
            raise ValueError("Only a Kite current-only inventory can be attached")
        self._inventory=snapshot
    def _request(self,endpoint:str,*,method:str="GET",params:list[tuple[str,str]]|None=None)->Any:
        allowed=ALLOWED_ENDPOINTS.get(endpoint)
        if allowed is None or allowed[0]!=method.upper():
            raise KiteReadOnlyViolation("Endpoint or HTTP method is not in the read-only allowlist")
        try:
            response=self._http.get(API_ROOT+allowed[1],params=params,
                headers={"X-Kite-Version":"3","Authorization":self._session.authorization_header},timeout=20)
            if getattr(response,"status_code",None) in (401,403):
                raise KiteInvalidSessionError("Kite session is expired or invalid; log in again")
            response.raise_for_status(); return response
        except KiteCurrentDataError: raise
        except Exception as exc: raise KiteCurrentDataError("Kite current-data request failed or timed out") from exc
    def validate_session(self)->str|None: return self._data(self._request("profile")).get("user_id")
    def discover_current_instruments(self)->CurrentInstrumentSnapshot:
        response=self._request("instruments")
        try:
            instruments=tuple(self._normalize_instrument(r) for r in csv.DictReader(io.StringIO(response.text)))
            if not instruments: raise ValueError
        except Exception as exc: raise KiteCurrentDataError("Kite instrument response has an unsupported schema") from exc
        now=self._now(); self._inventory=CurrentInstrumentSnapshot("kite_connect",now,now.date().isoformat(),"/instruments","kite_instruments_csv_v1",instruments)
        return self._inventory
    def get_current_quotes(self,instrument_keys:Sequence[str],*,mode:str="quote")->CurrentQuoteSnapshot:
        if mode not in {"ltp","quote","ohlc"}: raise KiteReadOnlyViolation("Quote mode is not in the read-only allowlist")
        keys=tuple(dict.fromkeys(str(k).strip() for k in instrument_keys if str(k).strip()))
        if not keys or len(keys)>MAX_QUOTE_SYMBOLS: raise ValueError(f"Choose between 1 and {MAX_QUOTE_SYMBOLS} instruments")
        if self._inventory is None: raise ValueError("Load the current instrument inventory before requesting quotes")
        valid={i.provider_key for i in self._inventory.instruments}
        if any(k not in valid for k in keys): raise ValueError("One or more instruments are not in the current inventory")
        cache_key,now=(mode,keys),self._now(); cached=self._quote_cache.get(cache_key)
        if cached and (now-cached.retrieved_at).total_seconds()<=QUOTE_CACHE_SECONDS:
            return CurrentQuoteSnapshot(cached.provider,cached.retrieved_at,cached.source_endpoint,cached.quotes,"FRESH_CACHE",cached.scope)
        try:
            payload=self._data(self._request(mode,params=[("i",k) for k in keys]))
        except KiteInvalidSessionError:
            raise
        except KiteCurrentDataError:
            if cached:
                return CurrentQuoteSnapshot(cached.provider,cached.retrieved_at,cached.source_endpoint,
                    cached.quotes,"STALE_CACHE",cached.scope)
            raise
        quotes=[]
        for key in keys:
            item=payload.get(key)
            if item is None: quotes.append(CurrentQuote(key,"MISSING",None,None,None,"Provider returned no value")); continue
            ohlc=item.get("ohlc")
            detail_fields=("last_quantity","average_price","volume","buy_quantity","sell_quantity",
                "oi","oi_day_high","oi_day_low","lower_circuit_limit","upper_circuit_limit")
            details={field:item.get(field) for field in detail_fields if field in item}
            quotes.append(CurrentQuote(key,"AVAILABLE",self._number(item.get("last_price")),
                {k:float(v) for k,v in ohlc.items() if v is not None} if isinstance(ohlc,dict) else None,
                item.get("timestamp") or item.get("last_trade_time"),details=details or None))
        result=CurrentQuoteSnapshot("kite_connect",now,ALLOWED_ENDPOINTS[mode][1],tuple(quotes)); self._quote_cache[cache_key]=result; return result
    def _json(self,response:Any)->dict[str,Any]:
        try:
            body=response.json()
            if not isinstance(body,dict): raise TypeError
            if body.get("status")=="error" and body.get("error_type") in {"TokenException","PermissionException"}:
                raise KiteInvalidSessionError("Kite session is expired or invalid; log in again")
            return body
        except KiteInvalidSessionError: raise
        except Exception as exc: raise KiteCurrentDataError("Kite returned a malformed response") from exc
    def _data(self,response:Any)->dict[str,Any]:
        data=self._json(response).get("data",{})
        if not isinstance(data,dict): raise KiteCurrentDataError("Kite returned a malformed response")
        return data
    @staticmethod
    def _number(value:Any)->float|None: return None if value in (None,"") else float(value)
    @classmethod
    def _normalize_instrument(cls,row:dict[str,str])->CurrentInstrument:
        required=("instrument_token","tradingsymbol","exchange","segment","instrument_type")
        if any(not row.get(f) for f in required): raise ValueError
        return CurrentInstrument(int(row["instrument_token"]),int(row["exchange_token"]) if row.get("exchange_token") else None,
            row["tradingsymbol"],row["exchange"],row["segment"],row["instrument_type"],row.get("expiry") or None,
            cls._number(row.get("strike")),cls._number(row.get("tick_size")),int(row["lot_size"]) if row.get("lot_size") else None)
