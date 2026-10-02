# PhantomLayer — Judge Demo Runbook

**Local, synthetic demonstration · 3–5 minutes after preparation.** No real customers, funds, payment networks, external targets, or unrestricted scanning. Keep generated credentials and raw logs off the projected screen. This is a working prototype, **not production-certified software**.

## 1. What We Are Demonstrating

PhantomLayer evaluates application operations before a customer-side gateway accesses business data. Deterministic detection rules and session history produce risk evidence and routing decisions. Normal PhantomBank activity reaches the fictional Maya Bennett dataset; controlled reconnaissance is redirected to an isolated John Carter dataset. The suspicious session stays in deception even when it returns to an ordinary-looking operation. Defenders can inspect correlated events, a chronological attack timeline, and clearly labeled mock advisory analysis. The demonstration verifies these implemented paths and their data boundary, not universal attack coverage.

## 2. Core Architecture

```text
Request → Gateway → Detection → Risk Scoring → Routing
                                                 ├─ Ordinary operation → Real bank dataset
                                                 └─ Recon / sensitive operation / pinned session
                                                                           ↓
                                                                    Deception dataset
                                                                           ↓
                                                                       Telemetry
                                                                           ↓
                                                                    Incident Analysis
                                                                           ↓
                                                                      Defender UI
```

PhantomBank's **server-side gateway**, not the browser, calls `POST /integrations/bank/decision` with its registered agent identity **before business SQL**. PhantomLayer evaluates the allowlisted operation and accumulated session history. The bank executes against the returned destination and calls `POST /integrations/bank/observe` afterward. These are server-to-server calls; do not paste agent credentials into DevTools.

**Important presentation distinction:** the first reconnaissance request is diverted at risk **27**, due to explicit operation policy. The next two requests raise risk to **49 → 67**. The bank adapter does **not** wait for a generic numerical threshold to divert sensitive operations. Subsequent requests remain pinned by persisted session decision history. Analysis is downstream and cannot override routing.

The older `/gateway/query` and `/routing/route` endpoints demonstrate a shared synthetic e-commerce catalog. They are **not** the bank adapter, transparent SQL interception, or customer production-database access.

## 3. System Components

| Component | Implemented responsibility |
| --- | --- |
| **PhantomLayer** | FastAPI control plane, organization authentication, domains, protection configuration, registered agents, deterministic decisions, persistent security evidence, and React defender console. |
| **PhantomBank** | Separate React/FastAPI fictional banking application with sign-in, account reads, activity, cards, profile, and transactional synthetic transfers. |
| **Real database** | Bank PostgreSQL dataset containing Maya Bennett and her fictional ledger. “Real” means the normal application destination, not real-world customer data. |
| **Deception database** | Separate bank PostgreSQL dataset containing John Carter and a fictional ledger, with its own volume/internal network. Neither bank database publishes a host port. |
| **Gateway** | Bank API adapter that requests authorization of the destination before business data access; recon also has a bank-side guard against a `real` destination. |
| **Detection engine** | Recognizes supported reconnaissance, enumeration, sensitive access, and repetition signals from allowlisted operations. No arbitrary SQL or free-form exploit execution is exposed. |
| **Risk engine** | Weighted rule/severity scoring plus session history. The bank retains the maximum risk and raises repeated suspicious operations by at least 10, capped at 100. |
| **Telemetry** | Tenant-owned decisions, rule metadata, operation outcomes, and synthetic entity counts persisted in PhantomLayer's control PostgreSQL. Bank rows/passwords are not analysis inputs. |
| **Incident analysis** | Sanitized session projection and on-demand deterministic **mock** advisory analysis; hypotheses and recommendations do not execute security actions. |
| **Dashboard** | Environment readiness, verified domains, reported agent health, incident queue, routing counts, events, session details, and timeline/analysis inspection. |

PhantomLayer's three PostgreSQL services are its older real/demo catalog, honeypot/demo catalog, and control plane. PhantomBank adds **two separate bank databases**. Do not confuse those five stores when explaining isolation. The trusted bank API and local host can reach both bank datasets; separate networks do not make a compromised gateway harmless.

## 4. Starting Everything

### Already initialized presentation workspace — recommended

Prerequisites: Docker Engine with Compose, Python 3.11+, and the existing two sibling repositories. Node 20+ is needed for host frontend builds/tests. Existing `.env` files, volumes, bank agent provisioning, and the ignored `.env.demo-login` must be retained.

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose up -d --wait

