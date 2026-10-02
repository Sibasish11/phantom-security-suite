# Final presentation verification

Verified **2026-10-02 UTC**. The independent backend/bank check below finished at **20:48:53 UTC**; the final deployment, builds, isolation/restart rerun and browser rehearsal finished around **21:09 UTC**. All nine services were healthy at the **21:08:52 UTC** health check. This is evidence for a bounded local synthetic demo, not a production-readiness, compliance, or penetration-test certificate. The final frontend/browser evidence is recorded in the last section.

## Scope and preservation

- PhantomLayer: `/home/anubhav/Projects/phantomlayer`; separate bank: `/home/anubhav/Projects/PhantomBank`.
- Read the existing QA report, bank README, guarded runners, verification scripts, and the implemented decision, gateway, database, telemetry, analysis and dashboard paths.
- Preserved existing uncommitted application changes, existing databases and Docker volumes. No reset, destructive seed, volume removal, protection disablement or credential rotation was performed.
- Only repository file added by this verification: **`docs/final-demo-verification.md`**. No backend/bank defect requiring a source change was found. No frontend or `docs/JUDGE-DEMO.md` changes were made by this worker.
- Before live checks, SHA-256 manifests of application Python sources confirmed that **both running API images matched their workspace `backend/app/**/*.py` files**.
- The guarded runners created fresh QA databases: three for PhantomLayer and two for PhantomBank. These are retained for operator-approved cleanup. Running demo tables were not used by the regression suites.
- Live operations used localhost APIs and fictional records only. Normal logins/reads legitimately append real-dataset gateway audit entries; the attack-isolation baseline is deliberately taken **after** legitimate login/account access. This worker submitted **no live transfer**. Transfer mutations were confined to the disposable regression databases.
- Runtime defender/integration authentication was consumed privately by existing helpers; no runtime credential, token, environment content or complete Docker configuration is included in this evidence.

## Commands and results

Commands are relative to `/home/anubhav/Projects/phantomlayer` unless stated otherwise. Every listed functional command exited successfully.

| Exact command | Fresh result |
| --- | --- |
| `docker compose up -d --wait` | Five PhantomLayer services healthy |
| `(cd ../PhantomBank && docker compose up -d --wait)` | Four bank services healthy |
| `./scripts/test-backend.sh -q` | **206 passed in 7.93s**, no skips |
| `(cd agent && .venv/bin/python -m pytest -q -p no:cacheprovider tests)` | **16 passed in 0.33s**, no skips |
| `(cd ../PhantomBank && ./scripts/test-postgres.sh)` | **19 passed**, no skips; includes the actual PostgreSQL test |
| `(cd ../PhantomBank/backend && .venv/bin/python -m pytest --collect-only -q -o addopts= -p no:cacheprovider)` | Independently confirmed **19 collected cases**; collection is not an additional test run |
| `(cd ../PhantomBank && python scripts/safe_attack_simulation.py)` | Login and three reconnaissance requests HTTP 200; synthetic result counts **7 tables, 15 operations, 1 customer** |
| `(cd ../PhantomBank && python scripts/verify_isolation.py)` | **Passed twice**, in separate sessions |
| `python /tmp/phantomlayer-final-backend-check.py` | Additional authenticated live assertions passed; described below |
| `(cd ../PhantomBank && python scripts/verify_restart.py)` | Incident/report/analysis/events/timeline and both bank datasets/audits preserved; both UI API proxies recovered |
| `(cd ../PhantomBank && python scripts/verify_restart.py --recreate)` | Same assertions passed after forced API container recreation |
| `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` in each project | All **nine** services running and healthy after recreation |
| `git diff --check` | Passed; the new evidence file also passed an explicit trailing-whitespace/newline check |

**241 automated test cases passed in total.** Bank execution and collection emitted the existing Starlette/httpx deprecation warning. The bank runner is double-quiet because `pytest.ini` already sets `-q`; the separate collection confirmed its case count. No skipped PostgreSQL result has been counted as a pass.

