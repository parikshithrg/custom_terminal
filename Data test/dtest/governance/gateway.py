"""Thin laboratory adapter over dependency-neutral governance contracts.

Direct scripts can still be used for development, but only this gateway emits
governed evidence. This module intentionally does not import ``market_intel``.
"""

from research_contracts.governance import (
    GovernedAbort,
    GovernedExecutionGateway,
    GovernanceError,
    label_ungoverned_output,
)

__all__ = [
    "GovernedAbort", "GovernedExecutionGateway", "GovernanceError",
    "label_ungoverned_output",
]
