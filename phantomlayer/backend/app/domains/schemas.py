from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DomainCreateRequest(BaseModel):
    domain: str = Field(
        min_length=3,
        max_length=253,
    )


class DomainResponse(BaseModel):
    local_verification_available: bool = False
    id: UUID
    domain: str
    verification_record_name: str
    verification_token: str
    token_expires_at: datetime
    verified: bool
    verified_at: datetime | None = None


class DomainVerificationResponse(BaseModel):
    id: UUID
    domain: str
    verified: bool
    verified_at: datetime | None = None
    detail: str
