# Split-Access Governance

## Controls

| Split | Required governed evidence | Consumption behavior |
|---|---|---|
| Training | Registered family, locked preregistration and passed preflight | Reusable only as declared family/experiment versions; no confirmation claim |
| Validation | One exact `VALIDATION_ACCESS_GRANTED` event bound to family, experiment, preregistration hash and dataset split | Event is retained and referenced by the root manifest |
| Test | One exact `TEST_ACCESS_GRANTED` event with an authorization ID and the same bindings | Gateway appends `TEST_ACCESS_CONSUMED`; the grant cannot be reused |
| Replication | `REPLICATION_REGISTERED` with exact bindings | Root manifest references the registration event |

The gateway rejects validation, test or replication execution when the exact
event is absent. A test grant is unique per family version. Once any test grant
exists, another cannot be issued for that family version; after consumption,
the gateway also rejects another attempt. Later test access therefore requires
a new family version and must be classified exploratory rather than retaining
confirmatory status.

## Bound authorization

Validation and test events bind:

- exact family ID/version;
- exact experiment ID/version;
- preregistration SHA-256;
- dataset split version;
- authorization ID and reason;
- actor classification and timestamp;
- previous catalog-event hash.

The root manifest retains the consumed or granted event ID and event hash. The
canonical importer validates that reference against the catalog.

## Security boundary

These controls govern the execution gateway and record authorized access. They
do not encrypt local split files or prevent the computer's filesystem owner
from opening them manually. Accordingly, “untouched” means there is no governed
or otherwise detected access event. It does not mean cryptographic secrecy.
Encrypted split storage and external access controls would be a separate future
security milestone.

Direct scripts cannot generate canonical evidence. Their outputs can be marked
`UNGOVERNED_NONCANONICAL_OUTPUT`, but R.3 cannot prevent a user from running
arbitrary local code outside the gateway.
