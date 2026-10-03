from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(str, Enum):
    PENDING = "pending"
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class AgentRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._-]*$",
    )
    domain_id: UUID | None = None
    version: str = Field(
        min_length=1,
        max_length=50,
    )
    capabilities: list[str] = Field(
        default_factory=list,
        max_length=20,
    )


class AgentRegistrationResponse(BaseModel):
    agent_id: UUID
    name: str
    status: AgentStatus
    registration_token: str = Field(
        description=(
            "Store in the customer secret manager; "
            "shown only on registration"
        ),
    )


class AgentHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    integration_ready: bool = False
    status: AgentStatus
    real_db_reachable: bool
    honeypot_db_reachable: bool
    telemetry_events_sent: int = Field(
        default=0,
        ge=0,
    )


class AgentResponse(BaseModel):
    agent_id: UUID
    name: str
    domain_id: UUID | None = None
    version: str
    capabilities: list[str]
    status: AgentStatus
    registered_at: datetime
    last_heartbeat_at: datetime | None = None
    real_db_reachable: bool | None = None
    honeypot_db_reachable: bool | None = None
    telemetry_events_sent: int = 0
    integration_ready: bool = False


class AgentTokenRotationResponse(BaseModel):
    agent_id: UUID
    name: str
    status: AgentStatus
    registration_token: str = Field(
        description=(
            "Store in the customer secret manager; "
            "shown only after token rotation"
        ),
    )
