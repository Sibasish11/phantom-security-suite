from .database import LocalDatabaseGateway
from .policy import assess_request
from .schemas import (
    ProtectionRequest,
    ProtectionResponse,
    ProtectionTarget,
)

from ..session.manager import attack_session_manager
from ..telemetry.schemas import TelemetryEvent
from ..telemetry.queue import telemetry_queue


class ProtectionService:
    def __init__(
        self,
        *,
        database: LocalDatabaseGateway,
    ):
        self.database = database

    async def handle(
        self,
        request: ProtectionRequest,
    ) -> ProtectionResponse:

        existing_session = (
            attack_session_manager.get_session(
                request.session_id
            )
        )

        active_honeypot_session = (
            existing_session is not None
        )

        history_count = (
            existing_session.interaction_count
            if existing_session is not None
            else 0
        )

        assessment = assess_request(
            operation=request.operation,
            session_history_count=history_count,
            active_honeypot_session=active_honeypot_session,
        )

        session_id = request.session_id

        # Suspicious traffic gets an attack session.
        if assessment.suspicious and not session_id:
            session = attack_session_manager.create_session()
            session_id = session.session_id

        # Once an attacker has entered a honeypot session,
        # subsequent requests remain pinned to the honeypot.
        if (
            session_id
            and attack_session_manager.get_session(session_id)
            is not None
            and (
                assessment.suspicious
                or active_honeypot_session
            )
        ):
            final_target = ProtectionTarget.HONEYPOT
            routing_reason = (
                "Attack session is active; "
                "request pinned to HONEYPOT"
            )
        else:
            final_target = ProtectionTarget(
                assessment.final_target
            )
            routing_reason = assessment.reason

        try:
            data = await self.database.execute(
                target=final_target.value,
                operation=request.operation,
                parameters=request.parameters,
            )

            success = True
            error = None

        except Exception as exc:
            data = None
            success = False
            error = str(exc)

        if session_id and (
            final_target == ProtectionTarget.HONEYPOT
        ):
            try:
                attack_session_manager.record_interaction(
                    session_id=session_id,
                    operation=request.operation,
                    target=final_target.value,
                    risk_score=assessment.risk_score,
                    suspicious=assessment.suspicious,
                )
            except ValueError:
                session = attack_session_manager.create_session()
                session_id = session.session_id

                attack_session_manager.record_interaction(
                    session_id=session_id,
                    operation=request.operation,
                    target=final_target.value,
                    risk_score=assessment.risk_score,
                    suspicious=assessment.suspicious,
                )

        session = (
            attack_session_manager.get_session(session_id)
            if session_id
            else None
        )

        attack_stage = (
            session.attack_stage
            if session is not None
            else None
        )

        interaction_count = (
            session.interaction_count
            if session is not None
            else None
        )

        # ---------------------------------------------------------
        # TELEMETRY
        # ---------------------------------------------------------

        telemetry_event = TelemetryEvent(
            event_id=__import__("uuid").uuid4(),
            agent_id=__import__(
                "uuid"
            ).UUID(
                __import__(
                    "os"
                ).environ.get(
                    "AGENT_ID",
                    "00000000-0000-0000-0000-000000000000",
                )
            ),
            session_id=session_id,
            event_type="protection_query",
            operation=request.operation,
            original_target=ProtectionTarget.REAL.value,
            final_target=final_target.value,
            risk_score=assessment.risk_score,
            severity=assessment.severity,
            suspicious=assessment.suspicious,
            attack_stage=attack_stage,
            interaction_count=interaction_count,
            triggered_rules=[
                rule.rule
                for rule in assessment.rules
            ],
            metadata={
                "routing_reason": routing_reason,
                "success": success,
            },
        )

        telemetry_queue.put(telemetry_event)

        return ProtectionResponse(
            original_target=ProtectionTarget.REAL,
            final_target=final_target,
            operation=request.operation,
            risk_score=assessment.risk_score,
            severity=assessment.severity,
            suspicious=assessment.suspicious,
            triggered_rules=[
                {
                    "rule": rule.rule,
                    "score": rule.score,
                    "reason": rule.reason,
                }
                for rule in assessment.rules
            ],
            routing_reason=routing_reason,
            success=success,
            data=data,
            error=error,
            session_id=session_id,
            attack_stage=attack_stage,
            interaction_count=interaction_count,
        )

    async def health(self) -> dict[str, str]:
        real_ok = await self.database.health_check("real")

        honeypot_ok = await self.database.health_check(
            "honeypot"
        )

        if real_ok and honeypot_ok:
            status = "healthy"
        elif real_ok or honeypot_ok:
            status = "degraded"
        else:
            status = "offline"

        return {
            "service": (
                "PhantomLayer Local Protection Gateway"
            ),
            "status": status,
            "real_database": (
                "healthy"
                if real_ok
                else "offline"
            ),
            "honeypot_database": (
                "healthy"
                if honeypot_ok
                else "offline"
            ),
        }