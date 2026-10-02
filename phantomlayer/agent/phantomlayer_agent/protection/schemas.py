from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProtectionTarget(str, Enum):
    REAL = "real"
    HONEYPOT = "honeypot"


class ProtectionOperation(str, Enum):
    HEALTH_CHECK = "health_check"
    LIST_TABLES = "list_tables"
    GET_USERS = "get_users"
    GET_CUSTOMERS = "get_customers"
    GET_PRODUCTS = "get_products"
    GET_ORDERS = "get_orders"
    GET_CUSTOMER = "get_customer"
    GET_ORDER = "get_order"
    GET_USER = "get_user"


class ProtectionRequest(BaseModel):
    operation: str
    parameters: dict[str, Any] = Field(
        default_factory=dict
    )
    session_id: str | None = None


class TriggeredRule(BaseModel):
    rule: str
    score: int
    reason: str


class ProtectionResponse(BaseModel):
    original_target: ProtectionTarget
    final_target: ProtectionTarget
    operation: str
    risk_score: int = Field(
        ge=0,
        le=100,
    )
    severity: str
    suspicious: bool
    triggered_rules: list[TriggeredRule]
    routing_reason: str
    success: bool
    data: Any = None
    error: str | None = None
    session_id: str | None = None
    attack_stage: str | None = None
    interaction_count: int | None = None


class ProtectionHealthResponse(BaseModel):
    service: str
    status: str
    real_database: str
    honeypot_database: str