"""Control-plane persistence models for security telemetry and incidents.

These records intentionally live in the control database.  The JSON columns hold
already-sanitized telemetry / analysis documents; raw gateway responses and
request bodies are never persisted here.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import ControlBase


class SecurityEventRecord(ControlBase):
    """Durable security event with optional trusted tenant ownership.

    ``organization_id`` is nullable for legacy events written before trusted
    context existed.  Read paths must not expose such rows.  ``session_id`` is
    also nullable because health/system events do not necessarily have an
    attack session; when present it provides the ownership fallback through
    ``AttackSession.organization_id``.
    """

    __tablename__ = "security_events"

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    domain_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    agent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    session_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("attack_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    original_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suspicious: Mapped[bool | None] = mapped_column(nullable=True)
    triggered_rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    routing_decision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    gateway_success: Mapped[bool | None] = mapped_column(nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class IncidentReportRecord(ControlBase):
    """Durable advisory incident report keyed one-to-one with a session."""

    __tablename__ = "incident_reports"

    report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Kept as a denormalized ownership hint for writes made with trusted
    # context.  Reads still join AttackSession and require its tenant owner.
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("attack_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sanitized_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
