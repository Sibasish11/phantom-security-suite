# PhantomLayer

A tenant-scoped cybersecurity-deception MVP. Deterministic detection and session risk direct suspicious application operations to synthetic deception; persisted evidence supports a SOC investigation interface. Analysis is **advisory** and the current provider is explicitly labeled **mock**.

This is a hardened local/hackathon demonstration, **not a production-readiness or compliance certification**. No production customer data or bank credentials are required.

## Architecture and trust boundaries

```text
PhantomBank browser → bank API / customer-side proxy
                         │
                         ├─ authenticated metadata → PhantomLayer decision service
                         │                              └─ control PostgreSQL
                         │                                 decisions / incidents / events
                         ├─ allow → bank real PostgreSQL (synthetic Maya Bennett)
                         └─ divert → isolated bank deception PostgreSQL (synthetic John Carter)
                                      │
                         counts only ─┘→ PhantomLayer observe → tenant SOC dashboard
```

- `../PhantomBank` is a **separate application**, not a replacement for this repository.
- The bank makes its own database connections. PhantomLayer never receives its connection strings, passwords, account rows, or authentication payloads.
- Tenant/domain/agent ownership comes from validated server-side identity, not client-supplied tenant IDs.
- Agent authentication requires an active organization, verified owned domain, and enabled API/full protection. Missing protection is a fail-closed 503, not permission to bypass routing.
- Bank session pinning and nondecreasing risk use a durable decision ledger and PostgreSQL advisory transaction locks. Observations are idempotent. Unsupported operations cannot execute arbitrary SQL.
- Persisted security events, honeypot interactions and incident reports are tenant-filtered. Legacy unowned records are hidden, not assigned to whichever tenant requests them.
- `/admin` is **organization administration**, not a platform-wide superadmin role. `/organizations` returns only the authenticated organization.

### Existing structured gateway

The original detection, risk, gateway, routing, honeypot and agent APIs remain. `/gateway/query` and `/routing/route` now require authentication, `DEMO_MODE=true`, and an owned verified domain (`X-Domain-ID` if more than one exists). They access the original shared **synthetic e-commerce catalog**; they are not production customer-database integrations. Historical `real`/`honeypot` target names identify demo stores, not real-world data provenance. The separate bank contract is the demonstrated customer-side integration.

## Local startup

Prerequisites: Docker Compose and Python 3.11+. Host frontend development also needs Node 20+.

**New installation only:**

1. Copy `.env.example` to `.env` **only if it does not exist**. Set a random database password and a random `AUTH_SECRET_KEY` of at least 32 characters. Never overwrite an existing deployment's database password blindly.
2. Set `DEMO_MODE=true` only for the local synthetic demonstration. Leave analysis at `AI_ENABLED=false`, `AI_PROVIDER=mock`.
3. Start and initialize:

   ```sh
   docker compose up --build -d --wait
   # Fresh databases only: creates schema and inserts the synthetic catalog.
   docker compose exec -T backend python -m app.init_db init-all
   docker compose exec -T backend python -m scripts.migrate_control
   ```

**Existing installation:** preserve `.env` and all volumes. Build/start and run only the additive control migration; do not reseed existing catalogs:

```sh
docker compose up --build -d --wait
docker compose exec -T backend python -m scripts.migrate_control
```

The migration creates security record/decision tables and indexes without dropping data. Its normalized-email unique index intentionally fails if legacy duplicates exist; resolve those with an approved migration, not record deletion.

- Dashboard: <http://localhost:3000>
- API: <http://127.0.0.1:8000>
- PostgreSQL: loopback ports 5432 / 5433 / 5434. Separate internal data networks and separate publish networks preserve database separation.
- Local PhantomLayer web/API ports bind to loopback; the supplied stack is not a TLS deployment. Healthchecks establish liveness, not exhaustive database/schema readiness.

For the presentation, follow [the Judge Demo Runbook](docs/JUDGE-DEMO.md): startup commands, the complete signup-to-investigation sequence, synthetic credentials, before/after proof and recovery. [The integration guide](docs/hackathon-demo.md) explains optional automated judge provisioning without printing generated credentials.

