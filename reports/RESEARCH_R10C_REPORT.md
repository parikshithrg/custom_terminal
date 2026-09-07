# R.10C synthetic security-event and terminal-economics reconstruction

## Result

R.10C validates provider-neutral software semantics for fictional security
events, identity continuity, non-destructive corporate-action treatment and
terminal economics. It is not evidence about real corporate actions, delisting
coverage, security populations, momentum, market performance or production
readiness.

The final implementation checkpoint is commit
`9737868493649b9c1484f460ebe32ab32dc6158d`. Evidence generation began from
that exact commit with an empty `git status --porcelain`; the root manifest
records `execution_start_dirty: false`.

## Contracts unified and reused

The implementation retains the older `SecurityRecord`, dated alias resolution,
corporate-action discontinuity classifier, terminal-reason enum, canonical
schemas, outcome materialization and R.10B incremental graph. No prior contract
or momentum definition was rewritten.

One new versioned layer supplies the missing shared semantics:

- source-specific immutable event vintages;
- separate issuer, listing and tradable-instrument identities;
- dated symbol assertions and predecessor/successor relationships;
- causal `known_at` and separate `effective_at` views;
- explicit verification, confidence and conflict states;
- declared ratio orientation and units;
- separately materialized adjustment factors and adjusted-price views;
- evidence-bound cash, share, mixed and fractional terminal proceeds;
- outcome reconciliation that retains every prediction.

## Event cases tested

The deterministic fixture contains a continuous-listing rename, 2-for-1 split,
3-for-2 bonus, cash-dividend marker, unresolved rights issue, share merger, cash
merger, mixed merger, parent-continuing demerger, suspension and resumption,
cash delisting, unresolved disappearance, relisting under new listing/security
IDs, unrelated ticker reuse, cancellation, corrected ratio, conflicting source
assertions, advance announcement and an event learned after its effective date.

All instruments, issuers, listings, sources and events are fictional.

## Point-in-time and identity results

- `ORBIT_OLD` and `ORBIT_NEW` resolve to `SYN_C_I001` only in their respective
  validity intervals, preserving the same instrument and listing through the
  rename.
- A later unrelated reuse of `ORBIT_OLD` resolves to `SYN_C_I013`, not the old
  instrument.
- The demerged child `SYN_C_I108` is absent before its creation/effective time.
- Relisting uses `SYN_C_I012` and `SYN_C_L012`; it does not bridge the old
  holding period automatically.
- Announcements are knowable after publication but do not become economically
  effective early.
- The late-published event is absent from prior knowledge snapshots even though
  its effective time has passed.
- Cancellation and correction vintages leave the earlier view reconstructible.
- Conflicting source assertions remain two rows marked `CONFLICT`; row order is
  never used to choose one.

Later disappearance or delisting does not erase earlier identity or universe
eligibility. Current aliases are not substituted into earlier dates.

## Corporate-action price treatment

Raw OHLC and volume are immutable. The raw logical-table SHA-256 is identical
before and after derived adjustment processing:

`1d1dcba3c546a7261530ca01b6c2525ef1ece8ee95bd39c407b154c6b75ae136`

The separately materialized backward factors are:

- split price factor: `0.5`, volume factor: `2.0`;
- bonus price factor: `0.6666666666666666`, volume factor: `1.5`.

Ratios explicitly mean `NEW_SHARES_PER_OLD_SHARES`. Dividends are not silently
folded into price returns. Rights remain unresolved. Mergers, demergers and
delistings are handled through terminal economics, not generic price factors.
Conflicting, unverified or cancelled actions block adjusted-series publication.

`momentum_12_1_v1` was not changed or retrofitted to use adjusted prices.

## Terminal-economic known answers

For 100 source shares:

- share merger: 40 successor shares at the declared historical settlement
  price of INR 50 = INR 2,000;
- cash merger: INR 120 per share = INR 12,000;
- mixed merger: INR 2,000 cash plus 25 successor shares at INR 80 = INR 4,000;
- demerger: 33 child shares at INR 60 plus exactly INR 10 cash in lieu of the
  fractional share = INR 1,990;
