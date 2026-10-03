"""Explicit manifest-scoped cleanup for customer-journey QA. Never a public API.

Input is a manifest on stdin. Every organization must match the exact run name,
ID and recorded user ID before any deletion. Canonical/demo organizations fail
the checks. Bank cleanup is separate and never touches its business datasets.
"""
import json
import re
import sys
from uuid import UUID

from sqlalchemy import delete, select

from app.database import get_sync_control_db_manager
from app.models.control_plane import Organization, OrganizationUser, Agent, Domain, ProtectionConfiguration, AttackSession
from app.models.security_records import SecurityEventRecord, IncidentReportRecord
from app.integrations.models import IntegrationDecisionRecord


def main():
    manifest = json.load(sys.stdin)
    run = manifest['run']
    if not re.fullmatch(r'[a-f0-9]{16}', run) or manifest['purpose'] != 'customer-journey-qa':
        raise SystemExit('Invalid QA manifest')
    with get_sync_control_db_manager().session() as db:
        for record in manifest['organizations']:
            org = db.get(Organization, UUID(record['id']))
            if org is None:
                continue  # Idempotent cleanup of a previously completed run.
            assert org.name == record['name'] and org.name in {f'Customer QA {run}', f'Customer QA {run} isolation'}
            users = db.execute(select(OrganizationUser).where(OrganizationUser.organization_id == org.id)).scalars().all()
            assert len(users) == 1 and str(users[0].id) == record['user_id']
            assert users[0].email == record['email'] and record['email'].startswith(f'customer-qa-{run}')
        counts = {}
        for record in manifest['organizations']:
            oid = UUID(record['id'])
            for model in (SecurityEventRecord, IncidentReportRecord, IntegrationDecisionRecord, AttackSession,
                          Agent, ProtectionConfiguration, Domain, OrganizationUser):
                count = db.execute(delete(model).where(model.organization_id == oid)).rowcount
                counts[model.__tablename__] = counts.get(model.__tablename__, 0) + count
            db.execute(delete(Organization).where(Organization.id == oid))
        db.commit()
        print(json.dumps({'removed_qa_records': counts, 'organizations': len(manifest['organizations'])}))


if __name__ == '__main__':
    main()
