# Hypothesis Log Reconciliation

## Evidence boundary

The append-only CSV under `Data test/runs` is ignored by the root Git
configuration even though `dtest.evaluate.hypothesis_log` says it is committed.
The repository-local file is therefore local evidence, not version-controlled
evidence. It was read and hashed but not changed.

| Object | SHA-256 | Status |
|---|---|---|
| Repository-local 31-row log | `80d80aa9372f5dc0ff857acba36575c125438508ebededecd789a31ece799777` | ignored, local |
| Located 32-row source log | `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d` | ignored, separate checkout |
| Repository config | `cb68999f6e0dd16796d017f1104cc630483ada44ed1959143b99c9e9d11d29a2` | tracked |
| Located source config | `82dd7d602560c35c40062ba30df7c5fe647f78249568749928cab93adcf584c9` | tracked in separate checkout |

## Verified counts

The repository-local log contains 31 rows: 25 rejected and 6 accepted. It has
17 exact titles because variants and windows are separate rows. The PDF's 32,
26 and 6 counts are reproduced only from the sibling source log after adding
the reported `mf_accumulation` rejection.

The 13 economic constructions in the PDF are a manually grouped reporting
taxonomy, not a field in the log. They are reproducible from the source log
only with the grouping rules below:

1. mean reversion;
2. delivery breakout;
3. OI momentum;
4. participant tilt, including its stress gate;
5. volatility-squeeze breakout, including delayed entry;
6. price action;
7. pairs reversion;
8. same-sector pairing, including Oil & Gas variants;
9. 12-1 momentum;
10. earnings surprise;
11. value;
12. quality;
13. MF accumulation.

Because `economic_construction_id` is absent, a future adapter must version
this grouping and never infer it solely from title similarity.

## Accepted-row reconciliation

| Family | Accepted rows | Later evidence | Reconciled interpretation |
|---|---:|---|---|
| Same-sector pairing | 2 train | both primary validation rows rejected; delivery train rows rejected | `VALIDATION_REJECTED` at family level |
| Momentum | 1 train, 1 validation | no test row | legacy `VALIDATION_CONFIRMED`, also `PRODUCTION_INELIGIBLE` |
| Oil & Gas same-sector pairing | 2 train | both validation rows rejected | `VALIDATION_REJECTED` at family level |

The mapping implemented in `research_contracts` is deliberately row-level:
train acceptance is `TRAIN_PROMOTED`, validation acceptance is
`VALIDATION_CONFIRMED`, and neither implies production eligibility. A family
state requires an explicit family ID and ordered lineage; the old rows lack
both, so ambiguous family aggregation remains a reconciliation artifact rather
than a mutation of the log.

## Classification of the 32nd entry

`mf_accumulation` is **located but not reproducible**. The source row, source
code commit history and narrative PDF agree that it was rejected. However, no
root run manifest records the exact dataset bytes, derived panels, code dirty
fingerprint, output hashes or execution environment. It is not “recovered and
verified” because agreement among mutable artifacts is not full reproduction.

## Manifest contradiction

`dtest.determinism.RunManifest` says a result without a manifest is not a
result. Only `runs/audit_data/manifest.json` was located. It predates the
hypothesis series, records a dirty/unresolved Git state and 430 input hashes,
and cannot serve as the manifest for later strategy rows. The hypothesis CSV
contains metrics but no manifest pointer or dataset-version hashes.

## Untouched test status

There are zero `window=test` rows. That proves only that the log has no test
entry. The test windows are readable through ordinary commands and no access
ledger or sealed workflow prevents inspection, so “untouched” is unverified.