- cash delisting: INR 75 per share = INR 7,500.

The disappearance and rights issue remain `UNRESOLVED_TERMINAL`. A missing
successor price at the declared settlement time also remains unresolved. A last
quoted price is never considered terminal consideration. Zero recovery is
allowed only when explicitly declared by verified evidence.

Temporary suspension, unresolved disappearance, permanent delisting, merger,
relisting, ordinary missing data and right-censoring have distinct states.

## Outcome integration

Three prediction rows exist both before and after terminal reconciliation:

- one missing exit becomes `RESOLVED_TERMINAL` with INR 7,500 proceeds;
- one missing exit becomes `UNRESOLVED_TERMINAL`;
- one remains `RIGHT_CENSORED`.

No prediction is dropped and missing exits are never silently converted to zero
returns. Share successors continue value only under the declared conversion and
historical settlement-price policy.

## Incremental rebuilding

R.10B's dependency machinery was applied to announcement, effectiveness,
correction, cancellation, terminal consideration, conflicting evidence,
conflict resolution and ticker reuse.

Across 200 node decisions:

- 54 were `REBUILT_INPUT_CHANGED`;
- 146 were `REUSED_HASH_IDENTICAL`.

All eight incremental results match their independently built clean candidates,
and all unaffected hashes remain unchanged. A 2020 correction leaves the 2019
event-knowledge node unchanged. Terminal evidence rebuilds outcomes/economics
without rebuilding predictions. Split corrections rebuild adjusted features,
not raw prices. Ticker reuse is scoped to the new identity.

## Adversarial behavior

Named failures cover cyclic successors, simultaneous multiple issuers,
overlapping aliases, invalid intervals, negative cash, non-positive ratios,
missing ratio orientation, unknown currency, successor-before-creation,
duplicate event identities, supersession cycles, silent outcome omission,
current-alias leakage and final-state substitution. Conflicting terminal
classifications remain explicit conflicts.

## Evidence and verification

The approximately 196 KB evidence package contains four immutable raw object
groups, event vintages, identity graph, raw and adjusted price views, adjustment
factors, terminal results, before/after outcomes, rebuild plans and ledger,
known answers, failure matrix and a root manifest. The manifest binds the clean
implementation commit, source tree, environment, entry point, fixture and all
27 artifact hashes while referencing rather than duplicating R.10A/R.10B.

- Final R.10A-R.10C focused preservation and evidence suite: 88 passed.
- All 20 JSON and eight Parquet evidence objects parsed successfully.
- JSON and Parquet artifacts load and all declared hashes reconcile.
- R.10A root manifest remains
  `ec24fe04c895255e07433dde3068c7685b36a225a547fc749ce126d890f35580`.
- R.10B root manifest remains
  `316ced19c3d196aea0b0a404e51dbad3f3b0f732704cbd8d9813166244efabb2`.
- Momentum specification, golden fixture, R.9P and production interlock are
  unchanged.
- No APSW production dependency, private/real data, network, broker, UI, score,
  recommendation or trading path was added.

## Limitations

- Generic synthetic schemas do not claim official NSE compatibility. Official
  F&O format remains `PENDING_OFFICIAL_FORMAT_EVIDENCE`.
- Synthetic event evidence cannot establish completeness or correctness of real
  corporate-action and terminal datasets.
- The compact dependency evidence validates invalidation semantics; it does not
  perform genuine market backtesting.
- Monetary arithmetic is deterministic for the declared examples but a future
  production currency layer should use fixed-point decimal types.

## Next smallest synthetic task

Build an exchange-calendar and session-clock layer covering holidays, special
sessions, intraday publication cutoffs, settlement days and next-executable-
session rules. After that, begin multi-feature and score-contract machinery.

`SYNTHETIC_SECURITY_EVENT_RECONSTRUCTION_VALIDATED_NONCANONICAL`
