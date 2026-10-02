from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control_plane import Agent


class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        domain_id: UUID | None,
        name: str,
        version: str,
        capabilities: str,
        token_hash: str,
        status,
    ) -> Agent:
        agent = Agent(
            organization_id=organization_id,
            domain_id=domain_id,
            name=name,
            version=version,
            capabilities=capabilities,
            token_hash=token_hash,
            status=status,
        )

        self.session.add(agent)
        await self.session.flush()

        return agent

    async def get(
        self,
        agent_id: UUID,
        organization_id: UUID | None = None,
    ) -> Agent | None:
        query = select(Agent).where(
            Agent.id == agent_id
        )

        if organization_id is not None:
            query = query.where(
                Agent.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: UUID | None = None,
    ) -> list[Agent]:
        query = select(Agent).order_by(Agent.created_at)

        if organization_id is not None:
            query = query.where(
                Agent.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_heartbeat(
        self,
        agent: Agent,
        *,
        status,
        last_heartbeat_at,
        real_db_reachable: bool,
        honeypot_db_reachable: bool,
        telemetry_events_sent: int,
    ) -> Agent:
        agent.status = status
        agent.last_heartbeat_at = last_heartbeat_at
        agent.real_db_reachable = real_db_reachable
        agent.honeypot_db_reachable = honeypot_db_reachable
        agent.telemetry_events_sent += telemetry_events_sent

        await self.session.flush()

        return agent

    async def delete_all(self) -> None:
        records = await self.list()

        for record in records:
            await self.session.delete(record)

        await self.session.flush()