# R.10B implementation plan

R.10B extends the R.10A synthetic-only boundary. It does not alter R.10A's
committed evidence or research definitions.

The implementation has four deliberately small parts:

1. An immutable multi-object raw store publishes payload and manifest together,
   indexes stable source identities, reuses identical bytes and rejects identity
   conflicts.
2. A declared schema registry routes exact and additive schemas, records parser
   identity and quarantines breaking drift before downstream use.
3. An explicit dependency graph and causal impact planner choose rebuilds from
   domain, event, availability, effective interval and instrument scope.
4. Canonical logical-table hashes and exact build fingerprints prove selective
   reuse is equivalent to a clean rebuild even when container bytes differ.

Implementation and offline tests are committed first. Evidence generation then
starts from that clean checkpoint and refuses unexpected source changes. The
generated evidence and report are committed separately.

No market source, broker, private configuration, APSW production dependency,
Streamlit page, score or trading action is in scope.
