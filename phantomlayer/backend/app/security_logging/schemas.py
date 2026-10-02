from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    REQUEST_ANALYZED = "request_analyzed"
    SUSPICIOUS_REQUEST = "suspicious_request"
    ROUTING_DECISION = "routing_decision"
    HONEYPOT_INTERACTION = "honeypot_interaction"
    GATEWAY_FAILURE = "gateway_failure"


class EventSource(str, Enum):
    DETECTION = "detection"
    RISK = "risk"
    ROUTING = "routing"
    GATEWAY = "gateway"
    HONEYPOT = "honeypot"


class SecurityEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    session_id: Optional[str] = None
    # Ownership is internal telemetry metadata.  API response models below do
    # not expose these identifiers; every read is scoped server-side instead.
    organization_id: Optional[UUID] = None
    domain_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: EventType
    source: EventSource
    original_target: Optional[str] = None
    final_target: Optional[str] = None
    operation: Optional[str] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    severity: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_level: Optional[str] = None
    suspicious: Optional[bool] = None
    triggered_rules: list[dict[str, Any]] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    routing_decision: Optional[str] = None
    routing_reason: Optional[str] = None
    gateway_success: Optional[bool] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SecurityEventResponse(BaseModel):
    event_id: str
    session_id: Optional[str] = None
    timestamp: str
    event_type: str
    source: str
    original_target: Optional[str] = None
    final_target: Optional[str] = None
    operation: Optional[str] = None
    risk_score: Optional[int] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    suspicious: Optional[bool] = None
    triggered_rules: list[dict[str, Any]] = []
    reasons: list[str] = []
    routing_decision: Optional[str] = None
    routing_reason: Optional[str] = None
    gateway_success: Optional[bool] = None
    metadata: dict[str, Any] = {}



class LoggingHealthResponse(BaseModel):
    service: str
    status: str
    events_stored: int
    event_types_supported: list[str]


class EventsListResponse(BaseModel):
    events: list[SecurityEventResponse]
    total: int
    limit: int