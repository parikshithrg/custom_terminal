"""Prospective governed execution boundary for future laboratory runs."""

from .gateway import (
    GovernedAbort,
    GovernedExecutionGateway,
    GovernanceError,
    preview_governed_run,
    register_run_approval,
)

__all__ = [
    "GovernedAbort", "GovernedExecutionGateway", "GovernanceError",
    "preview_governed_run", "register_run_approval",
]
