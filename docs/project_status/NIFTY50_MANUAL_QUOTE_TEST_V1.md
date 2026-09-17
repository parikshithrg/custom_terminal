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

## Owner-approved timeout amendment — 2026-09-17

One bounded diagnostic GET encountered ReadTimeout under the original ten-second
limit; no payload was retained or quotes requested. Owner answered “yes” to
increasing only the constituent-list request timeout to 30 seconds. The fixed
URL, one GET, 64-KiB limit, no redirects/retries/fallback roster and all quote
boundaries remain unchanged. The original ten-second scope above is historical;
this explicit amendment supersedes only that timeout. Requests timeout is a
connect/read timeout, not a total download wall-clock guarantee.
Server restart and automatic refetch are not authorized by this amendment.

## Owner-approved official CSV upload amendment — 2026-09-17

After the fixed GET also timed out at 30 seconds, the owner approved a manual
upload option using the same validator. The owner downloads an unedited CSV from
the fixed official link, uploads it, declares its download date, and confirms its
official origin. Only today's IST download date is accepted; reuploading an old
copy cannot refresh its declared source date. This attestation does not
independently authenticate publisher provenance or effective membership.

The application accepts at most 64 KiB of UTF-8 CSV with exactly 50 unique EQ
symbols and ISINs. Streamlit's transport upload ceiling is one MiB; application
validation rejects files above 64 KiB before reading their contents. Accepted
metadata records OWNER_SUPPLIED_UPLOAD, the declared date, received timestamp,
fixed source URL and content hash, separately from DIRECT_OFFICIAL_GET.
Validation makes no HTTP requests. An invalid submission clears the previous
accepted list and combined results; it cannot silently fall back to either.

Upload bytes, declarations and results remain in Streamlit session memory under
kite_ keys, cleared on disconnect/reconnect. No filesystem output or alternative
roster is introduced. Same-day inventory checks and two manual 25-equity quote
batches remain unchanged. Dashboard remains synthetic; F&O, research and source
qualification remain excluded. Restart is separately gated because it clears
the owner's authenticated in-memory session.

Validation: 273 focused offline tests passed across upload/batch, authentication,
synthetic contracts, UI/cash scope and source governance. Compilation and diff
checks passed. No live upload or quote outcome is claimed; known unrelated root
fingerprint/R9K failures were not rerun or modified.
