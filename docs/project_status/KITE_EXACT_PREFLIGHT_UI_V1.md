# Kite exact local preflight UI v1

Implemented and tested offline on 2026-09-22 after the owner approved proceeding
from the transport core to the local preflight step. This changes only the manual
NIFTY 50 Data Coverage panel and local in-memory contracts. It does not execute the
two-request test.

## User flow

1. The owner loads or uploads today's validated official NIFTY 50 CSV using the
   existing bounded controls.
2. The owner loads the current Kite inventory using the existing manual control.
3. **Prepare exact 50-equity binding · no request** validates the exact unique
   `NSE` `EQ` crosswalk and builds a private in-memory binding.
4. The panel displays only target count, two batch sizes, exchange, instrument
   class and the binding SHA-256. It does not display the private target inventory,
   provider tokens, credentials or prices.
5. The owner reviews the displayed hash, checks the explicit confirmation and
   selects **Confirm exact binding · still no request**. Confirmation is bound to
   the exact constituent and selected-inventory hashes and expires at the original
   ten-minute preflight deadline.

Changing or refreshing the constituent list or inventory removes the stored
binding and approval. Login replacement and disconnection already clear every
`kite_` session value. A changed crosswalk, provenance or parser version also
invalidates confirmation.

## Boundaries

The view does not import or call `execute_two_batch_test`. There is no live exact
test button. Preparing and confirming make zero HTTP requests and perform no file
or database writes. The older operational coverage check remains visibly labelled
as legacy and is not represented as the exact Decimal/freshness test.

A local confirmation object is necessary but not sufficient for execution. The
next step must separately add an owner-triggered execution control that consumes
the still-current binding and approval, reports only the permitted transient
result and clears it on expiry/disconnect/failure. That step must not clear the
unresolved currency or maintained-calendar Dashboard gates.
