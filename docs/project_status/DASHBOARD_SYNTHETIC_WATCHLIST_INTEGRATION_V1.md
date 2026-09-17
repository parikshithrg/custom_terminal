# Dashboard synthetic watchlist integration v1

Baseline: `988be481242068d94293661f2d82493706cc3ce8`.
Owner instruction: “build it”, following the proposed bounded synthetic Dashboard
integration. This authorizes presentation of the existing offline contract only;
it does not approve any real source, provider access, research or activation.

Dashboard now builds the in-memory v1 fixture and validates its envelope and hash
before rendering the existing four watchlist columns. Exact Decimal strings are
preserved; missing price stays unavailable with `MISSING_PRICE`, never zero or a
fallback. Demo change is unavailable for every record because v1 defines no
change semantics. Source status carries synthetic source/record references and
currency. The caption exposes fixture version, full content hash, invented as-of
and `SYNTHETIC_NOT_MARKET_READY`, explicitly not market freshness.

The fixed aware cutoff is 2026-01-01 10:00 UTC, invented fixture metadata, not the
wall clock. Contract failures display unavailable with no legacy-price fallback.
Only Dashboard opts into this boundary. Market Gate retains its existing
synthetic preview. Index cards remain synthetic and unchanged. No styling,
navigation, manual Data Coverage scope, hidden pages or contract fields changed.

Validation: 118 focused tests passed across watchlist integration/contract,
UI, cash scope, news readiness and alternative/quarantine governance. Tests cover
precision, missingness, deterministic presentation, unchanged input bytes,
tampered bindings, consumer refusal, no I/O and failed-contract presentation.
The previous unwired-only contract test now permits exactly the separately
authorized presentation helper. Compilation and diff/privacy checks passed.
No full root suite was run; known unrelated research-fingerprint and R9K timing
failures remain untouched. No sealed evidence or retained package was accessed
or changed. No external access, persistent data output or provider activation.

F&O remains deferred and `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`;
experimental outputs cannot feed UI/research. Retention remains 2026-12-31.

Next separately authorized scope: prepare an offline feasibility/permission and
field-semantics decision for one cash-equity source and this one consumer using
existing repository evidence only. Identify missing identity, as-of, provenance,
freshness and unavailable-state prerequisites without browsing or activating a
connector. The synthetic contract is not evidence that a real source is ready.