The temporary additional checker and its sanitized JSON output (`/tmp/phantomlayer-final-backend-evidence.json`) are local verification artifacts, not a new supported project runner. The existing repository scripts above remain the reproducible entry points. The simulation prints a bounded recent defender buffer, which can include previous sessions; the detailed assertions below explicitly group evidence by session instead of treating that entire buffer as fresh activity.

## Authentication, legitimate activity, detection and pinning

Actual bank login and read operations returned **Maya Bennett**, **two accounts** (Everyday and Savings), and **10 existing activity rows**. No starting balance or transaction count is assumed immutable: prior legitimate demo transfers are retained.

Actual negative HTTP checks returned:

- unauthenticated PhantomLayer `/incidents`: **401**;
- unauthenticated bank `/api/accounts`: **401**;
- uncredentialed bank `/internal/defender-evidence`: **404**;
- authenticated bank logout without the CSRF token: **403**;
- logout with the matching CSRF token: **200**, followed by `/api/accounts`: **401**.

The authenticated organization directory returned exactly one organization. Backend regressions also exercised two actual registered tenants, cross-tenant 404s, scoped event/statistics feeds, agent-owned observations, rejected ownership overrides, disabled-protection fail-closed behavior and replay idempotency. This fresh live run did not create another persistent tenant just to repeat those isolated-suite cases.

Both complete isolation sessions produced **identical** operation/risk/destination sequences:

| Operation | Risk | Destination | Stage |
| --- | ---: | --- | --- |
| `login` | 0 | real | normal |
| `get_accounts` | 0 | real | normal |
| `list_tables` | 27 | honeypot | reconnaissance |
| `enumerate_api` | 49 | honeypot | reconnaissance |
| `get_customers` | 67 | honeypot | enumeration |
| `enumerate_accounts` | 77 | honeypot | exfiltration |
| `enumerate_transactions` | 87 | honeypot | exfiltration |
| `probe_admin` | 97 | honeypot | exfiltration |
| `get_customers` again | 100 | honeypot | exfiltration |
| `credential_probe` | 100 | honeypot | credential_access |
| ordinary `get_profile` follow-up | 100 | honeypot | credential_access |

The first reconnaissance operation fired `RULE_ENUMERATION` and `RULE_RECONNAISSANCE`; the second also fired `RULE_REPEATED_ACCESS`. Sensitive operations fired `RULE_SENSITIVE_DATA_ACCESS` and `RULE_REPEATED_ACCESS`. The final benign-looking profile request had **no fresh triggered rules**, but remained at risk 100 and in deception because of persistent session history.

Routing is **not merely a score >= 50 threshold**: the bank integration explicitly diverts reconnaissance/sensitive operations, including the first score-27 request. This is an allowlisted, deterministic operation policy, not arbitrary payload analysis or AI-controlled routing.

Both attack proofs saw **John Carter**, not Maya, on customer enumeration and on the later profile request. Both compared SHA-256 fingerprints of the real PostgreSQL `bank_customers`, `accounts`, `transactions`, `transfers`, `beneficiaries`, `cards` **and `gateway_audit`** before and after the suspicious sequence. **Both fingerprints were unchanged.** Normal authentication/account access occurs before that baseline, not inside the no-real-access claim.

## Fresh telemetry and analysis evidence

Persistent incident useful for the subsequent browser demonstration:

