# Vertical Slice A.8 — Twelve-Date Historical Population Acquisition and Qualification

A.8 answered the decisive question negatively for the locked sample: official public evidence obtained here cannot reconstruct the NSE cash-equity population on all fixed dates. Twelve bhavcopies are not twelve populations. Only three direct dated MII snapshots fall within the documented website-product period.

- Baseline: clean `94dbd08`.
- Representative pair: 2024-06-04, qualified.
- Requested/retrieved/quarantined: 15 / 15 / 0.
- Bhavcopies: 12/12; dated security snapshots: 3/12; qualified pairs: 3/12.
- Non-trading EQ rows preserved: 1,488; 1,611; 1,557.
- Price-only EQ rows: zero.
- ISIN coverage: 98.97%, 99.03%, 99.05%.
- Cross-date additions/removals: 242/62 and 98/22; all causally unresolved.

Direct reconstruction fails at 3/12. Event-derived reconstruction fails because selected circulars are not a complete ledger. Modern non-trading evidence cannot establish inactive/terminated coverage back to 2016.

After the bounded requests, current NSE Terms of Use were found to prohibit systematic/automated collection. Acquisition stopped. Automated retrieval is `FAIL`; retention and derived use are `REQUIRES_REVIEW`. No raw payload is committed or redistributed.

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`: **50 passed**.
- With `PYTHONPATH` set to the absolute `Data test` directory, `.\.venv\Scripts\python.exe -m pytest "Data test\tests" -q --basetemp=.pytest_tmp/a8-legacy`: **289 passed**, with existing SWIG deprecation warnings only.
- JSON validation: **18 versioned specifications parsed successfully**.
- Protected momentum specification, golden fixture, prior reports/manifests, and prior raw payloads: no diff.

| Capability | A.8 status |
|---|---|
| Historical population sample | FAIL — 3/12 pairs |
| Historical universe reconstructible | FAIL |
| Survivorship safe | UNKNOWN |
| Stable security identity verified | FAIL |
| Direct snapshot reconstructibility | FAIL |
| Event-derived reconstructibility | FAIL |
| Production historical coverage | FAIL |
| Experiment readiness | FAIL |

`momentum_12_1_v1`, its golden fixture, earlier manifests/raw payloads, and A.5–A.7 verdicts were unchanged. No 2024 pilot, momentum rerun, Slice B, production score, or decision integration occurred.

## Final readiness decision

`HISTORICAL_POPULATION_RECONSTRUCTION_INCOMPLETE`

## Recommended next milestone

Obtain written NSE/NSE Data clarification covering manual access, immutable local retention, and non-commercial derived research, and ask whether official pre-2024 dated security snapshots can be supplied without a paid-data relationship. Do not acquire more files first.