cd /home/anubhav/Projects/PhantomBank
docker compose up -d --wait
```

The local configuration uses `DEMO_MODE=true`, `AI_PROVIDER=mock`, and `AI_ENABLED=false`. The bank also needs demo mode for its private defender evidence endpoint. **Do not print `.env` or full resolved Compose configuration to check this.** Allow one **30-second heartbeat** for the bank agent; overview/events refresh every **10 seconds** or use their refresh buttons.

To deploy frontend edits without interrupting the APIs:

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose build frontend
docker compose up -d --no-deps --wait frontend

cd /home/anubhav/Projects/PhantomBank
docker compose build bank-ui
docker compose up -d --no-deps --wait bank-ui
```

### Health and addresses

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose ps
curl -fsS http://127.0.0.1:8000/health
curl -sS -o /dev/null -w 'PhantomLayer UI: %{http_code}\n' http://localhost:3000/login

cd /home/anubhav/Projects/PhantomBank
docker compose ps
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://localhost:3001/health
curl -sS -o /dev/null -w 'PhantomBank UI: %{http_code}\n' http://localhost:3001/
```

Expect five healthy PhantomLayer services, four healthy bank services, successful health responses, and UI HTTP **200**. These are liveness/proxy checks; the browser rehearsal below establishes functionality.

| Surface | Exact URL |
| --- | --- |
| PhantomLayer public / signup / login | `http://localhost:3000/` · `/signup` · `/login` |
| Security overview | `http://localhost:3000/dashboard` |
| Incident queue | `http://localhost:3000/dashboard/incidents` |
| Security events | `http://localhost:3000/dashboard/events` |
| Domains / agents / protections | `http://localhost:3000/admin/domains` · `/admin/agents` · `/admin/protections` |
| PhantomLayer backend | `http://127.0.0.1:8000` |
| PhantomBank frontend | `http://localhost:3001` |
| PhantomBank backend | `http://127.0.0.1:8001` |

Use `localhost` consistently for browser tabs; the bank enforces allowed browser Origins. The bank joins the existing `phantomlayer_edge` Docker network to reach `http://backend:8000`.

### Only if bank provisioning is missing

After PhantomLayer is initialized and running:

```sh
cd /home/anubhav/Projects/PhantomBank
./scripts/setup.sh
python scripts/provision_demo.py
docker compose up --build -d --wait
```

These existing scripts generate local secrets as needed and create/reuse the demo organization, demo-verified domain, API protection, and registered agent. They save credentials privately, without printing them. For an entirely fresh PhantomLayer deployment, follow [the repository README](../README.md). **Do not run fresh-install catalog seeds on this initialized workspace. Never remove volumes to prepare a demo.**

### Pre-presentation rehearsal and checks

Run sequentially, not alongside bank browsing, transfers, or restarts. Finish Docker-backed QA **before** browser QA: creating/removing disposable containers can trigger Chromium `ERR_NETWORK_CHANGED`, even when the application is healthy:

```sh
cd /home/anubhav/Projects/phantomlayer
./scripts/test-backend.sh -q

cd /home/anubhav/Projects/PhantomBank
./scripts/test-postgres.sh
python scripts/safe_attack_simulation.py
python scripts/verify_isolation.py
python scripts/verify_restart.py
python scripts/verify_restart.py --recreate

cd /home/anubhav/Projects/phantomlayer/frontend
npm ci
npm run build
cd /home/anubhav/Projects/PhantomBank/frontend
npm ci
npm run build

cd /home/anubhav/Projects/phantomlayer/frontend
# No shell tracing: credentials are sourced privately, never printed.
set +x
set -a
. ../../PhantomBank/.env.demo-login
set +a
CHROMIUM_PATH=/opt/google/chrome/chrome npm test
unset PHANTOMLAYER_EMAIL PHANTOMLAYER_PASSWORD
```

`/opt/google/chrome/chrome` is the verified executable on this presentation machine. Elsewhere use an installed Chromium path, or `npx playwright install chromium` and omit `CHROMIUM_PATH`. `npm test` runs cross-app smoke, responsive UI/onboarding checks, and the full **single-session judge rehearsal**. `npm run test:judge` runs only that last rehearsal with the same private credential setup.

Backend runners create fresh QA databases and retain them; they do not drop demo data. UI tests retain a fresh synthetic organization and a **£0.01 fictional transfer** per smoke run. The rehearsal records more incidents/events. Restart checks invalidate bank logins: sign in again before presenting. Fresh executed evidence is in [final-demo-verification.md](final-demo-verification.md); earlier QA and limitations remain in [qa-report.md](qa-report.md).

