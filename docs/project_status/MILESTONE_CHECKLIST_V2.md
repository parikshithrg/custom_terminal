# Market terminal milestone checklist v2

Updated 2026-09-18 against application baseline `94cdcf4`. This editable checklist
extends the earlier printable checklist with the owner's requested reference
inspirations. It does not replace sealed milestone evidence or grant implementation,
provider access, retention, research, scheduling, or trading authorization.
The earlier PDF and roadmap image are historical snapshots, not regenerated here.

## Covered

- [x] Architecture, data contracts, source governance and synthetic research infrastructure.
- [x] NSE F&O investigation, requalification and quarantine audit; source remains unqualified.
- [x] Alternative F&O corroboration proposal; evidence route deferred.
- [x] Website skeleton and owner-approved visual baseline; visual refinement paused.
- [x] Equity-first priorities and hidden derivative-dependent features.
- [x] Data-readiness audit, non-F&O consumer requirements and legacy-news execution gate.
- [x] Synthetic equity watchlist contract and Dashboard integration.
- [x] Offline equity parsing, freshness/readiness checks and combined validation pipeline.
- [x] Manual Kite login, owner-supplied NIFTY 50 CSV and two-batch manual quote controls.
- [x] Owner-reported manual result: 50 returned, zero missing; not source qualification.
- [x] Offline exact-price Kite decoder, separate clocks, completion timing and two-decimal display.
- [x] Bounded exact-price live-test proposal; transport implementation and execution still gated.

## Upcoming — equity-first priority order

All unchecked items are planned, not executed or authorized by this checklist.

1. [x] **Freeze the equity consumer requirements and acceptance matrix.** The
   `DASHBOARD_EQUITY_DISPLAY_ELIGIBILITY_V1` decision binds the exact current-EQ
   universe and fields plus independent identity, currency, adjustment, session,
   permission, freshness, quality, retention and operational gates. All must pass
   before separate wiring approval; coverage cannot override another gate and
   thresholds cannot be revised after results. Current decision is not eligible.
2. [ ] **Resolve the existing exact-price live-test prerequisites.** Bind account
   entitlement, private transient processing and compliance obligations; obtain
   explicit approval of the committed two-request scope and local target binding.
3. [ ] **Implement and test the bounded exact-price live transport/manual controls.**
   Only under separately approved scope; preserve immutable Decimal facts,
   timestamps, budgets, no fallback/retry and transactional combined reporting.
4. [ ] **Run the separately approved exact 50-equity operational test.** Report
   requested/returned/missing/unavailable/stale counts truthfully. Complete
   coverage cannot override permission, clock, session or semantic gates.
5. [x] **Build an offline Daily Equity Data Health read model.** Implemented in
   `daily_equity_data_health_v1` with synthetic fixtures only. It reuses existing
   readiness results and emits sanitized aggregate counts, separate clock ranges,
   fixture session status, last-successful-refresh and blocking reasons. It is
   deterministic, in-memory, never market-ready and not wired into the UI.
   The original planned boundary was: start with
   synthetic fixtures and caller-injected time. One consumer; expose session
   status (without account identifiers), counts, separate provider/retrieval
   clocks, inventory age, last successful refresh and explicit blocking reasons.
   Unknown, expired, stale, incomplete and unavailable states must be tested.
6. [x] **Add a sanitized validation/refresh ledger contract.** Implemented as an
   in-memory, deterministic synthetic contract binding contract, code,
   configuration and policy versions, permitted input hashes, aggregate counts and
   rejection reasons. Evidence classification is explicit; manual, provider,
   historical, quarantined and claimed verified modes fail closed. It contains no
   credentials, raw quotes, instrument inventories or private paths and grants no
   persistence, refresh, activation, research or production authority. Aggregate
   or hash persistence still needs a separately approved provider-specific record
   and retention policy.
7. [x] **Add read-only equity quality diagnostics and stronger fixtures.** The
   aggregate diagnostic extends existing readiness output and covers implicated
   duplicates, declared-universe gaps, malformed identity refusal,
   missing/invalid/nonfinite prices, timestamps, incompatible semantics and source
   failures. Gap checks require an explicit synthetic session: non-trading days
   are not counted as missing and unknown sessions remain indeterminate. Original
   facts stay immutable; interpolation, repair, zero substitution, silent duplicate
   removal, gap filling and provider selection are all unavailable.
