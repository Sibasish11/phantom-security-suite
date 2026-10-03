import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.agent.schemas import (
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    AgentResponse,
)
from app.database import get_sync_control_db_manager
from app.readiness import agent_status, integration_ready
from app.models.control_plane import (
    Agent,
    AgentStatus as ControlAgentStatus,
    Domain,
    Organization,
    OrganizationStatus,
)


class AgentRegistry:
    """
    Control-plane agent registry.

    The control plane stores agent metadata and a hash of the
    agent credential. Database credentials are never accepted here.
    """

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _to_response(agent: Agent) -> AgentResponse:
        try:
            capabilities = json.loads(
                agent.capabilities or "[]"
            )
        except (TypeError, json.JSONDecodeError):
            capabilities = []

        return AgentResponse(
            agent_id=agent.id,
            name=agent.name,
            domain_id=agent.domain_id,
            version=agent.version,
            capabilities=capabilities,
            status=agent_status(agent),
            integration_ready=integration_ready(agent),
            registered_at=agent.registered_at,
            last_heartbeat_at=agent.last_heartbeat_at,
            real_db_reachable=agent.real_db_reachable,
            honeypot_db_reachable=agent.honeypot_db_reachable,
            telemetry_events_sent=agent.telemetry_events_sent,
        )

    def register(
        self,
        request: AgentRegistrationRequest,
        organization_id: UUID,
    ) -> tuple[AgentResponse, str]:

        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)

        db = get_sync_control_db_manager()

        with db.session() as session:
            domain = session.execute(
                select(Domain).where(
                    Domain.id == request.domain_id,
                    Domain.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if domain is None:
                raise ValueError(
                    "Domain not found in your organization"
                )

            if not domain.verified:
                raise ValueError(
                    "Domain must be verified before "
                    "registering an agent"
                )

            existing = session.execute(
                select(Agent).where(
                    Agent.organization_id == organization_id,
                    Agent.domain_id == request.domain_id,
                    Agent.name == request.name,
                )
            ).scalar_one_or_none()

            if existing is not None:
                raise ValueError(
                    "An agent with this name already exists "
                    "for this domain"
                )

            agent = Agent(
                organization_id=organization_id,
                domain_id=request.domain_id,
                name=request.name,
                version=request.version,
                capabilities=json.dumps(
                    request.capabilities
                ),
                token_hash=token_hash,
                status=ControlAgentStatus.PENDING,
                registered_at=datetime.now(timezone.utc),
                real_db_reachable=False,
                honeypot_db_reachable=False,
                telemetry_events_sent=0,
            )

            session.add(agent)
            session.flush()

            response = self._to_response(agent)

            session.commit()

            return response, token

    def rotate_token(
        self,
        agent_id: UUID,
        organization_id: UUID,
    ) -> tuple[AgentResponse, str] | None:

        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)

        db = get_sync_control_db_manager()

        with db.session() as session:
            agent = session.execute(
                select(Agent).where(
                    Agent.id == agent_id,
                    Agent.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if agent is None:
                return None

            agent.token_hash = token_hash
            agent.status = ControlAgentStatus.PENDING
            agent.last_heartbeat_at = None
            agent.real_db_reachable = False
            agent.honeypot_db_reachable = False
            agent.metadata_json = "{}"

            session.flush()

            response = self._to_response(agent)

            session.commit()

            return response, token

    def get(
        self,
        agent_id: UUID,
        organization_id: UUID,
    ) -> AgentResponse | None:

        db = get_sync_control_db_manager()

        with db.session() as session:
            agent = session.execute(
                select(Agent).where(
                    Agent.id == agent_id,
                    Agent.organization_id == organization_id,
                )
            ).scalar_one_or_none()

            if agent is None:
                return None

            return self._to_response(agent)

    def list(
        self,
        organization_id: UUID,
    ) -> list[AgentResponse]:

        db = get_sync_control_db_manager()

        with db.session() as session:
            agents = session.execute(
                select(Agent)
                .where(
                    Agent.organization_id == organization_id
                )
                .order_by(Agent.created_at.desc())
            ).scalars().all()

            return [
                self._to_response(agent)
                for agent in agents
            ]

    @staticmethod
    def _calculate_status(
        requested_status: ControlAgentStatus,
        real_db_reachable: bool,
        honeypot_db_reachable: bool,
    ) -> ControlAgentStatus:

        if requested_status == ControlAgentStatus.OFFLINE:
            return ControlAgentStatus.OFFLINE

        if requested_status == ControlAgentStatus.PENDING:
            return ControlAgentStatus.PENDING

        if (
            requested_status == ControlAgentStatus.HEALTHY
            and real_db_reachable
            and honeypot_db_reachable
        ):
            return ControlAgentStatus.HEALTHY

        return ControlAgentStatus.DEGRADED

    def heartbeat(
        self,
        agent_id: UUID,
        token: str,
        heartbeat: AgentHeartbeatRequest,
    ) -> AgentResponse | None:

        db = get_sync_control_db_manager()

        with db.session() as session:
            agent = session.execute(
                select(Agent).where(
                    Agent.id == agent_id,
                )
            ).scalar_one_or_none()

            if agent is None:
                return None

            supplied_hash = self._hash_token(token)

            if not agent.token_hash or not secrets.compare_digest(
                agent.token_hash,
                supplied_hash,
            ):
                return None

            domain = session.get(Domain, agent.domain_id) if agent.domain_id else None
            organization = session.get(Organization, agent.organization_id)
            if (not domain or not domain.verified or domain.organization_id != agent.organization_id
                    or not organization or organization.status != OrganizationStatus.ACTIVE):
                return None

            requested_status = ControlAgentStatus(
                "pending" if heartbeat.status.value == "connecting" else heartbeat.status.value
            )

            actual_status = self._calculate_status(
                requested_status=requested_status,
                real_db_reachable=heartbeat.real_db_reachable,
                honeypot_db_reachable=(
                    heartbeat.honeypot_db_reachable
                ),
            )

            agent.status = actual_status
            agent.metadata_json = json.dumps({"integration_ready": heartbeat.integration_ready})
            agent.last_heartbeat_at = datetime.now(
                timezone.utc
            )
            agent.real_db_reachable = (
                heartbeat.real_db_reachable
            )
            agent.honeypot_db_reachable = (
                heartbeat.honeypot_db_reachable
            )
            agent.telemetry_events_sent += (
                heartbeat.telemetry_events_sent
            )

            session.flush()

            response = self._to_response(agent)

            session.commit()

            return response

    def clear(self) -> None:
        """
        Test/development utility.

        This intentionally does not belong to a public API route.
        """

        db = get_sync_control_db_manager()

        with db.session() as session:
            agents = session.execute(
                select(Agent)
            ).scalars().all()

            for agent in agents:
                session.delete(agent)

            session.flush()
            session.commit()


agent_registry = AgentRegistry()
