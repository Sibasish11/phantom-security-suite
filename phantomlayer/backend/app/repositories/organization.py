from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control_plane import Organization, OrganizationStatus


class OrganizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, organization_id: UUID) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(
                Organization.id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(
                Organization.slug == slug
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_system_organization(self) -> Organization:
        """
        Temporary development organization.

        This exists only until authentication/RBAC provides the
        organization context from the authenticated user.
        """
        slug = "system"

        organization = await self.get_by_slug(slug)

        if organization is not None:
            return organization

        organization = Organization(
            name="PhantomLayer System",
            slug=slug,
            status=OrganizationStatus.ACTIVE,
        )

        self.session.add(organization)
        await self.session.flush()

        return organization