## 5. Demo Credentials

| Account | How to obtain/use it |
| --- | --- |
| Normal synthetic bank customer | Email **`maya.bennett@northstar.test`**, password **`DemoMaya!2025`**. These public fictional demo credentials are present in the bank seed. |
| PhantomLayer defender | Use `PHANTOMLAYER_EMAIL` and `PHANTOMLAYER_PASSWORD` from `/home/anubhav/Projects/PhantomBank/.env.demo-login`. Open this ignored, owner-only file **privately**, off the shared screen. They are dynamically generated, so no values are copied here. |
| Deception identity | **John Carter** is returned after diversion. He is not a second normal sign-in account. |

If the defender file is absent, use the provisioning commands in §4. Do not replace an existing password, disclose agent tokens, show browser Authorization headers/cookies, or copy credentials into slides. Sign into the **bank's dedicated defender organization**, not an older unrelated tenant; organization administrators cannot see all tenants.

## 6. 3–5 Minute Live Demonstration

**Preparation:** keep PhantomBank and the signed-in defender console in separate tabs. Open a terminal in `/home/anubhav/Projects/PhantomBank`. Open browser DevTools **Console on the bank tab** for the three bounded requests below. Start with a fresh bank login, not a previously diverted session. Close other active bank clients before the isolation check. Do not show DevTools storage, network headers, or raw service logs.

### Step 1 — Open PhantomBank · 0:00

- **UI location:** `http://localhost:3001`, sign-in page.
- **Exact action:** show the fictional-demo notice; enter the synthetic Maya credentials from §5. Do not submit yet.
- **Expected result:** a normal banking sign-in surface, clearly labeled as fictional.
- **Say:** “This is PhantomBank, our synthetic target application. No real customer or payment network is connected.”

### Step 2 — Legitimate User · 0:15

- **UI location:** bank → **Sign in** → Overview → sidebar **Accounts**, **Activity**, **Profile**.
- **Exact action:** sign in and open those pages. If demonstrating writes, return to Overview, enter **0.01** in the transfer amount, keep a seeded beneficiary selected, and click **Send synthetic transfer**. Do this **before** any isolation baseline.
- **Expected result:** Maya Bennett's profile, account balances and transaction activity load. Optional transfer shows “Synthetic transfer completed. Your balance and activity are updated.” and debits one fictional penny.
- **Say:** “This request is considered legitimate and reaches the real environment. Here, ‘real’ is still a completely fictional banking dataset.”

### Step 3 — Show PhantomLayer · 0:40

- **UI location:** SOC `/dashboard` → **Refresh snapshot**; then **Security events** → **Real**.
- **Exact action:** show the verified domain, healthy agent, active protection, and the protection-path Real environment count. In events show a recent `get_profile` or `get_accounts` decision.
- **Expected result:** real destination, risk **0**, and ordinary operation metadata. Counts are cumulative recorded decisions, not all network traffic.
- **Say:** “The application keeps working normally. The defender can see which destination the gateway was authorized to use.”

### Step 4 — Controlled Attack · 1:00

- **UI location:** browser DevTools **Console on `http://localhost:3001`**, using the same signed-in bank session.
- **Exact action:** run these three requests, in order:

```js
await fetch('/api/security/list-tables').then(r => r.json());
await fetch('/api/security/enumerate-api').then(r => r.json());
await fetch('/api/security/customers').then(r => r.json());
```

- **Expected result:** bounded local reconnaissance succeeds against synthetic deception. The third response's `result.records` contains **John Carter**, not Maya. No destination/risk metadata appears in the customer response.
- **Say:** “These are controlled, allowlisted reconnaissance operations on our own local demo. We are not scanning or attacking an external system.”

**Terminal fallback:** `python scripts/safe_attack_simulation.py` runs the three operations with its **own** fresh synthetic session and prints a separate, privately authenticated defender-only routing view without printing its token. Do not confuse that new session with the browser session.

### Step 5 — Detection · 1:25

- **UI location:** SOC `/dashboard` → **Refresh snapshot** → **Open latest investigation** → **Triggered rules**; or Incidents → newest item → **Open full investigation**.
- **Exact action:** identify the new bank incident by time/session. Show the rule list and the timeline's `list_tables`, `enumerate_api`, `get_customers` operations. Stop other simulations so “latest” is unambiguous.
- **Expected result:** reconnaissance, enumeration, sensitive-data-access and repeated-access rule evidence belongs to this session. Later pinned benign operations need not independently match a new rule.
- **Say:** “We record the operations and the deterministic rule matches. We do not need an AI model to decide that this supported reconnaissance belongs in deception.”

