import logging

from fastapi import APIRouter, Depends, HTTPException
from app.gateway.context import gateway_identity

from app.routing.service import automatic_routing_service
from app.routing.schemas import RoutingHealthResponse, RoutingRequest, RoutingResponse

router = APIRouter(prefix="/routing", tags=["routing"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=RoutingHealthResponse)
async def routing_health():
    health = await automatic_routing_service.health_check()
    return RoutingHealthResponse(**health)


@router.post("/route", response_model=RoutingResponse, dependencies=[Depends(gateway_identity)])
async def route_request(request: RoutingRequest):
    try:
        result = await automatic_routing_service.route(request)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        logger.exception("Routing failed")
        raise HTTPException(status_code=500, detail="Routing failed") from exc