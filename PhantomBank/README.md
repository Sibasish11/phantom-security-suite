# PhantomBank

A separate, wholly fictional banking application demonstrating PhantomLayer's defensive decision contract. There are **no real funds or customers**, no external payments, and no compliance or production-readiness claim.

## Included

- Responsive ivory/forest-green React + TypeScript + Vite interface: sign-in, overview, accounts, filtered activity, cards, profile, support explanation and working synthetic transfers.
- FastAPI behind the UI's nginx `/api/` proxy.
- Separate PostgreSQL databases and internal networks: **Maya Bennett** in the real synthetic dataset, **John Carter** in deception.
- Signed HttpOnly session cookies, salted PBKDF2 passwords, Origin/CSRF checks and a bounded per-process login limiter.
- Parameterized, transactional transfers with customer-row locking and idempotency, including concurrent retry protection.
- Customer-side gateway: obtains an authenticated PhantomLayer decision **before business database access**, and sends an observation afterward.
- Durable destination audit rows, plus a separately protected, bounded recent defender evidence view.
- Non-destructive bootstrap: existing customer data, transfers and audits are not reseeded on restart.

## Local setup

Prerequisites: Docker Compose and Python 3.11+; Node 20+ for host frontend development. Keep this directory beside `phantomlayer/`.

First start/initialize PhantomLayer as described in its README, with local `DEMO_MODE=true` and mock analysis. Then:

```sh
cd /home/anubhav/Projects/PhantomBank
./scripts/setup.sh
docker compose up --build -d --wait
```

The setup script preserves an existing `.env`, replacing only placeholders with random runtime values. A fresh bank starts in local synthetic **standalone** mode with no pre-provisioned agent. Open <http://localhost:3001/owner>, then follow [customer onboarding](../phantomlayer/docs/CUSTOMER-ONBOARDING.md): signup, add `phantombank.example.test`, publish the challenge with `python scripts/connect.py verify`, verify it in the UI, select API Protection, register and download your customer configuration, then install it with `python scripts/connect.py install /path/to/phantomlayer-integration.json`.

The installer validates organization/domain/agent binding through the authenticated API, writes owner-only `.env`, switches to protected mode and recreates bank-api. Its embedded adapter sends real connectivity heartbeats; registration alone does not activate protection. The bank API joins `phantomlayer_edge` to reach `http://backend:8000`; bank databases do **not** join that network. Database credentials never enter the downloaded configuration or SaaS.

`python scripts/provision_demo.py` remains an **optional automated judge** convenience after both stacks are running. It uses the same authenticated onboarding/challenge/install contracts and stores that separate tenant's login in ignored `.env.demo-login`. It is not needed by the manual UI journey and must not be run to connect an unrelated browser owner.

- Bank UI: <http://localhost:3001>
- Bank API: <http://127.0.0.1:8001>
- SOC: <http://localhost:3000>, using **the owner account you created** (or `.env.demo-login` only for automated provisioning)

**Normal synthetic login:** `maya.bennett@northstar.test` / `DemoMaya!2025`.

John Carter is the deception identity shown after diversion, not an alternative normal sign-in. Disjoint defender markers (`REAL-MAYA-7Q4N`, `DECOY-JOHN-3M8Z`) exist in the datasets but are stripped from public customer responses. Some internal synthetic IDs still have demo-oriented prefixes.

## Server-only PhantomLayer contract

Headers: `X-Agent-ID: <registered ID>` and `X-Agent-Token: <one-time registration token>`.

Before executing an operation, `POST /integrations/bank/decision`:

```json
{
  "session_id": "original server-issued bank UUID",
  "operation": "get_accounts",
  "client_ip": "127.0.0.1"
}
```

The response supplies `decision_id`, an internal namespaced `session_id`, `target`, `risk_score`, `attack_stage` and `triggered_rules`. The bank **keeps sending its original UUID**, not the returned namespaced handle, on subsequent decisions. Tenant identity is never taken from the customer request.

In protected mode, a missing, malformed, unauthorized, disabled or unavailable decision returns 503 with **no business banking SQL for that request**. Database initialization and periodic health probes are separate operational paths. Recon/admin operations also have a bank-side guard: even an erroneous `real` decision cannot authorize them against the real database. Standalone mode is an explicit DEMO_MODE-only deployment with no agent credentials. Its bounded read-only baseline additionally requires a local presenter token and bank authentication; pausing SaaS protection never enables it.

After execution, `POST /integrations/bank/observe`:

```json
{
  "decision_id": "decision UUID",
  "success": true,
  "exposed_entities": {"transactions": 4},
  "response_count": 4
}
```

Observations are decision-owned and idempotent. Only synthetic exposure counts are sent; real responses use an empty exposure map. Metadata includes operation, session ID and optional peer IP, **not passwords, account rows, email addresses or database credentials**. A peer IP can be a proxy hop and is not independently verified attribution.

