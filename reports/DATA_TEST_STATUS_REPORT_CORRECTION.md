# Correction Notice — Data Test Status Report

This notice preserves `Data_Test_Status_Report.pdf` unchanged and corrects only
claims that can be checked against the repository and the separately located
source checkout. The machine-readable source is
`specs/data_test_status_correction_v1.json`.

## Counts

| Evidence | Entries | Rejected | Accepted |
|---|---:|---:|---:|
| PDF headline | 32 | 26 | 6 |
| `custom_terminal/Data test` local log | 31 | 25 | 6 |
| Located sibling source-checkout log | 32 | 26 | 6 |

The missing repository-local row is `7facf033cb36`, `mf_accumulation
(Axis+SBI holdings, honest execution)`, a rejected delivery/train entry. It is
**located but not reproducible**: the row exists in the sibling checkout, but
the result has no per-run manifest linking code state, configuration, input
dataset hashes and output hashes. It is not copied into or appended to the
original repository-local log by this milestone.

## Validation wording

“None survived validation” is false under the old row-level vocabulary. The
log contains a momentum delivery/validation row marked `accepted`. The accurate
statement is:

> One momentum variant passed the legacy train and validation gates; no logged
> row reached the test window, no independent replication exists, and no result
> is production eligible.

The six accepted rows are not six independently accepted hypotheses. They are:

- two train rows for same-sector pairing, followed by two validation failures;
- one momentum train row and one momentum validation row;
- two Oil & Gas pairing train rows, followed by two validation failures.

Thus the six rows cover three families, and only momentum has an accepted
validation row.

## Provenance limits

- PDF SHA-256:
  `940efd19fa4b385230c3b5cb51e66c6cb2353e178381b0188e001c0f536bdae3`.
- The PDF names the sibling `Data test` checkout and was written at
  2026-08-26 11:58:01 IST.
- The matching generator source was committed 53 seconds later as `349cf124`;
  the PDF embeds neither a commit nor a dirty-tree fingerprint, so the exact
  generation state is unverified.
- The source log is ignored by Git. Its row history therefore cannot be
  reconstructed from the cited commit.
- The only located `dtest` manifest is the earlier `audit_data` manifest. It
  records 430 price-file hashes, but not the inputs of the 32 hypothesis rows.
- The report does not record dataset-version hashes or a report-generator
  version identifier.

The original PDF remains useful as a narrative snapshot, but it is not a root
experiment manifest or a reproducible status ledger.
