from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AttackStage(str, Enum):
    RECONNAISSANCE = "reconnaissance"
    ENUMERATION = "enumeration"
    EXPLORATION = "exploration"
    EXFILTRATION = "exfiltration"
    CREDENTIAL_ACCESS = "credential_access"


class ExposedEntityTracker(BaseModel):
    customer_ids: list[int] = Field(default_factory=list)
    customer_emails: list[str] = Field(default_factory=list)
    order_ids: list[int] = Field(default_factory=list)
    order_numbers: list[str] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)
    # Counts from external integrations are intentionally stored without
    # identifiers. This lets the SOC show "12 accounts exposed" without
    # importing bank/customer records into PhantomLayer.
    external_entity_counts: dict[str, int] = Field(default_factory=dict)

    def add_external_counts(self, counts: dict[str, int]) -> None:
        for entity_type, count in counts.items():
            if isinstance(entity_type, str) and isinstance(count, int) and count > 0:
                self.external_entity_counts[entity_type] = (
                    self.external_entity_counts.get(entity_type, 0) + count
                )

    def add_customer(self, customer_id: Optional[int] = None, email: Optional[str] = None) -> None:
        if customer_id is not None and customer_id not in self.customer_ids:
            self.customer_ids.append(customer_id)
        if email and email not in self.customer_emails:
            self.customer_emails.append(email)

    def add_order(self, order_id: Optional[int] = None, order_number: Optional[str] = None) -> None:
        if order_id is not None and order_id not in self.order_ids:
            self.order_ids.append(order_id)
        if order_number and order_number not in self.order_numbers:
            self.order_numbers.append(order_number)

    def add_user(self, user_id: Optional[int] = None, username: Optional[str] = None) -> None:
        if user_id is not None and user_id not in self.user_ids:
            self.user_ids.append(user_id)
        if username and username not in self.usernames:
            self.usernames.append(username)

    def has_customer(self, id_or_email: Any) -> bool:
        if isinstance(id_or_email, int):
            return id_or_email in self.customer_ids
        return str(id_or_email) in self.customer_emails

    def has_order(self, id_or_number: Any) -> bool:
        if isinstance(id_or_number, int):
            return id_or_number in self.order_ids
        return str(id_or_number) in self.order_numbers

    def has_user(self, id_or_username: Any) -> bool:
        if isinstance(id_or_username, int):
            return id_or_username in self.user_ids
        return str(id_or_username) in self.usernames


class HoneypotInteractionRecord(BaseModel):
    step: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    operation: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_score: int = 0
    attack_stage: AttackStage = AttackStage.RECONNAISSANCE
    entities_exposed: dict[str, list[Any] | int] = Field(default_factory=dict)
    success: bool = True
    details: Optional[str] = None


class AttackerSession(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    attack_stage: AttackStage = AttackStage.RECONNAISSANCE
    interaction_count: int = 0
    interactions: list[HoneypotInteractionRecord] = Field(default_factory=list)
    exposed_entities: ExposedEntityTracker = Field(default_factory=ExposedEntityTracker)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionSummaryResponse(BaseModel):
    session_id: str
    created_at: str
    last_active_at: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    attack_stage: AttackStage
    interaction_count: int
    exposed_entities_count: dict[str, int]


class SessionDetailResponse(BaseModel):
    session_id: str
    created_at: str
    last_active_at: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    attack_stage: AttackStage
    interaction_count: int
    interactions: list[HoneypotInteractionRecord]
    exposed_entities: ExposedEntityTracker
    metadata: dict[str, Any]


class SessionListResponse(BaseModel):
    sessions: list[SessionSummaryResponse]
    total: int


class HoneypotHealthResponse(BaseModel):
    service: str
    status: str
    active_sessions: int
    attack_stages_supported: list[str]
