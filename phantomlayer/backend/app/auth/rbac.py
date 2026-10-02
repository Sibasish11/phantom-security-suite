from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import CurrentUser, get_current_user


def require_role(*allowed_roles: str) -> Callable:
    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency
