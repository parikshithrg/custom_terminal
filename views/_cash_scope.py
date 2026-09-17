"""Presentation-only cash-equity/index filtering; never mutate provider facts."""
from dataclasses import replace


def cash_inventory(snapshot):
    if snapshot is None:
        return None
    return replace(snapshot, instruments=tuple(
        item for item in snapshot.instruments
        if item.exchange in {"NSE", "BSE"} and item.instrument_type in {"EQ", "INDICES"}
    ))


def cash_quotes(snapshot, inventory):
    if snapshot is None or inventory is None:
        return None
    keys = {item.provider_key for item in cash_inventory(inventory).instruments}
    return replace(snapshot, quotes=tuple(item for item in snapshot.quotes if item.instrument_key in keys))
