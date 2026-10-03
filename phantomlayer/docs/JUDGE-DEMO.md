# PhantomLayer × PhantomBank — actual customer demonstration

**Local, synthetic, bounded.** This presentation starts with a bank owner signing
up and deploying their own integration. Automated judge provisioning is optional
and is a separate convenience path, not a prerequisite.

## Start the applications

New checkout: initialize PhantomLayer according to [README](../README.md), set
local `DEMO_MODE=true`, `AI_ENABLED=false`, `AI_PROVIDER=mock`. Preserve all existing
`.env` files, passwords and volumes on an initialized installation.

```sh
# From phantomlayer/
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.migrate_control

# From PhantomBank/
./scripts/setup.sh
docker compose up --build -d --wait
```

Addresses: PhantomLayer <http://localhost:3000>, bank <http://localhost:3001>, bank
owner instructions <http://localhost:3001/owner>. APIs are loopback ports 8000/8001.
Bank databases have no published ports. Expect five healthy SaaS services and
four healthy bank services. `docker compose ps` checks service health; activation
checks actual customer readiness. Do not display `.env`, full Compose configuration,
Authorization headers or agent downloads on the projector.

Normal fictional bank login: **maya.bennett@northstar.test / DemoMaya!2025**.
John Carter is the deception identity, not a second normal login. The dataset
contains no actual funds, real customers, or payment integrations.

## Live sequence

### 1. Introduce the customer and show BEFORE

Open the bank owner page. A new installation is standalone with no installed
PhantomLayer credential. On an existing connected presentation environment:

```sh
# Explicit, local-only deployment change; saves the original connection privately.
python scripts/connect.py standalone
```

The script refuses production mode or overwriting an existing recovery backup.
It does not pause SaaS protection to bypass it; it starts the explicitly
unintegrated local customer deployment with no agent installed.

With other bank tabs idle, run:

```sh
python scripts/compare_attack.py before
```

It logs in as synthetic Maya, makes a legitimate account request, fingerprints
both business datasets, then sends these fixed HTTP operations:

`list-tables → enumerate-api → customers → accounts → transactions → probe-admin
→ customers → credential-probe` under `/api/security/`.

The presenter-only baseline requires the local private evidence credential as
well as the bank login. Ordinary standalone callers cannot enumerate the real
path. No SQL input, external target, destructive operation, or scan is accepted.

Show the recorded destination **real**, customer **Maya Bennett**, and unchanged
business fingerprints. The real access-audit fingerprint changes, proving these
instrumented reads reached that path. Risk 0 means *unprotected*, not a security
assessment. The command retains its local audit evidence; it changes no business data.

### 2. Signup → organization → verified domain

Open PhantomLayer, click signup and create your owner account/organization.
Demonstrate login using that new account. Onboarding shows its organization.

Add **phantombank.example.test**. Explain the DNS TXT production flow. For the
isolated local proof, copy the challenge, then from `PhantomBank/`:

```sh
python scripts/connect.py verify
```

Paste the challenge at the prompt and click **Use local demo verification** in
PhantomLayer. Show **VERIFIED**. The SaaS fetched the exact challenge from the
fixed bank deployment; it cannot demo-verify arbitrary public domains. This is
not a claim to own public `phantombank.com`.

### 3. Protection → agent installation → ACTIVE

Choose **API Protection**, register the agent, confirm the organization/domain,
and **Download integration configuration**. The secret is not shown in the UI.

```sh
python scripts/connect.py install "$HOME/Downloads/phantomlayer-integration.json"
```

The installer authenticates and checks the customer binding, stores the agent
credential locally, and recreates bank-api. Open **Check activation** and wait up
to a heartbeat interval (30 seconds). Show:

- DOMAIN VERIFIED
- AGENT HEALTHY
- REAL DB CONNECTED
- HONEYPOT CONNECTED
- PROTECTION ACTIVE

Registration alone remains pending. Stale heartbeat, failed probes, disabled
protection, absent routing adapter or wrong ownership cannot produce Active.
No database credentials are part of the customer download or heartbeat.

### 4. Show legitimate banking, then AFTER

Sign into the bank as Maya; show accounts/activity/profile. Normal requests reach
REAL with risk 0. Stop other bank activity during integrity checks. Run:

```sh
python scripts/compare_attack.py after
```

This is the **same attack path and same eight operations**. Expected evidence:

| Operation | Before destination | After destination / risk |
|---|---|---|
| list_tables | REAL | HONEYPOT / 27 |
| enumerate_api | REAL | HONEYPOT / 49 |
| get_customers | REAL, Maya | HONEYPOT, John / 67 |
| enumerate_accounts | REAL | HONEYPOT / 77 |
| enumerate_transactions | REAL | HONEYPOT / 87 |
| probe_admin | REAL path, denied response | HONEYPOT / 97 |
| get_customers | REAL, Maya | HONEYPOT, John / 100 |
| credential_probe | REAL path, rejected credentials | HONEYPOT / 100 |