- Incident/report ID: **`aff4c8b1-acd6-4482-90f6-58af522b00d6`**.
- Session ID: `bank:88b4a098-0296-4073-8b2f-4f55c8547bff:256f738848c589c63cb15206cffe7f06`.
- Maximum risk: **100**; final stage: **credential_access**.
- **Nine** successful ordered timeline steps, including the pinned ordinary profile read.
- **35** session-correlated events: **9** `request_analyzed`, **9** `routing_decision`, **8** `suspicious_request`, **9** `honeypot_interaction`.
- Analysis status **completed**, provider explicitly **mock**. Immediate report read-back matched the response. `?force=true` re-analysis completed and retained the report ID.
- Live report/event/timeline payload assertions found no bank customer names/emails, password hashes, session-cookie material or defender marker strings. Source inspection confirms analysis receives an explicit allowlist of operations, risk/rules/stages and synthetic exposure counts rather than banking result rows.
- The bank's registered agent was **healthy**, with both database reachability flags true. Its last heartbeat was **11.06 seconds** old during the detailed check and **24.43 seconds** old during final post-recreation verification.

The demo bank implements the customer-side adapter and heartbeat inside **`bank-api`**. There is no separate agent container in this nine-service deployment. The standalone agent unit suite is a separate regression check. The bank heartbeat currently reports `telemetry_events_sent: 0`; actual bank events arrive through `/integrations/bank/decision` and `/integrations/bank/observe`, not through that heartbeat counter.

## Restart and recreation evidence

Both supplied modes passed. They restart/recreate the **two APIs**, not the PostgreSQL containers or volumes.

1. Authenticate to PhantomLayer and complete mock analysis of the newest incident.
2. Capture its report ID, completed analysis, timeline and event response.
3. Restart/recreate PhantomLayer API; reuse the authenticated bearer to reach `/organizations` through the SOC proxy; verify the captured incident data is unchanged.
4. Fingerprint both bank PostgreSQL datasets, including transfers and gateway audit rows.
5. Restart/recreate bank API; verify both fingerprints are unchanged and the bank UI proxy reaches `/health`.

A separate final read-back after both modes again confirmed the named incident, completed mock analysis, nine timeline steps, the exact risk sequence, 35 events, healthy agent and HTTP 200 from **both UI API proxies**. The protected recent bank evidence buffer was **empty**, confirming its process-local reset.

**All services are ready for the parent session's browser checks. No further restarts are planned by this worker.** Bank login sessions reset with the bank API; browser users must sign in again. Persisted SOC incident evidence remains available. No claim is made that bank login sessions survive restart.

## Network facts and operational caveats

Targeted Docker inspection read only network names/internal flags and port bindings, not complete container configuration.

- Five distinct internal data networks exist across the two stacks.
- The bank databases each occupy their own internal-only network, share **no network** with one another, and expose **no host ports**.
- Each PhantomLayer database additionally has its own non-internal `*_publish` network for existing loopback development access: real **127.0.0.1:5432**, honeypot **127.0.0.1:5433**, control **127.0.0.1:5434**.
- An initial ad-hoc topology assertion incorrectly assumed every PostgreSQL container had only an internal network. It failed on those existing PhantomLayer publishing bridges. The corrected check verified the actual topology above; no configuration was changed. Do not describe all five PostgreSQL services as internal-only or having no host bindings.

## Boundaries not proved by this run

- The isolation proof covers instrumented bank application requests and their audit ledger, not arbitrary unaudited reads, host compromise or a production attacker. Separate health probes execute `SELECT 1`.
- Deterministic mock analysis is advisory and makes no routing decisions, blocking actions or outbound alerts. No external model or attack-prevention guarantee was tested.
- Decision and banking commits are not one distributed transaction. A transfer can commit before its observation fails; there is no durable bank observation outbox/retry worker yet.
- Login sessions, login rate limits and the bounded defender evidence buffer are process-local. Multiworker/HA, scale, failover and chaos behavior were not verified.
- Health flags are last-reported metadata, not proof of end-to-end coverage. Peer IP may identify a shared proxy rather than the original browser.
- Existing tests cover CSRF/auth rejection, amounts, foreign-account denial, idempotency conflicts and six concurrent PostgreSQL retries producing one transfer/debit. Those are **QA-database** results; this worker did not perform a live write or browser transfer.
- TLS/mTLS, separate production cookie hostnames, restrictive host exposure, managed secrets, least-privilege database roles, retention, backup/restore and production operations remain deployment work.
- The backend-only phase did not establish frontend behavior; that was subsequently checked below.

