from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.auth.tokens import create_access_token
from app.models.control_plane import (
    Organization,
    OrganizationRole,
    OrganizationStatus,
    OrganizationUser,
)
from app.repositories.user import OrganizationUserRepository


class RegistrationError(Exception):
    pass


@dataclass(frozen=True)
class RegistrationResult:
    access_token: str
    token_type: str
    user_id: str
    organization_id: str
    organization_name: str
    organization_slug: str
    email: str
    full_name: str
    role: str


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")

    if not value:
        raise RegistrationError(
            "Company name must contain letters or numbers"
        )

    return value[:90]


async def register_company(
    session: AsyncSession,
    *,
    company_name: str,
    full_name: str,
    email: str,
    password: str,
) -> RegistrationResult:
    company_name = company_name.strip()
    full_name = full_name.strip()
    email = email.strip().lower()

    if len(company_name) < 2:
        raise RegistrationError("Company name is too short")

    if len(full_name) < 2:
        raise RegistrationError("Full name is too short")

    if len(password) < 8:
        raise RegistrationError(
            "Password must be at least 8 characters"
        )

    slug = _slugify(company_name)

    existing_email = await session.execute(
        select(OrganizationUser).where(
            OrganizationUser.email == email
        )
    )

    if existing_email.scalar_one_or_none() is not None:
        raise RegistrationError(
            "An account with this email already exists"
        )

    existing_name = await session.execute(
        select(Organization).where(
            Organization.name == company_name
        )
    )

    if existing_name.scalar_one_or_none() is not None:
        raise RegistrationError(
            "A company with this name already exists"
        )

    existing_slug = await session.execute(
        select(Organization).where(
            Organization.slug == slug
        )
    )

    if existing_slug.scalar_one_or_none() is not None:
        raise RegistrationError(
            "A company with this name already exists"
        )

    organization = Organization(
        name=company_name,
        slug=slug,
        status=OrganizationStatus.ACTIVE,
    )

    session.add(organization)
    await session.flush()

    repository = OrganizationUserRepository(session)

    user = await repository.create(
        organization_id=organization.id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=OrganizationRole.ADMIN,
    )

    await session.commit()

    token = create_access_token(
        user_id=user.id,
        organization_id=organization.id,
        role=OrganizationRole.ADMIN.value,
    )

    return RegistrationResult(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        organization_id=str(organization.id),
        organization_name=organization.name,
        organization_slug=organization.slug,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
    )