# Non-F&O consumer requirements v1 — offline planning freeze

Recorded 2026-09-17 after the owner requested “build the next milestone”, bound
to the proposed legacy-news execution/readiness gate and requirements scope in
`DASHBOARD_WATCHLIST_CONTRACT_V1.md`. Baseline
`a71bf65b014ad9513c1f7c101c48fa086abe0df6`; initial worktree clean.
This records implementation scope, not provider/retention/research permission.
Frozen v1 requirements are offline design targets, not claims of available data.
Owner review is still required before any real-consumer/source activation.

## Common contract requirements

Every future non-synthetic consumer must bind source/publisher, exact consumer
and fields, rights/retention evidence, parser/dataset version, immutable payload
hash and record identity. Prices need declared currency/units/adjustment basis;
historical equity identity needs effective-dated listing/security/alias evidence,
not today's ticker list. Dates cannot masquerade as event/publication times.
Timestamps must be timezone-aware with event/publication/retrieval and explicit
availability/knowledge-cutoff semantics. Unknown provider time/calendar stays
unknown, not replaced with the retrieval clock. Revisions retain earlier facts.

Missing/partial/stale/blocked inputs need named states; never fill prices with
zero, infer quantities, silently forward-fill across sessions, relax diagnostics
or promote a source to make panels appear populated. Failure and empty source
results are distinct. Cache TTL is not freshness evidence. No registered eligible
new real source/consumer, operational session or source-specific reuse permission
is established by this freeze. Manual Data Coverage remains its existing scope.

## Retained consumers and minimum data targets

History/frequency below are requirements, not authorizations for downloads.
Provider-specific thresholds, exact historical ranges and computation methods
must be separately frozen before real use; until then the consumer is unavailable.

| Consumer | Required fields beyond common provenance/time/state | History/update need | Current eligibility |
|---|---|---|---|
| Dashboard equity watchlist | Synthetic contract's exact fields: simulated identity/class/label, currency, Decimal last_price and missingness. Change% remains outside v1. | Caller-injected synthetic snapshot only. | Offline contract complete, not yet wired. No real Dashboard source approved. |
| Dashboard index overview | Cash-index ID, level, reference-session close, currency/units, index methodology/classification; change basis. VIX tile stays synthetic. | Explicit prior reference session plus as-of snapshot; refresh budget pending. | Existing synthetic tiles only; no provider access. |
| Market & Sector Context | Listing ID, session OHLCV, exchange turnover, PIT equity population, effective-dated sector membership, cash-index references. | Trend/rotation lookbacks must be frozen with method; daily aligned sessions. | Unwired; historical population, semantics and rights missing. |
| Setup Scanner | Same equity identity/session OHLCV/turnover/population; rule version and field-level quality. | Exact indicator lookback/rules and update cadence pending owner review. | Unwired; no scores, recommendations or research authorized. |
| Asset Allocation & Protection | Owner positions, quantities/currency, cash flows, valuation, asset class, policy limits, benchmark exposures. | Valuation history and risk window pending portfolio scope. | Owner inputs absent; no account integration or inferred holdings. |
| Performance & Benchmarks | Dated valuations/contributions/withdrawals/fees, benchmark PRI/TRI and methodology, currency, aligned cash sessions. | Inception and YTD; return methodology/flow handling pending. | Unwired; benchmark and portfolio provenance not verified. |
| Goal Tracker | Goal ID, currency, target date/corpus, contributions, owner assumptions, valuation as-of. | Owner-input revisions; no market-data update implied. | Inputs/assumptions unbound. |
| News & Calendar | Frozen article/event fields below; publisher and rights, authoritative revisions, availability state. | Bounded latest article snapshot and <=30-day forward event view; no crawl/history acquisition. | New offline unavailable shell; legacy automatic execution disabled. |
| Correlation Explorer | Approved non-derivative asset IDs, aligned returns/currency/adjustment, session/timezone calendars and methodology. | Predeclared rolling-window length and aligned observations, not sparse F&O dates. | Unwired; no qualified multi-asset feed. |
| Market Gate Home | Qualified equity/index inputs, model version, uncertainty and pipeline-state evidence. | Required model lookbacks pending validation. | Explicit synthetic preview only; no composite activation. |
| Lab / Backtesting Framework | PIT equity inputs, universe/action/terminal completeness, costs/calendars, hypothesis/input/run/review bindings. | Frozen experiment-specific history. | UI stubs; research separately gated, not part of site population. |
| Seasonality | PIT equity/cash-index prices, session/event calendars, action/listing/terminal evidence. | Predeclared sample range/seasonal categories; daily sessions. | No eligible history or approved study. |

