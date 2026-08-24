"""Explicit terminal and missing-data classifications."""

from enum import StrEnum


class TerminalReason(StrEnum):
    ORDINARY_MISSING_DATA = "ORDINARY_MISSING_DATA"
    TEMPORARY_SUSPENSION = "TEMPORARY_SUSPENSION"
    PERMANENT_DELISTING = "PERMANENT_DELISTING"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    DEMERGER = "DEMERGER"
    TICKER_CHANGE = "TICKER_CHANGE"
    DATA_SOURCE_FAILURE = "DATA_SOURCE_FAILURE"
    UNRESOLVED_TERMINAL_STATE = "UNRESOLVED_TERMINAL_STATE"


def outcome_status_for_terminal(reason: TerminalReason | None) -> str:
    if reason is None or reason == TerminalReason.UNRESOLVED_TERMINAL_STATE:
        return "UNRESOLVED_TERMINAL_STATE"
    return f"TERMINAL_{reason.value}"
