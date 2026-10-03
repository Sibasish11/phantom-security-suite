# Customer journey implementation and QA report

Executed locally on **2026-10-03**. Final browser run: `ad3817c3a9efd393`.
Evidence and screenshots: `/tmp/omnirush/customer-qa-ad3817c3a9efd393/`.
This reports the tested bounded architecture, not general attack resistance.

## Result

**Passed:** browser signup → login → new organization → domain → bank-published
ownership challenge → API protection → agent registration → credential recovery
by rotation → downloaded configuration → customer-side installation → actual bank
heartbeat → both DBs reachable → ACTIVE → legitimate banking → same before/after
attack → tenant incident → timeline → mock analysis → restart recovery → cleanup.

Fresh state means a fresh customer on the preserved running applications. Both
backend suites also used freshly created isolated PostgreSQL QA databases. No
live volume was erased or reseeded to obtain these results.

## Architecture and lifecycle changes

- The bank can start independently in explicit local standalone mode with no
  installed agent; the real customer journey no longer requires demo provisioning.
- Local verification is restricted to reserved `phantombank.example.test`, both
  DEMO_MODE gates and an exact tenant challenge fetched from a fixed bank endpoint.
  Other domains use DNS TXT. Challenges can be renewed after expiry.
- The UI downloads the registration/rotation credential once without displaying
  the token or persisting it in browser storage. The installer authenticates and
  checks the full organization/domain/agent tuple before writing customer `.env`.
- The existing embedded `bank-api` adapter/heartbeat is reused. Credentials and
  raw bank records remain local. Only metadata/counts enter SaaS/analysis.
- Protection status is computed from ownership, enabled compatible protection,
  fresh agent health, both DB probes and adapter readiness. Manual `status=active`
  is rejected. Staleness is 90 seconds; rotation clears readiness.
- Tenant filtering, JWT authority, agent secrets, deterministic routing, durable
  session pinning and independent bank databases remain enforced server-side.
- Incident detail now supplies server-scoped customer context and timeline rules
  correlated to each decision. Analysis stays advisory and explicitly mock.

## Observed before/after proof

Both phases used the same authenticated, loopback-only eight HTTP operations.
The baseline additionally required the private local presenter credential. It is
not an ordinary public application enumeration permission.

| Operation | Before | After risk / destination |
|---|---|---|
| list_tables | REAL | 27 / HONEYPOT |
| enumerate_api | REAL | 49 / HONEYPOT |
| get_customers | Maya / REAL | 67 / John / HONEYPOT |
| enumerate_accounts | REAL | 77 / HONEYPOT |
| enumerate_transactions | REAL | 87 / HONEYPOT |
| probe_admin | REAL path, unavailable response | 97 / HONEYPOT |
| get_customers | Maya / REAL | 100 / John / HONEYPOT |
| credential_probe | REAL path, credentials rejected | 100 / HONEYPOT |

These requests are read-only and allowlisted. Legitimate login/accounts reached
REAL before the attack fingerprint window. Protected recon was diverted below
50 by deterministic policy, with recorded rules and nondecreasing session risk.

SHA-256 business-dataset fingerprints were unchanged across both attack phases
and remained identical after QA cleanup:

```text
REAL      404f05ec0bdefe86c95a00cd68d44e9aa19d53967c77e097896386de596eff1a
HONEYPOT  0d0b9f4886bee70afa54e778241b7cdbd10cf7cb8df4fb21faf01e82bf140bfc
```

Protected attack's REAL access-audit fingerprint, before **and** after:

```text
1d78157ab908a7d0c0b626c4a6f6b4dcef721c4d448e7f817d52ff1c12d86727
```

The baseline changed the real access audit, as expected; the protected attack did
not. Entire original business-data **and audit** fingerprints were restored after
deleting only QA-owned access-audit rows. Neither business dataset was modified
by cleanup. Docker inspection confirmed separate bank networks and `{}` host port
bindings for both bank PostgreSQL services.

## Incident, isolation and UI evidence

The final disposable incident was `d38e0f32-da5a-4dfa-a266-efd35eedb66d`:
8 timeline interactions, 50 tenant events including legitimate activity, analysis
`completed`, provider `mock`. Rules, risk, stages, destinations and synthetic
exposure counts were visible in the browser. This incident was subsequently
removed as QA data; its sanitized evidence remains in the private report.

The second tenant received 404 for foreign domain, agent, protection, incident,
timeline, report, token rotation and analysis access; its incident/event lists
were empty. Foreign protection mutation was rejected. Invalid agent heartbeat
returned 401. Paused protection returned 503 to the integration. Backend tests
also covered cross-agent observations, JWT/resource isolation, expired heartbeat,
DB degradation, suspended organization and old credentials after rotation.

Checked SaaS event/report payloads excluded Maya/John records, seed identity
markers, bank login password, bank email and agent secret. Contract inspection
confirmed bank DB credentials/rows are not request fields and AI sees only the
sanitized projection. This was not a packet-capture test against production data.

