"""
Phase 11 – AI Incident Analysis: Client Abstraction

Security contract
-----------------
- BaseIncidentAnalysisClient.analyze() receives ONLY a SanitizedSessionPayload.
- It MUST return a validated IncidentAnalysisResponse Pydantic model.
- It MUST NOT make any database calls.
- It MUST NOT have access to routing logic or production credentials.
- AI output is advisory intelligence; it MUST NOT alter routing decisions.

Providers
---------
- MockAnalysisClient   – deterministic, no network; used in CI and when
                         AI_ENABLED=False.
- Future real providers (OpenAI, Anthropic, local LLM) must extend
  BaseIncidentAnalysisClient and be wired in client_factory() below.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from app.incident_analysis.schemas import (
    ActionPriority,
    AttackPattern,
    AttackTimelineStep,
    IncidentAnalysisResponse,
    PatternConfidence,
    RecommendedAction,
    SanitizedSessionPayload,
)


class IncidentAnalysisError(Exception):
    """Raised when the AI client cannot complete analysis."""


class IncidentAnalysisTimeoutError(IncidentAnalysisError):
    """Raised when the AI provider times out."""


class IncidentAnalysisMalformedResponseError(IncidentAnalysisError):
    """Raised when the AI provider returns unparseable output."""


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------


class BaseIncidentAnalysisClient(ABC):
    """
    Provider-agnostic interface for AI incident analysis.

    Subclasses must:
    - Accept a SanitizedSessionPayload (no raw data, no secrets).
    - Return a validated IncidentAnalysisResponse.
    - Raise IncidentAnalysisError (or a subclass) on failure.
    - Never access the database or the routing service.
    """

    @abstractmethod
    async def analyze(self, payload: SanitizedSessionPayload) -> IncidentAnalysisResponse:
        """Analyse a sanitized session payload and return a structured report."""


# ---------------------------------------------------------------------------
# Mock implementation (deterministic, used for tests and when AI is disabled)
# ---------------------------------------------------------------------------

# Mapping from attack stage names to human-readable objective inferences
_STAGE_OBJECTIVES: dict[str, str] = {
    "reconnaissance": "Initial reconnaissance to identify available data endpoints and table structure.",
    "enumeration": "Bulk enumeration of customer or user records to build a target list.",
    "exploration": "Targeted drill-down into specific records to gather detailed PII.",
    "exfiltration": "Systematic extraction of sensitive data across multiple entity types.",
    "credential_access": "Credential harvesting targeting admin or privileged user accounts.",
}

_PATTERN_BY_STAGE: dict[str, tuple[str, str, PatternConfidence]] = {
    "reconnaissance": (
        "API Surface Probing",
        "Attacker systematically explored available API endpoints to enumerate capabilities.",
        PatternConfidence.HIGH,
    ),
    "enumeration": (
        "Bulk Data Enumeration",
        "Attacker queried broad collections of records, typical of data harvesting preparation.",
        PatternConfidence.HIGH,
    ),
    "exploration": (
        "Targeted Record Lookup",
        "Attacker drilled into specific records after initial enumeration.",
        PatternConfidence.MEDIUM,
    ),
    "exfiltration": (
        "Systematic Data Exfiltration",
        "Attacker performed multiple queries across entity types in a pattern consistent with bulk data export.",
        PatternConfidence.HIGH,
    ),
    "credential_access": (
        "Credential Harvesting",
        "Attacker targeted user/account endpoints, consistent with credential theft or privilege escalation.",
        PatternConfidence.HIGH,
    ),
}

_BASE_RECOMMENDATIONS: list[RecommendedAction] = [
    RecommendedAction(
        action_type="network_block",
        description="Verify the true client origin through trusted proxy logs before considering a scoped block or rate limit; the recorded source may be a shared proxy.",
        priority=ActionPriority.HIGH,
    ),
    RecommendedAction(
        action_type="alert",
        description="Generate a real-time alert to the security operations team for manual review.",
        priority=ActionPriority.HIGH,
    ),
    RecommendedAction(
        action_type="audit",
        description="Audit API access logs for the same IP across other services and time windows.",
        priority=ActionPriority.MEDIUM,
    ),
    RecommendedAction(
        action_type="review_controls",
        description="Review API authentication controls – consider enforcing OAuth2/JWT on all endpoints.",
        priority=ActionPriority.MEDIUM,
    ),
]

_CREDENTIAL_RECOMMENDATION = RecommendedAction(
    action_type="credential_rotation",
    description=(
        "Credential-related operations were observed in deception. "
        "Investigate separately for actual credential compromise; rotate real credentials only if that investigation supports it."
    ),
    priority=ActionPriority.CRITICAL,
)

_EXFILTRATION_RECOMMENDATION = RecommendedAction(
    action_type="data_classification_review",
    description=(
        "Bulk data access was detected. "
        "Review data classification and ensure sensitive fields (PII, payment) are masked or tokenized."
    ),
    priority=ActionPriority.HIGH,
)


class MockAnalysisClient(BaseIncidentAnalysisClient):
    """
    Deterministic mock AI client.  Used in tests and when AI_ENABLED=False.

    Produces a realistic-looking but fully synthetic IncidentAnalysisResponse
    derived only from the provided SanitizedSessionPayload.  No network calls.
    """

    async def analyze(self, payload: SanitizedSessionPayload) -> IncidentAnalysisResponse:
        stage = payload.final_attack_stage

        # Build annotated timeline
        annotated_timeline: list[AttackTimelineStep] = []
        intent_map: dict[str, str] = {
            "list_tables": "Enumerate available database tables to identify data targets.",
            "get_customers": "Bulk-retrieve all customer records for PII harvesting.",
            "get_customer": "Retrieve a specific customer record by identifier.",
            "get_orders": "Retrieve order records, potentially to map financial relationships.",
            "get_order": "Access detailed order data including line items and payment info.",
            "get_users": "Enumerate user/account records to identify privileged accounts.",
            "get_user": "Retrieve a specific user account, likely targeting credentials.",
            "get_products": "Enumerate product catalog — low-value reconnaissance step.",
        }
        for step in payload.timeline:
            annotated_timeline.append(
                AttackTimelineStep(
                    step=step.step,
                    operation=step.operation,
                    attack_stage=step.attack_stage,
                    inferred_intent=intent_map.get(
                        step.operation,
                        f"[AI INFERENCE] Unknown intent for operation '{step.operation}'.",
                    ),
                )
            )

        # Sensitive resources targeted
        sensitive_resources: list[str] = []
        if "get_customers" in payload.unique_operations or "get_customer" in payload.unique_operations:
            sensitive_resources.append("customers (PII: name, email, address)")
        if "get_orders" in payload.unique_operations or "get_order" in payload.unique_operations:
            sensitive_resources.append("orders (financial records, payment references)")
        if "get_users" in payload.unique_operations or "get_user" in payload.unique_operations:
            sensitive_resources.append("users (account credentials, roles)")

        # Attack patterns
        patterns: list[AttackPattern] = []
        pdata = _PATTERN_BY_STAGE.get(stage)
        if pdata:
            patterns.append(AttackPattern(pattern_name=pdata[0], description=pdata[1], confidence=pdata[2]))
        if len(payload.unique_operations) >= 3:
            patterns.append(
                AttackPattern(
                    pattern_name="Multi-Stage Attack Chain",
                    description=(
                        f"The session contains {len(payload.unique_operations)} distinct operations. "
                        "A multi-step probing sequence is possible; telemetry alone does not establish deliberate intent."
                    ),
                    confidence=PatternConfidence.MEDIUM,
                )
            )
        if "RULE_REPEATED_ACCESS" in payload.triggered_rule_names:
            patterns.append(
                AttackPattern(
                    pattern_name="Repeated Session Activity",
                    description=(
                        "The detection engine flagged repeated activity within one session. "
                        "Automation or scraping is a hypothesis, not an observed fact."
                    ),
                    confidence=PatternConfidence.MEDIUM,
                )
            )

        # Recommendations
        recommendations = list(_BASE_RECOMMENDATIONS)
        if stage in ("credential_access",):
            recommendations.insert(0, _CREDENTIAL_RECOMMENDATION)
        if stage in ("exfiltration",):
            recommendations.insert(0, _EXFILTRATION_RECOMMENDATION)

        # Risk assessment narrative
        risk_narrative = (
            f"Session risk score peaked at {payload.max_risk_score}/100 "
            f"(average {payload.avg_risk_score:.1f}/100) across "
            f"{payload.total_interactions} interactions. "
            f"The attacker progressed to attack stage '{stage}'. "
            f"{len(payload.triggered_rule_names)} detection rule(s) fired: "
            f"{', '.join(payload.triggered_rule_names) or 'none'}."
        )

        # Stage progression list (deduplicated, ordered)
        stage_progression = list(dict.fromkeys(step.attack_stage for step in payload.timeline))

        return IncidentAnalysisResponse(
            session_id=payload.session_id,
            incident_summary=(
                f"Attacker session '{payload.session_id}' performed "
                f"{payload.total_interactions} honeypot interaction(s) over "
                f"{payload.session_duration_seconds or 0:.1f}s, reaching attack stage '{stage}'. "
                f"The session triggered {len(payload.triggered_rule_names)} detection rule(s) "
                f"with a peak risk score of {payload.max_risk_score}/100."
            ),
            attack_stage_progression=stage_progression,
            timeline=annotated_timeline,
            observed_behavior=(
                f"Recorded {payload.total_interactions} interactions with synthetic resources. "
                f"Operations: {', '.join(payload.unique_operations)}. "
                "Intent and activity outside this integration were not directly observed."
            ),
            operations_performed=payload.unique_operations,
            sensitive_resources_targeted=sensitive_resources,
            exposed_synthetic_entities=payload.exposed_entity_counts,
            risk_assessment=risk_narrative,
            suspicious_patterns=patterns,
            likely_objective=_STAGE_OBJECTIVES.get(
                stage,
                "[AI INFERENCE] Objective unclear from available telemetry.",
            ),
            defensive_recommendations=recommendations,
            limitations=(
                "This analysis was generated by a mock AI client using deterministic rules. "
                "All inferences are based solely on sanitized honeypot telemetry. "
                "No production data was supplied to this analysis; this report alone does not prove absence of access elsewhere. "
                "Treat 'likely_objective' and 'inferred_intent' as advisory intelligence only."
            ),
            analysis_provider="mock",
        )


# ---------------------------------------------------------------------------
# Factory: returns the appropriate client based on settings
# ---------------------------------------------------------------------------


def client_factory(
    provider: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> BaseIncidentAnalysisClient:
    """
    Returns the appropriate AI client.

    - If enabled is False (or AI_ENABLED env var is False), always returns
      MockAnalysisClient regardless of provider setting.
    - Only "mock" provider is implemented in Phase 11.
    - Future providers ("openai", "anthropic") will be wired here.
    """
    from app.incident_analysis.config import ai_settings

    use_enabled = enabled if enabled is not None else ai_settings.ai_enabled
    use_provider = provider or ai_settings.ai_provider

    if not use_enabled:
        return MockAnalysisClient()

    if use_provider == "mock":
        return MockAnalysisClient()

    # Future: real LLM providers wired here
    # if use_provider == "openai":
    #     return OpenAIAnalysisClient(...)
    # if use_provider == "anthropic":
    #     return AnthropicAnalysisClient(...)

    raise ValueError(
        f"Unknown AI provider '{use_provider}'. "
        "Only 'mock' is supported in Phase 11. "
        "Set AI_PROVIDER=mock or AI_ENABLED=false."
    )
