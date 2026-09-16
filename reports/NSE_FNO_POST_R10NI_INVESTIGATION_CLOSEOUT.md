# Post-R10N-I documentation investigation closeout

Outcome: investigation unresolved; the route remains unqualified. The owner approved the unchanged five-URL documentation scope and isolated review-copy retention after reviewing permission. This supersedes earlier pending execution records, not the historical qualification results. All three raw packages remain deleted; this task does not restore or requalify them.

## Acquisition and review

On 2026-09-16 the single bounded session made five GET transactions, with HTTP 200 for each fixed URL, zero redirects, retries or HEAD requests, and 961,466 received bytes. The largest response was 356,297 bytes; elapsed request-session time was 1.125 seconds. Limits remained eight transactions including hops, two hops per initial URL, 4 MiB/response, 8 MiB total, ten-second request timeout and thirty-minute session. No additional URL, link, circular, report, trade file, authentication, consent acceptance or contact message was accessed.

The PDF parsed as a 16-page unencrypted document. Both XLSX archives passed member/path, CRC and declared/actual expansion checks: 42 members/641,120 expanded bytes and 19 members/171,856 expanded bytes, below the approved 128-member, 32 MiB and 100x limits. Read-only spreadsheet inspection preserved workbook bytes; an unsupported slicer warning affected the reader only, with no workbook export or repair. The PDF and both XLSX hashes match the earlier R10N-G inventory. Only sanitized metadata and minimal paraphrases are tracked; full review copies are in an isolated ignored directory.

## Authority, policy and inference

The [NSE UDiFF catalogue](https://nsearchives.nseindia.com/web/mediaattachment/2026-06/Annexure_B_UDiFF_Catalogue_Ver4.0.xlsx_20260630115645.xlsx), Field Master rows 347-350 and 357, names daily opening/high/low/closing prices and total quantity separately. The [Trade and Bhavcopy formats](https://nsearchives.nseindia.com/web/mediaattachment/2026-06/UDiFF_trade_and_Bhavcopy_file_formats_20260630115803.xlsx) identify price precision and trade-status fields, but do not supply the required aggregate trade-contribution matrix. Clearing-corporation remarks about modified trades and custodian confirmation concern obligation computation; they must not be substituted for exchange bhavcopy OHLC rules.

The [NSE settlement methodology](https://www.nseindia.com/static/products-services/equity-derivatives-settlement-price), Daily Settlement table, explicitly distinguishes a last-half-hour NSE-based average for index futures from an across-exchange average for individual-security futures. It separately describes theoretical settlement for illiquid unexpired futures. This is authoritative calculation context, not proof of how UDiFF ClsPric maps to it or of either recorded exception. A weighted average over the same trades cannot exceed their extrema. A different cross-exchange universe is a plausible hypothesis, not verified case attribution or an accepted exception.

| Question | Established context | Still missing |
| --- | --- | --- |
| Exact close-field mapping | Distinct UDiFF fields and differing settlement-calculation universes | Explicit ClsPric mapping, each field's eligible trade universe/fallbacks, and 2026-09-10 applicability |
| Trade-state contributions | Status names exist; trade-status attribution is not a bhavcopy row field | Inclusion/exclusion rules for original, modified, cancelled, rejected, confirmed and special trades in every aggregate field |
| Applicability to the two observations | Sealed F/I evidence records two nonzero-volume stock-futures close-range cases | Authoritative case-applicability proof; raw-row and cross-exchange/trade-state verification is unavailable and not authorized |

The Forms & Formats page labels catalogue Version 4.0 and an update of 2026-06-30; the methodology page shows 2023-01-03. The PDF has a V2023.10 version label. Page updates, filenames and version labels do not establish effective-date applicability on 2026-09-10. Complete exact URLs, hashes, versions, dates and section locators are recorded in `document_inventory.json`.

## Source and retention closeout

The source remains `MULTI_DATE_SCHEMAS_STABLE_SOURCE_NOT_QUALIFIED`, with two `CLOSE_OUTSIDE_DAILY_RANGE_UNRESOLVED_BASIS` observations and one date-level `TRADE_STATE_ATTRIBUTION_UNAVAILABLE` diagnostic still blocking. Absence of a documented containment rule is not proof of validity. Every approved date must pass; no date is dropped, waiver applied, trade state inferred, price changed or historical result reinterpreted. Expiry decoding remains resolved. No adapter/diagnostic changes, implementation, reacquisition, requalification, ingestion, research, fingerprint refresh, production activation or deletion occurred.

Five documentation review copies remain retained under the approved earlier-of-owner-closeout-or-2026-12-31 rule. Owner closeout confirmation is pending; expiry/closeout must be handled without silently extending retention. Actual copy deletion requires separate exact-path authorization. No full document, raw report row, ticker, instrument identifier, cookie, credential, sensitive response header or private absolute path is tracked.

## Recommended separately authorized next step

Keep the route unqualified. The owner may defer, or separately authorize preparation of a scope amendment seeking an explicit NSE field-mapping/contribution clarification or specifically applicable official circular. Such preparation must name exact proposed sources or contact wording, budgets and privacy/retention controls before any new access or message. No new source/contact is approved here. Any later implementation, reacquisition and requalification require independent explicit scopes; owner approval is never authoritative source evidence.
