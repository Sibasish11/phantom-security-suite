from typing import Any, Optional

from app.detection.engine import detection_engine
from app.detection.schemas import DetectionRequest, DetectionRule
from app.gateway.service import gateway_service
from app.gateway.schemas import GatewayOperation, GatewayRequest, GatewayTarget
from app.risk.engine import risk_scoring_engine
from app.risk.schemas import RecommendedTarget, RiskAssessmentRequest
from app.routing.schemas import (
    GatewayOperation,
    GatewayTarget,
    RoutingDecision,
    RoutingRequest,
    RoutingResponse,
)
from app.security_logging.service import security_event_logger
from app.honeypot import honeypot_session_manager


class AutomaticRoutingService:
    def __init__(self):
        pass

    def _map_to_gateway_operation(
        self,
        operation: str,
    ) -> Optional[GatewayOperation]:
        try:
            return GatewayOperation(operation)
        except ValueError:
            return None

    def _map_to_gateway_target(self, target: str) -> GatewayTarget:
        try:
            return GatewayTarget(target)
        except ValueError:
            raise ValueError(f"Unknown target: {target}")

    def _map_from_gateway_operation(
        self,
        operation: GatewayOperation,
    ) -> str:
        return operation.value

    def _map_from_gateway_target(
        self,
        target: GatewayTarget,
    ) -> str:
        return target.value

    @staticmethod
    def _references_honeypot_order(
        operation: GatewayOperation,
        parameters: Optional[dict[str, Any]],
    ) -> bool:
        """
        Return whether a request explicitly names a synthetic honeypot order.

        ``HPD-`` is the documented identifier namespace used by the honeypot
        seed. Treating that namespace as a honeypot reference lets a client
        continue an interaction without turning every normal order lookup into
        a sensitive operation. This is deliberately limited to ``get_order``
        and does not inspect arbitrary request values.
        """
        if operation != GatewayOperation.GET_ORDER or not parameters:
            return False

        order_number = parameters.get("order_number")

        return (
            isinstance(order_number, str)
            and order_number.upper().startswith("HPD-")
        )

    def _determine_routing_decision(
        self,
        original_target: GatewayTarget,
        risk_score: int,
        recommended_target: RecommendedTarget,
        operation: GatewayOperation,
        parameters: Optional[dict[str, Any]] = None,
        has_active_session: bool = False,
    ) -> tuple[GatewayTarget, RoutingDecision, str]:

        is_reconnaissance = (
            operation == GatewayOperation.LIST_TABLES
            and original_target == GatewayTarget.REAL
        )

        is_sensitive_access = operation in (
            GatewayOperation.GET_USERS,
            GatewayOperation.GET_CUSTOMERS,
            GatewayOperation.GET_CUSTOMER,
            GatewayOperation.GET_USER,
        )

        is_honeypot_order_reference = self._references_honeypot_order(
            operation,
            parameters,
        )

        is_honeypot_target = (
            original_target == GatewayTarget.HONEYPOT
            or has_active_session
        )

        if is_honeypot_target:
            final_target = GatewayTarget.HONEYPOT
            decision = RoutingDecision.ROUTED_TO_HONEYPOT

            if has_active_session:
                reason = (
                    f"Active honeypot session pinned. "
                    f"Request executed on HONEYPOT. Risk score: {risk_score}."
                )
            else:
                reason = (
                    f"Explicit honeypot target. "
                    f"Request executed on HONEYPOT. Risk score: {risk_score}."
                )

        elif (
            is_reconnaissance
            or is_sensitive_access
            or is_honeypot_order_reference
        ):
            final_target = GatewayTarget.HONEYPOT
            decision = RoutingDecision.ROUTED_TO_HONEYPOT

            if is_reconnaissance:
                reason = (
                    f"Reconnaissance operation (list_tables on REAL). "
                    f"Automatically routed to HONEYPOT. "
                    f"Risk score: {risk_score}."
                )

            elif is_honeypot_order_reference:
                reason = (
                    f"Synthetic honeypot order reference "
                    f"({operation.value}). Request executed on HONEYPOT. "
                    f"Risk score: {risk_score}."
                )

            else:
                reason = (
                    f"Sensitive data access ({operation.value}). "
                    f"Automatically routed to HONEYPOT. "
                    f"Risk score: {risk_score}."
                )

        elif risk_score >= 50:
            final_target = GatewayTarget.HONEYPOT
            decision = RoutingDecision.ROUTED_TO_HONEYPOT

            reason = (
                f"High risk request (score: {risk_score}). "
                f"Risk assessment recommended "
                f"{recommended_target.value}. "
                f"Request automatically routed to HONEYPOT."
            )

        else:
            final_target = GatewayTarget.REAL

            if original_target == GatewayTarget.REAL:
                decision = RoutingDecision.ORIGINAL_TARGET_PRESERVED

                reason = (
                    f"Low risk request (score: {risk_score}). "
                    f"Original target REAL preserved."
                )

            else:
                decision = RoutingDecision.ROUTED_TO_REAL

                reason = (
                    f"Risk assessment recommended REAL. "
                    f"Request routed to REAL. Risk score: {risk_score}."
                )

        return final_target, decision, reason

    async def route(self, request: RoutingRequest) -> RoutingResponse:
        original_target = self._map_to_gateway_target(request.target)
        operation = self._map_to_gateway_operation(request.operation)

        session_id = request.session_id
        from fastapi import HTTPException
        from sqlalchemy import select
        from app.database import get_sync_control_db_manager
        from app.models.control_plane import AttackSession
        from app.security_context import current_context
        context = current_context()
        if session_id and context:
            with get_sync_control_db_manager().session() as db:
                owner = db.execute(select(AttackSession).where(
                    AttackSession.session_id == session_id,
                )).scalar_one_or_none()
                if owner is not None and (
                    owner.organization_id != context.organization_id
                    or owner.domain_id != context.domain_id
                ):
                    raise HTTPException(404, "Session not found")
        session_history_count = None
        has_active_session = False

        if session_id:
            existing_session = honeypot_session_manager.get_session(session_id)

            if existing_session:
                session_history_count = existing_session.interaction_count
                has_active_session = True

        # ---------------------------------------------------------------
        # Invalid operation
        # ---------------------------------------------------------------

        if operation is None:
            if session_id:
                honeypot_session_manager.get_or_create_session(session_id=session_id)
            risk_request = RiskAssessmentRequest(
                target=request.target,
                operation=request.operation,
                parameters=request.parameters,
                session_id=session_id,
                session_history_count=session_history_count,
            )

            risk_assessment = risk_scoring_engine.assess(risk_request)

            security_event_logger.log_gateway_failure(
                original_target=original_target.value,
                operation=request.operation,
                error=f"Unsupported operation: {request.operation}",
                risk_score=risk_assessment.risk_score,
                session_id=session_id,
            )

            attack_stage = None
            interaction_count = None

            if session_id:
                record = honeypot_session_manager.record_interaction(
                    session_id=session_id,
                    operation=request.operation,
                    parameters=request.parameters or {},
                    risk_score=risk_assessment.risk_score,
                    data=None,
                    success=False,
                    details=f"Unsupported operation: {request.operation}",
                )

                attack_stage = record.attack_stage.value
                interaction_count = record.step

            return RoutingResponse(
                original_target=original_target,
                final_target=original_target,
                operation=request.operation,
                risk_score=risk_assessment.risk_score,
                severity=risk_assessment.severity,
                confidence=risk_assessment.confidence,
                confidence_level=risk_assessment.confidence_level,
                suspicious=risk_assessment.risk_score > 0,
                triggered_rules=[
                    {
                        "rule": r.rule.value,
                        "description": r.description,
                        "severity": r.severity.value,
                        "base_score": r.base_score,
                        "weighted_score": r.weighted_score,
                        "weight": r.weight,
                    }
                    for r in risk_assessment.triggered_rules
                ],
                reasons=risk_assessment.reasons,
                routing_decision=RoutingDecision.ROUTED_TO_HONEYPOT,
                routing_reason=(
                    f"Invalid operation '{request.operation}'. "
                    f"Request rejected."
                ),
                gateway_result=None,
                gateway_success=False,
                gateway_error=f"Unsupported operation: {request.operation}",
                session_id=session_id,
                attack_stage=attack_stage,
                interaction_count=interaction_count,
            )

        # ---------------------------------------------------------------
        # Risk assessment
        # ---------------------------------------------------------------

        risk_request = RiskAssessmentRequest(
            target=request.target,
            operation=request.operation,
            parameters=request.parameters,
            session_id=session_id,
            session_history_count=session_history_count,
        )

        risk_assessment = risk_scoring_engine.assess(risk_request)

        # ---------------------------------------------------------------
        # Automatic routing decision
        # ---------------------------------------------------------------

        final_target, routing_decision, routing_reason = (
            self._determine_routing_decision(
                original_target=original_target,
                risk_score=risk_assessment.risk_score,
                recommended_target=risk_assessment.recommended_target,
                operation=operation,
                parameters=request.parameters,
                has_active_session=has_active_session,
            )
        )

        attack_stage = None
        interaction_count = None

        # Create a honeypot session when routing to deception.
        if final_target == GatewayTarget.HONEYPOT:
            session = honeypot_session_manager.get_or_create_session(
                session_id=session_id
            )

            session_id = session.session_id

        # ---------------------------------------------------------------
        # Security telemetry: request analyzed
        # ---------------------------------------------------------------

        triggered_rules = [
            {
                "rule": r.rule.value,
                "description": r.description,
                "severity": r.severity.value,
                "base_score": r.base_score,
                "weighted_score": r.weighted_score,
                "weight": r.weight,
            }
            for r in risk_assessment.triggered_rules
        ]

        security_event_logger.log_request_analyzed(
            original_target=original_target.value,
            operation=operation.value,
            risk_score=risk_assessment.risk_score,
            severity=risk_assessment.severity.value,
            confidence=risk_assessment.confidence,
            confidence_level=risk_assessment.confidence_level.value,
            suspicious=risk_assessment.risk_score > 0,
            triggered_rules=triggered_rules,
            reasons=risk_assessment.reasons,
            routing_decision="pending",
            routing_reason=(
                "Risk assessment complete, determining routing"
            ),
            session_id=session_id,
        )

        # ---------------------------------------------------------------
        # Security telemetry: suspicious request
        # ---------------------------------------------------------------

        if risk_assessment.risk_score > 0:
            is_reconnaissance = (
                operation == GatewayOperation.LIST_TABLES
                and original_target == GatewayTarget.REAL
            )

            is_sensitive_access = operation in (
                GatewayOperation.GET_USERS,
                GatewayOperation.GET_CUSTOMERS,
                GatewayOperation.GET_CUSTOMER,
                GatewayOperation.GET_USER,
            )

            is_honeypot_order_reference = (
                self._references_honeypot_order(
                    operation,
                    request.parameters,
                )
            )

            is_honeypot_target = (
                original_target == GatewayTarget.HONEYPOT
                or has_active_session
            )

            if (
                is_honeypot_target
                or is_reconnaissance
                or is_sensitive_access
                or is_honeypot_order_reference
                or risk_assessment.risk_score >= 50
            ):
                security_event_logger.log_suspicious_request(
                    original_target=original_target.value,
                    final_target=final_target.value,
                    operation=operation.value,
                    risk_score=risk_assessment.risk_score,
                    severity=risk_assessment.severity.value,
                    confidence=risk_assessment.confidence,
                    confidence_level=(
                        risk_assessment.confidence_level.value
                    ),
                    triggered_rules=triggered_rules,
                    reasons=risk_assessment.reasons,
                    session_id=session_id,
                )

        # ---------------------------------------------------------------
        # Security telemetry: routing decision
        # ---------------------------------------------------------------

        security_event_logger.log_routing_decision(
            original_target=original_target.value,
            final_target=final_target.value,
            operation=operation.value,
            risk_score=risk_assessment.risk_score,
            routing_decision=routing_decision.value,
            routing_reason=routing_reason,
            session_id=session_id,
        )

        # ---------------------------------------------------------------
        # Gateway execution
        # ---------------------------------------------------------------

        gateway_request = GatewayRequest(
            target=final_target,
            operation=operation,
            parameters=request.parameters or {},
        )

        gateway_response = await gateway_service.execute(
            gateway_request
        )

        # ---------------------------------------------------------------
        # Honeypot interaction + incident candidate
        # ---------------------------------------------------------------

        if final_target == GatewayTarget.HONEYPOT and session_id:
            record = honeypot_session_manager.record_interaction(
                session_id=session_id,
                operation=operation.value,
                parameters=request.parameters or {},
                risk_score=risk_assessment.risk_score,
                data=gateway_response.data,
                success=gateway_response.success,
                details=gateway_response.error,
            )

            attack_stage = record.attack_stage.value
            interaction_count = record.step

            if gateway_response.success:
                result_count = (
                    len(gateway_response.data)
                    if isinstance(gateway_response.data, list)
                    else (1 if gateway_response.data else 0)
                )

                security_event_logger.log_honeypot_interaction(
                    original_target=original_target.value,
                    final_target=final_target.value,
                    operation=operation.value,
                    result_count=result_count,
                    session_id=session_id,
                    attack_stage=attack_stage,
                )

                # Create a pending incident candidate from the
                # now-correlated session + security telemetry.
                #
                # IMPORTANT:
                # This does NOT call the AI provider.
                # It does NOT influence routing.
                from app.incident_analysis.service import incident_service

                incident_service.ensure_incident(session_id)

            else:
                security_event_logger.log_gateway_failure(
                    original_target=original_target.value,
                    operation=operation.value,
                    error=(
                        gateway_response.error
                        or "Honeypot query failed"
                    ),
                    risk_score=risk_assessment.risk_score,
                    session_id=session_id,
                )

        # ---------------------------------------------------------------
        # Final routing response
        # ---------------------------------------------------------------

        return RoutingResponse(
            original_target=original_target,
            final_target=final_target,
            operation=operation,
            risk_score=risk_assessment.risk_score,
            severity=risk_assessment.severity,
            confidence=risk_assessment.confidence,
            confidence_level=risk_assessment.confidence_level,
            suspicious=risk_assessment.risk_score > 0,
            triggered_rules=triggered_rules,
            reasons=risk_assessment.reasons,
            routing_decision=routing_decision,
            routing_reason=routing_reason,
            gateway_result=gateway_response.data,
            gateway_success=gateway_response.success,
            gateway_error=gateway_response.error,
            session_id=session_id,
            attack_stage=attack_stage,
            interaction_count=interaction_count,
        )

    async def health_check(self) -> dict[str, Any]:
        gateway_health = await gateway_service.health_check()

        return {
            "service": "PhantomLayer Automatic Routing",
            "status": (
                "healthy"
                if gateway_health["real_database"] == "healthy"
                and gateway_health["honeypot_database"] == "healthy"
                else "degraded"
            ),
            "routing_policy": "risk_based_automatic",
            "detection_rules_active": 5,
            "risk_scoring_active": True,
            "real_database": gateway_health["real_database"],
            "honeypot_database": gateway_health["honeypot_database"],
        }


automatic_routing_service = AutomaticRoutingService()