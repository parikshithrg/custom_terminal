# Vertical Slice A.7 — Manual Official-Evidence Qualification and One-Year Archive Readiness

## Outcome

A.7 adds deterministic lifecycle, population, benchmark, cost, and archive-pilot gates. Missing evidence remains missing: the lifecycle quotas, 12-date population sample, benchmarks, historical costs, and one-year pilot are incomplete or blocked.

The inspected baseline was clean commit `afa5d74` (`Qualify official public market data sources`) except for a pre-existing untracked local `.pytest_tmp/` directory, which is now ignored. Earlier relevant commits were `493e883` and `56312cf`.

| Layer | Result |
|---|---|
| Individual-source accessibility | PARTIAL |
| Sample qualification | INCOMPLETE |
| One-year pilot readiness | BLOCKED |
| One-year pilot completion | NOT EXECUTED |
| Production historical coverage | FAIL |
| Experiment readiness | FAIL |

## Changes

- Evidence normalization preserves conflicting official assertions.
- Economic-terminal logic rejects last-price-only treatment.
- Paired security/price reconciliation preserves non-trading and unresolved rows.
- PRI/TRI identity and classification are strict.
- Date-effective costs expose gaps without backward inheritance.
- A 2024 pilot specification declares completeness and abort gates.
- Root pytest discovery now collects `tests/` only; `Data test` remains separately runnable.

No external object was retrieved in A.7. No raw object was overwritten or committed. The A.6 manifests retain the exact qualified and quarantined bytes.

Official public surfaces reviewed were NSE All Reports and historical reports, NSE/NSE Indices methodology and PRI/TRI reports, BSE listed securities, and SEBI regulations/circulars. AMFI was not used because it is not equity identity or survivorship evidence.

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`: **42 passed**.
- With `PYTHONPATH` set to the absolute `Data test` directory, `.\.venv\Scripts\python.exe -m pytest "Data test\tests" -q --basetemp=.pytest_tmp/a7-legacy`: **289 passed**, with only existing SWIG deprecation warnings.
- Every JSON specification parsed successfully.

Capabilities remain: price completeness FAIL; survivorship UNKNOWN; historical universe reconstruction FAIL; corporate actions UNKNOWN; delisting outcomes FAIL; turnover UNKNOWN at production scale; publication timing UNKNOWN; stable identity FAIL.

`momentum_12_1_v1`, its golden fixture, earlier manifests, A.5 verdict, and A.6 artifacts were not modified. No momentum run, Slice B work, production score, or decision integration occurred.

## Final readiness decision

`PUBLIC_SOURCES_REQUIRE_FURTHER_MANUAL_EVIDENCE`

## Recommended next milestone

Manually prove ordinary, retainable access to one paired historical NSE security snapshot and bhavcopy for each fixed sample date, then execute only the 12-date population qualification before reconsidering the 2024 pilot.
