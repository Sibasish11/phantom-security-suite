from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)

from app.agent.schemas import (
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentResponse,
    AgentTokenRotationResponse,
)
from app.agent.service import agent_registry
from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.rbac import require_role
from app.telemetry import (
    AgentTelemetryBatch,
    AgentTelemetryResponse,
)
from app.telemetry.service import (
    TelemetryAuthenticationError,
    TelemetryValidationError,
    telemetry_service,
)


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
)


@router.post(
    "/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(
    request: AgentRegistrationRequest,
    current_user: CurrentUser = Depends(
        require_role("admin")
    ),
):
    try:
        agent, token = agent_registry.register(
            request,
            current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return AgentRegistrationResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        status=agent.status,
        registration_token=token,
    )


@router.get(
    "",
    response_model=list[AgentResponse],
)
async def list_agents(
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    return agent_registry.list(
        current_user.organization_id
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
)
async def get_agent(
    agent_id: UUID,
    current_user: CurrentUser = Depends(
        get_current_user
    ),
):
    agent = agent_registry.get(
        agent_id,
        current_user.organization_id,
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return agent


@router.post(
    "/{agent_id}/rotate-token",
    response_model=AgentTokenRotationResponse,
)
async def rotate_agent_token(
    agent_id: UUID,
    current_user: CurrentUser = Depends(
        require_role("admin")
    ),
):
    result = agent_registry.rotate_token(
        agent_id,
        current_user.organization_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    agent, token = result

    return AgentTokenRotationResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        status=agent.status,
        registration_token=token,
    )


@router.post(
    "/{agent_id}/heartbeat",
    response_model=AgentResponse,
)
async def agent_heartbeat(
    agent_id: UUID,
    request: AgentHeartbeatRequest,
    x_agent_token: str | None = Header(
        default=None,
    ),
):
    if not x_agent_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent token",
        )

    agent = agent_registry.heartbeat(
        agent_id,
        x_agent_token,
        request,
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials",
        )

    return agent


@router.post(
    "/telemetry",
    response_model=AgentTelemetryResponse,
)
async def ingest_agent_telemetry(
    batch: AgentTelemetryBatch,
    x_agent_token: str | None = Header(
        default=None,
    ),
):
    if not x_agent_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent token",
        )

    try:
        return telemetry_service.ingest(
            batch,
            x_agent_token,
        )

    except TelemetryAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except TelemetryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc