"""Bounded owner-triggered current-equity operational test, not qualification."""
import csv
from dataclasses import dataclass
from datetime import timezone, timedelta
import hashlib
import io
import math
import re

OFFICIAL_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
IST = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True, slots=True)
class Constituents:
    symbols: tuple[str, ...]
    payload_hash: str
    retrieved_at: object
    source_url: str = OFFICIAL_URL


def fetch_constituents(*, http, now):
    """One fixed GET, no redirects/retries, <=64 KiB decoded CSV, 30s timeout."""
    response = http.get(OFFICIAL_URL, timeout=30, stream=True, allow_redirects=False)
    try:
        if response.status_code != 200 or response.url != OFFICIAL_URL:
            raise ValueError("Official constituent list unavailable within approved route")
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in {"text/csv", "application/csv", "text/plain", "application/octet-stream"}:
            raise ValueError("Unexpected constituent content type")
        chunks, size = [], 0
        for chunk in response.iter_content(chunk_size=4096):
            size += len(chunk)
            if size > 65536:
                raise ValueError("Constituent size limit exceeded")
            chunks.append(chunk)
        return parse_constituents(b"".join(chunks), retrieved_at=now())
    finally:
        response.close()


def parse_constituents(payload, *, retrieved_at):
    if type(payload) is not bytes or not 0 < len(payload) <= 65536:
        raise ValueError("Bounded constituent bytes required")
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("Aware retrieval timestamp required")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        if (not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or
                not {"Symbol", "Series", "ISIN Code"} <= set(reader.fieldnames)):
            raise ValueError("Unsupported official constituent schema")
        symbols, isins = [], []
        for row in reader:
            symbol, isin = row.get("Symbol", ""), row.get("ISIN Code", "")
            if (None in row or row.get("Series") != "EQ" or
                    not re.fullmatch(r"[A-Z0-9&_.-]{1,32}", symbol) or
                    not re.fullmatch(r"IN[A-Z0-9]{10}", isin)):
                raise ValueError("Invalid equity constituent")
            symbols.append(symbol)
            isins.append(isin)
            if len(symbols) > 50:
                raise ValueError("Unexpected constituent count")
        if len(symbols) != 50 or len(set(symbols)) != 50 or len(set(isins)) != 50:
            raise ValueError("Exactly 50 unique equity constituents required")
    except (UnicodeError, csv.Error, TypeError):
        raise ValueError("Invalid official constituent CSV") from None
    return Constituents(tuple(sorted(symbols)), hashlib.sha256(payload).hexdigest(), retrieved_at)


def plan_batches(constituents, inventory, *, as_of):
    if (type(constituents) is not Constituents or constituents.source_url != OFFICIAL_URL or
            len(constituents.symbols) != 50 or len(set(constituents.symbols)) != 50 or
            not re.fullmatch(r"[0-9a-f]{64}", constituents.payload_hash)):
        raise ValueError("Verified official constituent binding required")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Aware as-of required")
    if (constituents.retrieved_at > as_of or inventory.retrieved_at > as_of or
            constituents.retrieved_at.astimezone(IST).date() != as_of.astimezone(IST).date() or
            inventory.retrieved_at.astimezone(IST).date() != as_of.astimezone(IST).date()):
        raise ValueError("Load today's official list and current inventory first")
    if inventory.provider != "kite_connect" or inventory.scope != "CURRENT_TRADABLE_ONLY":
        raise ValueError("Current Kite inventory required")
    keys = []
    for symbol in constituents.symbols:
        matches = [item for item in inventory.instruments if item.exchange == "NSE" and item.trading_symbol == symbol]
        if (len(matches) != 1 or matches[0].instrument_type != "EQ" or matches[0].segment != "NSE" or
                matches[0].quality_flags or type(matches[0].provider_instrument_token) is not int or
                matches[0].provider_instrument_token <= 0 or matches[0].expiry):
            raise ValueError("Missing, ambiguous or ineligible cash-equity crosswalk")
        keys.append(matches[0].provider_key)
    tokens = [next(item.provider_instrument_token for item in inventory.instruments if item.provider_key == key) for key in keys]
    if len(set(tokens)) != 50:
        raise ValueError("Ambiguous provider token crosswalk")
    return tuple(keys[:25]), tuple(keys[25:])


def run_test(*, constituents, inventory, client, as_of):
    batches = plan_batches(constituents, inventory, as_of=as_of)
    results = []
    for keys in batches:
        snapshot = client.get_current_quotes(keys, mode="quote")
        if (snapshot.provider != "kite_connect" or snapshot.scope != "CURRENT_TRADABLE_ONLY" or
                snapshot.source_endpoint != "/quote" or snapshot.cache_status not in {"LIVE_PROVIDER_VALUE", "FRESH_CACHE"} or
                len(snapshot.quotes) != 25 or set(row.instrument_key for row in snapshot.quotes) != set(keys)):
            raise ValueError("Incomplete, stale or incompatible batch; no combined result published")
        for row in snapshot.quotes:
            if row.status not in {"AVAILABLE", "MISSING"}:
                raise ValueError("Unclassified quote state")
            if row.status == "AVAILABLE" and (type(row.last_price) not in {int, float} or
                                             not math.isfinite(row.last_price) or row.last_price <= 0):
                raise ValueError("Invalid available price; operational test stopped")
            if row.status == "MISSING" and row.last_price is not None:
                raise ValueError("Inconsistent missing quote")
        results.append(snapshot)
    return tuple(results)
