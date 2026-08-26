# Population Capability Reconciliation

The shared versioned definitions are in
`specs/shared_population_capabilities_v1.json`. This milestone does not promote
any capability.

| Capability | Current status | Reconciliation |
|---|---|---|
| `historically_traded_population_reconstructible` | UNKNOWN | Bhavcopies can enumerate securities that traded. A.8 obtained all 12 locked trade files, but full-period coverage, revisions and permitted immutable retention are not established. |
| `historically_listed_population_reconstructible` | FAIL | A.8 has only 3/12 direct dated security snapshots and no complete event-ledger alternative. |
| `inactive_security_coverage` | UNKNOWN | Three modern snapshots retain non-trading rows; the intended historical interval does not. |
| `suspension_history_available` | UNKNOWN | No complete authoritative suspension/resumption ledger is qualified. |
| `terminal_outcomes_available` | FAIL | Delisting, merger and successor economics remain materially unresolved. |
| `stable_security_identity_verified` | FAIL | Dated identity works in three modern samples only; ticker-keyed historical panels remain unresolved. |

## What `dtest` actually reconstructs

`dtest.universe.build_universe` causally recomputes a liquidity-ranked universe
from symbols that appear in its price panel. Within those supplied rows it uses
only past turnover, history, staleness and price. That is useful and avoids a
current-index-constituent rule.

It does not prove the panel contains every listed security, every suspended
security, or every subsequently inactive listing. Its symbol columns are not
stable security identities. Accordingly, the precise claim is:

> A point-in-time liquidity rule over the observed historically traded panel.

It must not be described as a complete historical NSE listed population.

## Defensible traded-population-only questions

Subject to price provenance, identity and terminal caveats, traded-population
scope can support descriptive questions such as:

- cross-sectional properties among securities actually observed trading on a
  session;
- liquidity and turnover distributions of observed traded rows;
- signal behavior conditional on continuous observed history;
- sensitivity analyses that explicitly censor gaps and do not generalize to
  inactive listings.

It cannot support production-grade claims requiring complete eligible
population, survivorship-safe portfolio returns, suspension-aware selection,
delisting economics, stable issuer continuity, or index-like historical
membership. These restrictions apply even if every available bhavcopy was
parsed successfully.
