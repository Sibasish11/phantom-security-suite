from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.control_plane import ProtectionLayer


class ProtectionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain_id: UUID
    layer: ProtectionLayer
    configuration: dict = Field(default_factory=dict)


class ProtectionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layer: ProtectionLayer | None = None
    enabled: bool | None = None
    configuration: dict | None = None


class ProtectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    domain_id: UUID
    layer: ProtectionLayer
    status: Literal["configuring", "connecting", "active", "paused", "degraded"]
    readiness_blockers: list[str] = Field(default_factory=list)
    enabled: bool
    configuration: dict
    created_at: datetime
    updated_at: datetime
