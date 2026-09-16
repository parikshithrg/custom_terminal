# Approved isolated NSE quarantine — coverage audit closeout

Owner response “all 3 approved” is bound to the unchanged `quarantine_coverage_v1` protocol hash. It authorizes implementation, the two offline audit consumers and zero-loss thresholds only. Historical proposed/pending records remain intact and are superseded by the separate authorization receipt.

All three packages passed contained-path/reparse, exact manifest/file/URL/role, payload size/hash and bounded ZIP/GZIP integrity checks before normalization. Embedded UDiFF dates, unchanged H/I diagnostics, unique identity joins, decoded expiries and source/normalized/historical price digests agree on all dates. New manifests are hash-bound independently; the original deletion receipt and historical manifests are unchanged.

| Audit scope | Baseline contract-dates | Filtered contract-dates | Quarantine gaps | Coverage loss |
| --- | ---: | ---: | ---: | ---: |
| 2026-09-09 | 33,250 | 33,250 | 0 | 0% |
| 2026-09-10 | 33,729 | 33,727 | 2 | 0.005930% |
| 2025-07-08 | 32,047 | 32,047 | 0 | 0% |
| Pooled | 99,026 | 99,024 | 2 | 0.002020% |
| Stock futures on 2026-09-10 | 629 | 627 | 2 | 0.317965% |

The two close-range row diagnostics map to two uniquely joined contract-dates. The one `TRADE_STATE_ATTRIBUTION_UNAVAILABLE` diagnostic remains date-level, restricting all 33,729 baseline rows (33,727 filtered rows). It is not a third row and is not resolved by exclusion. All 71,217 nonblocking settlement/zero-volume diagnostics remain in immutable diagnostic storage; none triggers automatic masking.

The approved offline integrity, reconciliation, missingness, uniqueness, attribution-preservation and no-fill/no-mutation checks pass in baseline and filtered audits. Contract-date no-loss fails for the filtered 2026-09-10 view as an expected mask effect; unexpected consumer invariant differences are zero. Field state counts, zero values, not-applicable states, explicit quarantine gaps and fixed baseline denominators are detailed in `measured_results.json`.

Result: MATERIAL_FOR_COVERAGE under the approved zero-loss thresholds. Thresholds were frozen before results and were not revised. The small pooled percentage cannot justify ignoring evidence, clearing date-wide attribution or qualifying a source.

Original facts, quarantine reasons/source locators/provenance, diagnostic and date-restriction tables are held in a new ignored SQLite database. Update/delete/insert triggers lock completed tables; the separate experimental filtered view exposes an explicit date restriction. Database integrity, exact stored facts, mask counts, diagnostic counts and restriction counts were checked. No existing local F&O database was opened. Retention remains 2026-12-31; no deletion or amendment occurred.

Exact-contract corroboration: NOT_EVALUATED_NO_AUTHORIZED_EVIDENCE; independence NOT_ESTABLISHED. No provider API, website, contact, additional download, price substitution, research, fingerprint refresh, scoring, backtest or trading was used. Three sparse dates do not establish long-term return/drawdown sensitivity.

Original route remains MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED. Historical acceptance results are unchanged; filtered outputs are experimental and unavailable to production or research.

Next owner decision: keep the route unqualified and defer downstream use, or separately authorize preparation of a bounded exact-contract alternative-evidence acquisition scope. The two contract-date identities exist only in ignored local storage. Any actual alternative access requires a later explicit provider/query, payload/request budget and retention-permission approval; nothing is downloaded or contacted by this proposal.

Validation: pre-execution synthetic and affected tests 57 passed, with one then-pending closeout hash check skipped; finalized experiment, adapter and governance suite 139 passed, zero failures/skips. Compilation, JSON/root hash bindings, historical evidence/acceptance, privacy, Git-ignore and diff checks passed. Known unrelated stale research-fingerprint and R9K timing failures were preserved, not rerun; full root suite was not run. Runtime database checks verified immutable facts, exact masks, diagnostic counts and persisted date restrictions.
