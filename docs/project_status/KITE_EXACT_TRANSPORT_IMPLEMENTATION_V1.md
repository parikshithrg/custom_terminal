# Kite exact two-batch transport implementation v1

Implemented and tested offline on 2026-09-22 after the owner said to proceed with
the next test. This implements the transport core constrained by
`KITE_EXACT_LIVE_TEST_SCOPE_V1.json`; it does not authorize or perform a live
request, bind today's private targets, or wire any UI.

## Implemented boundary

- A pure local preflight binds exactly 50 unique, sorted, current `NSE` `EQ`
  inventory matches to the owner-supplied constituent and inventory hashes.
- The private identities and provider tokens remain in memory. Only a sanitized
  count/batch/hash summary is serializable for reporting.
- Execution requires a matching `OWNER_CONFIRMED_LOCAL_BINDING` object valid for
  no more than ten minutes. Missing, mismatched or expired approval stops before
  the injected HTTP client is called.
- Exactly two ordered GET transactions of 25 targets use the fixed HTTPS quote
  URL, identity encoding, no redirects, no retries, no cache and no fallback.
- Each response is limited to 64 KiB and the pair to 128 KiB. The transport checks
  the sixty-second total deadline while streaming, validates status, final URL,
  content type/encoding, declared length and nonempty completion, and closes every
  internally obtained response.
- Either transaction or combined decode failure returns only a sanitized error;
  no partial combined result is published.
- The common `as_of` is captured after both responses. The existing exact Decimal
  decoder preserves source precision and separate quote/trade/retrieval clocks.
- Results remain transient for a declared sixty seconds, retain currency as
  `NOT_VERIFIED`, and cannot persist, expose real data or authorize Dashboard use.

## Not implemented or authorized

No Streamlit/manual execution control was added because today's exact local target
binding and confirmation do not exist. No current Kite session, credentials,
instrument inventory, constituent CSV or provider endpoint was inspected. No live
request, market payload, cache, file/database output, research, trading, F&O work
or Dashboard wiring occurred.

The implementation is therefore ready for a separately approved local preflight
and owner confirmation. Only after the UI shows the sanitized binding hash and the
owner confirms it may the two-request operational test execute. That test can
establish bounded transport/decoder behavior only; the unresolved REST currency
binding and maintained official calendar still block Dashboard display.
