# PhantomLayer × PhantomBank integration guide

The final manual journey is documented in [CUSTOMER-ONBOARDING.md](CUSTOMER-ONBOARDING.md)
and the presentation sequence in [JUDGE-DEMO.md](JUDGE-DEMO.md).

## Optional automated judge setup

First initialize/start PhantomLayer and the standalone bank using their READMEs.
Both must have local `DEMO_MODE=true`. From `PhantomBank/` run:

```sh
python scripts/provision_demo.py
```

This convenience script signs up or logs into the dedicated owner recorded in
ignored owner-only `.env.demo-login`, adds/reuses `phantombank.example.test`, publishes
the tenant-specific challenge from the bank when verification is needed, verifies
through the authenticated domain API, configures API protection, registers a
matching agent and calls the same customer installer. The installer validates
the authenticated organization/domain/agent tuple before writing its credential
to local `.env` and recreating bank-api. It does not reset bank datasets or write
control-plane rows directly.

The saved judge account is separate from an independently registered browser
customer. For the real customer story **use that browser customer's download**;
do not run provisioning to attach some other tenant. Tenant isolation correctly
prevents either account from seeing the other's incidents.

## Additional focused checks

`scripts/verify_isolation.py`, `scripts/safe_attack_simulation.py` and
`scripts/verify_restart.py` still exercise the installed protected bank. They
retain demonstration incidents/access-audit evidence. For fresh onboarding,
before/after proof and cleanup use `npm run test:customer` from
`phantomlayer/frontend` instead. See the judge runbook for the recovery manifest,
test isolation, and honest boundaries.