## Final frontend, deployment, and judge rehearsal

### Frontend finishing work

Preserved the existing coherent near-black/violet visual system and all existing page flows, then closed presentation gaps:

- Onboarding name/organization validation rejects whitespace-only input, input limits match backend limits, password visibility respects loading, and all six setup step numbers now agree with the progress navigation. Existing single-brand layout, success/pending states, sign-in navigation and privacy explanation were retained and exercised.
- Overview readiness now matches protection, verified domain and healthy agent **for the same domain**, with an explicit active-protection count. Recent evidence names its event type and links to the session's event feed instead of presenting similar-looking unlabelled rows.
- Incidents retain severity, risk, time and status on mobile. The queue now links directly to **Open full investigation**.
- Incident detail puts the attack timeline first, adds a chronological **27 → 49 → 67** risk visualization, observed synthetic counts/outcomes, **Refresh evidence**, and a session-specific event link. Advisory intent and mock analysis remain explicitly labeled.
- Event console supports server-filtered session evidence and a working **Show all sessions** action. Existing search, severity/destination filters, expandable metadata, retry/empty states and keyboard navigation remain functional.
- PhantomBank's startup no longer sends a guaranteed-to-fail session-restoration request for a brand-new visitor. Presence of its readable CSRF cookie is only a restoration hint; the signed HttpOnly session is still authenticated by the API. Valid session restoration, logout and a new Maya login were verified.
- No backend architecture or security routing was rewritten. Existing working data, source changes, and volumes were preserved.

### Final commands and outcomes

| Exact command | Result |
| --- | --- |
| `./scripts/test-backend.sh -q` | **206 passed in 8.81s**, no skips, fresh guarded databases |
| `cd agent && .venv/bin/python -m pytest -q -p no:cacheprovider tests` | **16 passed in 0.32s**, no skips |
| `cd ../PhantomBank && ./scripts/test-postgres.sh` | **19 passed**, no skips; existing Starlette/httpx deprecation warning |
| `cd frontend && npm run build` | Passed TypeScript + Vite; final assets `index-CajtG0Yi.css` and `index-CYx3L3eh.js` |
| `cd ../PhantomBank/frontend && npm run build` | Passed TypeScript + Vite; final assets `index-DGJjfFvE.css` and `index-4wqigDik.js` |
| `docker compose build frontend` / bank `docker compose build bank-ui` | Both passed and deployed. Docker reported missing buildx and used its working classic builder; no build failure. |
| `docker compose up -d --wait` in both repositories | All nine services healthy |
| Bank `python scripts/safe_attack_simulation.py` | Repeated successfully against loopback; real login and three deception reconnaissance responses |
| Bank `python scripts/verify_isolation.py` | Repeated successfully after final UI deployment; real business and audit fingerprints unchanged during attack |
| Bank `python scripts/verify_restart.py` and `python scripts/verify_restart.py --recreate` | Both repeated successfully; persisted analysis/incident/timeline/events and bank data/audit intact; UI proxies recovered |
| `docker compose exec -T frontend nginx -t` / bank `docker compose exec -T bank-ui nginx -t` | Both successful |
| `CHROMIUM_PATH=/opt/google/chrome/chrome npm test` in `frontend`, with privately sourced local defender credentials | **All three browser workflows passed**, final complete run **51 seconds** |
| `git diff --check` | Passed |

**241 backend/agent/bank test cases passed, plus three real-browser workflows.** No PostgreSQL skip was counted as a pass. No standalone frontend unit-test or lint suite is claimed; the frontend test command executes Playwright against the actual served applications, and both builds include TypeScript checks.

### Browser coverage and actual outcome

