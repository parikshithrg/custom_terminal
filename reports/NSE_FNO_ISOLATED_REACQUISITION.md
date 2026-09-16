# Isolated NSE package reacquisition

Owner authorized exactly the three previously tested packages for an isolated comparison, retained through 2026-12-31 without production activation.

Result: all three paired packages were reacquired in six GET transactions (all HTTP 200), with no redirects or retries. All six payload sizes and SHA-256 hashes match sealed R10N-I integrity evidence. Newly timestamped acquisition manifests are not substitutes for historical manifests.

The packages are in the ignored directory recorded in `reacquisition_receipt.json`; original deleted package locations remain absent. No payload, raw row, instrument identifier or contract inventory is tracked. Historical evidence and adapter contracts are unchanged.

Existing offline downloader and deletion governance preflight: 72 passed. No quarantine table, alternative-source payload comparison, sensitivity test, price substitution, diagnostic waiver, source qualification or production activation has occurred in this reacquisition step.

Next: implement the previously requested isolated quarantine and exact-contract corroboration experiment. Fix consumer/test scope and materiality thresholds before viewing exclusion results. These three dates alone cannot establish strategy-wide return/drawdown sensitivity over a continuous history. Lack of a large measured effect does not prove source semantics or authorize deleting evidence. Keep the original route unqualified and any filtered experiment separate.
