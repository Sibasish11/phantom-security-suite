from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control_plane import Domain


class DomainRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        domain: str,
        verification_record_name: str,
        verification_token: str,
        token_expires_at,
        verified: bool = False,
    ) -> Domain:
        record = Domain(
            organization_id=organization_id,
            domain=domain,
            verification_record_name=verification_record_name,
            verification_token=verification_token,
            token_expires_at=token_expires_at,
            verified=verified,
        )

        self.session.add(record)
        await self.session.flush()

        return record

    async def list(
        self,
        organization_id: UUID | None = None,
    ) -> list[Domain]:
        query = select(Domain).order_by(Domain.created_at)

        if organization_id is not None:
            query = query.where(
                Domain.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get(
        self,
        domain_id: UUID,
        organization_id: UUID | None = None,
    ) -> Domain | None:
        query = select(Domain).where(
            Domain.id == domain_id
        )

        if organization_id is not None:
            query = query.where(
                Domain.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_domain(
        self,
        domain: str,
        organization_id: UUID | None = None,
    ) -> Domain | None:
        query = select(Domain).where(
            Domain.domain == domain
        )

        if organization_id is not None:
            query = query.where(
                Domain.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def mark_verified(
        self,
        record: Domain,
        verified_at,
    ) -> Domain:
        record.verified = True
        record.verified_at = verified_at

        await self.session.flush()

        return record

    async def delete_all(self) -> None:
        records = await self.list()

        for record in records:
            await self.session.delete(record)

        await self.session.flush()