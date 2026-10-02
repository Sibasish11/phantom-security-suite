# PhantomLayer × PhantomBank: local demo runbook

Only synthetic data and bounded, allowlisted operations are used. These scripts do not scan external systems, send arbitrary SQL, or require production credentials. Keep both applications in sibling directories named `phantomlayer` and `PhantomBank`.

## 1. Start PhantomLayer

From `phantomlayer/`, follow the [README](../README.md) for first-time initialization. Preserve an existing `.env` and all volumes. For an already initialized deployment:

```sh
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.migrate_control
```

The local deployment must have `DEMO_MODE=true`. Demo verification is an explicit local-only shortcut, not a substitute for real DNS ownership verification. Leave `AI_ENABLED=false` and `AI_PROVIDER=mock` for this runbook.

## 2. Provision and start the separate bank

```sh
cd ../PhantomBank
./scripts/setup.sh
python scripts/provision_demo.py
docker compose up --build -d --wait
```

`setup.sh` generates runtime secrets only when needed. `provision_demo.py` uses authenticated public APIs to create/reuse a dedicated defender tenant, verified demo domain, enabled API protection and registered agent. It stores defender login credentials in ignored, owner-only `.env.demo-login`, and the bank's agent credential in ignored `.env`. It never prints those secrets. Re-running it does not reset bank data. It deliberately targets only the local PhantomLayer API.

Alternatively, register your own organization, verify its domain, enable API/full protection, register an agent, and set its one-time `AGENT_ID`/`AGENT_TOKEN` in `PhantomBank/.env` without running provisioning. Never put the token in a browser or commit it.

| Service | URL |
| --- | --- |
| PhantomLayer SOC | `http://localhost:3000` |
| PhantomLayer API | `http://127.0.0.1:8000` |
| PhantomBank | `http://localhost:3001` |
| Bank API | `http://127.0.0.1:8001` |

Sign in to PhantomLayer with the credentials in `PhantomBank/.env.demo-login` to see the bank's incidents. An older or different tenant correctly sees only its own data. The bank sends health metadata every 30 seconds; give its agent/protection indicators one heartbeat interval to update.

## 3. Show normal banking

Open PhantomBank and sign in with the explicitly synthetic login:

- Email: `maya.bennett@northstar.test`
- Password: `DemoMaya!2025`

Explore Overview, Accounts, Activity, Cards, Profile and Support. Submit a small transfer to a seeded beneficiary if desired. Transfers really update the fictional ledger, are transactional, and use an idempotency key; there are no actual funds or external payments.

The bank calls PhantomLayer before business database access. Normal operations reach the real **synthetic** Maya dataset. Customer responses do not disclose routing destination, risk, agent token, or tenant ID.

## 4. Run controlled reconnaissance and inspect evidence

With no concurrent bank browsing or transfers during the fingerprint proof:

```sh
# From PhantomBank/
python scripts/verify_isolation.py
python scripts/safe_attack_simulation.py
```

The scripts use loopback only. No uncontrolled attack tooling is involved.

The isolation proof:

1. Performs a legitimate synthetic login and account request.
2. Fingerprints real business tables and the real gateway audit ledger.
3. Exercises table/API reconnaissance, customer/account/transaction enumeration, admin probing and credential probing.
4. Verifies the customer listing contains **John Carter**, not Maya Bennett.
5. Calls a benign-looking profile endpoint and confirms the session is still pinned to John.
6. Confirms the real dataset **and gateway access audit** fingerprint is unchanged after diversion.

The second script prints a separate defender-only destination/risk view. Observed risk on the extended sequence rises `27 → 49 → 67 → 77 → 87 → 97 → 100` and remains nondecreasing. The low-risk-looking follow-up stays in deception.

**Evidence scope:** valid authentication happened before the proof window. The assertions cover these instrumented proxy paths and synthetic database/audit snapshots. They are not general proof against every possible bypass or unaudited read. Background health probes can still execute `SELECT 1`; no bank rows leave the environment.

## 5. Investigate in the SOC

Refresh the PhantomLayer overview, open the latest investigation, inspect operations, rules, source hop, risk progression and synthetic exposure counts, then select **Analyze incident** (or **Re-analyze**).

- Reports label the provider **mock** and separate recorded operations from inferred intent.
- Source addresses may be a Docker/Nginx proxy hop; they are not independently verified attacker identities.
- The overview's request/diversion metrics are recorded decisions, not measurements of every request elsewhere in an infrastructure.
- A report never changes routing or automatically executes a recommendation.
- `/admin/organizations` displays only the current authenticated organization, not all customers.

## 6. Demonstrate restart persistence

Close bank tabs or leave them idle, then:

```sh
# Restarts the two APIs, not the database containers or volumes.
python scripts/verify_restart.py
# Stronger deployment check: recreate API containers and verify UI proxy recovery.
python scripts/verify_restart.py --recreate
```

This asserts that incident ID, completed mock analysis, event feed and timeline survive the PhantomLayer API restart. It fingerprints both bank datasets and audits before/after bank API restart to prove startup does not reseed or erase them.

**Expected:** bank login sessions and the recent in-memory defender evidence buffer reset on API restart. Sign in again; durable PostgreSQL records remain.

## Reproduce the automated checks

```sh
# From PhantomBank/
./scripts/test-postgres.sh

cd ../phantomlayer
./scripts/test-backend.sh -q

cd frontend
npm ci
npm run build
# Load only the locally generated demo login into this shell; do not echo it.
set -a
. ../../PhantomBank/.env.demo-login
set +a
# Either npx playwright install chromium, or select an existing Chromium/Chrome.
CHROMIUM_PATH=/opt/google/chrome/chrome npm test

cd ../../PhantomBank/frontend
npm ci
npm run build
```

The browser path above is specific to this machine; omit `CHROMIUM_PATH` after installing Playwright Chromium elsewhere. Screenshots default to `/tmp/phantomlayer-qa-screenshots`. Browser QA submits one £0.01 synthetic transfer per run and checks the displayed balance update; that demo ledger entry is retained. Backend QA uses new databases and never resets running demo data. See [the QA report](qa-report.md) for exact executed results and gaps.

## Troubleshooting safely

- **Bank 503:** check both API health endpoints, registered agent credentials, verified domain and enabled API/full protection. Do not add a local allow-on-error bypass.
- **Empty SOC:** check which tenant you logged in to. Do not weaken ownership filters to correlate someone else's session.
- **Agent pending:** allow one heartbeat interval and inspect service health; the health payload contains connectivity booleans, not credentials or rows.
- **Migration rejects duplicate email:** stop and plan a non-destructive resolution. Do not delete users to force the index through.
- **No browser executable:** install Playwright Chromium or set a valid `CHROMIUM_PATH`.
- **Existing data:** do not run `docker compose down -v`, database drop commands, or fresh-install seed commands. QA databases accumulate intentionally; cleanup is an explicit operator action.
