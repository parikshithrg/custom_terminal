# NIFTY 50 manual operational test

Baseline `d2470c7`; initial worktree clean. Owner approved the proposed two-batch
equity test, official current constituent list, memory-only results, no Dashboard
wiring. Owner reported session validation succeeded; not independently observed.

Data Coverage → Current Quotes → NIFTY 50 two-batch test:
1. Load today's current inventory using the existing manual inventory control.
2. Load the official latest published NIFTY 50 constituent list.
3. Click Test all 50 equities to request two batches of 25 full quotes.

The [official NIFTY 50 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty--50)
links its Index Constituent download to the fixed CSV route used by the tool.
Web access confirmed the link, but could not render its octet-stream response;
no current constituent payload or live Kite quotes were inspected by the agent.
CSV contents are validated only after the owner's manual load succeeds.

List budget: one fixed HTTPS GET, ten-second timeout, no redirect/retry, at most
64 KiB decoded response; explicit content-type and CSV checks. Exact 50 distinct
EQ symbols/ISINs required, hash/retrieval/source bound in memory. Retrieval date
is not the publication/effective date; this is latest published membership only,
not historical or independently certified same-day effective membership.
No guessed/static/fallback roster or date enumeration.

Crosswalk: same-day retrieved current Kite inventory, one unflagged NSE/EQ/NSE
record per symbol, positive unique provider tokens, no expiry. This validates
current operational symbol/token matching, not a permanent ISIN security master.
Sorted deterministic keys split 25+25; the provider's existing 25-key limit stays
unchanged. At most two existing quote-client operations, 20-second timeout each,
15-second cache; no automatic retry/polling. Both batches required before combined
publication. Explicit missing rows remain visible; unexpected/invalid prices,
stale cache or incompatible batches fail closed. Intermediate client caches may
exist in memory after failure, but no partial combined result is displayed.

Display only instrument/status/last price/provider timestamp/message and batch
counts/retrieval/cache state. No OI/derivative columns, price repair, scores,
streaming or simultaneous-snapshot claim. Existing float parser, merged provider
timestamp and unknown market session remain limitations: this operational test
does not qualify precise-price/freshness semantics or promote a source.

Memory-only constituent metadata/quote results live under kite_ session keys and
clear on disconnect/reconnect. No payload file/export, credentials or real rows
tracked. Existing manual controls unchanged; Dashboard stays synthetic. F&O stays
deferred/unqualified and NSE retention unchanged. No research/activation/deletion.

264 focused tests passed, including new batch/CSV/crosswalk/failure/cleanup and
zero-request panel-load tests plus all 253 prior auth/contract/UI/governance checks.
Compilation/privacy/staged diff checks passed. No full root/live-suite claim;
known unrelated fingerprint/R9K failures untouched. Server deliberately not
restarted to preserve the owner's authenticated in-memory session.
Live outcome remains NOT_TESTED_BY_AGENT until the owner runs the manual controls
and reports aggregate returned/missing counts or a sanitized error.
