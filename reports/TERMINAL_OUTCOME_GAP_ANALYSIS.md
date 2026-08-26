# Terminal-Outcome Gap Analysis

## Shared terminal contract

The neutral contract distinguishes:

1. ordinary missing observation;
2. temporary suspension;
3. permanent delisting;
4. merger or acquisition;
5. demerger;
6. symbol or ISIN transition;
7. source failure;
8. unresolved disappearance.

Unknown economics remain `UNRESOLVED`. A final quoted price does not become
delisting consideration, and an unresolved row cannot assert cash or successor
consideration. Resolved economics require evidence references.

## Existing engine paths

| Situation | `dtest` behavior | `market_intel` behavior | Gap |
|---|---|---|---|
| Missing entry open/volume | rejects/no-fill | `MISSING_ENTRY` or unfillable | explicit but not causally classified |
| Missing intended time-exit open | trade remains `unresolved` | `UNRESOLVED_DELISTING` | both block that observation, but label may over-attribute delisting |
| End-of-window | unresolved/right-censored | `RIGHT_CENSORED` | broadly compatible |
| Missing portfolio mark | marks at entry price | no equivalent slot portfolio | can conceal suspension losses and stale marks |
| Later signals after unresolved trade | symbol busy indefinitely | symbol busy indefinitely for unresolved/right-censored | conservative, but no economic resolution |
| Pair contract expiry | explicit mark/rollover rule | not implemented | strategy-specific, not a cash terminal outcome |
| Merger/demerger/successor | no authoritative conversion | typed canonical fields exist | evidence absent |
| Delisting cash consideration | not available | schema supports it | evidence absent |

The `dtest` universe drops stale names from later eligibility, but that is not a
terminal-economic treatment for already open positions. A disappearing ticker
may be a suspension, merger, rename, delisting, source failure or missing row;
the current panel cannot distinguish them.

## Existing-artifact quantification

A read-only scan of 66 saved CSV artifacts containing `exit_reason` found
181,775 rows, including 14,944 no-fill rows and 246 unresolved rows. These
figures are deliberately **not** interpreted as unique trades: the artifacts
include real runs, placebos, diagnostics, repeated variants and portfolio
views. The 246 unresolved rows include end-of-window cases and cannot be
classified as delistings from the stored columns.

Representative raw strategy artifacts include 41 unresolved value trades, 25
momentum primary/train trades, 9 momentum delivery/train trades, 3 momentum
delivery/validation trades, and smaller unresolved counts across other runs.
No authoritative terminal ledger is joined, so the economically affected count
cannot be established from these files.

## Promotion consequence

The materially unresolved terminal population blocks production promotion.
Dropping unresolved rows from metrics, assigning zero, carrying last price, or
using entry price for marking are different assumptions and must never be mixed
without an explicit versioned outcome policy and sensitivity analysis.
