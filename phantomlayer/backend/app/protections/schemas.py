from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.control_plane import ProtectionLayer, ProtectionStatus


class ProtectionCreateRequest(BaseModel):
    domain_id: UUID
    layer: ProtectionLayer
    configuration: dict = Field(default_factory=dict)


class ProtectionUpdateRequest(BaseModel):
    layer: ProtectionLayer | None = None
    enabled: bool | None = None
    status: ProtectionStatus | None = None
    configuration: dict | None = None


class ProtectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    domain_id: UUID
    layer: ProtectionLayer
    status: ProtectionStatus
    enabled: bool
    configuration: dict
    created_at: datetime
    updated_at: datetime