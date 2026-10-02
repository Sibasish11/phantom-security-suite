from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class AgentTelemetryEvent(BaseModel):
    event_id: UUID
    agent_id: UUID

    session_id: str | None = None

    event_type: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=100)

    original_target: str = Field(min_length=1, max_length=50)
    final_target: str = Field(min_length=1, max_length=50)

    risk_score: int = Field(ge=0, le=100)
    severity: str = Field(min_length=1, max_length=50)

    suspicious: bool

    attack_stage: str | None = Field(
        default=None,
        max_length=100,
    )

    interaction_count: int | None = Field(
        default=None,
        ge=0,
    )

    triggered_rules: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict = Field(default_factory=dict)


class AgentTelemetryBatch(BaseModel):
    events: list[AgentTelemetryEvent] = Field(
        min_length=1,
        max_length=100,
    )


class AgentTelemetryResponse(BaseModel):
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)