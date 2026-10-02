from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.config import settings


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.auth_access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.auth_secret_key,
        algorithms=[settings.auth_algorithm],
        options={"require": ["sub", "org", "role", "iat", "exp"]},
    )
