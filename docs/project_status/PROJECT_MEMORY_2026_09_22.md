# Project memory and handoff — 2026-09-22

This is the durable restart note for `custom_terminal`. It records project
purpose, completed work, current local work, boundaries, and the next milestone
so the owner can safely pause this project and work on a different idea. It is a
status record, not new permission for provider access, research, trading, or
production activation.

## Project purpose

Build a private, local-first Indian-market information and decision-support
terminal that gradually combines:

- a clear market overview and current cash-equity coverage;
- market and sector context and an equity setup scanner;
- long-term allocation, goals, performance, benchmarks, news, and events;
- explicit data freshness, provenance, quality, and unavailable states;
- later, only after trustworthy point-in-time data and separate approval,
  governed research and explanatory scores.

The product is analysis-only. It must never place, modify, or cancel trades.
Unsupported values stay unavailable instead of being guessed. Visual completion
does not override source permission, identity, semantic, freshness, or quality
requirements.

## Product direction already decided

- The approved UI base is the current TradingQnA-inspired white layout: slim
  header, grouped left sidebar, compact cards/tables, restrained cyan accents,
  and generous spacing. Version 2.0 Static is a visual reference only; its data
  and logic are not merged.
- Visual refinement is paused until the data foundation works reliably.
- Equity-first is the active priority. F&O work is last.
- Trade Decision Helper, Options & Positioning, Trade Management, and other
  derivative-dependent surfaces stay hidden with their code retained.
- Dashboard and Market Gate demo values remain clearly synthetic until every
  frozen consumer eligibility gate passes and a separate wiring decision is made.
- Kite is for private current-market cash-equity display and transient in-memory
  processing. It is not a historically complete universe and cannot replace
  point-in-time historical membership, delisted securities, or corporate actions.
- Credentials, tokens, raw inventories, and raw quote payloads must not be saved
  to Git or durable project artifacts.

## Major milestones completed

1. Built the repository architecture, provider-neutral data contracts,
   provenance/quality gates, and synthetic research-governance infrastructure.
2. Investigated NSE F&O reports through bounded qualification, requalification,
   policy review, and quarantine experiments. Schemas and most joins were stable,
   but close-price-basis and date-wide trade-state attribution remained unresolved.
   The route remains `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`.
3. Deferred the alternative F&O corroboration route because no already legally
   retained, provider-attributed, semantically documented exact-contract evidence
   was available. F&O is intentionally last in the roadmap.
4. Built and accepted the website skeleton and current visual baseline, then hid
   F&O-dependent features while keeping their code.
5. Completed the data-readiness audit and mapped visible pages to their actual
   data needs and readiness states.
6. Built the synthetic, offline Dashboard watchlist contract and its presentation
   integration without pretending the fixture is live market data.
7. Built offline equity parsing, exact Decimal handling, readiness/freshness
   checks, quality diagnostics, missing-data rules, validation/refresh records,
   cash-session policy, and sanitized compliance contracts.
8. Added a private manual Kite daily-login flow. Secrets and tokens remain in the
   Streamlit process/session only and are removed on disconnect or rejection.
9. Added current-instrument inventory, current quote/OHLC/LTP controls, coverage
   health, an owner-supplied official NIFTY 50 CSV path, and the bounded two-batch
   25 + 25 quote workflow. The owner observed 50 returned and zero missing in the
   earlier operational coverage check; that is useful operational evidence, not
   source qualification or historical readiness.
10. Built an exact-price, read-only Kite transport offline: exactly 50 validated
    NSE cash equities, two ordered batches of 25, fixed quote endpoint, no retry,
    redirect, fallback, or persistent cache, bounded bytes/time, transactional
    combined output, exact Decimal facts, and transient results.
11. Built the local exact-target preflight and confirmation model and added UI
    guidance for authentication and inventory refresh. No new exact live request
    was made while implementing these controls.
12. Reviewed official Kite/NSE documentation for current-price semantics,
    sessions, and currency. Current LTP use is sufficiently defined for a bounded
    operational check. An explicit Kite REST binding of NSE EQ price fields to
    INR major units was not found, so `currency_state=NOT_VERIFIED` remains and
    the real-price Dashboard wiring gate remains closed.

## Current repository state

- Repository: `C:\Users\parik\OneDrive\Desktop\custon_new_terminal`
- Branch: `main`
- Last committed/pushed checkpoint: `e90ca10722124e608bef95bcd532cb85027c2bfe`
  (`Add offline equity readiness governance layers`)
- The work listed below is present locally but is not yet committed or pushed.
  Preserve it when resuming.

Local work includes:

- explicit-date cash-session and sanitized compliance contracts and tests;
- REST currency/unit documentation-review records and tests;
- exact two-batch Kite transport implementation, documentation, and tests;
- exact target-binding preflight implementation, UI, documentation, and tests;
- IST inventory session-date correction;
- Dashboard eligibility and milestone-checklist updates;
- clearer authentication/inventory-refresh messages and disabled-state controls.

The local Streamlit site was running at `http://127.0.0.1:8505/` during this
session. Process state is temporary and must not be treated as a saved service.

## What is genuinely usable now

