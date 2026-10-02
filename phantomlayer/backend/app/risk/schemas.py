from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.detection.schemas import DetectionRule, RecommendedTarget, Severity


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RiskAssessmentRequest(BaseModel):
    target: str = Field(..., description="Target database: real or honeypot")
    operation: str = Field(..., description="Operation to execute")
    parameters: Optional[dict[str, Any]] = Field(default=None, description="Optional parameters")
    client_ip: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    session_id: Optional[str] = Field(default=None, description="Attacker session ID")
    session_history_count: Optional[int] = Field(default=None, description="Number of previous interactions in session")



class TriggeredRuleDetail(BaseModel):
    rule: DetectionRule
    description: str
    severity: Severity
    base_score: int = Field(..., ge=0, le=100)
    weighted_score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    triggered_rules: list[TriggeredRuleDetail]
    reasons: list[str]
    recommended_target: RecommendedTarget
    scoring_method: str = "deterministic_weighted"


class RiskHealthResponse(BaseModel):
    service: str
    status: str
    scoring_method: str
    confidence_thresholds: dict[str, float]