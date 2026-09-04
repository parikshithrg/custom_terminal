# Market System - Owner Decision Brief

**Version 6 | R.9L | Review preparation only | 4 September 2026**

## The decision now required

The current approved stack cannot enforce the proposed target-specific logical database-read-byte cap. Continuing this SQLite audit route requires an explicit decision about the access technology, the requirement, or whether to defer the route.

This is a limitation of one proposed database-access route, not a failure of the overall market-system project. Synthetic containment success is not production readiness.

**PDF_V6_GENERATED_AWAITING_OWNER_ARCHITECTURE_DECISION**

## What we are building

An analysis-only Indian market research system with eventual evidence-backed market-sentiment and stock scores, reproducible evidence and visible uncertainty. Deterministic code supplies quantitative results; AI helps interpret them. Untested scores remain hidden. No trade execution.

Use free lawful data sources and Kite where appropriate. Kite current instruments are not a historical universe. version2.0 remains separate and noncanonical; exploratory displays do not become validated evidence merely by appearing in a dashboard.

## Current boundaries

- Local F&O database: **LOCATED_AND_SAMPLED_NOT_QUALIFIED**.
- Production interlock: **R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE**.
- No new approval, dependency selection, installation, experiment or execution authority.
- Historical trust gates and momentum remain unchanged and non-actionable.

Source checkpoint: `846f28fe740841c3e58de9caa2842b1a062d18de`, clean at inspection.

This report proposes an engineering next step only. It provides no market recommendation and authorizes no production implementation, private-data access, audit, acquisition, broker action, analysis, scoring, simulation or backtesting.

[PAGE BREAK]

## 1. Completed work and demonstrated limits

Earlier slices established reproducible experiment contracts, immutable evidence, provider-neutral ingestion, historical trust gates and current-only Kite coverage. Historical population qualification remains incomplete; the official-response gate remains AWAITING_SUBSTANTIVE_OFFICIAL_RESPONSE. R.9F recorded a bounded filesystem identity sample, not a SQLite audit. A sampled fingerprint is not a full-file hash or data-quality qualification. R.9H remains a non-executable boundary proposal.

### R.9J: enforcement gaps made observable

Durable synthetic approval consumption had exactly one winner among two competing consumers. Consumption survived restart, rejected replay and retained incomplete attempts after crashes. However, the existing approval payload lacks an explicit attempt ID: uniqueness at consumption is not prior owner binding of that ID.

Statement and output guards worked in their tested paths. The row counter was absent, a fetch outlived its deadline, generic catalog SQL was accepted, and killing a parent left a descendant alive. These findings are retained, not silently repaired.

### R.9K: native mechanisms, not a production boundary

| Evidence class | Demonstrated finding | Boundary of the claim |
| --- | --- | --- |
| Tested native behavior | Main-file share-read-only guard allowed SQLite read-only access and denied independent write, rename and replacement | Held before hashing through reader closure; sibling sidecars remained writable |
| Tested native behavior | Suspended assignment and Job Object timeout, last-handle close and supervisor death cleaned up fixed process trees | Ordinary tested descendants; measured latency, not a hard real-time guarantee |
| Tested native behavior | 48 MiB per-process committed-memory cap rejected 64 MiB allocation; no-cap control succeeded | Not working set, aggregate memory cap or host-exhaustion testing |
| Mocked failure path | Job creation failure prevented launch | Control-flow test, not an observed OS resource failure |
| Native failure path | Invalid-handle assignment failed; suspended worker was not resumed | Specific injected error, not every host-job policy |
| Source inspection plus tiny probe | Public sqlite3 API lacks VFS read interception; Python open hook saw no calls | Not proof of zero I/O; no alternative binding evaluated |

Untested assumptions include hostile same-user containment, namespace/reparse races, preexisting mappings, all allocation patterns and other host job policies. No filesystem/network sandbox, complete quiescence or production-safe resource envelope has been established.

Historical verification only: R.9J recorded **91 passed, 3 skipped**; R.9K recorded **25 passed, 0 skipped**. R.9L does not repeat these experiments or claim their counts as new tests.

[PAGE BREAK]

## 2. Blockers and the meaning of the byte cap

| Remaining blocker | Why it still matters |
| --- | --- |
| Sidecars and namespace/quiescence | Main-file sharing does not continuously protect WAL/SHM/journal siblings or prevent directory/identity races. Clean checkpoints are observations, not continuous exclusion. |
| Target-specific logical read bytes | Approved sqlite3 stack has no enforcing I/O interceptor. xRead and mapped xFetch paths, applicable sidecars and exhaustion behavior need explicit treatment. |
| Temporary-storage quota | No process-wide quota was proven. An output-file size guard is narrower than scratch/spill storage control. |
| Returned-row enforcement | Source lacks a row-budget counter. The tiny 64-row/two-row probe is not a test of the proposed 25,000-row threshold. |
| Fetch deadline | Progress handler was removed before fetching; execute-time interruption does not establish fetch coverage. |
| Exact SQL templates | Generic catalog SELECT acceptance is broader than a sealed enumerated-template contract. |
| Explicit attempt ID | Existing synthetic approval does not seal the ID before consumption. Durable uniqueness alone does not satisfy exact prior approval. |

**Solving the read-byte problem alone would not resolve the other blockers.** Native prototypes have not been integrated into a production boundary. No current control or proposal is promoted here.

### Three motivations must remain separate

