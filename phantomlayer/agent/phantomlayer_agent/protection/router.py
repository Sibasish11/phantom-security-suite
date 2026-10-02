from fastapi import APIRouter, HTTPException

from ..session.manager import attack_session_manager
from .schemas import (
    ProtectionHealthResponse,
    ProtectionRequest,
    ProtectionResponse,
)
from .service import ProtectionService


def create_router(
    service: ProtectionService,
) -> APIRouter:
    router = APIRouter(
        prefix="/protection",
        tags=["protection"],
    )

    @router.get(
        "/health",
        response_model=ProtectionHealthResponse,
    )
    async def health():
        return await service.health()

    @router.post(
        "/query",
        response_model=ProtectionResponse,
    )
    async def query(
        request: ProtectionRequest,
    ):
        response = await service.handle(request)

        if not response.success:
            raise HTTPException(
                status_code=400,
                detail=response.model_dump(),
            )

        return response

    @router.get("/sessions")
    async def sessions():
        return [
            {
                "session_id": session.session_id,
                "created_at": session.created_at,
                "last_seen_at": session.last_seen_at,
                "interaction_count": session.interaction_count,
                "attack_stage": session.attack_stage,
            }
            for session in attack_session_manager.list_sessions()
        ]

    @router.get("/sessions/{session_id}")
    async def session_detail(
        session_id: str,
    ):
        session = attack_session_manager.get_session(
            session_id
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )

        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_seen_at": session.last_seen_at,
            "interaction_count": session.interaction_count,
            "attack_stage": session.attack_stage,
            "interactions": [
                {
                    "step": interaction.step,
                    "operation": interaction.operation,
                    "target": interaction.target,
                    "risk_score": interaction.risk_score,
                    "suspicious": interaction.suspicious,
                    "attack_stage": interaction.attack_stage,
                    "timestamp": interaction.timestamp,
                }
                for interaction in session.interactions
            ],
        }

    return router