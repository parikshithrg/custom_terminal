"""Read-only legacy-ledger adapter.

This module intentionally depends only on the neutral ``research_contracts``
package. It never imports ``market_intel`` and never runs a hypothesis.
"""

from research_contracts.legacy_ledger import (
    LegacyLedgerError,
    export_legacy_ledger,
    write_neutral_ledger,
)

__all__ = ["LegacyLedgerError", "export_legacy_ledger", "write_neutral_ledger"]
