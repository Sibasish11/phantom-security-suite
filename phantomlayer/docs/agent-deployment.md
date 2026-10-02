# PhantomLayer customer agent (MVP)

Run the agent/proxy inside the customer network. Configure its production and honeypot database URLs in the customer secret manager as `PHANTOMLAYER_AGENT_REAL_DATABASE_URL` and `PHANTOMLAYER_AGENT_HONEYPOT_DATABASE_URL`; do not send either value to the PhantomLayer API.

Register the agent at `POST /agents/register`. Store the returned registration token only in the local secret manager. The agent sends an outbound `POST /agents/{id}/heartbeat` with that token in `X-Agent-Token` and reports only booleans for local connectivity plus a sanitized telemetry count.

The MVP is a control-plane registration and health abstraction. It does not clone a production database, run destructive database commands, or provide inbound access to customer infrastructure. A production agent should perform local gateway/deception routing, use TLS and tenant authentication, and batch only sanitized event metadata outbound.
