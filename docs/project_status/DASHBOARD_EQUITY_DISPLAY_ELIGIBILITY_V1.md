# Dashboard equity display eligibility decision v1

Prepared 2026-09-19 from baseline `141e1ba` after the owner directed work to
continue. This freezes the current-equity consumer acceptance matrix using
existing repository evidence only. No external access or application behavior
change occurred.

## Decision

**NOT_ELIGIBLE_FOR_DASHBOARD_WIRING.** Kite current full quote remains the best
candidate for a future private cash-equity watchlist, but no real values may be
wired yet. Every gate in the adjacent JSON matrix is independently blocking.
Complete quote coverage or owner approval cannot override missing source
semantics, permission, session, freshness, quality or retention evidence.

The consumer remains at most 25 explicitly selected current NSE/BSE EQ targets.
Permitted future fields are current identity/provenance, exact last traded price,
declared currency, separate provider-quote/last-trade/retrieval clocks, value
state and quality reasons. Two-decimal half-up rendering is display-only.
Percentage change remains unavailable because no previous-close basis is approved.

## What is established

- Official public documentation describes private personal interfaces
  conditionally and documents full-quote last price plus separate quote/trade
  clocks and IST response strings.
- The exact offline decoder, readiness, health, ledger and quality contracts are
  implemented and tested with invented fixtures.
- The manual legacy result reported 50 returned and zero missing, but used a
  different float path and cannot qualify this consumer.

These facts establish feasibility, not account-specific permission, operational
quality or display eligibility.

## What remains blocking

- A separately approved Dashboard consumer after the evidence gates are complete.
- Exact current target/inventory binding and bounded operational validation.
- Authoritative REST NSE-EQ currency/unit binding. Current LTP semantics are now
  resolved for this current-only, no-history/no-change consumer.
- A maintained, versioned exchange-session/non-trading-day policy.
- Operational validation of the already frozen per-record freshness rules.
- Implementation and review of the proposed transient-memory and sanitized
  compliance-record policy.

Owner confirmation is a prerequisite declaration; it is not publisher-issued
source evidence. Public deployment, research, history, recommendations and trading
remain outside this consumer.

## Frozen acceptance rule

All gates must pass independently before a separate wiring approval. Thresholds
cannot be relaxed after observing results. Unknown, partial, stale, incompatible
or unverified states remain unavailable; there is no fallback, price repair,
zero substitution, inferred session or promotion from synthetic/manual results.

The Dashboard therefore remains explicitly synthetic. No Streamlit, provider,
adapter or diagnostic code was changed. F&O remains last, hidden and unqualified.

## Subsequent documentation review

The owner supplied the account/application permission confirmation and authorized
a documentation-only prerequisite review. Its result is recorded in
`DASHBOARD_EQUITY_PREREQUISITE_REVIEW_V1`: current LTP meaning is resolved,
official NSE session sources are identified, REST currency remains unresolved,
and calendar/compliance implementations remain absent. This does not change the
overall not-eligible decision.

## Next separate decision

The smallest next scope is offline implementation of a versioned session-policy
contract and sanitized compliance-ledger contract using invented fixtures only.
It cannot make a market-data request or authorize Dashboard wiring. REST currency
binding remains a separate evidence prerequisite.

Only after those prerequisites are bound should the already proposed exact
two-request operational test be finalized for separate implementation/execution
approval. Dashboard wiring remains a later independent decision.
