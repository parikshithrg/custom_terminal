# R.10D implementation boundary

R.10D adds a provider-neutral, synthetic-only calendar and session-clock layer.
It does not change the legacy `next_open_21_session_excess_v1` contract. A new
`next_open_21_venue_session_excess_v2` path is used to prove explicit venue
session scheduling while preserving the golden fixture.

Implemented contracts:

- versioned point-in-time calendar assertions and revisions;
- canonical UTC instants with `Asia/Kolkata` local trading dates;
- typed decision clocks and exact boundary inclusivity;
- dataset-specific publication and processing-lag policies;
- next, nth and previous executable-session resolution;
- explicit session-ordinal outcome and fold scheduling;
- separate dated settlement rules and cash/share settlement legs;
- shared cross-sectional decision-clock validation;
- R.10B causal rebuild planning for calendar, publication and settlement changes;
- R.10C event effectiveness and settlement-clock integration.

The fixture, dates, venue and answers are fictional. No official NSE calendar,
real data, broker, score, market analysis, APSW production dependency or
production-interlock change is included.
