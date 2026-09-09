"""Forward pytest semantics for immutable historical evidence tests."""

from __future__ import annotations

import pytest


_HISTORICAL_NONAPPROVAL_TEST = (
    "tests/test_research_r9l_pdf_v6.py::"
    "test_nonapproval_generation_has_no_new_authority"
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep R.9L byte-exact while acknowledging its later approved successor.

    The R.9L assertion correctly described the repository at PDF-v6 generation
    time.  A separately committed v6 owner-review record now exists.  Marking
    that one historical-state assertion as a strict expected failure preserves
    the hash-bound test and makes an unexpected disappearance of the conflict a
    failure requiring deliberate reconciliation.
    """
    for item in items:
        if item.nodeid.replace("\\", "/") == _HISTORICAL_NONAPPROVAL_TEST:
            item.add_marker(pytest.mark.xfail(
                strict=True,
                reason=(
                    "R.9L immutable generation-time assertion is superseded by "
                    "the separate forward v6 owner-review record"
                ),
            ))
