# PhantomLayer customer agent (MVP)

For PhantomBank, follow [CUSTOMER-ONBOARDING.md](CUSTOMER-ONBOARDING.md): the real
request adapter and heartbeat are embedded in `bank-api`, installed using the
one-time customer bundle. Do not run a second generic agent for that deployment.

Run the agent/proxy inside the customer network. Configure its production and honeypot database URLs in the customer secret manager as `PHANTOMLAYER_AGENT_REAL_DATABASE_URL` and `PHANTOMLAYER_AGENT_HONEYPOT_DATABASE_URL`; do not send either value to the PhantomLayer API.

Register the agent at `POST /agents/register`. Store the returned registration token only in the local secret manager. The agent sends an outbound `POST /agents/{id}/heartbeat` with that token in `X-Agent-Token` and reports only booleans for local connectivity plus a sanitized telemetry count.

The generic agent is a control-plane registration and health abstraction. A health
probe alone does not activate protection: the integration must report
`integration_ready=true` from its installed request-routing adapter. The bank
adapter implements that data path. Heartbeat freshness is 90 seconds. Neither
agent clones production data or provides inbound database access. Use TLS and
managed credentials for nonlocal deployment. Registration/rotation requires a
tenant admin; only a credential hash is stored by the SaaS.