### Step 6 — Risk · 1:45

- **UI location:** same incident → **Attack timeline** → **Risk progression**.
- **Exact action:** point to the three chronological scores **27 → 49 → 67** and current severity **High**.
- **Expected result:** risk grows with the sequence; the first request was already diverted by explicit policy at 27.
- **Say:** “Risk accumulates across this session. Sensitive-operation policy diverts early; a low first score is not permission to enumerate the normal bank.”

### Step 7 — Deception · 2:00

- **UI location:** same incident → six-stage **Detection → Risk → Routing → Deception → Telemetry → Analysis** strip and **Protection decisions**.
- **Exact action:** show **Isolated deception** and the timeline destinations.
- **Expected result:** all attack interactions have Deception as their destination. `honeypot` is the internal API name for the same destination.
- **Say:** “The gateway selected a separate synthetic database before executing these operations. Neither the browser nor the analysis provider chooses that destination.”

### Step 8 — Attacker Interaction · 2:15

- **UI location:** bank tab → DevTools Console; optionally reload bank and open **Profile**.
- **Exact action:** make an ordinary-looking follow-up:

```js
await fetch('/api/profile').then(r => r.json());
```

- **Expected result:** `profile.full_name` is **John Carter**, still at accumulated risk 67. Reloading the bank and opening Profile also displays John; reload adds more pinned observations. It does **not** restore Maya or require a new login.
- **Say:** “Looking harmless again does not escape this deception session. The caller continues to see believable synthetic application data.”

### Step 9 — Telemetry · 2:35

- **UI location:** incident → **Refresh evidence** → **Inspect this session's detection and routing events**.
- **Exact action:** click the link, select **Deception**, expand an event row. For rules, expand a **request analyzed** or **suspicious request** entry; routing-decision entries record the destination.
- **Expected result:** session-scoped feed shows the full session identifier, timestamps, operations, event type, risk, destination, and available rule/reason metadata. Multiple event types for one operation are not multiple bank requests.
- **Say:** “This is one correlated session, not an unrelated stream of alerts. Detection, routing, and observed interaction are separate evidence records.”

### Step 10 — Incident Analysis · 2:55

- **UI location:** return to the same incident; **Refresh evidence**, then **Analyze incident** or **Re-analyze**.
- **Exact action:** show provider **mock**, summary, observed behavior, advisory objective, recommendations, synthetic counts, and limitations.
- **Expected result:** completed analysis and the attack timeline persist after reloading the incident. New interactions invalidate the old analysis, so analyze after the last bank action.
- **Say:** “The current analysis is a deterministic mock, clearly labeled. It summarizes sanitized evidence and proposes hypotheses; it cannot route requests or execute a recommendation.”

### Step 11 — Isolation · 3:25

- **UI location:** prepared local terminal in `/home/anubhav/Projects/PhantomBank`; stop all concurrent bank browsing/transfers.
- **Exact action:** run:

```sh
python scripts/verify_isolation.py
```

- **Expected result:** eight bounded recon/probe checks and a pinned profile follow-up pass. Final messages include **real PostgreSQL data AND access audit unchanged** and **attacker sees John Carter**. The script uses a separate fresh session and will create another incident; do not mistake it for the incident already on screen.
- **Say:** “After legitimate authentication, this check fingerprints the real business tables and gateway-access audit. They remain unchanged throughout this controlled attack window.”

The baseline includes customers, accounts, transactions, transfers, beneficiaries, cards, and gateway audit. It starts **after** legitimate login/account access, excludes the expected legitimate penny transfer, and proves the instrumented paths—not arbitrary unaudited reads, host compromise, or all possible attacks. Health probes still perform `SELECT 1`. The extended risk sequence reaches **27 → 49 → 67 → 77 → 87 → 97 → 100** and stays pinned.

### Step 12 — Final Explanation · 3:50

- **UI location:** SOC incident's pipeline/timeline; leave the successful isolation output beside it.
- **Exact action:** recap normal destination versus deception, evidence correlation, and the analysis boundary. Do not call mock analysis a live external-model result.
- **Expected result:** judges see one coherent path from application request to detection, risk, diversion, synthetic response, telemetry, and investigation.
- **Say:** “Blocking ends the interaction; bounded deception can preserve a sequence of behavior for defenders while reducing the data value exposed. It complements blocking and other controls—it is not a claim that every attacker or bypass is covered.”

