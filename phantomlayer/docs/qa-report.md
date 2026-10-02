# Hardening and integration QA report

Recorded **2026-10-02 UTC** against local Docker stacks. This is evidence for a bounded synthetic MVP, not a penetration-test, compliance, or production-readiness certificate.

## Scope and repository state

- Existing application: `/home/anubhav/Projects/phantomlayer`, branch `main`, starting revision `de29616`.
- Separate new application: `/home/anubhav/Projects/PhantomBank`.
- Changes remain **uncommitted**. Pre-existing untracked `__agent__/` was preserved. The sibling bank is not included in PhantomLayer's Git diff and needs separate version-control handling.
- Existing volumes were retained; no database or volume drop was performed. New QA databases are deliberately retained, not automatically deleted.
- Important baseline safety finding: an early legacy-suite run used fixtures that clear honeypot sessions against the demo configuration. Later full runs use newly created, guarded QA databases. The report does **not** claim that the initial run preserved every pre-existing session.

## Executed results

| Check | Result | What it establishes |
| --- | --- | --- |
| Initial PhantomLayer backend baseline | 187 passed, 8 failed | Historical claims of 195 passing did not match the starting deployment |
| Final `./scripts/test-backend.sh -q` | **206 passed**, no skipped tests | Isolated PostgreSQL-backed backend regressions, including auth, tenant boundaries, persistence and integration contract |
| Existing agent suite | **16 passed** | Registration/config/heartbeat unit regressions; not unrestricted production agent validation |
| `PhantomBank/scripts/test-postgres.sh` | **19 passed**, no skipped tests | SQLite unit/API boundaries plus real PostgreSQL SQL/audit/transfer paths and six concurrent idempotent retries |
| Both frontend `npm run build` commands | **Passed** | TypeScript and production bundle generation |
| Both Docker builds and `docker compose up -d --wait` | **Passed** | All five PhantomLayer and four bank services healthy after deployment |
| Additive control migration | **Passed**, repeatable | Durable event/report/decision tables and normalized-email index without deleting records |
| Live isolation script | **Passed** | Controlled suspicious/pinned requests did not change real business-data or proxy-access-audit snapshots |
| Restart and `--recreate` scripts | **Passed** | Incident ID, completed mock analysis, timeline/events and bank PostgreSQL datasets/audits survived API restart/recreation; both UI proxies recovered |
| Browser smoke on actual Chrome | **Passed** | Bank desktop/mobile/navigation, an actual £0.01 synthetic transfer and displayed balance update, SOC login/overview/incident analysis/settings/onboarding/tenant-only directory, and no page errors |
| Docker network inspection | **Passed** | Five distinct internal data networks; no shared network between the bank's two database containers |
| `git diff --check` | **Passed** | No tracked patch whitespace errors |
| Current high-entropy runtime-secret/source comparison | **No matches** | Generated deployment secrets were not found in inspected source/docs; this is not a full historical secret-scanner audit |

The bank's PostgreSQL run emits a Starlette/httpx deprecation warning. Plain local `pytest -q` without the two PostgreSQL test URLs intentionally skips its PostgreSQL test; the executed Docker QA script supplies fresh databases, so that check was **not skipped** here. Earlier pytest cache-permission warnings were resolved by disabling cache writes in the isolated runner.

## Functional and security evidence

### Authentication and ownership

- Real authenticated tenant fixtures replaced legacy unauthenticated assumptions. No production auth bypass was introduced to make tests pass.
- Expired, malformed and missing authentication, suspended organizations and incorrect agent credentials are rejected.
- JWTs require identity/organization/role/time claims. Organization role is checked against current server-side identity.
- Two-tenant tests cover domains, agents, protection records, incidents/details/timelines, security events, sessions/statistics and integration observations/telemetry.
- A live second tenant received 404 for another tenant's incident and timeline and empty scoped feeds/statistics.
- Client-supplied integration ownership fields are forbidden. Cross-agent decision observations are rejected. Disabled API protection fails closed.
- `/organizations` returns exactly one authenticated organization; `admin` is not a platform-superuser role.
- The global event-clear API was removed. Legacy records with no defensible ownership are hidden from tenant feeds.

### Bank routing and data separation

- Normal synthetic login and account reads return Maya Bennett from the real bank dataset.
- Reconnaissance, sensitive enumeration and probing return believable synthetic John Carter records without routing metadata.
- Observed risk progressed **27 → 49 → 67 → 77 → 87 → 97 → 100**; a later ordinary profile operation stayed pinned to deception at the accumulated risk.
- The local proof fingerprints bank customers, accounts, transactions, transfers, beneficiaries, cards and the real gateway audit ledger **after initial legitimate authentication**. Those fingerprints remain unchanged through the attack sequence.
- The proof covers instrumented paths. Fingerprints and advisory reports alone cannot prove absence of an arbitrary unaudited read elsewhere. Background connectivity checks still perform `SELECT 1` without reading customer rows.
- Parameterized transfer tests cover decimals, foreign accounts, missing CSRF/auth, idempotency conflicts, and six concurrent PostgreSQL retries producing a single transfer/debit.
- A regression specifically proves the bank reuses its original server-issued UUID instead of mistakenly sending PhantomLayer's namespaced response handle on the next decision.

