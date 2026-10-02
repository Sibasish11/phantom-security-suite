from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    event_id: str
    agent_id: str
    session_id: str | None = None

    event_type: str

    operation: str
    original_target: str
    final_target: str

    risk_score: int = Field(
        ge=0,
        le=100,
    )

    severity: str
    suspicious: bool

    attack_stage: str | None = None
    interaction_count: int | None = None

    triggered_rules: list[str] = Field(
        default_factory=list,
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(
        min_length=1,
        max_length=100,
    )


class TelemetryResponse(BaseModel):
    accepted: int
    rejected: int