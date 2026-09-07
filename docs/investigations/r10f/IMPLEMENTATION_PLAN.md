# R.10F implementation boundary

R.10F publishes the existing R.10E synthetic snapshot through a validated,
content-addressed immutable bundle and exposes it through a bounded read-only
facade. The application boundary copies no quantitative truth and imports no
scoring/fitting functions.

The slice includes deterministic freshness, publication eligibility,
supersession history and `NO_DECISION` gating. It does not connect to Streamlit
or version2.0, access real/private data or brokers, publish a real score, create
a recommendation, adopt APSW, or modify production interlocks.
