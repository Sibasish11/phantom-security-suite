from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DetectionRule(str, Enum):
    RULE_SENSITIVE_DATA_ACCESS = "RULE_SENSITIVE_DATA_ACCESS"
    RULE_ENUMERATION = "RULE_ENUMERATION"
    RULE_INVALID_OPERATION = "RULE_INVALID_OPERATION"
    RULE_HONEYPOT_TARGET = "RULE_HONEYPOT_TARGET"
    RULE_RECONNAISSANCE = "RULE_RECONNAISSANCE"
    RULE_REPEATED_ACCESS = "RULE_REPEATED_ACCESS"


class RecommendedTarget(str, Enum):
    REAL = "real"
    HONEYPOT = "honeypot"


class DetectionRequest(BaseModel):
    target: str = Field(..., description="Target database: real or honeypot")
    operation: str = Field(..., description="Operation to execute")
    parameters: Optional[dict[str, Any]] = Field(default=None, description="Optional parameters")
    client_ip: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")
    session_id: Optional[str] = Field(default=None, description="Attacker session ID")
    session_history_count: Optional[int] = Field(default=None, description="Number of previous interactions in session")



class TriggeredRule(BaseModel):
    rule: DetectionRule
    description: str
    severity: Severity
    score: int = Field(..., ge=0, le=100)


class DetectionResult(BaseModel):
    suspicious: bool
    risk_score: int = Field(..., ge=0, le=100)
    severity: Severity
    triggered_rules: list[TriggeredRule]
    reasons: list[str]
    recommended_target: RecommendedTarget