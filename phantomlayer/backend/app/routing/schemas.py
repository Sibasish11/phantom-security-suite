from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.detection.schemas import DetectionRule, RecommendedTarget, Severity
from app.gateway.schemas import GatewayOperation, GatewayTarget
from app.risk.schemas import ConfidenceLevel


from typing import Any, Optional, Union


class RoutingDecision(str, Enum):
    ROUTED_TO_REAL = "routed_to_real"
    ROUTED_TO_HONEYPOT = "routed_to_honeypot"
    ORIGINAL_TARGET_PRESERVED = "original_target_preserved"


class RoutingRequest(BaseModel):
    target: str = Field(..., description="Original target database: real or honeypot")
    operation: str = Field(..., min_length=1, max_length=100, pattern=r'^[A-Za-z][A-Za-z0-9_]*$', description="Operation to execute")
    parameters: Optional[dict[str, Any]] = Field(default=None, description="Optional parameters")
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=128, description="Optional attacker session ID")


class RoutingResponse(BaseModel):
    original_target: GatewayTarget
    final_target: GatewayTarget
    operation: Union[GatewayOperation, str]
    risk_score: int = Field(..., ge=0, le=100)
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    suspicious: bool
    triggered_rules: list[dict[str, Any]]
    reasons: list[str]
    routing_decision: RoutingDecision
    routing_reason: str
    gateway_result: Optional[Any] = None
    gateway_success: bool = True
    gateway_error: Optional[str] = None
    session_id: Optional[str] = None
    attack_stage: Optional[str] = None
    interaction_count: Optional[int] = None



class RoutingHealthResponse(BaseModel):
    service: str
    status: str
    routing_policy: str
    detection_rules_active: int
    risk_scoring_active: bool