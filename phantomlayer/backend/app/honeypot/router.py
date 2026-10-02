from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.rbac import require_role
from app.database import get_sync_control_db_manager
from app.honeypot.schemas import (
    AttackStage,
    HoneypotHealthResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummaryResponse,
)
from app.honeypot.service import honeypot_session_manager
from app.models.control_plane import AttackSession

router = APIRouter(prefix="/honeypot", tags=["honeypot"])


def _session_to_summary(session) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        last_active_at=session.last_active_at.isoformat(),
        client_ip=session.client_ip,
        user_agent=session.user_agent,
        attack_stage=session.attack_stage,
        interaction_count=session.interaction_count,
        exposed_entities_count={
            "customers": len(session.exposed_entities.customer_ids),
            "orders": len(session.exposed_entities.order_ids),
            "users": len(session.exposed_entities.user_ids),
        },
    )


def _owned_session_ids(organization_id):
    try:
        db = get_sync_control_db_manager()
        with db.session() as session:
            return set(
                session.execute(
                    select(AttackSession.session_id).where(
                        AttackSession.organization_id == organization_id,
                    )
                ).scalars().all()
            )
    except SQLAlchemyError:
        return set()


def _owned_session(session_id: str, organization_id):
    try:
        db = get_sync_control_db_manager()
        with db.session() as session:
            return session.execute(
                select(AttackSession.id).where(
                    AttackSession.session_id == session_id,
                    AttackSession.organization_id == organization_id,
                )
            ).scalar_one_or_none() is not None
    except SQLAlchemyError:
        return False


@router.get("/health", response_model=HoneypotHealthResponse)
async def honeypot_health(current_user: CurrentUser = Depends(get_current_user)):
    return HoneypotHealthResponse(
        service="PhantomLayer Interactive Honeypot",
        status="healthy",
        active_sessions=len(_owned_session_ids(current_user.organization_id)),
        attack_stages_supported=[stage.value for stage in AttackStage],
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: CurrentUser = Depends(get_current_user)):
    owned_ids = _owned_session_ids(current_user.organization_id)
    sessions = [
        session
        for session in honeypot_session_manager.list_sessions(
            current_user.organization_id,
        )
        if session.session_id in owned_ids
    ]
    return SessionListResponse(
        sessions=[_session_to_summary(session) for session in sessions],
        total=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    if not _owned_session(session_id, current_user.organization_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = honeypot_session_manager.get_session(
        session_id,
        organization_id=current_user.organization_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        last_active_at=session.last_active_at.isoformat(),
        client_ip=session.client_ip,
        user_agent=session.user_agent,
        attack_stage=session.attack_stage,
        interaction_count=session.interaction_count,
        interactions=session.interactions,
        exposed_entities=session.exposed_entities,
        metadata=session.metadata,
    )


@router.delete("/sessions/{session_id}", dependencies=[Depends(require_role("admin"))])
async def delete_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    if not _owned_session(session_id, current_user.organization_id):
        raise HTTPException(status_code=404, detail="Session not found")

    deleted = honeypot_session_manager.delete_session(
        session_id,
        organization_id=current_user.organization_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": f"Session {session_id} deleted", "session_id": session_id}
