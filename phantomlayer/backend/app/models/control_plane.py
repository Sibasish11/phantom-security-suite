from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    text,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import ControlBase


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrganizationRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"


class AgentStatus(str, Enum):
    PENDING = "pending"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class ProtectionLayer(str, Enum):
    API = "api"
    DATABASE = "database"
    INTERNAL = "internal"
    FULL = "full"


class ProtectionStatus(str, Enum):
    CONFIGURING = "configuring"
    ACTIVE = "active"
    PAUSED = "paused"


class Organization(ControlBase):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[OrganizationStatus] = mapped_column(
        SQLEnum(OrganizationStatus),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users: Mapped[list["OrganizationUser"]] = relationship(
        "OrganizationUser",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    domains: Mapped[list["Domain"]] = relationship(
        "Domain",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    agents: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    protections: Mapped[list["ProtectionConfiguration"]] = relationship(
        "ProtectionConfiguration",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationUser(ControlBase):
    __tablename__ = "organization_users"
    __table_args__ = (Index("uq_organization_users_email_normalized", text("lower(email)"), unique=True),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    role: Mapped[OrganizationRole] = mapped_column(
        SQLEnum(OrganizationRole),
        nullable=False,
        default=OrganizationRole.ANALYST,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users",
    )


class Domain(ControlBase):
    __tablename__ = "domains"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    verification_record_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    verification_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="domains",
    )

    protections: Mapped[list["ProtectionConfiguration"]] = relationship(
        "ProtectionConfiguration",
        back_populates="domain",
        cascade="all, delete-orphan",
    )


class ProtectionConfiguration(ControlBase):
    __tablename__ = "protection_configurations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    layer: Mapped[ProtectionLayer] = mapped_column(
        SQLEnum(ProtectionLayer),
        nullable=False,
    )

    status: Mapped[ProtectionStatus] = mapped_column(
        SQLEnum(ProtectionStatus),
        nullable=False,
        default=ProtectionStatus.CONFIGURING,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    configuration_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="protections",
    )

    domain: Mapped["Domain"] = relationship(
        "Domain",
        back_populates="protections",
    )


class Agent(ControlBase):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    capabilities: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[AgentStatus] = mapped_column(
        SQLEnum(AgentStatus),
        nullable=False,
        default=AgentStatus.PENDING,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    real_db_reachable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    honeypot_db_reachable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    telemetry_events_sent: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="agents",
    )

    domain: Mapped["Domain"] = relationship(
        "Domain",
        foreign_keys=[domain_id],
    )


class AttackSession(ControlBase):
    __tablename__ = "attack_sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    session_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    domain_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    client_ip: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attack_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="reconnaissance",
    )

    interaction_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    exposed_entities_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    metadata_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Intentionally untyped to avoid the Python 3.14 / SQLAlchemy
    # forward-reference typing bug in declarative relationship scanning.
    interactions = relationship(
        "AttackSessionInteraction",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AttackSessionInteraction.step",
    )


class AttackSessionInteraction(ControlBase):
    __tablename__ = "attack_session_interactions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        unique=True,
        index=True,
    )

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "attack_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    step: Mapped[int] = mapped_column(
        nullable=False,
    )

    operation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parameters_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    risk_score: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    attack_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    entities_exposed_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Intentionally untyped for the same Python 3.14 / SQLAlchemy
    # declarative typing compatibility reason.
    session = relationship(
        "AttackSession",
        back_populates="interactions",
    )