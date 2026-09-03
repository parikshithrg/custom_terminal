# F&O Production Interlocks

Production execution fails unless every future gate is satisfied:

1. A current reviewed PDF covers the exact binding phase.
2. Its research-state fingerprint is current.
3. The production activation object is exact.
4. The durable approval is registered.
5. The sampled file identity matches.
6. Stages are exactly `(1, 2, 3)`.
7. The resource envelope matches R.9A.
8. Expected outputs match R.9A.
9. The approval is unused and unexpired.
10. The source commit is clean and reviewed.
11. Protected evidence is unchanged.
12. A reviewed later commit removes the R.9D deliberate interlock.

R.9D cannot pass item 12. `evaluate_production_interlocks` always returns
`permitted=false`, and the production entry point raises
`PRODUCTION_LOCATOR_DISABLED_PENDING_EXACT_BINDING` before it could read a
configuration value or touch a target.

The activation template is non-executable and contains required placeholders.
PDF review is not audit approval. Synthetic-test completion is not locator
authority. Exact binding is not execution authority. A separate registered,
unexpired, one-use audit approval must be consumed atomically before the first
target SQLite connection.

The boundary imports no HTTP, broker, Kite, Streamlit, research, scoring,
portfolio, recommendation, or trading dependency. Runtime injection is also
rejected, so a caller cannot smuggle such a service through the boundary.