Explain the deterministic rule names and session context in the output. The
first recon is diverted at 27 by operation policy, not a generic score threshold.
The script asserts unchanged real/deception business fingerprints and unchanged
REAL access-audit fingerprint throughout the protected attack window. Legitimate
authentication/account access occurs **before** that window. Health probes still
execute `SELECT 1`; the assertion covers instrumented business paths.

### 5. Incident → timeline → AI/mock analysis

In the **same owner account**, open SOC → latest incident. Show the organization,
domain, agent, session, triggered rules, stages, destination, risk progression,
deception counts and timeline. Security Events shows detection/routing/observation
as separate records, not three different bank requests.

Click **Analyze incident**. Show **mock**, completed status, summary, rules,
deception interactions, hypotheses and defender recommendations. AI sees sanitized
metadata/counts, not customer rows or credentials, and never controls routing.
Analyze after the last interaction; new interactions invalidate older analysis.

Suggested explanation:

> “PhantomBank is our fictional customer. I onboarded the bank, proved control of
> its local domain, selected protection and installed a customer-specific adapter
> inside the bank. Its database credentials and raw records stay there. Once
> connected, deterministic policy diverts supported suspicious requests into a
> separate synthetic dataset. The caller sees fake data; the defender gets the
> timeline and advisory analysis. These fingerprints prove this bounded local
> demonstration, not security against every possible attacker.”

## Recovery and clean presentation state

- API restarts preserve bank data and control-plane incidents/analysis. Bank login
  sessions reset; sign in again. Heartbeats resume automatically.
- After changing environment values use `docker compose up -d --wait`, which
  recreates the affected service. After source changes also use `--build`.
- Lost credential: Agent → **Rotate credential and reconnect**, download and
  install again. The old credential is immediately invalid.
- Missing readiness: read the activation blockers. Never set Active manually.
- Paused SaaS protection / service outage / bad credential: configured bank
  requests fail closed. Do not enable a network-error bypass.
- If you used `connect.py standalone`, `python scripts/connect.py restore`
  reinstates the original saved presentation connection. It does not delete the
  new customer's legitimate organization or its evidence. Keep that intentionally
  retained demo account, or use the disposable QA workflow below for rehearsal.
- Existing unrelated `phantombank.com` and prebuilt bank tenants are preserved.
  A new manual customer never inherits either one's IDs or incident visibility.

## Reproducible QA with scoped cleanup

```sh
# From phantomlayer/
./scripts/test-backend.sh -q
# From PhantomBank/
./scripts/test-postgres.sh
# From phantomlayer/frontend/
npm ci
npx playwright install chromium   # or set CHROMIUM_PATH to an installed browser
npm run test:customer
```

Run while the local bank is otherwise idle. The backend runners create and remove
only newly named QA databases. The customer browser test creates a fresh owner
and isolation tenant, records their IDs before continuing, uses the real UI and
installer, tests routing/analysis/isolation/restarts, then removes only its own
organizations, users, domains, protections, agents, decisions, incidents,
interactions, reports, events and bank access audits. Original `.env` and both
business datasets/audits must match the pre-test fingerprints afterward.

Private evidence/manifest: `/tmp/omnirush/customer-qa-<run>/`. Temporary credential
downloads/backups are removed on successful cleanup. On interrupted cleanup,
retain the manifest, stop and investigate ambiguous ownership; never drop volumes
or guess which tenant is disposable. `npm test` now runs this same customer
lifecycle. Older `test:smoke`, `test:ui` and `test:judge` scripts retain demo
activity and use an earlier provisioning rehearsal.

## Automated judge convenience, separate from manual onboarding

After both stacks are started, `python scripts/provision_demo.py` can create/reuse
the owner in ignored `.env.demo-login`. It uses registration/login, domain APIs,
the same bank-published challenge, API protection, agent registration and the same
authenticated installer. It selects only an agent on that domain. It does not
silently attach a browser tenant or bypass domain ownership. The saved defender
login is for **that** automated tenant only.

## Honest limits

One fictional bank per dataset; fixed operation allowlist; local-only HTTP
installer; mock advisory analysis; agent-reported readiness; trusted bank process
with access to both DBs. No universal WAF, transparent SQL proxy, pentest/compliance
certification, arbitrary attack coverage, or real banking functionality. Bank
sessions/rate limits are process-local. Telemetry has no durable retry outbox;
an observation failure after a committed operation does not undo it. TLS/mTLS,
managed secrets, least-privilege operations, production DNS practices, retention,
load/failure testing and broader operational hardening remain deployment work.
