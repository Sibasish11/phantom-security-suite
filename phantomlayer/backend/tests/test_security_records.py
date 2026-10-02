"""Focused tests for control-plane security-record boundaries.

The existing gateway tests intentionally use the process-wide stores. These
unit tests inject isolated stores and therefore never clear or mutate a shared
control database. The opt-in integration test uses only the throwaway QA DB
created by scripts/test-backend.sh.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.database import get_sync_control_db_manager
from app.migrations.security_records import upgrade
from app.incident_analysis.schemas import AnalysisStatus, IncidentReport
from app.incident_analysis.service import IncidentReportStore
from app.models.control_plane import AttackSession, Organization
from app.models.security_records import IncidentReportRecord, SecurityEventRecord
from app.security_logging.schemas import EventSource, EventType, SecurityEvent
from app.security_logging.service import EventStore, SecurityEventLogger


def test_event_store_isolates_tenants_server_side():
    first_tenant = uuid4()
    second_tenant = uuid4()
    store = EventStore()
    logger = SecurityEventLogger(store)

    first = logger.log_event(
        EventType.REQUEST_ANALYZED,
        EventSource.ROUTING,
        organization_id=first_tenant,
        operation="first-tenant-operation",
    )
    logger.log_event(
        EventType.REQUEST_ANALYZED,
        EventSource.ROUTING,
        organization_id=second_tenant,
        operation="second-tenant-operation",
    )

    assert [event.event_id for event in store.get_recent(organization_id=first_tenant)] == [first.event_id]
    assert [event.operation for event in store.get_recent(organization_id=second_tenant)] == [
        "second-tenant-operation"
    ]
    assert store.get_by_id(first.event_id, organization_id=second_tenant) is None


def test_incident_store_preserves_report_id_when_session_is_replaced():
    store = IncidentReportStore()
    original = IncidentReport(
        session_id="sess-reanalysis",
        status=AnalysisStatus.PENDING,
    )
    store.save(original)

    replacement = IncidentReport(
        session_id="sess-reanalysis",
        status=AnalysisStatus.COMPLETED,
    )
    store.save(replacement)

    assert replacement.report_id == original.report_id
    assert store.get_by_session("sess-reanalysis") is not None
    assert store.get_by_session("sess-reanalysis").report_id == original.report_id
    assert store.count() == 1


def test_security_record_models_are_control_plane_records():
    assert SecurityEventRecord.__table__.metadata is IncidentReportRecord.__table__.metadata
    assert SecurityEventRecord.__table__.metadata.schema is None
    assert "organization_id" in SecurityEventRecord.__table__.c
    assert "session_id" in SecurityEventRecord.__table__.c
    assert "organization_id" in IncidentReportRecord.__table__.c
    assert "session_id" in IncidentReportRecord.__table__.c


@pytest.mark.skipif(
    os.environ.get("PHANTOMLAYER_TEST_DATABASES") != "1",
    reason="requires the isolated QA control database",
)
def test_persistent_stores_survive_restart_and_isolate_tenants():
    """Fresh store instances recover records and cannot cross tenant bounds."""

    db = get_sync_control_db_manager()
    # The additive migration is safe to apply repeatedly on the QA database.
    with db.engine.begin() as connection:
        upgrade(connection)
        upgrade(connection)

    first_tenant = Organization(
        name=f"record-qa-{uuid4().hex[:12]}",
        slug=f"record-qa-{uuid4().hex[:12]}",
    )
    second_tenant = Organization(
        name=f"record-qa-{uuid4().hex[:12]}",
        slug=f"record-qa-{uuid4().hex[:12]}",
    )
    session_id = f"persist-qa-{uuid4().hex}"
    event = SecurityEvent(
        event_type=EventType.REQUEST_ANALYZED,
        source=EventSource.ROUTING,
        session_id=session_id,
        organization_id=first_tenant.id,
        operation="restart-check",
    )

    try:
        with db.session() as control:
            control.add_all([first_tenant, second_tenant])
            control.flush()
            control.add(AttackSession(
                session_id=session_id,
                organization_id=first_tenant.id,
                attack_stage="reconnaissance",
                interaction_count=0,
                exposed_entities_json="{}",
                metadata_json="{}",
            ))
            control.commit()

        EventStore(persistent=True).add(event)
        report = IncidentReport(session_id=session_id, status=AnalysisStatus.PENDING)
        IncidentReportStore(persistent=True).save(report)

        restarted_events = EventStore(persistent=True)
        restarted_reports = IncidentReportStore(persistent=True)
        recovered_event = restarted_events.get_by_id(event.event_id, first_tenant.id)
        recovered_report = restarted_reports.get_by_session(session_id, first_tenant.id)

        assert recovered_event is not None
        assert recovered_event.event_id == event.event_id
        assert recovered_report is not None
        assert recovered_report.report_id == report.report_id
        assert restarted_events.get_by_id(event.event_id, second_tenant.id) is None
        assert restarted_reports.get_by_session(session_id, second_tenant.id) is None
    finally:
        # Scoped cleanup is limited to this test's random records; it is never
        # exposed as an application clear endpoint.
        with db.session() as control:
            control.execute(delete(SecurityEventRecord).where(SecurityEventRecord.event_id == event.event_id))
            control.execute(delete(IncidentReportRecord).where(IncidentReportRecord.session_id == session_id))
            control.execute(delete(AttackSession).where(AttackSession.session_id == session_id))
            control.execute(delete(Organization).where(Organization.id.in_([first_tenant.id, second_tenant.id])))
            control.commit()
