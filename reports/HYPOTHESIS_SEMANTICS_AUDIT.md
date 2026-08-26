# Hypothesis Semantics Audit

## Component contract

Every future experiment must bind, independently and explicitly:

- economic story;
- selection rule;
- decision clock;
- executable entry rule;
- holding horizon;
- exit overlay;
- date-effective cost schedule;
- portfolio construction;
- research split;
- exploratory, diagnostic or confirmatory status;
- experiment-family ID.

The neutral `HypothesisContract` implements this boundary. An economic signal
and an exit overlay are separate hypotheses unless the overlay was part of the
preregistered mechanism.

## Observed horizons

| Economic construction | Hold/exit in inspected implementation | Mechanism fit |
|---|---|---|
| Mean reversion | maximum 7 sessions, 2x ATR stop, 2.5R target | plausible short dislocation overlay, but overlay is not separately validated |
| Delivery breakout | same 7-session overlay | convenient common technical template; mechanism-specific horizon not established |
| OI momentum | same 7-session overlay | convenient template; contract/roll effects add risk |
| Participant tilt/stress gate | same 7-session overlay | short-horizon interpretation only |
| Volatility squeeze/delayed variant | same 7-session overlay | delay was selected through diagnostics; exploratory lineage |
| Price action | same 7-session overlay | short-horizon interpretation only |
| Pairs reversion | maximum 20 sessions or spread/roll event | distinct two-leg mechanism |
| Same-sector pairing/Oil & Gas | maximum 20 sessions or spread event | distinct two-leg mechanism; sector variants share family |
| 12-1 momentum | pure 21-session hold | monthly ranking/monthly outcome, not multi-month momentum performance |
| Earnings surprise | pure 60-session hold | approximately one quarter; closer to PEAD story |
| Value | pure 126-session hold | approximately six months |
| Quality | pure 60-session hold | medium-horizon fundamental trend |
| MF accumulation | reported in external log only | implementation/horizon absent from repository; not reproducible here |

The PDF statement that the same maximum seven-session exit is shared across
every signal is incorrect. Seven sessions is shared by a subset of technical
single-leg strategies. Momentum is 21 sessions, pairs are 20, earnings and
quality are 60, and value is 126.

No inspected current implementation computes a seven-session outcome following
the 12-1 rank. Both `Data test/scripts/test_momentum.py` and
`specs/momentum_12_1_v1.json` use 21 sessions. If a future seven-session 12-1
result is studied, it must be named as a short-horizon response to a long-horizon
ranking, not called conventional monthly or multi-month momentum.

## Split and status findings

- `dtest` uses fixed primary and delivery train/validation/test windows with a
  global 60-session embargo.
- The same economic title can be rerun on different split definitions without
  an explicit version/family link.
- Diagnostics informed later delay, stress and sector variants. Those are
  exploratory and cannot be retroactively called confirmatory.
- `market_intel` defines a 21-session outcome, horizon-derived purge/embargo and
  expanding walk-forward folds, but its local dataset trust gate blocks
  promotion.
- No old row is preregistered under the new contract. The economic story field
  is useful evidence of intent, but it does not lock parameters or dataset
  access before observation.
