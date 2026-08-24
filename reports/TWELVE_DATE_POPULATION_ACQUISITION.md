# Twelve-Date Population Acquisition

Baseline commit: `94dbd08`; the working tree was clean. Locked dates were unchanged. Representative date: 2024-06-04.

| Official route | Purpose | Result |
|---|---|---|
| NSE All Reports | Report discovery | PASS for discoverability; current terms prohibit automation |
| NSE historical reports | Legacy bhavcopy archive | PASS for exact locked objects |
| `archives.nseindia.com/content/historical/EQUITIES/...` | 2016/2018 bhavcopy ZIP | PASS |
| `archives.nseindia.com/products/content/...` | 2020–2024 bhavcopy CSV | PASS |
| `nsearchives.nseindia.com/content/cm/...` | MII security and UDiFF bhavcopy | PASS for three post-start snapshots and 2025 prices |
| NSE/MSD/60315 | MII provenance | PASS; website start 2024-02-05 |
| NSE circular/archive indexes | Pre-2024 snapshot discovery | UNKNOWN; no complete public index established |
| Member extranet references | Earlier security files | BLOCKED because membership/authentication is required |

Requests used a named user agent, one-second pacing, two retries, content/schema checks, and content-addressed caching. URL, timestamp, HTTP status, headers, content type, size, and SHA-256 are stored in ignored manifests.

- Requested: 15 exact objects.
- Retrieved: 15 (12 bhavcopies, 3 MII snapshots).
- Quarantined: 0.
- CAPTCHA/authentication/rate-limit responses: 0.
- Security snapshots blocked/not requested: 9.
- Large raw objects committed: 0.

Acquisition stopped after current NSE terms were reviewed and found to prohibit systematic or automated collection. No later network request occurred. Raw objects remain in ignored `artifacts/population_a8/`; Git receives only hashes, schemas, and summaries.
