# Market System - Owner Decision Report

**Version 7 | R.9O | Review preparation only | 5 September 2026**

## Decision requested

Decide whether to authorize one bounded synthetic-only integrated-boundary prototype. This report neither adopts APSW nor authorizes production implementation, private-data access or an audit.

**PDF_V7_GENERATED_AWAITING_OWNER_DECISION**

## Project objective

Build an analysis-only Indian market research system with eventual evidence-backed market-sentiment and stock scores. Use free lawful sources and Kite where appropriate. Untested scores stay hidden. Deterministic code remains the quantitative source of truth. No trade execution. version2.0 remains separate and noncanonical.

## Why APSW was evaluated

Python's standard sqlite3 interface could not enforce a target-specific logical database-read-byte budget. APSW exposes lower-level VFS read hooks. Evaluation is not dependency adoption or production approval.

## Current state

- APSW candidate: **3.53.4.0**; candidate SQLite: **3.53.4**.
- Wheel SHA-256: `13bd0c01cada861ce9cd4a09ff36c5a245185477c5fe6ce52d266c46e69f76e5`.
- Root environment and dependency files still contain no APSW.
- Production interlock remains **R9D_EXACT_PRODUCTION_ACTIVATION_IMPOSSIBLE**.
- R.9M/R.9N are synthetic-only evidence; real database behavior is untested.
- Official F&O format: **PENDING_OFFICIAL_FORMAT_EVIDENCE**.

Baseline `125af7bd30fa2e7eba1f01b4072b02dd2015e420`, synchronized with origin/main and clean when inspected.

[PAGE BREAK]

## 1. What R.9M and R.9N demonstrated

Overall classification: **DEMONSTRATED_WITH_LIMITATIONS**.

| Tested property | Recorded evidence | Limit |
| --- | --- | --- |
| Layout diversity | Page sizes 512, 1024 and 4096; files 36,352, 49,152 and 159,744 bytes | Finite generic fixtures only |
| Admission | Full read request reserved before delegation | Scoped VFS xRead, not whole-process I/O |
| Repetition/faults | Repeated offsets charged again; failed/short reads retained reservation | Injected read faults are mocks, not OS failures |
| Exhaustion | Sticky; exact observed budget succeeded; one byte below failed with zero completed output | Threshold varies by layout/workload |
| Shared attempt | Multiple statements consumed one cumulative budget | Exact fixed operations only |
| Cursor/output | Row and serialized-output limits accumulated; buffered result discarded on failure | Not allocator or temporary-storage quota |
| Deadlines | Checks covered execution and iteration | Injected clock/cooperative cancellation, not hard process deadline |
| SQL scope | Only exact catalog-operation templates exposed; authorizer rejected application rows | Synthetic schema; no market rows approved or published |

Observed successful logical budgets were 36,468, 25,716 and 28,788 bytes for the three layouts. One-byte-insufficient attempts saw partial rows internally (34, 32 and 24) but published **zero** completed rows. A separate fetch-threshold experiment failed after seeing 1, 3 and 12 rows respectively, again publishing zero.

Two permitted catalog statements returned 70 rows when fully budgeted. With the first-statement byte budget, the second failed and published nothing. A cumulative 40-row cap stopped at row 41; an 11,000-byte output cap stopped without exceeding the bound or publishing success.

These are candidate mechanics, not real-data accuracy, safety or production proof.

[PAGE BREAK]

## 2. Exact meaning of the byte budget

| Counter | Meaning |
| --- | --- |
| Requested | All lengths SQLite asked xRead to read, including refused requests |
| Reserved | Full admitted request lengths, charged before delegation and never refunded |
| Delegated | Lengths passed to the underlying read, including calls that later error |
| Returned | Actual byte-string lengths obtained; may be shorter than delegated before rejection |

Opening/header reads count. One attempt begins before its single read-only open and ends at close or failure. All permitted statements share its meter. Repeated reads cost again. Failure is sticky. A second connection, reopen or reset through supported APIs is rejected.

Logical SQLite reads are requests at the VFS boundary. They are not OS process I/O and not physical disk I/O. OS accounting includes unrelated files and process activity. Physical reads depend on caches, device behavior and read-ahead.

Fixture creation, hashing, imports, directory checks, native controls and other process activity are outside the VFS meter. This is not a whole-process I/O quota. Row, output and deadline limits supplement the read budget; they do not replace it.

## 3. Required restricted profile

Current evidence supports consideration only of:

- Read-only, exactly one connection per attempt.
- No mmap, WAL, rollback journal, shared memory or SQLite temporary-file access.
- No caller-provided SQL; exact statement templates only.
- Cumulative logical-read, returned-row and output budgets.
- Execute-and-fetch deadline checks.
- Fail closed; discard buffered output on every failed attempt.

Any future mmap, WAL or sidecar support requires separate evidence and authorization. These are experimental restrictions, not approved production policy.

[PAGE BREAK]