Browser: actual bank owner setup and Maya login/accounts; actual SaaS registration,
login, verification, protection, download/recovery, activation and analysis.
Desktop 1440px and mobile 390px SOC/deployment/protection/activation/incident pages
passed overflow checks with no recorded browser errors. Saved screenshots were
also visually inspected. API restarts retained the same incident, timeline,
completed analysis and dataset/audit fingerprints, and the agent reactivated.

## Commands and results

| Check | Result |
|---|---|
| `./scripts/test-backend.sh -q` in phantomlayer | **208 passed** |
| `./scripts/test-postgres.sh` in PhantomBank | **21 passed**, one upstream TestClient deprecation warning |
| `npm run build` in both frontends | Passed; final Docker builds also compiled both frontends |
| `npm run test:customer` | Full lifecycle/recovery/isolation/browser/cleanup passed |
| `python scripts/provision_demo.py` on existing canonical setup | Idempotent authenticated install succeeded with original tenant/agent |
| `git diff --check` | Passed |
| Docker services | **9/9 healthy**; bank DBs have separate internal networks and no host ports |

During development, one browser run found an installer check inconsistent with
Compose's demo-mode default; it now reads the running bank's mode. Another run
found an overly exact Accounts button locator; the selector was corrected. Both
failed runs executed scoped cleanup. The final expanded run passed in full.

## Cleanup and retained presentation state

All resources from four recorded browser QA runs were verified absent after
cleanup. Final run removal: 2 organizations/users, 1 domain, 1 agent, 1 protection,
17 decisions, 50 events, 1 incident/report and 1 attack session with its 8
interactions, plus only that run's baseline and agent-prefixed bank audit rows.
Temporary credential downloads, bank configuration backups and presenter recovery
files were removed. Synthetic datasets, schemas, Docker volumes and documented
credentials were preserved. Screenshots, sanitized reports and nonsecret cleanup
manifests are intentionally retained under `/tmp/omnirush/`.

The first five QA databases created during this task were explicitly removed by
their recorded names; the updated backend runners removed their next five on
exit. Older pre-existing QA databases/tenants were left intact because they were
not created by this task. Cleanup never guessed ownership.

Retained canonical connection (confirmed through authenticated APIs):

- domain `phantombank.example.test`, verified;
- organization `6ca268c8-9b27-43f7-a59d-c41a075d6ecc`;
- agent `88b4a098-0296-4073-8b2f-4f55c8547bff`, healthy;
- real and honeypot reachable, protection active.

The original browser `phantombank.com` tenant was not reassigned. New manual
customers install their own downloaded credentials. Existing presentation
credentials in `.env.demo-login` still belong to the canonical automated tenant.
Use the documented explicit standalone/restore workflow to present signup again.

## Changed files

**PhantomBank:** `.env.example`, `README.md`, `docker-compose.yml`;
`backend/app/{config,gateway,main}.py`;
`backend/tests/{conftest,test_standalone_boundary}.py`;
`frontend/src/App.tsx`;
`scripts/{connect,compare_attack,provision_demo}.py`;
`scripts/{setup,test-postgres}.sh`.

**PhantomLayer:** `README.md`; `backend/app/readiness.py`;
`backend/app/agent/{router,schemas,service}.py`;
`backend/app/domains/{router,schemas,service}.py`;
`backend/app/protections/{schemas,service}.py`;
`backend/app/honeypot/{schemas,service}.py`;
`backend/app/integrations/router.py`; `backend/app/security_dashboard/router.py`;
`backend/scripts/cleanup_customer_qa.py`;
`backend/tests/{dns_proof,test_customer_readiness,test_integration_contract,test_onboarding_dashboard,test_tenant_boundaries}.py`;
`scripts/test-backend.sh`; `frontend/package.json`;
`frontend/tests/customer-journey.cjs`; `frontend/src/hooks/useOrganization.ts`;
`frontend/src/lib/api.ts`; `frontend/src/types/{agent,protection}.ts`;
`frontend/src/pages/customer/{Agent,IncidentDetail,Protection}.tsx`;
`frontend/src/pages/onboarding/{Activation,ChooseProtection,DeployAgent,VerifyDomain}.tsx`;
`docs/{CUSTOMER-ONBOARDING,CUSTOMER-JOURNEY-QA,JUDGE-DEMO,agent-deployment,hackathon-demo}.md`.

## Remaining limitations

Fixed local adapter/operation coverage, a reserved demo domain and fixed local
installer endpoints, agent-reported rather than attested readiness, mock analysis,
trusted bank host, process-local bank sessions/rate limits and no durable telemetry
outbox. Production TLS/mTLS, secret management, HA/scale, retention and operational
hardening remain. The end-to-end test used fresh tenants on the preserved runtime;
it did not destroy/recreate the entire installation. No real-world security,
pentest, compliance or production-certification claim is made.
