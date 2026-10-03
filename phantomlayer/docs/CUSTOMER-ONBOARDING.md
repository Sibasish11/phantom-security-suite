# Customer onboarding: PhantomLayer + PhantomBank

The manual journey uses authenticated product APIs and the actual customer-side
bank adapter. **Do not run `provision_demo.py` for this journey.** Signup creates
one organization and its owner; login selects that organization from the signed
identity. This MVP does not implement multi-organization membership switching.

## 1. Start the customer application

Keep `phantomlayer/` and `PhantomBank/` beside one another. Initialize PhantomLayer
using its [README](../README.md), with `DEMO_MODE=true`, `AI_PROVIDER=mock`, and
`AI_ENABLED=false` for the local demonstration. From `PhantomBank/`:

```sh
./scripts/setup.sh
docker compose up --build -d --wait
```

A new bank `.env` starts in **standalone** mode without agent credentials. Existing
configuration is preserved. Open <http://localhost:3001/owner> for customer setup
instructions and the current deployment mode. The bank remains a separate
application, with its own real and deception PostgreSQL stores.

An already connected presentation environment can explicitly enter the BEFORE
deployment with `python scripts/connect.py standalone`. This requires bank
DEMO_MODE and saves the original configuration in owner-only
`.env.integration-backup`; an existing backup is never overwritten.
`python scripts/connect.py restore` restores that original connection afterward.
Neither command modifies database rows or removes volumes.

## 2. Account and organization

Visit <http://localhost:3000/signup>. Enter your organization, owner name, email
and password. Sign out and sign in if demonstrating login separately. Your
organization is created transactionally during signup. Every subsequent API
uses the authenticated server-side organization, never an organization selector
supplied as ownership by a request body.

## 3. Add and prove the domain

Use **`phantombank.example.test`** for this local fictional bank. `.test` is a
reserved demonstration namespace; this does not assert ownership of the public
`phantombank.com` domain. The existing `phantombank.com` tenant is not reassigned.

Production-shaped flow: add the displayed `_phantomlayer-verification.<domain>`
DNS TXT record, then click **Verify DNS record**. Challenges expire after 24 hours;
**Renew expired challenge** creates a replacement for an unverified domain.

Local flow:

1. Copy the TXT challenge from your own domain page.
2. On the bank host, from `PhantomBank/`, run:
   ```sh
   python scripts/connect.py verify
   ```
3. Paste the challenge at the prompt. The bank is recreated to publish it.
4. In PhantomLayer click **Use local demo verification**.

The SaaS checks a **fixed** local bank endpoint and requires that exact
tenant-specific challenge. Both applications must be in DEMO_MODE. Other domains
cannot use this path; production mode rejects it. There is no caller-supplied
verification URL, redirect following, arbitrary fetching, or unconditional
“verified” button. Local host access stands in for DNS-administrator access.

## 4. Protection and customer-specific installation

Select **API Protection**. This adapter protects the bank's implemented web/API
operations and routes deception to its separate honeypot. Database/internal/full
configuration templates do not install independent protection adapters.

On **Agent**:

1. Confirm the domain and organization displayed.
2. Click **Register agent** (owner/admin authorization required).
3. Click **Download integration configuration**. The credential is returned only
   by registration/rotation, held in page memory and downloaded; it is not
   displayed as a token or persisted in browser storage. Store the file privately.
4. From the bank directory:
   ```sh
   python scripts/connect.py install "$HOME/Downloads/phantomlayer-integration.json"
   ```

The local installer verifies the agent against the authenticated `/integrations/bank/identity`
contract, checks every organization/domain/agent identifier, stores `AGENT_ID` and
`AGENT_TOKEN` in owner-only `.env`, sets protected mode, and recreates `bank-api`.
It never writes control-plane rows. The local installer uses fixed loopback and
Compose addresses; downloaded files cannot redirect its credential to another URL.

No second agent container is needed. The adapter and heartbeat run inside
`bank-api`. If you lose the download, revisit Agent and **Rotate credential and
reconnect**. Rotation immediately invalidates the old credential and clears
previous readiness until the new credential heartbeats. Reinstall the new file.

## 5. What ACTIVE actually means

Registration starts **PENDING**. A connecting handshake can report **CONNECTING**;
successful probes report **HEALTHY**, failed probes **DEGRADED**, and a heartbeat
older than 90 seconds is **OFFLINE**. The bank sends every 30 seconds.

Protection is computed at read time, not set by an operator or stored status flag:

- active organization and verified domain;
- enabled API-compatible protection for that same organization/domain;
- fresh healthy agent for that same organization/domain;
- real DB and honeypot DB reachable from that agent;
- the request-routing integration reports installed/readiness.

The activation UI polls and lists specific missing conditions. A generic health
probe alone cannot activate bank protection. Configuring → Connecting → Active;
degradation/staleness removes Active, and disabled protection shows Paused.
Pausing protection causes configured bank requests to fail closed (503), never
switching into the standalone demo. Health is agent-reported, not remote attestation.

## 6. Traffic, investigation and trust boundary

```text
Bank browser → bank-api → authenticated operation-only decision → REAL or HONEYPOT
                       → local database access → bank response
                       → sanitized observation → tenant incident → SOC → mock analysis
```

The bank sends operation/session/optional peer-IP metadata, outcomes and deception
entity counts. Database URLs/passwords, bank authentication payloads and customer
records stay inside the bank. Separate bank data networks/volumes publish no DB
ports. The bank API/host is trusted and can reach both stores.

Deterministic rules and durable session history decide routing. Recon diverts at
risk 27; this is not an `if score >= 50` switch. Once diverted, ordinary-looking
follow-ups stay in deception. AI is downstream advisory analysis of a sanitized
projection and cannot override routing. In SOC open the incident, inspect rules,
stages, destinations, counts and timeline, then **Analyze incident**. The provider
is explicitly **mock**. Further interactions invalidate stale analysis.

## 7. Demonstration, QA and recovery

Follow [JUDGE-DEMO.md](JUDGE-DEMO.md) for the exact before/after attack and integrity
proof. `npm run test:customer` in `phantomlayer/frontend` exercises real UI onboarding,
deployment, attack, analysis, tenant isolation and restart recovery, then restores
the original bank connection and removes only manifest-owned QA records/audits.
It writes private evidence under `/tmp/omnirush/customer-qa-*`.

Restarting APIs preserves PostgreSQL data/evidence; bank login sessions are
process-local and require a new login. Use `docker compose up -d --wait` after
environment changes, not merely `restart`. Never reset bank datasets, manipulate
tenant rows, or delete volumes to force readiness. Cleanup refuses ambiguous
organization ownership. A retained manifest and private backup allow recovery if
the QA process is interrupted; inspect them before any manual cleanup.

This proves bounded local instrumented paths, not arbitrary attack coverage,
production certification, transparent SQL interception, or a hardened banking
service. TLS/mTLS, distributed sessions/rate limits, durable telemetry retry,
secret-management operations and wider deployment hardening remain future work.