Options, Futures, legacy Event Risk Assessment and Reports remain hidden as
recorded in `EQUITY_FIRST_PRIORITY_V1.md`. No derivative source, gold futures,
option-chain, OI or participant-futures input is included in these requirements.

## Frozen news/event requirements — no incoming data accepted yet

Article record target fields: `article_id`, `publisher_id`, `canonical_url`,
`headline`, `published_at`, `retrieved_at`, `available_at`, `source_record_id`,
`payload_hash`, `parser_version`, `dataset_version`, `revision_number`,
`supersedes_record_id`, `permission_reference`, `retention_deadline`,
`value_state`, `quality_flags`. No article body, sentiment score, trade inference
or portfolio impact. URL must be HTTPS without credentials; no link fetching.

Event target fields: `event_id`, `publisher_id`, `security_id`, `event_type`,
`scheduled_date`, `event_timezone`, `announced_at`, `retrieved_at`, `available_at`,
`source_record_id`, `payload_hash`, `parser_version`, `dataset_version`,
`revision_number`, `supersedes_record_id`, `permission_reference`,
`retention_deadline`, `value_state`, `quality_flags`. Events limited to
equity board meetings/corporate actions; no derivative expiry feed. A scheduled
date remains a date; do not invent exact times or announcement timestamps.

Identity/lineage: exact publisher record/revision binding, duplicate attribution
and redistribution lineage retained, not independence inferred. Article ID must
not merge different publishers silently. Event security crosswalk must be
authoritative/effective-dated; missing links block security-specific display.
Original publication time <= retrieval; availability follows known publication,
and forward scheduled dates need not precede publication. Future publication,
unknown time, missing rights or stale data has an explicit unavailable state.
Freshness policy and thresholds require source-specific review before activation;
old 10/30-minute caches do not establish them. No real retention default is
permission evidence, and no new review/payload copy is retained in this milestone.

## Implemented gate and preservation

`news_readiness_v1.assess_news_readiness` evaluates only bounded-name SHA-256
metadata claims for publisher, consumer scope, permissions, identity semantics,
timestamp/provenance/freshness/missingness/retention policies and execution approval.
Missing/malformed claims fail closed. Even complete hashes yield
`METADATA_BOUND_NOT_VERIFIED_EXECUTION_DISABLED`: both fetching and scoring
remain false. Claims are not authenticated evidence; no execution path exists.

The routed News & Calendar page imports no legacy/news/sentiment provider and
ignores activation session flags. It shows the existing two tabs as unavailable,
without requests, retries, scores, market-file reads or persistent output.
Old renderer preserved byte-exact as `_legacy_news_calendar.py`, not registered
in navigation or imported by the replacement. Existing `_news_data.py` and
`_sentiment.py` remain in code, unused by this page; they are not newly approved.
Shared theme, watchlist contract, Dashboard columns, Data Coverage, hidden-page
registry and sealed evidence remain unchanged. No provider activation, acquisition,
research/backtest, fingerprint refresh, retention change, deletion or F&O repair.

## Validation and next decision

137 selected tests passed: new news readiness/load guards, watchlist contract,
UI/cash scope, current health/Kite client with fake HTTP and alternative/quarantine
governance. News page tests deny HTTP, external connection, CSV reads/writes and
legacy/provider imports, including on rerun with purported approval flags.
AST checks restrict new page/gate imports/calls. Compilation, legacy-renderer
byte equality, changed-file scope, privacy and staged diff checks are verified
at completion. Full root suite and known unrelated stale fingerprint/R9K timing
failures are not rerun, repaired or refreshed. F&O remains last/unqualified;
2026-12-31 evidence retention and all source restrictions remain unchanged.

Recommended next scope, **not executed**: owner-approved synthetic watchlist
contract integration into Dashboard's existing table. Preserve approved layout
and columns, render exact contract identity/price/missingness/provenance, keep
change % explicitly unavailable because v1 lacks its semantics, and prove no
provider/file/network activation. This advances a functioning non-F&O site
without pretending mocks are real. Real-source feasibility/permission and
consumer activation remain later separate decisions. Review these requirements
and separately authorize the exact UI integration scope before implementation.
