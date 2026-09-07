# R.10D — Synthetic exchange calendar, session clock and executable-time semantics

## Result

R.10D validates the synthetic time and scheduling machinery. It does not
validate an official NSE calendar, real market data, an edge, a score or
production readiness.

Authoritative implementation checkpoint:
`447bf403fd4eb19b5d72b1cc2db9a7b1c7aa6698`.

## Existing assumptions discovered

- The legacy outcome engine uses the price panel index as its calendar and
  advances by positional rows.
- Earlier synthetic fixtures use `bdate_range` to generate weekday dates.
- Existing fold construction operates on a supplied index but does not bind it
  to a typed venue/calendar version.
- Existing v1 outcome language assumes next open and 21 sessions, while its
  implementation relies on the price-frame index to define those sessions.
- R.10C event economics preserve timezone-aware effective and settlement
  instants, but previously had no venue-session resolver.

These paths were not silently rewritten. The golden-compatible
`next_open_21_session_excess_v1` remains unchanged. New calendar-aware behavior
is versioned as `next_open_21_venue_session_excess_v2`.

## Contracts added

- `synthetic_exchange_calendar_r10d_v1`: typed daily assertions, revisions,
  venue, timezone, local date, UTC boundaries, eligibility, occurrence,
  provenance and conflicts.
- `synthetic_session_clocks_r10d_v1`: enumerated pre-open, open, close,
  post-close, next-executable-open and explicit intraday clocks.
- Dataset-specific availability policies combining publication, processing lag,
  precision, knowledge cutoff and calendar state.
- Shared next/nth/previous session resolution with named failure statuses.
- Exact cross-sectional decision bindings to one calendar version, session ID,
  clock and UTC instant.
- Session-ordinal outcome and fold scheduling.
- `synthetic_settlement_rules_r10d_v1`, separate from the trading calendar,
  with dated T+2/T+1 rules and distinct cash/share legs.

All contract-boundary instants reject naive timestamps. `retrieved_at` is
provenance and cannot advance economic availability before `published_at`.
Date-only evidence uses the conservative next-executable-session-open policy.

## Fictional calendar cases

The generated fixture spans 27 November 2019 through 13 May 2020, beginning and
ending midweek. Its 174 vintage rows resolve to 169 final dated assertions. It
includes normal sessions, weekends, full-day and consecutive holidays, a
special weekend session, shortened and delayed sessions, an unexpected closure,
advance and late announcements, a future revision, a non-session month-end,
year boundary and leap day. These dates are fictional and are not called or
treated as official exchange dates.

## Point-in-time and known answers

- Local 09:15 Asia/Kolkata maps to 03:45 UTC.
- The shortened session closes at 07:00 UTC.
- November 2019 month-end resolves to the final eligible session, 29 November.
- The explicit leap-day special session is included once.
- Before its announcement, the fictional 27 January holiday is scheduled as
  tradable; after publication, it is excluded.
- The unexpected closure is absent from the earlier plan and appears only after
  its late correction.
- Next entry after the 24 January close is 28 January.
- The 21st subsequent executable session is 28 February; distance is exactly 21.
- Publication available exactly at an inclusive cutoff is admitted; one instant
  after the boundary is not.
- Conflicting active source assertions remain visible and block scheduling.

## Outcome, feature/universe and fold effects

The v2 outcome path uses one venue calendar for instruments and benchmark.
Missing instrument bars do not shift the entry or exit date. Suspensions,
not-yet-listed instruments, terminations, missing prices and right censoring are
distinct named states. Special and shortened sessions count only because the
explicit calendar marks them eligible.

Every session-aware cross-section must share the same version, venue, session,
clock and UTC decision instant. A delayed publication cannot enter the snapshot
until its dataset-specific availability rule is satisfied.

The declared 21-session holding horizon plus next-open boundary produces the
existing 22-session purge/embargo rule. The evidence fold ends training on 2
January and begins validation after embargo on 10 March, using explicit session
ordinals rather than calendar days.

## Settlement and security events

- Fictional T+2 from 30 January skips a settlement closure and consecutive
  holidays, settling 6 February.
- The later T+1 rule settles a 2 March trade on 3 March.
- Corporate-action cash and shares may settle on separate sessions (4 and 5
  March in the fixture).
- R.10C announcement, effectiveness, trading and settlement instants remain
  separate.
- An event effective on a non-session resolves only through an explicit
  next-session policy.
- Relisting retains its successor identity and does not bridge the predecessor.
- Terminal economics and raw event evidence were not altered.

## Incremental behavior

Six changes were evaluated: future holiday, unexpected closure, corrected
session time, added special session, settlement-rule change and publication-time
correction. All six incremental results equal their clean rebuilds and preserve
all unaffected hashes. The ledger contains 14 causal rebuilds and 142
hash-verified reuses. Settlement changes do not invalidate signals or outcomes
that do not consume settlement.

## Verification

- Direct R.10D tests: 40 passed.
- Focused R.10A-R.10D preservation suite: 116 passed.
- Isolated slow R.10A pipeline suite: 15 passed.
- Evidence package: 12 files, approximately 134 KB; 11 declared artifact hashes.
- Three Parquet and nine JSON objects parse successfully.
- Prior R.10A, R.10B and R.10C root manifests, momentum specification and golden
  fixture hashes remain unchanged.
- No APSW production dependency, interlock change, network, private/real data,
  broker, genuine backtest, market score or trading path was added.
- Secret/private-path and Git whitespace checks pass.

## Limitations

- The baseline fixture recipe seeds normal weekdays and weekends before applying
  explicit fictional exceptions. Downstream session-aware code never uses a
  weekday fallback.
- Synthetic coverage cannot establish official holidays, session phases,
  correction practices, settlement operations or publication timing.
- The v2 outcome scheduler proves timing/status semantics, not investment
  performance.
- Real calendar ingestion and exchange compatibility remain untested and are
  prohibited without the later owner-authorized transition.

## Next task

Proceed to `MULTI_FEATURE_EVIDENCE_AND_SCORE_SEMANTICS`, remaining synthetic and
noncanonical. Before any private/real-data transition, genuine market analysis,
score publication, APSW adoption or interlock change, stop for the consolidated
PDF and explicit owner authorization.

`SYNTHETIC_SESSION_CLOCK_VALIDATED_NONCANONICAL`
