# Equity session and compliance contracts v1

Implemented 2026-09-22 under the owner's approval to build the previously proposed
offline session-policy and sanitized compliance-ledger milestone. The implementation
uses invented fixtures and caller-supplied dates and times only. It performs no
provider request, UI wiring, persistence, research or trading.

## Cash-session policy

`equity_cash_session_policy_v1` accepts a versioned, timezone-aware sequence of
explicit calendar-date declarations. Every date inside its coverage range must be
present and classified as `NORMAL`, `CLOSED` or `SPECIAL`. Trading declarations
require aware open and close clocks that resolve to the declared date in
`Asia/Kolkata`; closed dates cannot imply trading clocks.

The resolver never infers sessions from weekdays. Dates outside declared coverage
return `UNKNOWN_DATE`; evaluation after the caller-supplied validity boundary
returns `CALENDAR_EXPIRED`. Both states fail closed. The deterministic result is
bound to the calendar hash and remains `SYNTHETIC_NOT_MARKET_READY`.

This contract can later consume a separately authorized and maintained official
calendar, but the included calendar is invented test data. It does not establish
the actual NSE session for any date and cannot authorize a market-data request or
Dashboard display.

## Sanitized compliance record

`equity_compliance_ledger_v1` creates one immutable, deterministic aggregate record
from invented request metadata. It records only:

- contract, policy and code versions;
- caller-supplied start, completion and recording clocks plus derived duration;
- a generic synthetic endpoint category;
- request, requested, returned, missing and unavailable counts;
- total response-byte count, sanitized outcome/reason codes; and
- a hash binding to a resolved session policy.

The record contains no credentials, account or instrument identities, prices,
response body, sensitive headers or private path. It fixes cache policy to
`TRANSIENT_MEMORY_ONLY`, retains no raw payload, and grants no permission to
persist, request data, expose data, conduct research or activate production.
Unknown or expired session resolutions cannot support a record.

## Remaining Dashboard gates

This milestone proves offline contract behavior only. Dashboard wiring remains
blocked pending authoritative REST NSE-EQ currency/unit binding, an official and
maintained calendar input process, an owner-reviewed provider-specific compliance
retention decision, exact live target binding, bounded operational validation and
separate consumer/display approval. Existing synthetic/manual results do not
qualify the source. F&O remains hidden, deferred and unqualified.

## Validation target

Focused tests cover deterministic bytes and hashes, immutability, explicit normal,
closed and special dates, unknown and expired coverage, timezone/order errors,
bounds and aggregate reconciliation, sanitized fields, unresolved-session refusal,
promotion refusal, and absence of network, file/database, wall-clock, provider and
Streamlit dependencies.