- The approved non-F&O application shell and navigation.
- Synthetic Dashboard/Market Gate presentation.
- Manual daily Kite authentication.
- Read-only, current-instrument inventory and manually requested current quotes.
- Official NIFTY 50 CSV upload fallback and current 50-equity identity matching.
- Existing manual 25 + 25 coverage check.
- Offline-tested exact Decimal decoding, session/compliance rules, readiness,
  quality diagnostics, and bounded exact transport/preflight components.

## What is not ready

- One-click daily current-equity checking is not yet implemented.
- Exact live transport has not yet been exposed as the simplified owner-triggered
  workflow or executed under that final UI.
- REST currency is not explicitly verified, so do not label provider price fields
  as INR or wire them into the production Dashboard.
- A maintained exchange-session calendar and provider-specific durable retention
  policy are still missing.
- Cash-index tiles, previous-close change semantics, historical equity prices,
  corporate actions, point-in-time membership, sector history, news rights,
  portfolio inputs, benchmarks, and event feeds are not yet qualified/wired.
- No real-data research, backtest, score, recommendation, or trading capability is
  authorized.
- NSE F&O remains unqualified, quarantined from UI/research, and last priority.

## User-experience finding from today

The separate authentication, inventory, list loading, preflight, hash review,
checkbox confirmation, and quote-test steps made a basic data check unnecessarily
complicated. Safety contracts should remain under the hood; the daily owner flow
should be simple and nontechnical.

Agreed target daily flow:

1. Paste/create today's Kite access session.
2. Upload the official NIFTY 50 CSV only when automatic official-list retrieval
   is unavailable.
3. Click **Check today's equity data**.

That single click should visibly disclose that it performs read-only requests,
then validate the session, refresh current inventory, bind exactly 50 current NSE
EQ targets, execute two quote batches of 25, and show requested, returned,
missing, unavailable, and freshness counts. Hashes, binding details, and technical
diagnostics belong in an optional **Technical details** expander. Nothing should
run automatically on page load or in the background.

## Exact next milestone

Implement the simplified, owner-triggered **Check today's equity data** workflow
without weakening the existing contracts:

- one deliberate click, no background polling;
- at most one inventory refresh plus the existing two bounded quote requests;
- exact current NSE EQ target validation and unchanged Decimal facts;
- sanitized progress and errors;
- transient in-memory results only, expired/cleared on failure, disconnect, or
  the frozen result lifetime;
- counts and availability shown by default; private row detail optional;
- no INR label while currency remains unverified;
- no Dashboard production wiring, persistence, research, recommendations, or
  trading;
- keep the older controls only inside technical details or remove their duplicate
  presentation after equivalent test coverage is preserved.

Before calling this milestone complete, test authentication missing/expired,
official-list failure plus CSV fallback, inventory mismatch, changed/expired
binding, first/second batch failure, partial/missing response, stale/expired
results, and the 50-returned/zero-missing success presentation. Update the scope
record to state that the single owner click orchestrates one inventory request
plus the separately bounded two quote requests.

## Remaining equity-first roadmap

After the simplified daily check:

1. Resolve or explicitly contain the REST currency-label limitation and add a
   maintained cash-session calendar.
2. Obtain the separate consumer approval needed to wire eligible current equity
   prices and health states into Dashboard.
3. Add approved cash-index tiles with an explicit previous-close/change basis.
4. Qualify historical equity prices, corporate actions, effective-dated sectors,
   historical membership, and delisted coverage.
5. Complete Market & Sector Context and Setup Scanner using only eligible inputs.
6. Add owner-input allocation, positions, and goal contracts.
7. Validate performance, benchmarks, cash flows, fees, dividends, correlations,
   and explanatory charts.
8. Activate permitted News & Calendar sources with publisher, timestamp, lineage,
   and retention controls.
9. Complete security, storage, privacy, expiry/reconnect, partial-failure, and
   private deployment checks.
10. Deploy the functioning private non-F&O terminal.
11. Only then consider separately governed real-data research.
12. Last, revisit NSE F&O semantics and source qualification.

## How to approach the owner's next related project

Use the lessons from this project but make the sequence visibly simpler:

1. Write a one-paragraph purpose and a short list of permanent exclusions.
2. Choose one useful screen and one user action, not the whole product.
3. Define the smallest data contract and use synthetic fixtures first.
4. Build the visible workflow early and keep technical evidence behind an
   optional details panel.
5. Add one source only after identity, time, units, permission, failure behavior,
   and retention are understood.
6. Test one happy path and the important fail-closed paths.
7. Let the owner use it, record friction, and simplify before adding another
   consumer.
8. End every milestone with: usable now, blocked, next step, and exact decision
   needed.

This keeps the same careful data discipline while avoiding a long chain of
owner-visible approvals for ordinary, reversible, read-only checks.

## Resume checklist

1. Read this file and `MILESTONE_CHECKLIST_V2.md`.
2. Confirm the Git baseline and preserve every existing modified/untracked file.
3. Run the focused equity session/compliance, exact transport, preflight, Kite,
   NIFTY 50, Dashboard eligibility, and UI governance tests.
4. Implement the simplified daily check as the next bounded milestone.
5. Do not commit/push, run live provider requests, or broaden scope unless the
   owner explicitly asks.
