# First Governed Canary Review Checklist

## Before asking for approval

- Confirm clean `main` equals the reviewed remote commit.
- Confirm proposal-manifest and every proposal-object hash.
- Confirm the fixture remains exactly
  `b139b0d653a6171a2e07ae30ae770bdde5779d0d02cbc2f5fb6aee74bb1a15d2`.
- Bind the finalized input declaration to the exact clean Git commit, actual
  environment and dirty-worktree fingerprint; display its new hash.
- Display family `governance_canary__v1` and experiment
  `governance_canary_execution_v1__v1`.
- Display the canonical family and preregistration hashes after proposed
  registration/locking, before issuing approval.
- Confirm only the synthetic `train` split and
  `research_contracts.canary:run_governance_canary` are requested.
- Display the three exact runner artifacts and the gateway root manifest.
- Confirm lifecycle `INFRASTRUCTURE_CANARY_COMPLETED` and permanent
  `promotion_eligible=false`.
- Display the 5-second and 64-MiB declared, non-enforced limits and the enforced
  one-attempt consumption limit.
- Set a timezone-aware issue/expiry window no longer than 30 minutes.
- Confirm no network, market-data, broker, portfolio, scoring or trading path.

## Exact future approval question

After displaying all finalized hashes and bindings, ask:

> Do you explicitly authorize exactly one governed execution of
> `governance_canary_execution_v1__v1`, using the displayed family,
> preregistration, input, fixture and approval hashes, through
> `GovernedExecutionGateway.run`, before the displayed expiry time?

Only an explicit affirmative answer in that later turn, tied to the displayed
hashes, may be used to seal and register the approval. Silence, prior agreement,
approval of R.5, or a generic “continue” is not execution authorization.

## After explicit approval

The later operator action may register the exact family, lock the exact
preregistration, seal/register the exact approval and invoke the gateway once.
It must validate the atomic bundle and canonical importer result. Any changed
hash, expired window, unexpected artifact or reuse attempt stops the ceremony
and requires a fresh review and approval.

Approval to execute never authorizes interpretation, confirmation, promotion,
publication, production scoring, portfolio decisions or trading.
