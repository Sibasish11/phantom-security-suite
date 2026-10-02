from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.rbac import require_role
from app.protections.schemas import (
    ProtectionCreateRequest,
    ProtectionResponse,
    ProtectionUpdateRequest,
)
from app.protections.service import protection_service


router = APIRouter(
    prefix="/protections",
    tags=["protections"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=ProtectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_protection(
    request: ProtectionCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return protection_service.create(
            request,
            current_user.organization_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[ProtectionResponse],
)
async def list_protections(
    current_user: CurrentUser = Depends(get_current_user),
):
    return protection_service.list(
        current_user.organization_id,
    )


@router.get(
    "/{protection_id}",
    response_model=ProtectionResponse,
)
async def get_protection(
    protection_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    record = protection_service.get(
        protection_id,
        current_user.organization_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protection configuration not found",
        )

    return record


@router.patch(
    "/{protection_id}",
    response_model=ProtectionResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_protection(
    protection_id: UUID,
    request: ProtectionUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return protection_service.update(
            protection_id,
            request,
            current_user.organization_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/{protection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_protection(
    protection_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        protection_service.delete(
            protection_id,
            current_user.organization_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return None