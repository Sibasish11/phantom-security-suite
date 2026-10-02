from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.rbac import require_role


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.get("/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
):
    return {
        "user_id": str(current_user.user_id),
        "organization_id": str(current_user.organization_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@router.get("/admin-test")
async def admin_test(
    current_user: CurrentUser = Depends(
        require_role("admin")
    ),
):
    return {
        "message": "Admin access granted",
        "organization_id": str(current_user.organization_id),
        "user_id": str(current_user.user_id),
        "role": current_user.role,
    }