## 4. What remains unresolved

- Main-file protection does not guarantee sibling-file or namespace stability. A sidecar can appear between checks.
- Complete native sidecar-path coverage is inconclusive. Active WAL/rollback fixtures were rejected at preflight before the candidate SQLite open.
- Writer exclusion and continuous quiescence are not proven.
- Temporary-storage containment is unresolved.
- Injected/cooperative deadlines are not hard whole-process deadlines.
- Windows Job Object containment has not been integrated with APSW.
- Exact owner-sealed attempt IDs are not integrated.
- Production implementation and real-database behavior are untested.
- Licensing review, maintenance ownership, supported-version policy, supply-chain handling and SQLite-version regression policy are undecided.
- The wheel matched PyPI's published hash; reproducible build provenance was not established.
- Synthetic success cannot qualify the real F&O database.

Namespace replacement, transient sidecars, preexisting mappings, same-process hostile code and host differences remain outside demonstrated assurance. No filesystem/network sandbox has been proven. Solving integration cannot by itself prove provenance, completeness, survivorship safety or point-in-time correctness.

## 5. Official F&O format status

**PENDING_OFFICIAL_FORMAT_EVIDENCE**

The official NSE landing-page request timed out. No authoritative F&O field definitions, types, format version or effective date were obtained. No market records or current security lists were downloaded.

R.9M used seven names from an existing NSE MII subset; that was not verified F&O UDiFF parity. R.9N correctly returned to generic synthetic fields. CSV source fields and local SQLite types remain separate concepts: an exchange CSV definition does not mandate a SQLite storage type.

No header is guessed and no third-party example is treated as authoritative. Official NSE accuracy, revisions, provenance and coverage validation remains a separate later task. Synthetic tests cannot establish those properties.

[PAGE BREAK]

## 6. Options for the next step

| Option | Scope | What it does not authorize |
| --- | --- | --- |
| **A - Recommended** | Bounded synthetic-only integrated boundary prototype | APSW production adoption, production code, real data, audit or data qualification |
| B | Another narrow experiment only after owner names one unresolved hypothesis | Open-ended research or production implementation |
| C | Defer APSW route; retain all evidence and inaccessible production database | No weakening or substitute route inferred |

Option A may combine the restricted APSW VFS, existing Windows Job Object containment, exact synthetic one-use approvals with owner-sealed attempt IDs, fixed catalog templates, cumulative row/output/read-byte/deadline controls and fail-closed terminal evidence. It must remain outside production packages and use generated fixtures only.

### Proposed acceptance criteria for Option A - not implemented

1. One exact approval binds one explicit attempt ID.
2. Approval is durably consumed before the first synthetic target connection; replay and concurrent consumption fail.
3. Exactly one target connection is allowed.
4. Main-file guard and sidecar checks remain held throughout the attempt.
5. Restricted VFS refuses unapproved file categories; mmap and sidecar modes remain unavailable.
6. Only exact SQL templates execute.
7. Read, row and output limits fail closed; deadline plus Job Object containment covers worker and descendants.
8. Failure publishes no successful audit artifact.
9. Every consumed attempt has a detectable terminal or incomplete state.
10. No private or production path can enter the prototype.

Passing these synthetic criteria would still not adopt APSW, authorize production access, execute an audit or qualify market data.

[PAGE BREAK]

## 7. Owner questions - answers pending

1. Is the R.9M/R.9N summary accurate?
2. Do you accept that the demonstrated meter covers logical SQLite I/O, not physical disk or whole-process I/O?
3. Is the restricted no-mmap/no-sidecar/single-connection profile acceptable for further synthetic engineering?
4. May APSW remain an isolated candidate for that synthetic work, without production adoption?
5. Do you authorize only a bounded synthetic integrated-boundary prototype using generated fixtures?
6. Should official NSE F&O format/data validation remain a separate later task?
7. Is production access to remain blocked until another current PDF and explicit approval?

No answers are pre-filled. A generic instruction to continue is not production authority. An Option A authorization would apply only to the proposed synthetic prototype and criteria above.

## Evidence freshness and verification

PDF v7 binds the R.9M and R.9N manifests directly because the mechanical research fingerprint excludes these investigation artifacts. Fingerprint equality does not mean earlier PDFs contain these findings. No exclusion changes manufacture freshness or staleness. Historical reviews retain their original authority.

Historical evidence: R.9N recorded 4 native regression tests and 34 static tests. R.9O does not rerun native experiments or claim these as newly observed. Its manifest binds prior reports, manifests, results, source hashes, dependency files, production interlock and earlier PDFs/review records.

**Exact proposed next task:** build one bounded synthetic-only integrated-boundary prototype against generated fixtures and the ten proposed criteria, but only if question 5 is explicitly authorized. No production source, real data, audit, market analysis, scoring, simulation, backtesting, recommendation, broker access or trading.

**PDF_V7_GENERATED_AWAITING_OWNER_DECISION**
