"""Security event creation and control-plane persistence.

The default ``EventStore`` remains an injectable in-memory store for focused
unit tests.  The process-wide store used by the API is durable and scopes every
read by organization.  Ownership comes from trusted gateway context when
available, with an AttackSession lookup as a compatibility fallback.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_sync_control_db_manager
from app.models.control_plane import AttackSession
from app.models.security_records import SecurityEventRecord
from app.security_logging.schemas import EventSource, EventType, SecurityEvent


def _trusted_context():
    """Read the parent gateway's trusted context without importing it eagerly."""

    try:
        from app.security_context import current_context
    except (ImportError, ModuleNotFoundError):
        return None

    try:
        return current_context()
    except (LookupError, RuntimeError):
        return None


def _context_value(context: Any, name: str) -> Any:
    return getattr(context, name, None) if context is not None else None


def _json_dumps(value: Any, default: Any) -> str:
    try:
        return json.dumps(value if value is not None else default, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps(default, separators=(",", ":"))


def _json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default
    return parsed


class EventStore:
    """Store security events in memory and, optionally, the control database.

    ``persistent=False`` is deliberately the default so unit tests can inject a
    deterministic store without a database.  The module singleton below uses
    ``persistent=True``.  ``clear`` only clears the local test/cache copy; it
    never issues an unscoped database delete.
    """

    def __init__(self, *, persistent: bool = False, db_manager=None):
        self._events: list[SecurityEvent] = []
        self._lock = Lock()
        self._persistent = persistent
        self._db_manager = db_manager

    @property
    def persistent(self) -> bool:
        return self._persistent

    def _manager(self):
        return self._db_manager or get_sync_control_db_manager()

    @staticmethod
    def _ownership_from_context(event: SecurityEvent) -> None:
        context = _trusted_context()
        if context is None:
            return

        if event.organization_id is None:
            event.organization_id = _context_value(context, "organization_id")
        if event.domain_id is None:
            event.domain_id = _context_value(context, "domain_id")
        if event.agent_id is None:
            event.agent_id = _context_value(context, "agent_id")

    @staticmethod
    def _ownership_from_session(event: SecurityEvent) -> None:
        """Backfill ownership only when a session already has trusted ownership."""

        if event.organization_id is not None or not event.session_id:
            return

        try:
            db = get_sync_control_db_manager()
            with db.session() as session:
                row = session.execute(
                    select(
                        AttackSession.organization_id,
                        AttackSession.domain_id,
                    ).where(AttackSession.session_id == event.session_id)
                ).one_or_none()
                if row is not None:
                    event.organization_id = row.organization_id
                    if event.domain_id is None:
                        event.domain_id = row.domain_id
        except SQLAlchemyError:
            # Logging must not break request routing if control-plane storage is
            # temporarily unavailable.  The event remains an unowned legacy
            # object and therefore cannot be exposed by tenant APIs.
            return

    def _resolve_ownership(self, event: SecurityEvent) -> None:
        self._ownership_from_context(event)
        self._ownership_from_session(event)

    @staticmethod
    def _to_record(event: SecurityEvent) -> SecurityEventRecord:
        return SecurityEventRecord(
            event_id=event.event_id,
            organization_id=event.organization_id,
            domain_id=event.domain_id,
            agent_id=event.agent_id,
            session_id=event.session_id,
            timestamp=event.timestamp,
            event_type=event.event_type.value,
            source=event.source.value,
            original_target=event.original_target,
            final_target=event.final_target,
            operation=event.operation,
            risk_score=event.risk_score,
            severity=event.severity,
            confidence=event.confidence,
            confidence_level=event.confidence_level,
            suspicious=event.suspicious,
            triggered_rules_json=_json_dumps(event.triggered_rules, []),
            reasons_json=_json_dumps(event.reasons, []),
            routing_decision=event.routing_decision,
            routing_reason=event.routing_reason,
            gateway_success=event.gateway_success,
            metadata_json=_json_dumps(event.metadata, {}),
        )

    @staticmethod
    def _from_record(record: SecurityEventRecord) -> SecurityEvent:
        return SecurityEvent(
            event_id=record.event_id,
            session_id=record.session_id,
            organization_id=record.organization_id,
            domain_id=record.domain_id,
            agent_id=record.agent_id,
            timestamp=record.timestamp,
            event_type=EventType(record.event_type),
            source=EventSource(record.source),
            original_target=record.original_target,
            final_target=record.final_target,
            operation=record.operation,
            risk_score=record.risk_score,
            severity=record.severity,
            confidence=record.confidence,
            confidence_level=record.confidence_level,
            suspicious=record.suspicious,
            triggered_rules=_json_loads(record.triggered_rules_json, []),
            reasons=_json_loads(record.reasons_json, []),
            routing_decision=record.routing_decision,
            routing_reason=record.routing_reason,
            gateway_success=record.gateway_success,
            metadata=_json_loads(record.metadata_json, {}),
        )

    def _persist(self, event: SecurityEvent) -> None:
        if not self._persistent:
            return

        try:
            db = self._manager()
            with db.session() as session:
                existing = session.get(SecurityEventRecord, event.event_id)
                if existing is None:
                    record = self._to_record(event)
                    # A benign request may have a client correlation handle
                    # without an attack session. Keep ownership from trusted
                    # context, not an invalid attack-session foreign key.
                    if record.session_id and session.execute(select(AttackSession.id).where(
                        AttackSession.session_id == record.session_id,
                    )).scalar_one_or_none() is None:
                        record.metadata_json = _json_dumps({**event.metadata, "correlation_id": record.session_id}, {})
                        record.session_id = None
                    session.add(record)
                    session.commit()
        except SQLAlchemyError as exc:
            raise RuntimeError("Control-plane security event persistence failed") from exc

    def add(self, event: SecurityEvent) -> None:
        self._resolve_ownership(event)
        if self._persistent:
            self._persist(event)
        else:
            with self._lock:
                self._events.append(event)

    def _memory_owned(self, event: SecurityEvent, organization_id: Optional[UUID]) -> bool:
        if organization_id is None:
            return True
        if event.organization_id == organization_id:
            return True
        if event.organization_id is not None or not event.session_id:
            return False

        # Legacy in-memory event: use the same session fallback as SQL reads.
        try:
            db = get_sync_control_db_manager()
            with db.session() as session:
                owner = session.execute(
                    select(AttackSession.organization_id).where(
                        AttackSession.session_id == event.session_id
                    )
                ).scalar_one_or_none()
                return owner == organization_id
        except SQLAlchemyError:
            return False

    def _owned_clause(self, organization_id: UUID):
        return or_(
            SecurityEventRecord.organization_id == organization_id,
            and_(
                SecurityEventRecord.organization_id.is_(None),
                AttackSession.organization_id == organization_id,
            ),
        )

    def _query_records(self, *, organization_id: Optional[UUID] = None, limit: Optional[int] = None,
                       event_type: Optional[EventType] = None,
                       source: Optional[EventSource] = None,
                       session_id: Optional[str] = None,
                       event_id: Optional[UUID] = None) -> Optional[list[SecurityEvent]]:
        if not self._persistent:
            return None

        try:
            db = self._manager()
            with db.session() as session:
                query = select(SecurityEventRecord)
                if organization_id is not None:
                    query = query.outerjoin(
                        AttackSession,
                        SecurityEventRecord.session_id == AttackSession.session_id,
                    ).where(self._owned_clause(organization_id))
                if event_type is not None:
                    query = query.where(SecurityEventRecord.event_type == event_type.value)
                if source is not None:
                    query = query.where(SecurityEventRecord.source == source.value)
                if session_id is not None:
                    query = query.where(SecurityEventRecord.session_id == session_id)
                if event_id is not None:
                    query = query.where(SecurityEventRecord.event_id == event_id)
                query = query.order_by(SecurityEventRecord.timestamp.desc())
                if limit is not None:
                    query = query.limit(limit)
                records = session.execute(query).scalars().all()
                return [self._from_record(record) for record in records]
        except (SQLAlchemyError, ValueError) as exc:
            raise RuntimeError("Control-plane security event query failed") from exc

    def get_by_id(self, event_id: UUID, organization_id: Optional[UUID] = None) -> Optional[SecurityEvent]:
        records = self._query_records(organization_id=organization_id, event_id=event_id, limit=1)
        if records is not None:
            for event in records:
                if event.event_id == event_id:
                    return event
            return None

        with self._lock:
            for event in self._events:
                if event.event_id == event_id and self._memory_owned(event, organization_id):
                    return event
        return None

    def get_recent(self, limit: int = 100, organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        records = self._query_records(organization_id=organization_id, limit=limit)
        if records is not None:
            return records

        with self._lock:
            return [
                event
                for event in reversed(self._events)
                if self._memory_owned(event, organization_id)
            ][:limit]

    def get_all(self, organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        records = self._query_records(organization_id=organization_id)
        if records is not None:
            return records

        with self._lock:
            return [event for event in self._events if self._memory_owned(event, organization_id)]

    def count(self, organization_id: Optional[UUID] = None) -> int:
        if self._persistent:
            try:
                db = self._manager()
                with db.session() as session:
                    query = select(func.count(SecurityEventRecord.event_id))
                    if organization_id is not None:
                        query = query.select_from(SecurityEventRecord).outerjoin(
                            AttackSession,
                            SecurityEventRecord.session_id == AttackSession.session_id,
                        ).where(self._owned_clause(organization_id))
                    return int(session.execute(query).scalar_one())
            except SQLAlchemyError as exc:
                raise RuntimeError("Control-plane security event count failed") from exc

        with self._lock:
            return sum(self._memory_owned(event, organization_id) for event in self._events)

    def get_by_type(self, event_type: EventType, limit: int = 100,
                    organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        records = self._query_records(
            organization_id=organization_id,
            limit=limit,
            event_type=event_type,
        )
        if records is not None:
            return records

        with self._lock:
            filtered = [
                event for event in self._events
                if event.event_type == event_type and self._memory_owned(event, organization_id)
            ]
            return list(reversed(filtered[-limit:]))

    def get_by_source(self, source: EventSource, limit: int = 100,
                      organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        records = self._query_records(
            organization_id=organization_id,
            limit=limit,
            source=source,
        )
        if records is not None:
            return records

        with self._lock:
            filtered = [
                event for event in self._events
                if event.source == source and self._memory_owned(event, organization_id)
            ]
            return list(reversed(filtered[-limit:]))

    def get_by_session(self, session_id: str, limit: int = 100,
                       organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        records = self._query_records(
            organization_id=organization_id,
            limit=limit,
            session_id=session_id,
        )
        if records is not None:
            return records

        with self._lock:
            filtered = [
                event for event in self._events
                if event.session_id == session_id and self._memory_owned(event, organization_id)
            ]
            return list(reversed(filtered[-limit:]))

    def clear(self) -> None:
        """Clear only the injectable memory/cache; never globally delete tenants."""

        with self._lock:
            self._events.clear()

class SecurityEventLogger:
    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or EventStore()

    @property
    def store(self) -> EventStore:
        return self._store

    def log_event(
        self,
        event_type: EventType,
        source: EventSource,
        session_id: Optional[str] = None,
        original_target: Optional[str] = None,
        final_target: Optional[str] = None,
        operation: Optional[str] = None,
        risk_score: Optional[int] = None,
        severity: Optional[str] = None,
        confidence: Optional[float] = None,
        confidence_level: Optional[str] = None,
        suspicious: Optional[bool] = None,
        triggered_rules: Optional[list[dict[str, Any]]] = None,
        reasons: Optional[list[str]] = None,
        routing_decision: Optional[str] = None,
        routing_reason: Optional[str] = None,
        gateway_success: Optional[bool] = None,
        metadata: Optional[dict[str, Any]] = None,
        organization_id: Optional[UUID] = None,
        domain_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_type=event_type,
            source=source,
            session_id=session_id,
            organization_id=organization_id,
            domain_id=domain_id,
            agent_id=agent_id,
            original_target=original_target,
            final_target=final_target,
            operation=operation,
            risk_score=risk_score,
            severity=severity,
            confidence=confidence,
            confidence_level=confidence_level,
            suspicious=suspicious,
            triggered_rules=triggered_rules or [],
            reasons=reasons or [],
            routing_decision=routing_decision,
            routing_reason=routing_reason,
            gateway_success=gateway_success,
            metadata=metadata or {},
        )
        self._store.add(event)
        return event

    def log_request_analyzed(
        self,
        original_target: str,
        operation: str,
        risk_score: int,
        severity: str,
        confidence: float,
        confidence_level: str,
        suspicious: bool,
        triggered_rules: list[dict[str, Any]],
        reasons: list[str],
        routing_decision: str,
        routing_reason: str,
        session_id: Optional[str] = None,
    ) -> SecurityEvent:
        return self.log_event(
            event_type=EventType.REQUEST_ANALYZED,
            source=EventSource.ROUTING,
            session_id=session_id,
            original_target=original_target,
            operation=operation,
            risk_score=risk_score,
            severity=severity,
            confidence=confidence,
            confidence_level=confidence_level,
            suspicious=suspicious,
            triggered_rules=triggered_rules,
            reasons=reasons,
            routing_decision=routing_decision,
            routing_reason=routing_reason,
            metadata={"stage": "analysis_complete"},
        )

    def log_suspicious_request(
        self,
        original_target: str,
        final_target: str,
        operation: str,
        risk_score: int,
        severity: str,
        confidence: float,
        confidence_level: str,
        triggered_rules: list[dict[str, Any]],
        reasons: list[str],
        session_id: Optional[str] = None,
    ) -> SecurityEvent:
        return self.log_event(
            event_type=EventType.SUSPICIOUS_REQUEST,
            source=EventSource.DETECTION,
            session_id=session_id,
            original_target=original_target,
            final_target=final_target,
            operation=operation,
            risk_score=risk_score,
            severity=severity,
            confidence=confidence,
            confidence_level=confidence_level,
            suspicious=True,
            triggered_rules=triggered_rules,
            reasons=reasons,
            metadata={"detection_triggered": True},
        )

    def log_routing_decision(
        self,
        original_target: str,
        final_target: str,
        operation: str,
        risk_score: int,
        routing_decision: str,
        routing_reason: str,
        session_id: Optional[str] = None,
    ) -> SecurityEvent:
        return self.log_event(
            event_type=EventType.ROUTING_DECISION,
            source=EventSource.ROUTING,
            session_id=session_id,
            original_target=original_target,
            final_target=final_target,
            operation=operation,
            risk_score=risk_score,
            routing_decision=routing_decision,
            routing_reason=routing_reason,
            metadata={"decision_made": True},
        )

    def log_honeypot_interaction(
        self,
        original_target: str,
        final_target: str,
        operation: str,
        result_count: int,
        session_id: Optional[str] = None,
        attack_stage: Optional[str] = None,
    ) -> SecurityEvent:
        metadata: dict[str, Any] = {
            "interaction_type": "query_executed",
            "result_count": result_count,
            "target_database": final_target,
        }
        if attack_stage:
            metadata["attack_stage"] = attack_stage

        return self.log_event(
            event_type=EventType.HONEYPOT_INTERACTION,
            source=EventSource.HONEYPOT,
            session_id=session_id,
            original_target=original_target,
            final_target=final_target,
            operation=operation,
            gateway_success=True,
            metadata=metadata,
        )

    def log_gateway_failure(
        self,
        original_target: str,
        operation: str,
        error: str,
        risk_score: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> SecurityEvent:
        return self.log_event(
            event_type=EventType.GATEWAY_FAILURE,
            source=EventSource.GATEWAY,
            session_id=session_id,
            original_target=original_target,
            operation=operation,
            risk_score=risk_score,
            gateway_success=False,
            metadata={"error": error, "failure_type": "operation_error"},
        )

    def get_event(self, event_id: UUID, organization_id: Optional[UUID] = None) -> Optional[SecurityEvent]:
        return self._store.get_by_id(event_id, organization_id=organization_id)

    def get_recent_events(self, limit: int = 100, organization_id: Optional[UUID] = None) -> list[SecurityEvent]:
        return self._store.get_recent(limit, organization_id=organization_id)

    def clear_events(self) -> None:
        self._store.clear()


# API telemetry is durable.  Focused tests should inject EventStore() instead
# of mutating this process-wide store.
event_store = EventStore(persistent=True)
security_event_logger = SecurityEventLogger(event_store)
