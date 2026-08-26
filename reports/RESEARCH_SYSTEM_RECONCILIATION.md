# Research System Reconciliation R.1

## Outcome

Baseline `31a7c84` was clean. The two research systems have useful but different
strengths. `dtest` is the broader hypothesis laboratory with deterministic
signals, next-open fills, costed simulation, placebos and many saved artifacts.
`market_intel` is the stronger canonical trust/identity/temporal/manifest and
approval boundary. Neither is currently sufficient by itself for production
research approval.

The proposed ownership model is retained. A neutral `research_contracts`
package and versioned specifications now define the shared boundary without
coupling the packages.

## Status-report reconciliation

- Repository-local log: 31 rows, 25 rejected, 6 accepted.
- PDF/source log: 32 rows, 26 rejected, 6 accepted.
- The additional MF-accumulation rejection is located in a separate checkout
  but lacks a result manifest and is classified `LOCATED_BUT_NOT_REPRODUCIBLE`.
- Six accepted rows cover three families; only momentum has an accepted
  validation row.
- “None survived validation” conflicts with both the log and the PDF's own
  momentum table. The corrected statement is that momentum passed legacy train
  and validation gates but never reached test, replication or production.
- Thirteen constructions are reproducible only through a manual family mapping;
  the log has no family ID.
- The PDF was written before its generator commit and embeds no commit, dirty
  fingerprint, config hash, log hash, dataset hashes or generator version.

## Contract comparison

| Area | `dtest` | `market_intel` | Canonical owner / compatibility requirement | Risk |
|---|---|---|---|---|
| Price observations | symbol panels and bhavcopy store; limited per-run provenance | typed observation/snapshot provenance and immutable ingestion | `market_intel`; adapter retains raw `dtest` symbols and source hashes | high: many old runs lack input hashes |
| Historical population | liquidity rule over observed traded columns | explicit listed/traded capability gates and A.8 reconciliation | shared capability contract; never equate traded with listed | critical |
| Security identity | ticker columns | instrument/listing/issuer/ISIN/dated aliases | `market_intel`; ambiguous ticker mapping stays unresolved | critical |
| Universe membership | causal monthly 200/250 turnover rule | near-compatible versioned rule with decision/exclusion evidence | preserve both versions and compare materializations | medium |
| Corporate actions | inferred isolated `prev_close` factors | authoritative typed events and trust gate | `market_intel`; inferred stages remain candidates | critical |
| Adjusted prices | derived price-return series exists but is not used by hypothesis scripts | raw local OHLC with explicit limitation; separate canonical actions | shared series identity required in every manifest | high |
| Terminal outcomes | no-fill/unresolved/stale universe; portfolio marks missing close at entry | typed classifications and unresolved blocking | shared terminal contract; no invented value | critical |
| Benchmarks | NIFTY50 close-to-close, identity/PRI metadata weak | typed PRI/TRI classification and explicit benchmark inputs | `market_intel`; preserve old close-to-close convention for compatibility | high |
| Transaction costs | detailed but current flat config applied historically | same compatibility schedule plus date-effective wrapper | canonical dated schedules in `market_intel`; old version stays compatibility-only | high |
| Execution timing | close signal, next-open entry; stops/targets at levels; time exit next open | next-open entry and fixed next-open horizon outcome | shared explicit outcome; do not force different overlays into parity | medium |
| Fills | participation cap, volume/open rejection | basic price/share fill; no equivalent participation cap in Slice A | retain `dtest` simulator for lab; canonical artifact records fill version | high |
| Holding periods | per-script 7/20/21/60/126, despite PDF universal-7 claim | 21-session momentum contract | shared hypothesis components | high |
| Portfolio construction | slot/cash/sector-cap engine plus sizing-independent layer | equal-weight monthly approximation | neither universally canonical; version both | high |
| Placebo generation | same dates/counts, 30 seeds, random eligible names | 30 seeded matched/rank baselines | promotion policy supersedes both for future confirmation | high |
| Statistical inference | entry-week bucket t-stat | decision-date block bootstrap | `market_intel` approach closer; block must derive from horizon | high |
| Experiment manifests | implementation exists; only audit manifest located | mandatory root manifest and artifact hashes | `market_intel`; new lab exports must require manifest | critical |
| Lifecycle states | row-level accepted/rejected/inconclusive | research state plus non-actionable gate | shared explicit lifecycle mapping | high |
| Promotion gates | per-script formulas, inconsistent, no family ledger | declared gates but Slice A forced non-actionable | shared promotion policy and catalog events | critical |

## Population, corporate action and terminal conclusions

The `dtest` liquidity algorithm is causal inside its observed traded panel, but
complete historically listed population, inactive coverage, suspension history,
stable identity and terminal economics are not established. `prev_close`
discontinuities support inferred adjustment candidates, not verified action
types or total returns. Saved artifacts contain unresolved/no-fill observations,
but cannot determine their economic cause.

## Statistical-governance conclusion

Thirty placebos, inconsistent per-script gates, weekly buckets for long
overlapping holds, adaptive diagnostics, absent family IDs, validation reuse and
unenforced test access prevent legacy `accepted` rows from serving as canonical
confirmation. The new policy requires preregistration, explicit families,
horizon-aware dependence treatment, multiplicity control, one-time test access
and independent replication.

## Changes made

- Added neutral typed contracts and non-mutating legacy lifecycle mapping.
- Added versioned population, shared evidence, correction and promotion-policy
  specifications.
- Added eight focused reconciliation/policy/migration reports plus the PDF
  correction notice.
- Added offline contract and compatibility tests.

No hypothesis was run. No input data, legacy log row, PDF, momentum artifact,
historical trust verdict or Kite code was changed.

## Verification

- Root suite: `python -m pytest -q` — 114 passed.
- Separate `Data test` suite: 289 passed; five third-party SWIG deprecation
  warnings did not affect the result.
- Shared-contract tests: 18 passed as part of the root suite.
- JSON specifications: all 27 parsed successfully.
- Python compilation: `src`, `views` and `tests` passed.
- Git whitespace validation: passed.
- Protected-artifact comparison against `31a7c84`: no changes detected.
- Repository-local hypothesis-log and source-PDF SHA-256 values remained
  `80d80aa9372f5dc0ff857acba36575c125438508ebededecd789a31ece799777`
  and `940efd19fa4b385230c3b5cb51e66c6cb2353e178381b0188e001c0f536bdae3`.

## Decision

The shared vocabulary and migration plan are ready, but the ignored/mutable
hypothesis ledger, missing run manifests and unresolved dataset/terminal
provenance prevent complete evidence reconciliation.

`RESEARCH_EVIDENCE_CONFLICTS_UNRESOLVED`

## Safest next milestone

Create a read-only Phase 2 adapter around a user-designated immutable 32-row log
snapshot, assign reviewed family IDs, and require a manifest reference or
explicit missing-manifest failure for every row. Do not test another hypothesis.
