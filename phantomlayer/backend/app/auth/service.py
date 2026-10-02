from dataclasses import dataclass

from app.auth.security import verify_password
from app.auth.tokens import create_access_token
from app.models.control_plane import OrganizationRole
from app.repositories.user import OrganizationUserRepository


class AuthenticationError(Exception):
    """Raised when authentication fails."""


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    organization_id: str
    email: str
    full_name: str
    role: OrganizationRole


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str
    user: AuthenticatedUser


async def authenticate_user(
    repository: OrganizationUserRepository,
    email: str,
    password: str,
) -> LoginResult:
    user = await repository.get_by_email(email)

    if user is None:
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    authenticated_user = AuthenticatedUser(
        user_id=str(user.id),
        organization_id=str(user.organization_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )

    access_token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role.value,
    )

    return LoginResult(
        access_token=access_token,
        token_type="bearer",
        user=authenticated_user,
    )
