# Bounded alternative-evidence proposal — preparation closeout

Baseline `873299e67f05c63d0ac0b4ba05b9e12e1a22da58` verified, initial worktree clean. Owner explicitly approved proposal preparation and read-only verification of the two quarantined identities only. No external access, acquisition or comparison execution is authorized.

## Verification

Sealed execution and historical protocol bindings passed. The ignored database matched its recorded SHA-256 before opening, passed read-only integrity/protocol/source-provenance and immutability checks, and retained the same hash after verification. Exactly two uniquely joined stock-futures contract-dates were verified; whole-date attribution restriction remains intact. Private target descriptors, source locators and requested field details exist only in uniquely isolated ignored local storage, bound by hash in `target_verification.json`. No identities, raw prices, query targets or full inventories are tracked.

## Existing-evidence feasibility assessment

| Candidate | Target-date feasibility | Main unresolved prerequisites |
| --- | --- | --- |
| Kite Connect | Exact two-contract history unverified; retained evidence supports some OHLCV/continuous history | Exact historical crosswalk, field basis, settlement, entitlement and response retention; current-only connector is not authorized for this task |
| yfinance/Yahoo | Unverified | Exact NSE futures coverage, adjustment/session/units/close definitions, permission and lineage |
| Investing.com | Unverified | Exact contract export/endpoint, historical fields, permission and lineage |
| Moneycontrol | Unverified | Exact contract export/endpoint, historical fields, permission and lineage |
| Already retained licensed owner export | Conditional only; no file/provider registered | Exact file hash/targets, authoritative metadata and retention/reuse permission |

Basis: retained `FNO_SOURCE_ROUTE_REASSESSMENT.md`, R10M capability evidence, current Kite scope/health and prior NSE investigation. No new source documentation was fetched. General provider capability is not verified target coverage. BSE is another exchange, SEBI participant statistics are aggregates, and the unrelated local F&O database remains out of scope.

## Recommendation and bounded conditional design

No defensible executable external route can be selected from existing evidence. Recommend DEFER / UNQUALIFIED, not invented URLs, guessed identifiers or a fallback-source search.

The smallest conditional option is one owner-supplied, already legally retained provider-attributed UTF-8 JSON export: precisely the two locally hash-bound targets and six requested fields (open/high/low/close, quantity, separate settlement), plus per-field semantics, effective dates, identity/session/units/adjustment, lineage and permission metadata. Proposed limits: one file, 64 KiB, two records, zero HTTP/messages/new provider downloads/redirects/retries, ten-second offline review and ten-minute session. This is a template, not a selected input or an authorized review. If the format/budget is insufficient, stop and request an amendment.

Provider, incoming file hash and permission remain unspecified. Owner must supply those prerequisites and separately approve the finalized binding, rules, budgets and retention before review. Incoming evidence retention through 2026-12-31 requires publisher-specific permission; personal-use approval alone is not that evidence. Existing approved evidence/private descriptors retain the unchanged 2026-12-31 deadline. No incoming copy was acquired and no retention amendment/deletion occurred.

Comparison design is frozen before any access: exact contract matching; documented NOT_APPLICABLE distinct from missing; compatible field basis and unadjusted contract/session/units required; exact Decimal equality with zero unjustified tolerance. The observed two-decimal source precision does not prove tick-size. Classify field-level agreement/disagreement only when comparability is established; unknown source universe, missing/unmatched/adjusted/duplicate/incompatible fields remain INDETERMINATE or NOT_EVALUATED. Numerical agreement cannot supply missing semantics; duplicate NSE-feed evidence cannot establish independence.

## Owner decision

Provide an already retained licensed exact-contract export and its publisher/coverage/field-definition/lineage/permission evidence, or defer. Once a route and exact input are defensible, review the separate execution-approval question in `proposal.json`. It remains NOT_REQUESTABLE while provider/input/permission bindings are missing; a generic approval cannot authorize unspecified access. Any future network route requires a separate fixed URL/query/budget proposal.

The original route remains MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED. Agreement on two rows cannot resolve date-wide trade coverage, reverse historical acceptance, revise the approved zero-loss thresholds or promote experimental outputs to research/production. No adapter change, further filtering, ingestion, strategy sensitivity, backtest, research, scoring, fingerprint refresh, activation or deletion occurred.

Validation: 148 focused offline tests passed. JSON/root hashes, transitive historical evidence, compilation, private-descriptor hash/ignore rules, actual-identity scoped privacy scan and diff checks passed. Known unrelated stale research-fingerprint and R9K timing failures were preserved, not rerun; the full root suite was not run. No comparison results were viewed or generated.
