from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class GatewayTarget(str, Enum):
    REAL = "real"
    HONEYPOT = "honeypot"


class GatewayOperation(str, Enum):
    HEALTH_CHECK = "health_check"
    LIST_TABLES = "list_tables"
    GET_USERS = "get_users"
    GET_CUSTOMERS = "get_customers"
    GET_PRODUCTS = "get_products"
    GET_ORDERS = "get_orders"
    GET_CUSTOMER = "get_customer"
    GET_ORDER = "get_order"
    GET_USER = "get_user"


class GatewayRequest(BaseModel):
    target: GatewayTarget = Field(
        ...,
        description="Original requested database target: real or honeypot",
    )
    operation: GatewayOperation = Field(
        ...,
        description="Operation to execute",
    )
    parameters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for the operation",
    )
    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional attacker session ID. Reuse this ID to correlate requests into one attack session.",
    )


class GatewayResponse(BaseModel):
    target: GatewayTarget
    operation: GatewayOperation
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    row_count: Optional[int] = None


class GatewayHealthResponse(BaseModel):
    gateway: str
    status: str
    real_database: str
    honeypot_database: str