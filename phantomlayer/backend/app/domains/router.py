from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.rbac import require_role
from app.domains.schemas import (
    DomainCreateRequest,
    DomainResponse,
    DomainVerificationResponse,
)
from app.domains.service import domain_service


router = APIRouter(
    prefix="/domains",
    tags=["domains"],
)


@router.post(
    "",
    response_model=DomainResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_domain(
    request: DomainCreateRequest,
    current_user: CurrentUser = Depends(
        require_role("admin")
    ),
):
    try:
        return domain_service.create(
            request,
            current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[DomainResponse],
)
async def list_domains(
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    return domain_service.list(
        current_user.organization_id
    )


@router.get(
    "/{domain_id}",
    response_model=DomainResponse,
)
async def get_domain(
    domain_id: UUID,
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    domain = domain_service.get(
        domain_id,
        current_user.organization_id,
    )

    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    return domain


@router.post(
    "/{domain_id}/verify",
    response_model=DomainVerificationResponse,
)
async def verify_domain(
    domain_id: UUID,
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    try:
        return domain_service.verify(
            domain_id,
            current_user.organization_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/{domain_id}/demo-verify",
    response_model=DomainVerificationResponse,
)
async def demo_verify_domain(
    domain_id: UUID,
    current_user: CurrentUser = Depends(
        require_role("admin")
    ),
):
    try:
        return domain_service.demo_verify(
            domain_id,
            current_user.organization_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{domain_id}/renew-challenge", response_model=DomainResponse)
def renew_challenge(domain_id: UUID, current_user: CurrentUser = Depends(require_role("admin"))):
    try:
        return domain_service.renew_challenge(domain_id, current_user.organization_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
