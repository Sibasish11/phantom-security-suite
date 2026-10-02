from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


BankOperation = Literal[
    "login",
    "get_accounts",
    "get_balance",
    "get_transactions",
    "get_beneficiaries",
    "get_cards",
    "create_transfer",
    "get_profile",
    "list_tables",
    "enumerate_api",
    "get_customers",
    "enumerate_customers",
    "enumerate_accounts",
    "enumerate_transactions",
    "probe_admin",
    "credential_probe",
]


class BankDecisionRequest(BaseModel):
    """Minimal, non-sensitive request sent by a trusted bank-side proxy."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=128)
    operation: BankOperation
    client_ip: str | None = Field(default=None, max_length=255)


class BankDecisionResponse(BaseModel):
    decision_id: UUID
    session_id: str
    target: Literal["real", "honeypot"]
    risk_score: int = Field(ge=0, le=100)
    attack_stage: str
    triggered_rules: list[str] = Field(default_factory=list)


class BankObserveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: UUID
    session_id: str | None = Field(default=None, min_length=1, max_length=160)
    operation: BankOperation | None = None
    success: bool
    exposed_entities: dict[str, int] = Field(default_factory=dict)
    response_count: int = Field(default=0, ge=0, le=100000)

    @field_validator("exposed_entities")
    @classmethod
    def validate_counts(cls, counts):
        allowed = {"customers", "accounts", "transactions", "beneficiaries", "cards", "profile",
                   "balance", "transfers", "tables", "list_tables", "api", "api_operations",
                   "probe_admin", "credential_probe", "login"}
        if len(counts) > 16 or any(key not in allowed or isinstance(value, bool) or not 0 <= value <= 100000
                                   for key, value in counts.items()):
            raise ValueError("Only bounded synthetic entity counts are accepted")
        return counts


class BankObserveResponse(BaseModel):
    accepted: bool
    session_id: str
    target: Literal["real", "honeypot"]
