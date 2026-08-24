# Vertical Slice A.9 — Official Access and Rights Clarification Readiness

## Outcome

The clarification packet is complete but has not been transmitted because this workspace has no authorized email channel. No acquisition resumed.

Official contacts were verified from current NSE pages:

- `marketdata@nse.co.in`: historical/data product and licensing support.
- `nseri@nse.co.in`: Economic Policy & Research proposal route.

The request asks separately about manual access, automated access, immutable retention, correction vintages, derived non-commercial research, pre-2024 snapshots, paid/institutional requirements, display, and redistribution. A deterministic response gate rejects unofficial, unhashed, ambiguous, paid-only, non-retainable, or incomplete responses.

## Current gate

- Official response: not received.
- Additional acquisition authorized: no.
- Historical population capability: FAIL.
- A.8 decision: unchanged.
- Slice B and the 2024 pilot: blocked.

## Completion condition

The user sends `reports/NSE_DATA_CLARIFICATION_REQUEST.md` through an email account they control and attaches the exact official reply when received. The reply is retained, hashed, normalized into `specs/nse_official_response_template_v1.json`, and evaluated before any new download.

## Verification

- Root suite: **55 passed**.
- Separate `Data test` suite: **289 passed**, with existing SWIG warnings only.
- JSON validation: **20 specifications passed**.

## Current decision

`AWAITING_OFFICIAL_WRITTEN_RESPONSE`
