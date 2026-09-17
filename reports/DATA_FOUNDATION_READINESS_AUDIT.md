# Data-foundation readiness audit

Recorded 2026-09-17 against `2332e136932e1d68e72816ea581a42b791667104`.
Baseline matched; initial worktree clean. Documentation-only audit: no UI,
provider, adapter, gate or application behavior changes. The owner-approved
visual baseline is preserved; visual refinement is paused.

## Decision

The terminal has a usable synthetic interface, tested offline data contracts,
and a narrowly scoped manual current-data implementation. It does not yet have
a verified, consumer-approved real source for the Dashboard. Recommend an
offline **Dashboard watchlist read-model contract v1**, using synthetic fixtures
only and without UI wiring. Code existence is not operational qualification.

## Visible capability map

Requirements below describe what each advertised page would need, not approved
acquisition scopes. History windows and update frequencies outside the proposed
single consumer are not frozen. References are repository-relative.

| Visible consumer | Required data and history | Actual code/local capability | Readiness and boundary |
|---|---|---|---|
| Dashboard | Index levels and changes; watchlist identity, price and change basis; as-of and source state. Current snapshot; prior reference session needed for changes. | `views/home.py`, `_market_preview.py`: static index and equity/futures fixtures; radio changes presentation only. | SYNTHETIC. No retrieval, observation timestamp, market freshness or real coverage claim. |
| Market & Sector Context | Session OHLCV, official turnover, PIT population and sector membership, index/volatility series; multi-session trend/rotation history. | `td_market_sector_context.py` is a multi-tab stub. Foundation identity/calendar/prices and synthetic research helpers exist, not a qualified page provider. | IMPLEMENTED-BUT-UNWIRED infrastructure; page data ABSENT. Historical universe and source eligibility blocked. |
| Setup Scanner | PIT equity/contract identities, OHLCV, turnover, membership and indicator lookback; daily history plus current session where applicable. | `mg_screener.py` stub; research modules are separate from the page. | ABSENT page data. No approved scanner consumer, scoring or research activation. |
| Asset Allocation & Protection | Positions, quantities, cash flows, cost/currency, asset classes, valuation history, policy limits and risk-reference series. | `inv_asset_allocation.py`: three unavailable-state tabs; portfolio contracts/engine exist separately. | ABSENT account/portfolio input and page adapter. Market prices alone cannot supply personal positions or policy. |
| Performance & Benchmarks | Dated portfolio valuations/cash flows, fees, currency, benchmark PRI/TRI and aligned sessions; inception/YTD history. | `inv_performance_benchmarks.py` stub; foundation benchmark and portfolio infrastructure unwired. | ABSENT page data. Unverified benchmark methodology/history must not become performance evidence. |
| Goal Tracker | Owner goals, deadline/currency, corpus, contributions, inflation/return assumptions and valuation as-of. | `inv_goal_tracker.py` stub. | ABSENT owner-input contract; no account access or assumptions approved by page existence. |
| News & Calendar | Publisher-attributed articles with publication/retrieval times and reuse rights; event identity, announced/effective dates and revisions; current feeds/forward events, historical vintages for PIT use. | `news_feed_calendar.py` automatically calls `_news_data.py`: 11 RSS sources, VADER-derived sentiment, unofficial NSE board-meeting/corporate-action fetches. Cache TTL 600/1800 seconds; calendar defaults to 30 days ahead. | LEGACY IMPLEMENTED/WIRED, NOT VERIFIED FOR CURRENT GOVERNED USE. Fetch-on-page-load exists; no fresh operational or rights verification. Not run in this audit. |
| Event Risk Assessment | Versioned volatility/FX/gold series, dated breadth population, news history and methodology; positions for impact mapping. | `news_event_risk.py` calls `_blackswan_data.py`: five Yahoo series, roughly one-year inputs, external Dashboard breadth loader, RSS sentiment and local sentiment-log writes. Portfolio mapper is a stub. | LEGACY IMPLEMENTED/WIRED, BLOCKED for new use. Composite/provisional scales are not validated source or research guarantees. Opening may fetch, read external files, score and write state. Not run. |
| Correlation Explorer | Aligned cross-market/asset returns, currency/units, session calendars, adjustment and benchmark methodology; rolling-window history. | `lib_correlation_explorer.py` multi-tab stub. | ABSENT qualified provider/page wiring; Yahoo coverage is not established by registry descriptions. |
| Data Coverage | Current identity inventory, chosen quotes/OHLC/LTP, session/entitlement, retrieval/provider time, missingness and cache age. | `lib_data_coverage.py` manual Kite login/validation/inventory/selected snapshot and pure health functions. | MANUALLY AVAILABLE implementation, not live-verified here. Existing scope only; no transfer of authorization to Dashboard, history or research. |
| Market Gate Home | Ultimately qualified regime inputs, score methodology and pipeline state/history. | `lib_market_gate_home.py` currently renders the same synthetic preview/readiness component, not a real composite score. | SYNTHETIC. No market-gate qualification or scoring claim. |
| Lab | Qualified PIT datasets, hypothesis/input bindings, costs, execution/calendar rules and approved research scope. | `mg_lab.py` stub; offline research infrastructure exists separately. | IMPLEMENTED-BUT-UNWIRED engine, BLOCKED real-data research. No experiment launched. |
| Backtesting Framework | Same qualified research inputs, frozen configuration, lineage, costs, calendar and approval evidence. | `research_backtest_framework.py` stub; overlap with Lab remains recorded. | IMPLEMENTED-BUT-UNWIRED infrastructure, BLOCKED real-data research. No engine consolidation proposed here. |
| Seasonality | PIT prices/calendar, adjustments, listing/terminal coverage and sufficient predeclared seasonal samples. | `mg_seasonality.py` stub. | ABSENT page data and approved study. Three retained F&O dates cannot supply seasonal history. |
| Reports | Exact retained report files, publisher/run provenance, generated date, input/manifests and interpretation status. | `lib_reports.py` reads three legacy Data-test CSV result files on page load; one-hour cache, hard-coded narrative and dated report catalogue. | IMPLEMENTED historical-file renderer; file availability/hashes and current governance compatibility NOT VERIFIED. Historical narrative is not source qualification or fresh research. No report data read here. |