## 7. Judge Questions

| Question | Answer based on the implementation |
| --- | --- |
| **What problem are you solving?** | Suspicious application access can expose valuable data before defenders understand it. This adapter diverts supported suspicious operations to synthetic data while preserving investigative evidence. |
| **What makes PhantomLayer different from a traditional honeypot?** | The same application API selects real/deception data through an integrated decision gateway and correlates the session. The decoy is still a honeypot; we do not claim to have invented deception. |
| **Why not just block the attacker?** | A controlled decoy can reveal sequence and behavior beyond the first alert. Deception complements blocking; missing/invalid protection decisions fail closed. |
| **How is risk calculated?** | Weighted deterministic rule scores and severities with multi-rule/history effects. The bank uses the prior maximum, increments repeated suspicious operations by at least 10, and caps risk at 100. Confidence is heuristic, not calibrated probability. |
| **What triggers deception?** | A supported recon/sensitive operation, or an already diverted session. The generic risk engine's recommendation threshold is 50, but the bank's explicit operation policy diverts the first recon at 27. |
| **Why use AI?** | To help summarize sanitized evidence and suggest investigative hypotheses. Only a deterministic mock provider exists today; external-model performance is not demonstrated. |
| **What happens if AI is unavailable?** | Analysis can report a failure; deterministic routing remains independent. The current local configuration uses mock analysis even with external AI disabled. |
| **Can AI directly control security-critical routing?** | No. Recommendations are advisory text; no analysis result changes the gateway decision or executes a security action. |
| **How do you prevent production data exposure?** | Decisions precede business SQL; recon has an additional real-destination guard; only allowlisted operation/risk/rule metadata and synthetic counts enter analysis. This is not proof against an arbitrary bypass or compromised trusted host. |
| **How is deception isolated?** | Separate bank PostgreSQL containers, volumes, and internal networks; no published bank DB ports. The trusted bank API accesses both. |
| **How do you handle false positives?** | Recon/sensitive callers are diverted and pinned even if legitimate. No measured false-positive rate or operator review/unpin workflow exists. A fresh bank login creates a new session; there is no cross-login attacker tracking. |
| **How does multi-tenancy work?** | Ownership comes from authenticated server-side organization/agent identity. Incidents/events/configuration are tenant-filtered; an organization administrator is not a platform-wide administrator. |
| **How does onboarding work?** | Create a workspace, add a domain, verify DNS, choose protection, register/deploy an agent, then check readiness. A separately labeled local demo-verification shortcut requires backend demo mode. Registration alone is not a healthy agent. |
| **Why PhantomBank?** | Maya versus John plus a functioning fictional ledger makes routing and isolation observable without real funds or customer data. |
| **What happens if PhantomLayer goes down?** | Protected bank operations return 503 rather than bypassing the decision step; no business SQL executes for that undecided request. There is no HA/failover claim. If an observation fails after an already authorized operation commits, that commit remains and local audit/logs remain; there is no durable delivery outbox yet. |
| **What are the current production limitations?** | Fixed allowlisted adapter, mock analysis, process-local bank sessions/rate limits, no durable observation retry worker, and further deployment, availability, scaling and operational hardening. See §9. |

## 8. Troubleshooting

### Check Docker, health, frontend, and API proxies

```sh
docker version
docker compose version

cd /home/anubhav/Projects/phantomlayer
docker compose ps
curl -fsS http://127.0.0.1:8000/health
curl -sS -o /dev/null -w 'SOC UI: %{http_code}\n' http://localhost:3000/login
# Expected 401: the proxy is reachable but no bearer credential was supplied.
curl -sS -o /dev/null -w 'SOC API proxy: %{http_code}\n' http://localhost:3000/organizations
docker compose exec -T frontend nginx -t

cd /home/anubhav/Projects/PhantomBank
docker compose ps
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://localhost:3001/health
curl -sS -o /dev/null -w 'Bank UI: %{http_code}\n' http://localhost:3001/
docker compose exec -T bank-ui nginx -t
```