1. **`tests/browser-smoke.cjs`:** actual bank sign-in, Overview/Accounts/Activity/Cards/Profile/Support navigation, mobile bank view, one **£0.01 synthetic transfer**, verified displayed balance debit, SOC login/overview/analysis/settings/onboarding, and tenant-only administration. No page errors.
2. **`tests/ui-polish.cjs`:** all 26 public/setup/customer/admin routes at **1440, 820 and 390px**, plus mobile unauthorized/not-found pages. Checks document overflow, no duplicate signup logo, password visibility, visible mobile incident risk/status/time, consistent setup numbering, prominent timeline, keyboard/focus/Escape behavior, customer investigation link, event filters/detail/empty/retry, actual signup/domain/demo-verification/protection/agent-pending flow, pause/enable, and empty-tenant settings. **No unexpected console/page errors or functional API failures.** A deliberately intercepted **503** tests the event error/recovery state and is not mislabeled as a successful API request. DNS failure is browser-intercepted; no external DNS verification is performed by the test.
3. **`tests/judge-demo.cjs`:** no routing mocks. A single fresh bank browser session receives Maya and real/risk-0 decisions, performs the runbook's three recon requests, receives only John, then remains pinned on an ordinary profile request. It verifies exactly one new correlated incident, risks **27 → 49 → 67 → 67**, actual rule/routing events, the six-stage pipeline, mock analysis, session-filtered event inspection, believable John profile after bank reload, fresh telemetry invalidating analysis, successful re-analysis/read-back, and sign-out/new login returning to Maya. **Zero browser console errors, page errors or failed HTTP requests in the final full rehearsal.**

The judge browser test fingerprints real customers/accounts/transactions/transfers/beneficiaries/cards **and gateway audit after legitimate activity**, compares after recon/pinned profile, and compares again after the pinned bank UI reload and incident analysis. All comparisons matched. A fresh normal login is deliberately outside this window. This proves the bounded instrumented sequence, not that legitimate demo writes never change the database.

Both UIs returned HTTP **200**; both backend `/health` responses were healthy. Screenshots were inspected locally and are retained outside the repository:

- `/tmp/phantomlayer-ui-polish/`: public, onboarding, all console/admin pages, desktop/mobile, empty/error states.
- `/tmp/phantomlayer-qa-screenshots/`: banking/transfer and SOC smoke views.
- `/tmp/phantomlayer-judge-rehearsal/`: investigation, session evidence, believable synthetic bank profile.

These contain fictional demo UI only; one-time agent credentials were not screenshotted. No browser storage, authorization headers, raw runtime secrets or generated defender passwords are included in the documents.

### Failures found and resolved during this pass

- The new strict rehearsal initially caught the bank's fresh-visitor `/api/auth/session` **401** in the console. Fixed the unnecessary restoration request; the complete rehearsal then passed with no console failures.
- One rehearsal overlapped disposable Docker QA container activity and caught Chromium **`ERR_NETWORK_CHANGED`**. The checks were rerun sequentially and passed without suppressing these errors. The runbook now explicitly requires this ordering.
- The new setup-caption regression initially assumed the already-completed domain screen still had a numbered caption. It legitimately says **DOMAIN READY**. The test now explicitly recognizes only that state and checks it is step 2, while still requiring number agreement on the other setup screens; the full suite was rerun successfully.

Smoke runs made four retained **£0.01 fictional transfers** across successful and interrupted-suite attempts in this pass. Tests also retained synthetic UI QA organizations/configuration and new incident evidence. No data was deleted/reset to obtain a pass. The real-data **attack-isolation** result is unchanged; it does not deny those intended legitimate writes.

### Presentation handoff

Use **[`docs/JUDGE-DEMO.md`](JUDGE-DEMO.md)** for exact startup, private synthetic credentials, twelve presenter steps, judge questions, recovery commands and honest limitations. `README.md` and the sibling bank README link to it. Both stacks are left running and healthy. Restart/recreation checks intentionally reset bank login sessions, so presenters should sign in afresh. The production limitations above and in `qa-report.md` still apply.
