# R.10C implementation plan

R.10C composes the existing security master, identity resolution, corporate-
action integrity, terminal classifications, outcome layer, and R.10B dependency
machinery. The older contracts remain compatible and unchanged.

The smallest unification is one typed security-event module that adds:

- source-specific immutable event vintages and causal as-of views;
- explicit issuer, listing, instrument and dated-alias assertions;
- validated successor/predecessor relationships;
- separately materialized split/bonus factors and adjusted views;
- evidence-bound cash/share/mixed terminal-economic resolution;
- outcome reconciliation that never removes unresolved predictions.

Synthetic fixtures use fictional identifiers and generic schemas. They do not
claim official NSE compatibility or market validity. Implementation and tests
are committed first; evidence is generated from the exact clean checkpoint and
committed separately.
