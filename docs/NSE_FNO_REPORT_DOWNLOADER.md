# NSE F&O single-date report downloader

`tools/download_nse_fno_reports.py` prepares or downloads one explicitly
selected NSE F&O trading-date package. It supports the UDiFF daily bhavcopy,
the NSE-exclusive MII contract master, or both.

The utility deliberately has no date-range, archive-enumeration, retry, schema
parsing, research, or production-ingestion behavior. Downloads are written
under the ignored `artifacts/` directory by default. Existing packages are
never overwritten.

Publication is transactional. Both selected archives and the manifest are
completed in one uniquely named staging directory beside the destination. A
single directory rename publishes the completed package. Any download,
validation, manifest, or publication failure removes only that run's staging
directory and leaves no partial final package.

## Review the plan without network access

From the repository root:

```powershell
python -c "from tools.download_nse_fno_reports import main; raise SystemExit(main())" --date 2026-09-09 --report both --dry-run
```

The plan prints the exact official HTTPS URLs and expected filenames without
creating an HTTP session, making a request, creating the output directory, or
retaining a payload.

## Download after confirming retention authority

Review these policies first:

- <https://www.nseindia.com/static/nse-terms-of-use>
- <https://www.nseindia.com/static/nse-copyright>
- <https://www.nseindia.com/static/market-data/nse-data-policy>

Only if your use and retention are permitted, run:

```powershell
python -c "from tools.download_nse_fno_reports import main; raise SystemExit(main())" --date 2026-09-09 --report both --acknowledge-nse-terms
```

The utility downloads at most two files for that one date. It validates the
initial URL, every redirect source and destination, and the final URL against
the official HTTPS host allowlist. It rejects access-control responses,
unexpected content types, empty or truncated responses, and compressed-size
limit violations.

ZIP and GZIP integrity are checked without extracting members to disk.
Validation rejects corrupt archives, unsafe or absolute member paths,
encrypted or symbolic-link ZIP members, excessive member counts, excessive
declared or observed expansion, and excessive compression ratios. The default
limits are eight members, 1 GiB expanded data, and a 250:1 expansion ratio.

The sanitized manifest contains only official URLs, timestamps, sizes,
SHA-256 hashes, bounded archive-validation results, and an allowlisted subset
of response metadata. Cookies, authorization headers, response bodies,
credentials, and local absolute paths are never included. An internally
created HTTP session is closed; an injected session remains caller-owned.

Use `--output-root` to choose another local destination and `--max-bytes` to
lower the per-file limit. The default destination is
`artifacts/nse_fno_reports/<YYYY-MM-DD>/`.

## R.10N-A preflight

The required `2026-09-09` dry-run proposed exactly:

- `BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip` from
  `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20260909_F_0000.csv.zip`
- `NSE_FO_contract_09092026.csv.gz` from
  `https://nsearchives.nseindia.com/content/fo/NSE_FO_contract_09092026.csv.gz`

The run reported zero network requests and zero retained payloads, and its
fresh output target did not exist afterward. R.10N-A does not authorize the
non-dry-run command. See `reports/NSE_FNO_OWNER_RETENTION_DECISION.md`.