### Persistence and analysis

- Control-plane events/reports and integration decisions persist in PostgreSQL. Observation consumption and interaction/event insertion are atomic and retry-safe; incident projection can be retried after commit.
- Session reads now reload authoritative control-database state rather than hiding external telemetry behind an in-process cache.
- Additional interactions invalidate obsolete completed analysis. Forced re-analysis is wired through the UI.
- Restart verification compares the same report ID, completed analysis, timeline and event payloads before/after restart.
- Bank bootstrap preserves existing synthetic data and audits. Login sessions and the recent defender buffer are intentionally still process-local and reset on restart.
- Only allowlisted operation/risk/rule metadata and synthetic counts enter analysis, not raw bank rows or passwords. Unsupported raw operation strings are not copied into analysis narratives.
- The provider is **mock**. Recorded operations are separated from hypothetical intent; confidence is heuristic, and no recommendation controls routing or executes a security action. Advice warns against blindly blocking a shared proxy IP.

### Browser findings that builds missed

The initial frontend built and served HTTP 200 despite a missing router mount, a throwing dynamic onboarding component lookup, and mismatched nested authentication response/registration fields. These were fixed and exercised in a real browser.

A later backend recreation changed its Docker IP while Nginx retained the old address, causing login/API 502 responses despite healthy direct API access. Both frontend proxies now use Docker DNS re-resolution rather than requiring manual proxy restarts. `nginx -t` validates both configurations. The PhantomLayer API proxy also strips browser cookies: localhost cookies are shared across ports, whereas this API requires bearer authentication and should not receive the bank session cookie.

Browser QA submits one £0.01 transfer to a seeded beneficiary per successful run; these fictional ledger entries are retained. Screenshots are local artifacts in `/tmp/phantomlayer-qa-screenshots`, not committed customer evidence. The mobile overview was visually inspected and its overflowing wordmark corrected; hidden navigation labels now retain accessible link labels.

## Deliberate security-related contract changes

- Legacy `/gateway/query` and `/routing/route`: authentication + local demo mode + owned verified domain required. These remain shared synthetic-catalog demos, not customer production DB access.
- `/logging/events/clear`: removed rather than exposing global evidence deletion.
- Protection/session deletion mutations: organization-admin authorization.
- URL/path-shaped domain names: rejected in favor of normalized DNS hostnames.
- Integration decisions: require an enabled API/full protection; disabling it does not allow banking traffic to bypass protection.
- Configuration: reject short/placeholder signing secrets and identical bank dataset URLs. Existing passwords/volumes are not silently reset.

## Remaining limitations / next engineering work

1. **Before any external deployment:** tighter dependency/image pinning, TLS/mTLS, separate production hostnames/cookie boundaries, managed secrets/rotation, restrictive host exposure, least-privilege database roles, backup/restore and managed migrations. Runtime secrets appeared in early diagnostic inspection output; keep those logs private and rotate credentials before reuse/sharing. No such secret values are reproduced in these documents.
2. **Durable delivery:** a bank operation may commit before its observation fails. Local audit/logs remain, but there is no persistent bank observation outbox/retry worker or alert-notification service yet.
3. **Multiworker operation:** bank login sessions and rate limiters are process-local. PostgreSQL locks protect the implemented decision/transfer paths, but distributed-session, load/chaos and HA tests remain. The older structured-demo routing/cache paths are not certified for concurrent production workloads.
4. **Operational truthfulness:** healthchecks are liveness checks; agent health is last-reported metadata. Source IP may be a proxy hop. SOC decision counts are not a global measurement of every infrastructure request.
5. **Scale and lifecycle:** pagination/SQL aggregation, retention, resource limits, revocation/rotation workflows and complete schema constraints require more work. A pre-existing duplicate agent group was not deleted to force uniqueness.
6. **Product scope:** one fictional bank customer per dataset, recognizable synthetic IDs in some API data, no profile editing/support-ticket service, and no platform-wide tenant-admin dashboard. Existing browser bearer-token storage remains local storage.
7. **Analysis:** only the mock provider is implemented. No external model performance, production data-exfiltration prevention guarantee, complete threat coverage or compliance posture is asserted.

## Reproduce

Use [the runbook](hackathon-demo.md) and [PhantomBank README](../../PhantomBank/README.md). Do not run historical clearing fixtures against live/demo databases, overwrite existing `.env` values, run fresh-install seeds on existing catalogs, or remove volumes to obtain passing tests.
