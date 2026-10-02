import logging

from fastapi import APIRouter, Depends, HTTPException
from app.gateway.context import gateway_identity

from app.gateway.schemas import (
    GatewayHealthResponse,
    GatewayRequest,
    GatewayResponse,
)
from app.gateway.service import gateway_service
from app.routing.schemas import RoutingRequest, RoutingResponse
from app.routing.service import automatic_routing_service

router = APIRouter(prefix="/gateway", tags=["gateway"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=GatewayHealthResponse)
async def gateway_health():
    health = await gateway_service.health_check()

    return GatewayHealthResponse(
        gateway="PhantomLayer Gateway",
        status=(
            "healthy"
            if all(value == "healthy" for value in health.values())
            else "degraded"
        ),
        real_database=health["real_database"],
        honeypot_database=health["honeypot_database"],
    )


@router.post("/query", response_model=RoutingResponse, dependencies=[Depends(gateway_identity)])
async def gateway_query(request: GatewayRequest):
    """
    Main PhantomLayer gateway entry point.

    Every request goes through:

        Gateway
            ↓
        Detection
            ↓
        Risk Scoring
            ↓
        Automatic Routing
            ↓
        REAL / HONEYPOT
            ↓
        Session Tracking
    """

    routing_request = RoutingRequest(
        target=request.target.value,
        operation=request.operation.value,
        parameters=request.parameters or {},
        session_id=request.session_id,
    )

    try:
        return await automatic_routing_service.route(routing_request)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Gateway routing failed")
        raise HTTPException(
            status_code=500,
            detail="Gateway routing failed",
        ) from exc