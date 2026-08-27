# Legacy Experiment-Family Mapping

## Method

`specs/legacy_family_mapping_v1.json` assigns each exact row ID to a reviewed
family and variant. Runtime title similarity is prohibited. The mapping also
records split variants, diagnostics and reviewed lineage without altering the
legacy CSV's empty `supersedes` field.

All 32 rows map exactly once. There are no unresolved-family rows.

| Family | Rows | Main variants and lineage |
|---|---:|---|
| Mean reversion | 2 | primary/train and delivery/train |
| Delivery breakout | 1 | delivery/train |
| OI momentum | 2 | primary/train and delivery/train |
| Participant tilt | 2 | base row and adaptive calm-tercile stress gate |
| Volatility-squeeze breakout | 3 | immediate primary, delay-2 primary, delivery split |
| Price action | 2 | primary/train and delivery/train long side |
| Pairs reversion | 3 | pre-fix primary, roll-forward-fix primary, delivery split |
| Same-sector pairing | 10 | random/liquidity, train/validation/delivery, Oil & Gas diagnostics |
| 12-1 momentum | 3 | primary train, delivery train, delivery validation |
| Earnings surprise | 1 | SUE/PEAD primary/train |
| Value | 1 | trailing P/E versus own history |
| Quality | 1 | margin trend |
| MF accumulation | 1 | Axis+SBI delivery/train |

## Diagnostic treatment

- The delay-2 volatility-squeeze row remains in the volatility-squeeze family.
- The calm-tercile stress gate remains in the participant-tilt family.
- Oil & Gas rows remain sector diagnostics in the same-sector family.
- Primary versus delivery splits are variants, not new economic families.
- Validation rows link to their reviewed train parents but do not supersede the
  source rows.
- The two primary pairs rows are separate variants because the later notes
  record a roll-forward-at-entry fix.
- MF accumulation is the thirteenth family and the 32nd row; no missing
  manifest or horizon is invented for it.

## Component reconstruction

Only fields proved by the exact row or reviewed mapping are populated:

- economic story;
- split/window;
- exploratory research status under the retroactive policy;
- family and variant;
- 60-, 126- and 60-session horizons for earnings, value and quality because
  those values are written in their exact row notes.

The selection rule, decision clock, entry rule, exit overlay, cost schedule and
portfolio construction remain `UNRESOLVED_NO_RUN_MANIFEST` for all 32 rows.
Holding horizon remains unresolved for the other 29. R.1 source-code knowledge
is not silently asserted as the configuration of an unmanifested historical
run.