| Motivation | Required distinction |
| --- | --- |
| Resource protection | Bound target logical read requests under a defined metric. Rows, statements, time, memory and output limits are useful but not equivalent. Logical reads also differ from physical disk I/O and whole-process OS counters. |
| Restricting data exposure | A byte limit does not identify which data may be read or emitted. Exact scope, connection authorization and output controls remain necessary. |
| Audit scope | Catalog-only inspection must exclude market rows and unapproved SQL independently of resource usage. Passing metadata stages cannot qualify economic coverage or research fitness. |

The proposed logical metric concerns cumulative requests at SQLite's file I/O boundary, including repeated requests and a declared charging policy for mapped access. SQLite/OS caches make this different from physical storage reads. Neither the purpose nor an equivalent substitute is assumed on the owner's behalf.

[PAGE BREAK]

## 3. Architecture options - none approved

| Decision dimension | A. Retain cap; evaluate access approach | B. Reconsider resource contract | C. Defer SQLite route |
| --- | --- | --- | --- |
| What changes | Bounded synthetic evaluation of a maintained VFS-capable approach | Present stack retained; owner explicitly reviews requirements | No access work; evidence preserved |
| What stays protected | Hard cap and production block remain | Existing guarantees remain until a separate explicit decision; no silent equivalence | Production disabled; all evidence and gates retained |
| New engineering burden | Dependency support, versioning, maintenance, I/O accounting and failure testing | New threat/resource rationale and evidence for any revised contract | Later separately scoped source/access planning |
| Remaining blockers | Sidecars, namespace, temp quota, rows, fetch, templates, sealed ID; evaluation may be no-go | Same blockers; replacement limits cannot be called a read-byte cap | Entire audit route remains blocked; alternative data still needs qualification |
| Exact next authorization | Authorize a bounded synthetic-only dependency evaluation, not dependency approval or production access | Authorize a separate explicit requirements review, not an automatic weaker guarantee | Confirm deferral; separately authorize any later data-access/source plan |

### Conditional recommendation

**PROPOSED_NOT_APPROVED:** Choose A only if the owner accepts evaluating a new maintained dependency. A future separately authorized evaluation must cover target read interception, mapped access, sidecars and fail-closed budget exhaustion using synthetic inputs only. It may still conclude no-go. No specific library is selected or approved, and nothing is installed in R.9L.

Otherwise recommend C: defer the SQLite route rather than silently weaken the cap. Option B is available for a separate owner decision, but weaker guarantees are neither recommended as equivalent nor recorded as accepted.

Free official sources are not an automatic workaround: a later plan still needs provenance, completeness, lawful retention and reproducibility checks. No source is acquired or newly qualified here.

### Approval boundaries

Summary agreement is not implementation approval. Authorization to evaluate a dependency is not approval to adopt it. Dependency approval is not production access; production implementation is not audit execution. Any later real-data audit needs a separately reviewed exact scope and approval. No research or trading authority follows from any option.

[PAGE BREAK]

## 4. Evidence freshness and owner questions

Mechanical research fingerprint equality does not mean PDF v5 summarizes R.9J/R.9K. The existing fingerprint excludes investigation tools, documents and tests. It remains unchanged over 252 files; exclusions are not changed to manufacture a different result.

PDF v6's NON_APPROVAL_REPORT_GENERATION manifest explicitly binds the R.9J/R.9K manifests, results, assessments, reports and relevant source hashes, plus earlier PDF/review/proposal/binding evidence. The old review retains its original narrow authority and is not rewritten. No v6 approval record or pre-filled answers are created.

### Evidence map

- R.9J: `docs/investigations/r9j/completion_manifest_v1.json`; assessment and recorded results beneath the same directory. Interpretation: `reports/RESEARCH_R9J_REPORT.md`.
- R.9K: `docs/investigations/r9k/manifest_v1.json`; feasibility and recorded results beneath the same directory. Interpretation: `reports/RESEARCH_R9K_REPORT.md`.
- Prior review: `docs/project_status/pre_research_review_record_v5.json`.
- Exact v6 bindings and current static verification: `docs/project_status/pre_research_generation_manifest_v6.json` and `reports/RESEARCH_R9L_REPORT.md`.

These are repository-relative references to tracked sanitized evidence. Private configuration, runtime binding and the real database are not read. Historical observations are reused, not rerun. The PDF excludes its own hash to avoid self-reference; the generation manifest records it.

### Owner questions - answers pending

1. Is this updated summary accurate, including the distinction between tested synthetic mechanisms and disabled production capabilities?
2. Do you authorize a bounded synthetic-only dependency evaluation while retaining the hard read-byte cap? This would not approve a dependency, implement production access or execute an audit; those require separate decisions.
3. Should the local SQLite route instead remain deferred, with all evidence preserved and production disabled?
4. Is any resource requirement to be reconsidered through a separate explicit decision? If so, which requirement and purpose: resource protection, restricting data exposure or audit scope? No change is inferred from silence or summary agreement.

Questions 2 and 3 are alternatives; contradictory answers require clarification before work proceeds. Any requirements review under question 4 must be scoped separately. No answers or owner-review record have been recorded for v6.

**Recommended next milestone, only if separately authorized:** bounded synthetic-only evaluation of a maintained VFS-capable access approach. Otherwise defer the route. No new execution begins from this report.

**PDF_V6_GENERATED_AWAITING_OWNER_ARCHITECTURE_DECISION**
