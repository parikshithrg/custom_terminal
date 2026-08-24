import pandas as pd
import pytest

from market_intel.foundation.terminal import TerminalReason, outcome_status_for_terminal
from market_intel.simulation.costs import DatedCostSchedule, DeliveryCostDefinition


def test_unresolved_terminal_is_never_silently_resolved():
    assert outcome_status_for_terminal(None) == "UNRESOLVED_TERMINAL_STATE"
    assert outcome_status_for_terminal(TerminalReason.PERMANENT_DELISTING) == "TERMINAL_PERMANENT_DELISTING"


def test_cost_schedule_requires_date_coverage():
    schedule = DatedCostSchedule("v1", (DeliveryCostDefinition(),))
    assert schedule.at(pd.Timestamp("2026-08-13")).version.endswith("v1")
    with pytest.raises(LookupError):
        schedule.at(pd.Timestamp("2020-01-01"))
