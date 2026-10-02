from fastapi import APIRouter, HTTPException
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from app.models.control_plane import Organization, OrganizationStatus

from app.auth.registration import RegistrationError, register_company
from app.auth.schemas import (
    AuthenticatedUserResponse,
    CompanyRegistrationRequest,
    CompanyRegistrationResponse,
    LoginRequest,
    LoginResponse,
)
from app.auth.service import AuthenticationError, authenticate_user
from app.database import get_control_db_manager
from app.repositories.user import OrganizationUserRepository


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=CompanyRegistrationResponse,
    status_code=201,
)
async def register(request: CompanyRegistrationRequest):
    db = get_control_db_manager()

    async with db.session_factory() as session:
        try:
            result = await register_company(
                session,
                company_name=request.company_name,
                full_name=request.full_name,
                email=request.email,
                password=request.password,
            )
        except IntegrityError:
            await session.rollback()
            raise HTTPException(409, "Account or organization already exists")
        except RegistrationError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        return CompanyRegistrationResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            user=AuthenticatedUserResponse(
                user_id=result.user_id,
                organization_id=result.organization_id,
                email=result.email,
                full_name=result.full_name,
                role=result.role,
            ),
            organization_name=result.organization_name,
            organization_slug=result.organization_slug,
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    db = get_control_db_manager()

    async with db.session_factory() as session:
        repository = OrganizationUserRepository(session)

        try:
            result = await authenticate_user(
                repository,
                request.email,
                request.password,
            )
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            )

        organization = await session.get(Organization, UUID(result.user.organization_id))
        if organization is None or organization.status != OrganizationStatus.ACTIVE:
            raise HTTPException(401, "Invalid email or password")
        return LoginResponse(
            organization_name=organization.name,
            access_token=result.access_token,
            token_type=result.token_type,
            user=AuthenticatedUserResponse(
                user_id=result.user.user_id,
                organization_id=result.user.organization_id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role.value,
            ),
        )