There are 14 visible registry pages plus Dashboard. Four registry entries stay
hidden with their source/metadata retained: Trade Decision Helper, Options &
Positioning, Trade Management, and the standalone Risk & Capital Protection
page. The last is folded into the visible asset page; no further filtering occurs.

## Guarantees actually supported, and gaps

- **Current Kite** (`foundation/current_market.py`, `kite_connect.py`,
  `kite_current_market.py`, `current_market_health.py`): in-process daily session;
  read-client GET allowlist for profile, instruments, quote, OHLC and LTP;
  maximum 25 selected inventory keys, 20-second request timeout, 15-second quote
  cache and five-second UI manual cooldown. Login token exchange is distinct
  from the GET-only read client. No new login/request was made.
- Inventory identity is provider token plus exchange/symbol/segment/type and
  derivative metadata, **not** a permanent historical security master. Snapshots
  carry provider, endpoint, retrieval time, parser version (inventory), session
  date and `CURRENT_TRADABLE_ONLY`; historical-universe conversion raises.
  The client derives inventory session date from its clock, not a verified NSE
  trading session. Diagnostics count duplicates, incomplete rows and expiries;
  reporting those counts does not certify inventory completeness or reject all
  bad rows. Numeric float conversion is not a comprehensive finite-value,
  Decimal-precision or field-semantic validation guarantee.
- Quotes preserve explicit missing rows and provider timestamps when supplied;
  retrieval time is not exchange event time. Freshness/cache labels and provider
  age are implemented, but timestamp presence flags are not proof of valid
  timestamps for every row. Stale cache can be returned on temporary failure;
  entitlement/session errors are not hidden by that fallback. `CLEAR` health
  means no classified error, **not** licensing permission. Data Coverage passes
  `calendar=None`, so market session remains UNKNOWN. No maintained current
  holiday calendar or operational session is verified here.
- **Historical neutral foundation** (`providers.py`, `contracts.py`,
  `research_data.py`, `acceptance.py`, `quality.py`, `source_registry.py`): typed
  datasets, manifest/provenance hashes, PIT revision/availability contracts,
  effective-dated aliases and capability gates exist and are offline tested.
  Required UNKNOWN/FAIL capabilities cannot promote. This does not establish
  real-provider rights, historical coverage or current fingerprint validity.
