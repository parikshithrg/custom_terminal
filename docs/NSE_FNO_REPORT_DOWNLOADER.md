# NSE F&O single-date report downloader

`tools/download_nse_fno_reports.py` prepares or downloads one explicitly
selected NSE F&O trading-date package. It supports the UDiFF daily bhavcopy,
the NSE-exclusive MII contract master, or both.

The utility deliberately has no date-range, archive-enumeration, retry, schema
parsing, research, or production-ingestion behavior. Downloads are written
under the ignored `artifacts/` directory by default. Existing packages are
never overwritten.

## Review the plan without network access

From the repository root:

```powershell
python -c "from tools.download_nse_fno_reports import main; raise SystemExit(main())" --date 2026-09-09 --report both --dry-run
```

The plan prints the exact official HTTPS URLs and expected filenames without
making a request.

## Download after confirming retention authority

Review these policies first:

- <https://www.nseindia.com/static/nse-terms-of-use>
- <https://www.nseindia.com/static/nse-copyright>
- <https://www.nseindia.com/static/market-data/nse-data-policy>

Only if your use and retention are permitted, run:

```powershell
python -c "from tools.download_nse_fno_reports import main; raise SystemExit(main())" --date 2026-09-09 --report both --acknowledge-nse-terms
```

The utility downloads at most two files for that one date, validates ZIP/GZIP
signatures, imposes a per-file streaming byte limit, and writes a sanitized
manifest containing source URLs, timestamps, sizes, response metadata, and
SHA-256 hashes. It stops on access-control responses and does not attempt to
bypass CAPTCHA, HTTP 403/429, or redirects to non-NSE hosts.

Use `--output-root` to choose another local destination and `--max-bytes` to
lower the per-file limit. The default destination is
`artifacts/nse_fno_reports/<YYYY-MM-DD>/`.
