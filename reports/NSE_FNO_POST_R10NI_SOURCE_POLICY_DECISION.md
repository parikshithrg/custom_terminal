# Post-R10N-I bounded source-policy decision

Recommendation: select a separately authorized, documentation-only official-evidence investigation. Keep the route unqualified while it is proposed and while any question remains unresolved. Defer/unqualified is the safe alternative; an exception-policy design is not presently supported as a path to acceptance.

## What remains unresolved

R10N-G official evidence names daily opening/high/low/closing fields, separate traded quantity and settlement fields, last-half-hour weighted-average futures closing, and theoretical settlement for illiquid unexpired futures. It does not establish the exact UDiFF closing-price mapping or the common trade universe behind close, high/low and total quantity for these cases. Merely defining original/modified/cancelled/rejected/confirmed trade codes does not establish their contribution to aggregate OHLC. A weighted average over the same included trades would remain within their extrema; calculated closing alone is therefore not proof of a valid range exception.

R10N-F observes two nonzero-volume futures close-above-high cases on 2026-09-10. R10N-I establishes intact package bindings, stable schemas, 99,026 unique joins and matching expiries, and unchanged exact prices. Integrity does not prove economic correctness. The one `TRADE_STATE_ATTRIBUTION_UNAVAILABLE` diagnostic is date-level missing coverage, not a third anomalous row. MII expiry is resolved by R10N-H and must not be reopened based on older R10N-F/G findings.

Conservative project policy, not a documented exchange containment rule, keeps two `CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS` and one attribution diagnostic blocking. Absence of an official containment rule is not proof that these exceptions are valid. The passing 2026-09-09 and 2025-07-08 dates cannot compensate: every approved date must pass. The recorded overall result remains `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`.

## Bounded options

| Route | Evidence-based benefit | Limitation |
| --- | --- | --- |
| Defer; remain unqualified | Avoid unsupported acceptance and further external work | Does not resolve the missing semantics |
| Official-evidence investigation (recommended) | Seek applicable close-field mapping and trade-contribution rules | Authority may remain silent; general rules may not prove these cases |
| Versioned exception-policy design only | Specify uncertainty, provenance and consumer restrictions for owner review | Owner preference cannot establish exchange intent; unknown cases remain blocking |

The proposed investigation is limited to five fixed official documentation URLs already listed in R10N-G, eight HTTP transactions including redirects, no retries, 4 MiB per response and 8 MiB total, and one 30-minute session. It seeks effective-date-specific close basis, trade-state inclusion and case applicability. It excludes report endpoints, trade files, contact messages, new dates and archive enumeration. Exact URLs, content/expansion limits, permission and retention controls, and fail-closed stopping conditions are in `investigation_proposal.json`. No external request is authorized or performed here. Any new link, document or official contact needs a scope amendment. Insufficient authority ends unresolved, not qualified.

The alternative `exception_policy_proposal.json` is design-only: existing values/codes remain untouched and blocking; authority and owner policy have separate provenance; unresolved cases cannot feed production, ingestion, research or trading. Version/source/schema changes, conflicting authority, unsupported applicability or expired retention invalidate the design. Scope, authority, no-mutation, unknown-state, all-dates, consumer-denial and invalidation tests are required before separately authorized implementation and requalification. No waiver or reinterpretation of R10N-I is proposed.

## Independent owner decisions

1. Accept or decline the R10N-I aggregate evidence, including the unqualified result.
2. Select the next source-policy route. Selection alone does not authorize execution.
3. Clarify the 2026-09-09 anchor deadline explicitly as YYYY-MM-DD and its closeout trigger; no R10N-E deadline is recorded. The prior general year-end preference is not silently applied.
4. Separately authorize or decline each package deletion by date and verified exact path.

The two R10N-E deadlines remain 2026-12-31. Their earlier-of-deadline-or-owner-acceptance trigger can become applicable when hash-bound aggregate evidence is accepted, even though the source remains unqualified. That trigger establishes closeout eligibility, not permission to delete. Acceptance is pending; no deletion, deadline change or retained-package row access occurs in this task. Actual deletion requires separate explicit authorization and exact-path/binding verification.

## Separate proposed execution scope — stop before execution

Owner decision needed: choose the official-evidence route and independently answer the evidence, anchor-retention and deletion questions. Later execution needs a separate approval of the exact documentation-only limits and review-copy permission/retention controls in the proposal. Its only deliverable is a sanitized authoritative-versus-unresolved closeout; no adapter changes, new qualification result, ingestion, fingerprint refresh, research or production activation. Implementation and all-three-date requalification, if justified, need further separate authorization.
