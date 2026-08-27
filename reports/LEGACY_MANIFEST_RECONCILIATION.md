# Legacy Manifest and Artifact Reconciliation

## Search boundary

The read-only adapter accepts explicit roots and records only relative paths:

1. the ignored `runs/` tree retained inside this repository;
2. the ignored `runs/` tree in the sibling source checkout.

No search occurs outside those declared roots. Resolved paths are checked to
prevent boundary traversal. The adapter never matches a row by title or
timestamp at runtime; exact candidates come from the reviewed row-ID mapping.

## Result

| Provenance classification | Rows | Meaning |
|---|---:|---|
| `VERIFIED_MANIFEST` | 0 | No hypothesis row has a deterministically linked root run manifest. |
| `PARTIAL_ARTIFACTS_NO_MANIFEST` | 29 | Reviewed exact result/placebo/portfolio paths exist and are hashed, but no root manifest binds them to code, inputs and environment. |
| `AMBIGUOUS_ARTIFACT_MATCH` | 3 | Candidate files exist but cannot be deterministically assigned to one historical run. |
| `MISSING_MANIFEST` | 0 | No row asserted a manifest path that was then absent. |
| `MISSING_ARTIFACTS` | 0 | Every reviewed row had at least a plausible saved artifact at inspection time. |

The three ambiguous rows are:

- `cdd796d6e171`, the earlier primary pairs run;
- `0b11b017cef9`, the later primary pairs run after a roll-forward fix;
- `7facf033cb36`, MF accumulation in the mutable sibling checkout.

The two primary pairs rows point at the same saved filenames, which do not
contain a row ID. The MF folder is unique by name, but is ignored, mutable, and
not bound to the designated 32-row state. Exact current file hashes are
preserved as candidates; none is promoted to verified evidence.

## Unrelated manifest

Both checked run trees contain the same `audit_data/manifest.json`, SHA-256
`64288ce7f8f056e25bbcadf8f01bdec410b78e1b25b180b508f4a761f5e9ba10`.
It records a data audit, contains no hypothesis row ID, and cannot serve as a
manifest for any of the 32 rows.

No replacement manifest was constructed. Missing code commits, dirty-tree
fingerprints, row-specific configuration hashes, environment fingerprints and
dataset hashes remain missing.
