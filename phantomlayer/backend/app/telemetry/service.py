import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.database import get_sync_control_db_manager
from app.models.control_plane import (
    Agent,
    AttackSession,
    AttackSessionInteraction,
)
from app.telemetry.schemas import (
    AgentTelemetryBatch,
    AgentTelemetryEvent,
    AgentTelemetryResponse,
)


class TelemetryAuthenticationError(Exception):
    """Raised when an agent telemetry credential is invalid."""


class TelemetryValidationError(Exception):
    """Raised when telemetry does not match the authenticated agent."""


class TelemetryService:
    """
    Cloud-side telemetry ingestion.

    Agent credentials are verified against the hashed credential stored
    in the control plane. Telemetry is persisted into the existing
    AttackSession / AttackSessionInteraction model.
    """

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _authenticate_agent(
        session,
        agent_id: UUID,
        token: str,
    ) -> Agent:
        agent = session.execute(
            select(Agent).where(
                Agent.id == agent_id,
            ).with_for_update()
        ).scalar_one_or_none()

        if agent is None:
            raise TelemetryAuthenticationError(
                "Invalid agent credentials"
            )

        supplied_hash = TelemetryService._hash_token(token)

        if not agent.token_hash or not secrets.compare_digest(
            agent.token_hash,
            supplied_hash,
        ):
            raise TelemetryAuthenticationError(
                "Invalid agent credentials"
            )

        return agent

    @staticmethod
    def _get_or_create_session(
        session,
        *,
        agent: Agent,
        event: AgentTelemetryEvent,
    ) -> AttackSession:
        # Session correlation belongs to an authenticated agent, not to an
        # arbitrary globally unique ID supplied in telemetry.
        session_id = f"agent:{agent.id}:{hashlib.sha256((event.session_id or str(event.event_id)).encode()).hexdigest()[:32]}"
        if event.session_id:
            attack_session = session.execute(
                select(AttackSession).where(
                    AttackSession.session_id == session_id,
                    AttackSession.organization_id
                    == agent.organization_id,
                )
            ).scalar_one_or_none()

            if attack_session is not None:
                return attack_session

        attack_session = AttackSession(
            session_id=session_id,
            organization_id=agent.organization_id,
            domain_id=agent.domain_id,
            attack_stage=event.attack_stage or "unknown",
            interaction_count=0,
            exposed_entities_json=json.dumps({}),
            metadata_json=json.dumps(
                {
                    "agent_id": str(agent.id),
                    "telemetry_source": "phantomlayer_agent",
                }
            ),
            created_at=event.timestamp,
            last_active_at=event.timestamp,
        )

        session.add(attack_session)
        session.flush()

        return attack_session

    @staticmethod
    def _persist_event(
        session,
        *,
        agent: Agent,
        event: AgentTelemetryEvent,
    ) -> None:
        attack_session = TelemetryService._get_or_create_session(
            session,
            agent=agent,
            event=event,
        )

        step = attack_session.interaction_count + 1

        interaction_details = {
            "event_id": str(event.event_id),
            "agent_id": str(agent.id),
            "event_type": event.event_type,
            "original_target": event.original_target,
            "final_target": event.final_target,
            "severity": event.severity,
            "suspicious": event.suspicious,
            "triggered_rules": event.triggered_rules,
            # Raw metadata is not copied: the cloud accepts telemetry facts,
            # never production records, credentials or HTTP request bodies.
            "metadata": {},
            "source": "agent_reported_not_independently_verified",
        }

        interaction = AttackSessionInteraction(
            event_id=event.event_id,
            session_id=attack_session.id,
            step=step,
            operation=event.operation,
            parameters_json=json.dumps(
                {
                    "original_target": event.original_target,
                    "final_target": event.final_target,
                    "telemetry_event_id": str(event.event_id),
                }
            ),
            risk_score=event.risk_score,
            attack_stage=event.attack_stage or "unknown",
            entities_exposed_json=json.dumps({}),
            success=True,
            details=json.dumps(interaction_details),
            timestamp=event.timestamp,
        )

        session.add(interaction)

        attack_session.interaction_count = step
        attack_session.attack_stage = (
            event.attack_stage
            or attack_session.attack_stage
            or "unknown"
        )
        attack_session.last_active_at = event.timestamp

        metadata = {}

        try:
            metadata = json.loads(
                attack_session.metadata_json or "{}"
            )
        except (TypeError, json.JSONDecodeError):
            metadata = {}

        metadata["last_event_id"] = str(event.event_id)
        metadata["last_severity"] = event.severity
        metadata["last_risk_score"] = event.risk_score
        metadata["agent_id"] = str(agent.id)

        attack_session.metadata_json = json.dumps(metadata)

    def ingest(
        self,
        batch: AgentTelemetryBatch,
        token: str,
    ) -> AgentTelemetryResponse:
        if not token:
            raise TelemetryAuthenticationError(
                "Missing agent token"
            )

        if not batch.events:
            return AgentTelemetryResponse(
                accepted=0,
                rejected=0,
            )

        first_agent_id = batch.events[0].agent_id

        db = get_sync_control_db_manager()

        with db.session() as session:
            agent = self._authenticate_agent(
                session,
                first_agent_id,
                token,
            )

            for event in batch.events:
                if event.agent_id != agent.id:
                    raise TelemetryValidationError(
                        "Telemetry batch contains events "
                        "for another agent"
                    )

            accepted = 0

            for event in batch.events:
                if session.execute(select(AttackSessionInteraction.id).where(
                    AttackSessionInteraction.event_id == event.event_id,
                )).scalar_one_or_none() is not None:
                    continue  # Retry-safe event ID; do not expose another owner.
                self._persist_event(
                    session,
                    agent=agent,
                    event=event,
                )
                accepted += 1
                session.flush()

            agent.telemetry_events_sent += accepted

            session.flush()
            session.commit()

            return AgentTelemetryResponse(
                accepted=accepted,
                rejected=0,
            )


telemetry_service = TelemetryService()