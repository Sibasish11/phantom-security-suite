"""Additive migration for durable security records.

The project does not currently use Alembic.  This module intentionally exposes
an idempotent ``upgrade`` callable so deployment scripts can run it against an
existing control database without dropping or rewriting any data.
"""

from __future__ import annotations

from sqlalchemy.engine import Connection
from sqlalchemy import text

from app.models.security_records import IncidentReportRecord, SecurityEventRecord
from app.integrations.models import IntegrationDecisionRecord


TABLES = (
    SecurityEventRecord.__table__,
    IncidentReportRecord.__table__,
    IntegrationDecisionRecord.__table__,
)


def upgrade(connection: Connection) -> None:
    """Create security record tables and indexes when they are absent.

    ``checkfirst=True`` makes repeated invocations safe.  ``create_all`` is
    additive and does not remove existing rows or tables.
    """

    for table in TABLES:
        table.create(connection, checkfirst=True)
    # Fail instead of silently deleting/reassigning accounts if old data is
    # duplicated. The current deployment was checked before this migration.
    connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_organization_users_email_normalized ON organization_users (lower(email))"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_security_events_org_time ON security_events (organization_id, timestamp DESC)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_decisions_agent_session_target ON integration_decisions (agent_id, session_id, target)"))


def downgrade(connection: Connection) -> None:
    """Refuse destructive rollback; incident history must not be deleted."""

    raise RuntimeError(
        "security_records migration is additive and has no destructive downgrade"
    )


def main() -> None:
    from app.database import get_sync_control_db_manager

    manager = get_sync_control_db_manager()
    with manager.engine.begin() as connection:
        upgrade(connection)


if __name__ == "__main__":
    main()
