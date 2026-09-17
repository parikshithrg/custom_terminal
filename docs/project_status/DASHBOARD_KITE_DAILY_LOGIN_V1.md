# Dashboard manual Kite daily login

Owner explicitly requested Dashboard API login/key/secret and daily-token entry.
Implemented against `fa0c428`; initial worktree clean. This authorizes manual
authentication convenience, not new automatic acquisition or source activation.

Click **Kite API login** on Dashboard. All credential fields are masked.
Normal flow: enter API key/secret, open the official Zerodha login link, complete
login yourself and paste its request_token or redirect URL, then create the daily
session. The existing authentication primitive performs one POST token exchange.
Alternatively paste an already-created access token with its API key; no secret
or request is needed for local attachment. Attachment is not provider validation.
The official browser flow returns request_token, not access_token.
[Official login documentation](https://kite.trade/docs/connect/v3/user/#login-flow)

Inputs are bounded and never written to files or Git. Secret/request/access-token
widgets are removed after successful or failed attempts. Reconnection first
removes prior session/client/inventory/quote state. The new session shares the
existing manual Data Coverage client, with validation NOT_VALIDATED.
Disconnect clears all Kite application references; secure memory erasure is not
claimed. Sessions survive app reruns, not restarts/new browser sessions.

No page-load requests, automatic validation/inventory/quotes, background polling,
orders or token printing. Dashboard values remain synthetic; owner login does
not make the new watchlist contracts eligible for real data. Existing Data
Coverage controls retain their scope. F&O/retention/history restrictions unchanged.
No real credentials or live login were used during implementation.

253 focused tests passed, including fake-HTTP token exchange/failure, zero-network
direct attachment, old-cache cleanup, error sanitization, password widgets,
Dashboard open/attach/disconnect and prior parser/readiness/UI/governance checks.
Compilation/privacy/staged diff checks passed. One initial test assertion used
the AppTest element type instead of its password protobuf type; corrected without
changing widget masking. No full root/live suite; known unrelated fingerprint/R9K
failures untouched. Local preview restarted to load the new button.