The operation allowlist is `login`, `get_accounts`, `get_balance`, `get_transactions`, `get_beneficiaries`, `get_cards`, `create_transfer`, `get_profile`, `list_tables`, `enumerate_api`, `get_customers`, `enumerate_accounts`, `enumerate_transactions`, `probe_admin`, and `credential_probe`. There is no arbitrary-SQL endpoint. Customer responses do not reveal target, risk, rules or agent credentials.

A 30-second outbound heartbeat reports database connectivity, installed adapter readiness and successful observation counts. Readiness expires after 90 seconds without a heartbeat. It does not transmit database rows or credentials.

## Before/after customer demonstration

From a standalone bank run `python scripts/compare_attack.py before`, complete the manual onboarding above, then run `python scripts/compare_attack.py after`. These send exactly the same eight allowlisted HTTP operations and print destination, response, rules, risk, and dataset/audit fingerprints. Before: Maya on REAL. After: John on HONEYPOT, risk 27→49→67→77→87→97→100→100, real business and access-audit fingerprints unchanged during the attack.

For an existing connected local environment, `python scripts/connect.py standalone` saves its connection in owner-only `.env.integration-backup` and explicitly starts the unconnected baseline. `python scripts/connect.py restore` recovers that saved connection. Datasets and documented logins are preserved. Full presentation steps and bounded-proof limitations: [JUDGE-DEMO.md](../phantomlayer/docs/JUDGE-DEMO.md).

## Reproducible evidence

With both stacks running and no concurrent bank activity during fingerprint checks:

```sh
python scripts/verify_isolation.py
python scripts/safe_attack_simulation.py
python scripts/verify_restart.py
# Optional: recreate APIs to check Docker DNS/proxy recovery as well.
python scripts/verify_restart.py --recreate
```

- **Isolation:** after legitimate synthetic authentication, eight bounded recon/probe requests and a normal-looking profile follow-up remain in deception. Real business-data and gateway-audit fingerprints stay unchanged; the attacker sees John, not Maya.
- **Simulation:** prints destination/risk evidence from the separately token-protected `/internal/defender-evidence`. This is not a customer banking endpoint and is not proxied by the UI.
- **Restart:** restarts both APIs (not databases), verifies persisted incident/analysis/timeline/events, and confirms both bank datasets/audits are unchanged. Bank users must sign in again afterward.

The scripts use loopback APIs and synthetic datasets only. The evidence proves these instrumented application paths, not every possible uninstrumented database read. The bank's shared process and host remain trusted infrastructure.

## Automated checks

### PostgreSQL-backed suite (recommended)

```sh
./scripts/test-postgres.sh
```

Creates fresh `phantombank_qa_*` databases and runs all backend tests, including actual PostgreSQL audit insertion, transfer replay and six concurrent retries producing one debit. Its exact newly created QA databases are removed on exit. Existing databases/volumes are preserved.

### Fast local tests

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Uses temporary SQLite databases and a stub decision adapter; one PostgreSQL test is skipped unless **both** `BANK_REAL_POSTGRES_TEST_URL` and `BANK_HONEYPOT_POSTGRES_TEST_URL` are explicitly set to disposable QA databases. Prefer the script rather than pointing these variables at a live dataset.

### Frontend and browser

```sh
cd frontend
npm ci
npm run build
```

The final lifecycle test is `npm run test:customer` (also `npm test`) in `../phantomlayer/frontend`. It uses browser signup/verification/agent download, installs that customer's credential, proves before/after routing, investigates/analyzes in SOC, checks isolation and restarts, then removes only manifest-owned QA resources and restores the original bank connection and audit fingerprints. Run Docker-backed QA first, not concurrently with browser checks. Older `test:smoke`, `test:ui` and `test:judge` scripts retain transfers/demo activity and predate this cleanup-aware customer journey.

## Boundaries and remaining work

- The bank API, not the browser, selects the customer and destination. Body target/tenant overrides are rejected or are not accepted by these APIs. Authenticated writes require a matching CSRF token and allowed Origin.
- Only `bank-api` can reach both bank data networks; neither PostgreSQL database publishes host ports. Both datasets use fictional records.
- The two API/DB operations are not a distributed transaction. If an observation fails **after** a transfer commits, the transfer remains successful and local audit/log evidence remains. A durable observation outbox/retry is future work.
- Login sessions and the recent defender buffer are process-local. API restart invalidates logins and empties that buffer; PostgreSQL audit/data persist. Use distributed sessions before scaling workers.
- `/internal/defender-evidence` is token- and demo-mode-gated, not exposed by the UI proxy. The API host port is loopback-bound, but attached Docker peers can reach it; network placement alone is not its authorization control.
- TLS/mTLS, distinct production hostnames (cookies are not port-isolated), secure cookies (`COOKIE_SECURE=true` under HTTPS), managed secrets, least-privilege DB accounts, trusted reverse-proxy attribution, retention/backups and operational monitoring remain deployment work.
- This demonstrates one synthetic customer per dataset and a fixed allowlisted adapter, not a general banking platform, fraud detector, transparent SQL proxy, or unrestricted attack simulator.