Start the actual product journey with [Customer onboarding](docs/CUSTOMER-ONBOARDING.md).
PhantomBank now starts independently, publishes your local ownership challenge,
and installs a customer-specific configuration downloaded from the authenticated
UI. `provision_demo.py` is optional. ACTIVE is derived from verified ownership,
enabled matching protection, a fresh healthy agent, both local databases and the
installed routing adapter; clients cannot set it manually.

## Checks — do not point historical fixtures at live data

```sh
# From phantomlayer/: creates fresh, separately named QA databases.
./scripts/test-backend.sh -q

# Frontend build and complete customer browser QA (requires both running stacks).
cd frontend
npm ci
npm run build
# Install a browser with npx playwright install chromium, or set CHROMIUM_PATH.
npm run test:customer
```

The QA runner creates `phantomlayer_qa_*` databases, seeds test identities, refuses non-QA targets, and removes only the databases it just created on exit. It never drops live databases or volumes. **Do not run the full legacy backend suite directly against demo databases:** some historical fixtures clear sessions. The customer browser test (`npm test` or `npm run test:customer`) tracks and cleans its disposable tenants/events/incidents and bank audits, restores the original connection, and verifies both original dataset/audit fingerprints. Existing canonical and historical tenants are retained. Older `test:smoke`, `test:ui` and `test:judge` scripts retain activity and are not the final customer lifecycle test.

Bank tests, PostgreSQL concurrency checks, live isolation and restart scripts are documented in [PhantomBank's README](../PhantomBank/README.md). Fresh presentation checks are in [final demo verification](docs/final-demo-verification.md); earlier findings and boundaries remain in [the QA report](docs/qa-report.md). Run Docker-backed suites before (not during) browser QA to avoid Chromium network-change errors as disposable containers are created/removed.

## Main paths

| Path | Purpose |
| --- | --- |
| `backend/app/integrations/` | Agent-authenticated bank decisions and observations |
| `backend/app/security_context.py` | Trusted server-side ownership context |
| `backend/app/security_logging/` | Persistent, tenant-scoped event storage |
| `backend/app/incident_analysis/` | Sanitized evidence projection and advisory analysis |
| `backend/app/migrations/security_records.py` | Additive control migration |
| `backend/tests/qa_runner.py` | Isolated database QA runner |
| `frontend/src/pages/customer/Overview.tsx` | Evidence-focused SOC overview |
| `frontend/tests/browser-smoke.cjs` | Browser navigation, synthetic transfer and analysis smoke checks |
| `frontend/tests/ui-polish.cjs` | Responsive route, onboarding, accessibility and error-state checks |
| `frontend/tests/judge-demo.cjs` | Single-session bank → deception → SOC browser rehearsal with live isolation fingerprints |
| `docs/JUDGE-DEMO.md` | Presentation-ready runbook |
| `agent/` | Existing outbound registration/health agent |

## Production work still required

- TLS/mTLS, managed secrets and rotation, trusted proxy/IP configuration, least-privilege database roles, backup/restore drills, and an audited migration pipeline.
- Distributed rate limiting and bank session storage; the current auth limiters and bank login sessions are process-local. PhantomLayer frontend bearer tokens remain in local storage.
- Durable bank observation outbox/retry and alert delivery. A post-commit observation failure is logged locally; it does not undo a completed transfer or falsely report it as failed.
- Retention, pagination/aggregation at scale, resource limits and multiworker/load/failure testing. The older structured-demo routing path has not received the same multiworker validation as the bank contract.
- Full bank/customer tenancy, fraud controls and realistic operational lifecycle. This bank is one fictional customer per dataset. Some synthetic internal identifiers remain recognizable as demo identifiers.
- A real external analysis provider if desired. Current mock hypotheses/confidence are not measured probabilities, and no recommendation automatically executes a security action.

See also [agent deployment notes](docs/agent-deployment.md). Avoid sending credentials, raw records, or private request payloads to analysis providers.
