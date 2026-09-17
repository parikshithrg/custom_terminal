# Owner priority update — equity-first site

Recorded 2026-09-17. Supersedes the earlier audit's ordering and futures-demo
proposal, not its historical findings. Owner requested moving F&O issues to
last priority, until a functioning non-F&O site is ready, and hiding dependent
sections. Visual styling remains the accepted baseline.

## Ordered build sequence

1. Freeze and implement the offline **equity-only** Dashboard watchlist contract
   proposed in `NEXT_DATA_FOUNDATION_BUILD_PROMPT.md`; no real provider activation.
2. Separately scope legacy news execution/readiness gating and freeze retained
   non-F&O consumer data requirements (equities, cash indices, portfolio inputs,
   benchmarks and events). Do not execute legacy automatic paths for planning.
3. Qualify and obtain permission/authorization for one non-F&O source/consumer;
   wire it only after identity, timestamps, freshness and quality gates pass.
4. Incrementally complete and validate the non-F&O site: overview/scanner,
   investment/goal/benchmark features and events, using only eligible inputs.
   Unsupported analytical outputs stay unavailable; research remains separately
   gated. A functioning site is not defined by filling every panel with mocks.
5. **Last: revisit NSE F&O semantics, alternative evidence and qualification**,
   then separately authorize any implementation/requalification or restoration
   of derivative features. Do not reopen resolved expiry decoding.

## Temporary presentation boundaries

- Futures watchlist choice and F&O readiness panel hidden on Dashboard and
  Market Gate. Synthetic futures fixtures remain in code, unused.
- Data Coverage displays/selects only NSE/BSE EQ and INDICES inventory members;
  derivative metrics and previously cached derivative quote rows are hidden.
  Unknown/unclassified instruments fail closed for this cash-only display.
  Health/export counts explicitly describe that subset, not provider completeness.
  Filtering is presentation-only: full provider snapshots and source prices are
  not mutated. Existing manual current-data client/endpoints are unchanged;
  no authentication/request is performed by this update.
- Options & Positioning, Trade Decision Helper and Trade Management stay hidden.
  Event Risk Assessment is additionally hidden because its legacy stress path
  uses a gold futures series; Reports is hidden because its current single
  legacy report mixes F&O/OI-dependent results. Their files and metadata remain.
- Equity-capable Market & Sector Context/Setup Scanner and investment pages stay
  visible but unwired. This does not approve future derivative inputs, scores,
  research or providers. India VIX remains an explicitly synthetic index tile,
  not an option-chain integration or permission to source derivatives data.

NSE remains `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`. Experimental
quarantine outputs cannot feed UI or research. Alternative corroboration stays
deferred; no acquisition/comparison, source waiver, retention amendment, evidence
rewrite, fingerprint refresh or deletion. The 2026-12-31 retention deadline is
unchanged: deprioritization does not extend retention or authorize disposal.

This update authorizes presentation hiding and priority recording only. The
next contract implementation and any real-source activation still need their
previously required separate approvals.