### View logs privately

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose logs --tail=60 backend frontend
cd /home/anubhav/Projects/PhantomBank
docker compose logs --tail=60 bank-api bank-ui
```

Do not screen-share raw logs or full container inspection. Never use `docker compose config`, `env`, or credential-file dumps in the projected terminal.

### Restart services

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose restart backend frontend
docker compose up -d --wait
cd /home/anubhav/Projects/PhantomBank
docker compose restart bank-api bank-ui
docker compose up -d --wait
```

Sign into the bank again afterward and allow a heartbeat. Database data/audit and control-plane incidents/analysis persist; process-local bank sessions do not. Restarts do not compile source or apply changed environment settings.

### Rebuild and recreate changed application services

```sh
cd /home/anubhav/Projects/phantomlayer
docker compose build backend frontend
docker compose up -d --wait
cd /home/anubhav/Projects/PhantomBank
docker compose build bank-api bank-ui
docker compose up -d --wait
```

| Symptom | Exact recovery/check |
| --- | --- |
| Bank 503 | Check API health, bank agent registration/configuration, enabled API/full protection, verified domain, and shared edge network. Never add an allow-on-error bypass. |
| Empty/wrong SOC | Sign into the bank's dedicated defender organization; refresh; check the latest incident's session/time. Browser, simulator, and isolation verifier use separate sessions. |
| Pending/unhealthy agent | Wait 30 seconds, use Agent → Refresh, then inspect bank API logs privately. Registration does not prove connectivity. |
| Stale incident or analysis | Use **Refresh evidence** after further requests; generate analysis again. Overview refreshing does not refresh an already open incident detail. |
| UI 502 after recreation | Check direct API and UI proxy separately. Both Nginx configs re-resolve Docker DNS. Verify `nginx -t`; rebuild only the affected UI if needed. |
| Bank shows John before the demo | The browser is already pinned. Use **Sign out**, then sign in again as Maya to start a new session. Do not clear database evidence. |
| 401 after restart / 429 login | Sign in again after restart. For login rate limiting, pause at least 60 seconds rather than retrying rapidly. |
| Isolation assertion fails | Stop concurrent bank activity and retry once. If it still fails, preserve evidence and investigate; never reset data to manufacture a pass. |

**Never use `down -v`, database drops, fresh catalog seeds, password replacement, or relaxed authentication to repair a presentation.**

## 9. Known Limitations

These preserve the boundaries already recorded by QA:

- **Mock analysis only:** intent/stages are classifications or hypotheses; no external-model evaluation, complete detection coverage, certification, or measured false-positive rate.
- **Fixed integration scope:** one fictional customer per dataset, supported operation allowlist, recognizable synthetic IDs in some responses. No transparent WAF/SQL proxy, real payment rails, editable profile, support-ticket service, or platform-wide tenant administration.
- **Configuration versus enforcement:** selecting other protection-layer configurations does not automatically install additional enforcement. The demonstrated enforcement is the bank adapter and its API/full protection contract.
- **Trusted computing boundary:** separate datasets/networks do not protect against a compromised gateway/host that can reach both. Fingerprints and gateway audits prove the tested window and instrumented paths, not absence of every possible uninstrumented read.
- **Durable delivery gap:** an authorized bank operation can commit before observation delivery fails. Local audit/logs remain, but no persistent observation outbox/retry worker or alert-notification delivery service exists.
- **Process-local state:** bank logins, recent defender buffer, and rate limiters reset on API restart. PostgreSQL decisions, incidents, analysis, datasets, and audit persist. Distributed sessions, load/chaos tests, multiworker and HA work remain; legacy demo caches are not production-certified.
- **Operational meaning:** health checks are liveness; agent health is last-reported metadata; source IP can be a proxy hop. Recorded decision counts are not every infrastructure request. Domain attribution in the UI uses tenant-visible registered-agent context; no unsupported affected resource is invented.
- **Production deployment:** dependency/image pinning, TLS/mTLS, distinct hostnames/cookie boundaries, managed secrets and rotation, least-privilege DB roles, backups/restore, managed migrations, revocation, retention, resource limits, pagination/SQL aggregation, and restrictive host exposure require further work. The local Compose UI/API ports bind to loopback; browser bearer storage remains local storage.
- **Data stewardship:** earlier QA fixtures cleared some demo sessions before the guarded runners existed. Use only the isolated runners above. Do not claim all historical sessions were preserved. Rotate previously inspected runtime credentials before external reuse; no secret values are reproduced here.
- **Workspace packaging:** PhantomBank is a sibling project, not part of PhantomLayer's Git diff. Preserve/package it separately for another presentation machine, including privately provisioned configuration—not committed secrets.
