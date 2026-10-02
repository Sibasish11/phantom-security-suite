"""Durable, tenant-scoped incident reports and advisory analysis.

Only the explicit SanitizedSessionPayload whitelist crosses the AI boundary.
Neither report generation nor AI output influences gateway routing.
"""

from datetime import datetime, timezone
from threading import Lock
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select

from app.database import get_sync_control_db_manager
from app.honeypot.service import honeypot_session_manager
from app.incident_analysis.client import (
    BaseIncidentAnalysisClient,
    IncidentAnalysisError,
    IncidentAnalysisMalformedResponseError,
    IncidentAnalysisTimeoutError,
    client_factory,
)
from app.incident_analysis.schemas import (
    AnalysisStatus,
    IncidentAnalysisResponse,
    IncidentReport,
    IncidentReportDetailResponse,
    IncidentReportSummary,
    SanitizedSessionPayload,
    SanitizedTimelineStep,
)
from app.models.control_plane import AttackSession
from app.models.security_records import IncidentReportRecord
from app.security_context import current_context
from app.security_logging.service import event_store


class IncidentReportStore:
    """Injectable memory store; production uses ``persistent=True``.

    Persistent reads are always served from the database, not a process cache.
    Tenant reads join AttackSession in SQL, so legacy unowned sessions are
    invisible even if a report's denormalized ownership field is populated.
    """

    def __init__(self, *, persistent: bool = False, db_manager=None) -> None:
        self._persistent = persistent
        self._db_manager = db_manager
        self._reports: dict[str, IncidentReport] = {}
        self._ownership: dict[str, Optional[UUID]] = {}
        self._lock = Lock()

    def _manager(self):
        return self._db_manager or get_sync_control_db_manager()

    @staticmethod
    def _from_record(record: IncidentReportRecord) -> IncidentReport:
        return IncidentReport(
            report_id=record.report_id,
            session_id=record.session_id,
            created_at=record.created_at,
            status=record.status,
            sanitized_payload=(
                SanitizedSessionPayload.model_validate_json(record.sanitized_payload_json)
                if record.sanitized_payload_json else None
            ),
            analysis=(
                IncidentAnalysisResponse.model_validate_json(record.analysis_json)
                if record.analysis_json else None
            ),
            error=record.error,
        )

    @staticmethod
    def _query(organization_id: Optional[UUID] = None):
        query = select(IncidentReportRecord)
        if organization_id is not None:
            query = query.join(
                AttackSession,
                IncidentReportRecord.session_id == AttackSession.session_id,
            ).where(AttackSession.organization_id == organization_id)
        return query

    def save(self, report: IncidentReport,
             organization_id: Optional[UUID] = None) -> None:
        context = current_context()
        organization_id = organization_id or (context.organization_id if context else None)
        if not self._persistent:
            with self._lock:
                previous = self._reports.get(report.session_id)
                if previous:
                    report.report_id = previous.report_id
                    report.created_at = previous.created_at
                self._reports[report.session_id] = report.model_copy(deep=True)
                self._ownership[report.session_id] = organization_id
            return

        with self._manager().session() as db:
            # Serialize writers for a session, including the first candidate.
            owner = db.execute(
                select(AttackSession).where(
                    AttackSession.session_id == report.session_id,
                ).with_for_update()
            ).scalar_one_or_none()
            if owner is None:
                raise ValueError("Session not found")
            record = db.execute(
                self._query().where(IncidentReportRecord.session_id == report.session_id)
            ).scalar_one_or_none()
            if record is None:
                record = IncidentReportRecord(
                    report_id=report.report_id,
                    session_id=report.session_id,
                    created_at=report.created_at,
                )
                db.add(record)
            else:
                report.report_id = record.report_id
                report.created_at = record.created_at
            record.organization_id = owner.organization_id
            record.status = report.status.value
            record.sanitized_payload_json = (
                report.sanitized_payload.model_dump_json() if report.sanitized_payload else None
            )
            record.analysis_json = report.analysis.model_dump_json() if report.analysis else None
            record.error = report.error
            db.commit()

    def get_by_session(self, session_id: str,
                       organization_id: Optional[UUID] = None) -> Optional[IncidentReport]:
        if self._persistent:
            with self._manager().session() as db:
                record = db.execute(self._query(organization_id).where(
                    IncidentReportRecord.session_id == session_id,
                )).scalar_one_or_none()
                return self._from_record(record) if record else None
        if organization_id is not None:
            with self._lock:
                if self._ownership.get(session_id) != organization_id:
                    return None
        with self._lock:
            report = self._reports.get(session_id)
            return report.model_copy(deep=True) if report else None

    def get_by_report_id(self, report_id: UUID,
                         organization_id: Optional[UUID] = None) -> Optional[IncidentReport]:
        if self._persistent:
            with self._manager().session() as db:
                record = db.execute(self._query(organization_id).where(
                    IncidentReportRecord.report_id == report_id,
                )).scalar_one_or_none()
                return self._from_record(record) if record else None
        return next((report for report in self.list_all(organization_id)
                     if report.report_id == report_id), None)

    def list_all(self, organization_id: Optional[UUID] = None) -> list[IncidentReport]:
        if self._persistent:
            with self._manager().session() as db:
                records = db.execute(self._query(organization_id).order_by(
                    IncidentReportRecord.created_at.desc(), IncidentReportRecord.report_id,
                )).scalars()
                return [self._from_record(record) for record in records]
        with self._lock:
            return [report.model_copy(deep=True) for report in self._reports.values()
                    if organization_id is None or self._ownership.get(report.session_id) == organization_id]

    def delete(self, session_id: str, organization_id: Optional[UUID] = None) -> bool:
        if self._persistent:
            if organization_id is None:
                raise ValueError("Organization required for durable incident deletion")
            with self._manager().session() as db:
                report_ids = self._query(organization_id).with_only_columns(IncidentReportRecord.report_id)
                result = db.execute(delete(IncidentReportRecord).where(
                    IncidentReportRecord.report_id.in_(report_ids),
                    IncidentReportRecord.session_id == session_id,
                ))
                db.commit()
                return bool(result.rowcount)
        with self._lock:
            self._ownership.pop(session_id, None)
            return self._reports.pop(session_id, None) is not None

    def clear(self) -> None:
        """Clear an injected memory store, never delete durable history."""
        with self._lock:
            self._reports.clear()
            self._ownership.clear()

    def count(self, organization_id: Optional[UUID] = None) -> int:
        return len(self.list_all(organization_id))


