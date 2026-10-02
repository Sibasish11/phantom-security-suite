from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control_plane import OrganizationRole, OrganizationUser


class OrganizationUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        organization_id: UUID,
        email: str,
        password_hash: str,
        full_name: str,
        role: OrganizationRole = OrganizationRole.ANALYST,
    ) -> OrganizationUser:
        user = OrganizationUser(
            organization_id=organization_id,
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            role=role,
            is_active=True,
        )

        self.session.add(user)
        await self.session.flush()

        return user

    async def get(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> OrganizationUser | None:
        query = select(OrganizationUser).where(
            OrganizationUser.id == user_id
        )

        if organization_id is not None:
            query = query.where(
                OrganizationUser.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
        organization_id: UUID | None = None,
    ) -> OrganizationUser | None:
        query = select(OrganizationUser).where(
            OrganizationUser.email == email.strip().lower()
        )

        if organization_id is not None:
            query = query.where(
                OrganizationUser.organization_id == organization_id
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: UUID,
    ) -> list[OrganizationUser]:
        result = await self.session.execute(
            select(OrganizationUser)
            .where(
                OrganizationUser.organization_id == organization_id
            )
            .order_by(OrganizationUser.created_at)
        )

        return list(result.scalars().all())

    async def set_active(
        self,
        user: OrganizationUser,
        is_active: bool,
    ) -> OrganizationUser:
        user.is_active = is_active
        await self.session.flush()
        return user

    async def set_role(
        self,
        user: OrganizationUser,
        role: OrganizationRole,
    ) -> OrganizationUser:
        user.role = role
        await self.session.flush()
        return user