8. [ ] **Wire eligible equity prices and data-health states into Dashboard.**
   Separate consumer/display approval and currency, adjustment and session
   evidence required. Keep the approved visual baseline and display rounding;
   do not silently promote synthetic fixtures or quarantine data. Eligibility
   decision v1 is prepared and remains blocked on every frozen prerequisite; no
   wiring or provider request has occurred.
9. [ ] **Add separately approved cash-index tiles and change calculations.**
   Explicit previous-close basis, units, as-of and unavailable behavior; no
   derivative-dependent inputs or implied permission from equity access.
10. [ ] **Qualify equity history, corporate actions and effective-dated sectors.**
    Include historical membership/delistings and point-in-time provenance where
    required. Existing desktop CSVs are candidates, not qualified sources.
11. [ ] **Complete Market & Sector Context and Setup Scanner with eligible inputs.**
    Each calculation needs explicit semantics and test coverage; scoring or
    recommendations remain separately research-gated, not ordinary UI wiring.
12. [ ] **Build owner-input allocation, portfolio and goal features.** Keep manual
    inputs distinct from provider facts; use existing accounting/contracts first.
    A core/short-term allocation split is an optional future representation, not
    a prescribed investment strategy. Hidden Trade Management stays hidden.
13. [ ] **Validate performance, benchmarks and explanatory charts.** Handle cash
    flows, fees, dividends, return basis, periods and missing benchmarks explicitly.
    Borrow chart layouts, not the reference toolkit's dark theme or demo returns.
    Drawdown/recovery and correlation require suitable, aligned eligible data.
14. [ ] **Activate approved News & Calendar sources.** Publisher rights, timestamps,
    lineage and consumer gates first. Summaries must distinguish source statements
    from inference; news-driven signals/allocation are not part of this milestone.
15. [ ] **Complete integration, security, storage and failure-handling checks.**
    Test token expiry, reconnects, partial responses, unavailable feeds and privacy.
    Avoid duplicate full datasets; track storage growth. Propose scheduled health
    checks only separately, with exchange-calendar/timezone, request, retention and
    notification controls. No unattended acquisition authorized by roadmap entry.
16. [ ] **Deploy the private functioning non-F&O terminal within provider permissions.**
    Deployment readiness is operational, not proof of strategy profitability.

## Later, separately gated

- [ ] **Research validation improvements**, only after eligible history and explicit
  research authorization: freeze hypotheses, benchmarks, costs and search budgets;
  log every trial, account for multiple testing, protect a final untouched holdout,
  and test parameter robustness. Repeated holdout-driven tuning invalidates its
  untouched status. AI historical-news interpretation needs contamination controls;
  hiding dates alone is insufficient. No overnight strategy search approved here.
- [ ] **LAST — F&O semantics, alternative evidence and source qualification**, after
  a functioning non-F&O site. Route stays
  `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`; quarantine outputs cannot feed
  UI or research. Preserve diagnostics, all-dates acceptance and the existing
  2026-12-31 retention deadline. Restoration/requalification requires separate scope.

Automated order placement, leverage, copy trading and crypto/DeFi tools are not
added to the build scope. Owner approval is not authoritative source evidence.

## Reference assessment

The locally reviewed Claude Trading Skills collection supplies example diagnostics,
synthetic anomaly fixtures and later analytics/chart patterns; code reuse requires
its MIT notice and independent tests. Its mutating cleaning/merging defaults are
not adopted. The video's process/ledger/operational-check ideas are inspiration,
not verified performance evidence: [video](https://www.youtube.com/watch?v=TVNOTqv0n1k).

Next useful step: **resolve the frozen Dashboard display prerequisites** through
owner account/permission confirmation and a bounded official-documentation review
of currency/units, current-price adjustment meaning, session-calendar handling and
cache/compliance controls. This remains separate from live testing and UI wiring.

2026-09-19 update: the owner account/application confirmation and bounded official
documentation review are complete. Current LTP semantics are resolved for a
current-only display; official NSE session sources are identified. REST NSE-EQ
currency remains unresolved, and maintained calendar plus sanitized compliance-
ledger implementations remain separately gated. Dashboard wiring stays blocked.