class IncidentService:
    def __init__(self, store: Optional[IncidentReportStore] = None,
                 client: Optional[BaseIncidentAnalysisClient] = None) -> None:
        self._store = store if store is not None else IncidentReportStore(persistent=True)
        self._client = client if client is not None else client_factory()

    @staticmethod
    def _session_belongs_to_organization(session_id: str, organization_id: UUID) -> bool:
        with get_sync_control_db_manager().session() as db:
            return db.execute(select(AttackSession.id).where(
                AttackSession.session_id == session_id,
                AttackSession.organization_id == organization_id,
                AttackSession.organization_id.is_not(None),
            )).scalar_one_or_none() is not None

    async def analyze_session(self, session_id: str, force_reanalysis: bool = False,
                              organization_id: Optional[UUID] = None) -> IncidentReport:
        """Analyze a tenant-owned session; trusted internal callers may omit org."""
        context = current_context()
        organization_id = organization_id or (context.organization_id if context else None)
        session = honeypot_session_manager.get_session(session_id, organization_id=organization_id)
        if session is None:
            raise ValueError("Session not found")
        existing = self._store.get_by_session(session_id, organization_id)
        if existing and existing.status == AnalysisStatus.COMPLETED and not force_reanalysis:
            return existing

        report = existing or IncidentReport(session_id=session_id)
        report.status = AnalysisStatus.PENDING
        report.error = None
        report.analysis = None
        report.sanitized_payload = self._build_sanitized_payload(
            session, event_store.get_by_session(session_id, limit=1000, organization_id=organization_id),
        )
        self._store.save(report)
        try:
            analysis = await self._client.analyze(report.sanitized_payload)
            report.analysis = IncidentAnalysisResponse.model_validate(analysis)
            if report.analysis.session_id != session_id:
                raise IncidentAnalysisMalformedResponseError("Mismatched session")
            report.status = AnalysisStatus.COMPLETED
        except IncidentAnalysisTimeoutError:
            report.status = AnalysisStatus.FAILED
            report.error = "Analysis provider timed out"
        except IncidentAnalysisMalformedResponseError:
            report.status = AnalysisStatus.FAILED
            report.error = "Analysis provider returned an invalid response"
        except IncidentAnalysisError:
            report.status = AnalysisStatus.FAILED
            report.error = "Analysis provider unavailable"
        except Exception:  # Provider failures may contain credentials or payloads.
            report.status = AnalysisStatus.FAILED
            report.error = "Incident analysis failed"
        if report.status == AnalysisStatus.FAILED:
            report.analysis = None
        self._store.save(report)
        return report

    def get_report(
        self,
        session_id: str,
        organization_id: Optional[UUID] = None,
    ) -> Optional[IncidentReport]:
        return self._store.get_by_session(session_id, organization_id)

    def get_report_by_id(
        self,
        report_id: UUID,
        organization_id: Optional[UUID] = None,
    ) -> Optional[IncidentReport]:
        return self._store.get_by_report_id(report_id, organization_id)

    def list_reports(self, organization_id: UUID) -> list[IncidentReport]:
        return self._store.list_all(organization_id)

    def ensure_incident(self, session_id: str) -> IncidentReport:
        """Refresh pending facts on every interaction without invoking analysis."""
        context = current_context()
        organization_id = context.organization_id if context else None
        session = honeypot_session_manager.get_session(session_id, organization_id=organization_id)
        if session is None:
            raise ValueError("Session not found")
        report = self._store.get_by_session(session_id, organization_id) or IncidentReport(session_id=session_id)
        if (report.sanitized_payload is not None
                and report.sanitized_payload.total_interactions != session.interaction_count):
            # Do not show an old advisory report as analysis of new activity.
            report.status = AnalysisStatus.PENDING
            report.analysis = None
        if report.status == AnalysisStatus.PENDING:
            report.sanitized_payload = self._build_sanitized_payload(
                session, event_store.get_by_session(session_id, limit=1000, organization_id=organization_id),
            )
            self._store.save(report)
        return report

    @staticmethod
    def report_to_summary(report: IncidentReport) -> IncidentReportSummary:
        return IncidentReportSummary(
            report_id=str(report.report_id),
            session_id=report.session_id,
            created_at=report.created_at.isoformat(),
            status=report.status,
            final_attack_stage=report.sanitized_payload.final_attack_stage if report.sanitized_payload else None,
            likely_objective=report.analysis.likely_objective if report.analysis else None,
        )

    @staticmethod
    def report_to_detail(report: IncidentReport) -> IncidentReportDetailResponse:
        return IncidentReportDetailResponse(
            report_id=str(report.report_id),
            session_id=report.session_id,
            created_at=report.created_at.isoformat(),
            status=report.status,
            sanitized_payload=report.sanitized_payload,
            analysis=report.analysis,
            error=report.error,
        )

    @staticmethod
    def _build_sanitized_payload(session, correlated_events) -> SanitizedSessionPayload:
        """Whitelist telemetry: never raw parameters, results, headers or PII."""
        from app.incident_analysis.config import ai_settings

        interactions = session.interactions[-ai_settings.ai_max_timeline_steps:]
        duration = None
        if session.created_at and session.last_active_at:
            duration = (session.last_active_at - session.created_at).total_seconds()
        from app.detection.engine import detection_engine
        def safe_operation(operation):
            return operation if operation in detection_engine._valid_operations else 'unsupported_operation'
        operations = list(dict.fromkeys(safe_operation(interaction.operation) for interaction in session.interactions))
        rule_names = list(dict.fromkeys(
            name for event in correlated_events for rule in event.triggered_rules
            if isinstance(name := rule.get("rule") or rule.get("name") or rule.get("rule_id"), str)
        ))
        scores = [interaction.risk_score for interaction in session.interactions]
        exposed_counts = {
            "customers": len(session.exposed_entities.customer_ids),
            "orders": len(session.exposed_entities.order_ids),
            "users": len(session.exposed_entities.user_ids),
            **session.exposed_entities.external_entity_counts,
        }
        timeline = []
        for interaction in interactions:
            step_rules = list(dict.fromkeys(
                name for event in correlated_events if event.operation == interaction.operation
                for rule in event.triggered_rules
                if isinstance(name := rule.get("rule") or rule.get("name") or rule.get("rule_id"), str)
            ))
            timeline.append(SanitizedTimelineStep(
                step=interaction.step,
                timestamp_utc=(interaction.timestamp or datetime.now(timezone.utc)).isoformat(),
                operation=safe_operation(interaction.operation),
                risk_score=interaction.risk_score,
                attack_stage=interaction.attack_stage.value,
                triggered_rule_names=step_rules,
                entities_exposed_counts={
                    key: len(values) if isinstance(values, list) else values
                    for key, values in interaction.entities_exposed.items()
                    if isinstance(values, (list, int))
                },
                success=interaction.success,
            ))
        return SanitizedSessionPayload(
            session_id=session.session_id,
            session_duration_seconds=duration,
            final_attack_stage=session.attack_stage.value,
            total_interactions=session.interaction_count,
            unique_operations=operations,
            triggered_rule_names=rule_names,
            max_risk_score=max(scores, default=0),
            avg_risk_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
            exposed_entity_counts=exposed_counts,
            timeline=timeline,
            correlated_event_count=len(correlated_events),
        )


incident_report_store = IncidentReportStore(persistent=True)
incident_service = IncidentService(store=incident_report_store)
