# Frozen-versus-Live Legacy Log Divergence

## Boundary

The frozen canonical legacy evidence remains:

- version `legacy_hypothesis_snapshot_v1`;
- 32 rows;
- SHA-256 `124886d439a90071a9b0f884851afbffdba5dd783e52c2cedaeb4b2ac82eae1d`.

The R.3 monitor read the live sibling CSV only to calculate its byte hash,
row IDs and exact historical-row equality. It did not copy, report or interpret
new metrics, titles, stories, decisions or diagnostics.

## Sanitized result

| Field | Result |
|---|---|
| Live row count | 34 |
| Live SHA-256 | `1e26df878db4e33ffddbbd5882aba18053afee79e200d803e0a1401e54cc2514` |
| Added row IDs | `270dd119a8fb`, `345373baf942` |
| Missing frozen row IDs | none |
| Modified frozen row IDs | `7facf033cb36` |
| Governed R.3 manifest for either addition | no |
| Diverged | yes |
| Classification | `POST_FREEZE_UNGOVERNED_ROWS` |

The modified-ID result means the live representation of that row is not exactly
equal to the frozen row. R.3 does not interpret the changed fields and does not
replace the frozen copy.

The two added rows are outside the frozen legacy boundary. Their existence is
not authorization for research and they are not imported into either evidence
catalog. A separate user-requested evidence audit would be required to inspect
them substantively.

Machine-readable result:
`evidence/governance/legacy_log_divergence_v1.json`, SHA-256
`9f5fa4bf8211eec4f4e9c86a88dc289f0ff64490543af04720e5a6dacd190174`.