- `LocalAuditedFileProvider` is a dry-run adapter, not an eligible historical
  source: unresolved listing identity, unknown series/upstream rights, missing
  publication timing/turnover and absent authoritative actions/terminal outcomes.
  `DATASET_TRUST_REPORT.md` records survivor-selection and research rejection.
  Historical coverage figures in that report are prior evidence, not refreshed
  measurements; no local market file/database was opened.
- **Legacy exceptions to a mock-first interpretation**: News & Calendar and
  Event Risk Assessment are not offline placeholders. Their caches are not
  freshness/permission guarantees; naive timestamps, silent empty-on-error
  behavior, undocumented NSE calls, absent immutable payload bindings and
  cross-project reads prevent a readiness claim. Reports renders old results
  rather than running a backtest, but its narrative is not verified lineage.
  UI tests exercise Dashboard only and do not certify these other pages as safe
  offline. Before broader product use, separately authorize gating/remediation
  of these legacy execution paths. This audit does not silently change them.

## NSE and research lifecycle

`NSE_FNO_QUARANTINE_EXECUTION.md` and the latest alternative proposal remain
authoritative for this route: all 99,026 original facts are immutable, two
contract-dates were quarantined, zero-loss thresholds classify coverage loss as
material, and date-level `TRADE_STATE_ATTRIBUTION_UNAVAILABLE` restricts the
whole affected population. Removing two rows does not resolve trade coverage.
Original status remains `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`;
experimental outputs cannot feed UI or research. Expiry decoding is resolved.

The latest proposal completion has no selected external route/executable scope
and records `NOT_EVALUATED_NO_AUTHORIZED_EVIDENCE`. No registered incoming
provider-attributed owner export was identified in the reviewed records. The
owner subsequently chose to defer; do not repeat the proposal or inspect private
targets. Retention remains 2026-12-31 for authorized reacquired evidence; no
retention change, restoration, comparison or deletion is performed.

README's governed research gateway requires input bindings, preregistration,
review/fingerprint and run-specific approval. Connector availability, passing
unit tests, synthetic infrastructure and owner acceptance of aggregate evidence
are not acquisition, interpretation, qualification or research permissions.
The owner development sequence still requires a product/data-requirements freeze
and separate real-data authorization; visual acceptance alone does not supply it.

## Next milestone and priorities

1. Build the source-independent Dashboard watchlist read model described in
   `docs/project_status/NEXT_DATA_FOUNDATION_BUILD_PROMPT.md`, with synthetic
   fixtures only. No UI wiring, source access, scores or market-readiness claim.
2. Separately authorize a scope for explicit offline/readiness gating of the
   legacy news/risk/report paths before treating the whole app as mock-first.
3. Freeze one real consumer's data requirements and obtain source-specific rights,
   eligibility and access authorization before proposing real activation. NSE
   alternative corroboration stays deferred unless its missing prerequisites change.

Owner decision needed before the next build: approve this single-consumer,
offline synthetic implementation and its stated exclusions. No real-source
credential, export, provider access or policy waiver is required for that build.

## Validation actually performed

132 existing offline tests passed: UI preview, current health, Kite session and
current client (injected fake HTTP), ingestion readiness (temporary fixtures),
temporal contracts, alternative proposal, isolated quarantine, protocol/policy
governance and R10N-H/I tests. A uniquely isolated temporary test directory was
used. UI AppTest ran Dashboard and changed its synthetic watchlist selector only.
No news/risk/report page was executed; no network request or market payload was
acquired. Existing sealed-evidence governance checks passed. Full root suite,
known stale research-fingerprint and R9K timing failures were not rerun, fixed or
refreshed. Registry-to-report validation confirmed all 14 visible registry pages
plus Dashboard and four retained hidden entries. Proposed-only scope assertions,
private-path/credential-pattern checks and diff checks passed. Final review
showed only the two new audit/prompt Markdown files changed; application and
historical evidence files remain byte-exact. No new manifest/JSON package was
created; existing manifest/hash governance checks were exercised by the tests.

Evidence anchors: `README.md`, `app.py`, `views/_registry.py`, all visible page
modules named above, `_market_preview.py`, `_news_data.py`, `_blackswan_data.py`,
foundation files named above, `OWNER_DEVELOPMENT_SEQUENCE_V1.md`,
`NSE_FNO_ALTERNATIVE_EVIDENCE_PROPOSAL.md` and `NSE_FNO_QUARANTINE_EXECUTION.md`.
Only repository code/docs and offline fixtures were inspected/exercised.
