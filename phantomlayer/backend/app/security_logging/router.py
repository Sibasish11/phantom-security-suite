from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import CurrentUser, get_current_user
from app.security_logging.schemas import (
    EventsListResponse,
    LoggingHealthResponse,
    SecurityEventResponse,
)
from app.security_logging.service import event_store

router = APIRouter(prefix="/logging", tags=["logging"])


def _event_to_response(event) -> SecurityEventResponse:
    return SecurityEventResponse(
        event_id=str(event.event_id),
        session_id=event.session_id,
        timestamp=event.timestamp.isoformat(),
        event_type=event.event_type.value,
        source=event.source.value,
        original_target=event.original_target,
        final_target=event.final_target,
        operation=event.operation,
        risk_score=event.risk_score,
        severity=event.severity,
        confidence=event.confidence,
        confidence_level=event.confidence_level,
        suspicious=event.suspicious,
        triggered_rules=event.triggered_rules,
        reasons=event.reasons,
        routing_decision=event.routing_decision,
        routing_reason=event.routing_reason,
        gateway_success=event.gateway_success,
        metadata=event.metadata,
    )


@router.get("/health", response_model=LoggingHealthResponse)
async def logging_health(current_user: CurrentUser = Depends(get_current_user)):
    """Return health without disclosing another tenant's event count."""

    from app.security_logging.schemas import EventType

    return LoggingHealthResponse(
        service="PhantomLayer Security Event Logging",
        status="healthy",
        events_stored=event_store.count(current_user.organization_id),
        event_types_supported=[event_type.value for event_type in EventType],
    )


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    session_id: Optional[str] = Query(default=None, description="Filter events by session ID"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List only events owned by the authenticated organization."""

    organization_id = current_user.organization_id
    if session_id:
        events = event_store.get_by_session(
            session_id,
            limit=limit,
            organization_id=organization_id,
        )
        total = len(events)
    else:
        events = event_store.get_recent(limit=limit, organization_id=organization_id)
        total = event_store.count(organization_id)

    return EventsListResponse(
        events=[_event_to_response(event) for event in events],
        total=total,
        limit=limit,
    )


@router.get("/events/{event_id}", response_model=SecurityEventResponse)
async def get_event(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        event_uuid = UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    event = event_store.get_by_id(
        event_uuid,
        organization_id=current_user.organization_id,
    )
    if not event:
        # Do not reveal whether an event exists in another tenant.
        raise HTTPException(status_code=404, detail="Event not found")

    return _event_to_response(event)


# There is intentionally no global clear endpoint.  Event deletion/retention
# must be an explicit tenant-scoped operation, not a process-wide test helper.
