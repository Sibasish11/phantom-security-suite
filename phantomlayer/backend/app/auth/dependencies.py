import jwt
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.tokens import decode_access_token
from app.database import get_sync_control_db_manager
from app.models.control_plane import OrganizationUser, Organization, OrganizationStatus
from sqlalchemy import select


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: str


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> CurrentUser:
    if credentials is None:
        raise _authentication_error()

    if credentials.scheme.lower() != "bearer":
        raise _authentication_error()

    try:
        payload = decode_access_token(credentials.credentials)

        user_id = UUID(payload["sub"])
        organization_id = UUID(payload["org"])
        role = str(payload["role"])

    except (KeyError, TypeError, ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise _authentication_error()

    db = get_sync_control_db_manager()

    with db.session() as session:
        user = session.execute(
            select(OrganizationUser).where(
                OrganizationUser.id == user_id,
                OrganizationUser.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if user is None:
            raise _authentication_error()

        organization = session.get(Organization, user.organization_id)
        if (not user.is_active or organization is None
                or organization.status != OrganizationStatus.ACTIVE):
            raise _authentication_error()

        if user.role.value != role:
            raise _authentication_error()

        return CurrentUser(
            user_id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
        )
