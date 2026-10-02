from fastapi import FastAPI

from .config import get_settings
from .protection.database import LocalDatabaseGateway
from .protection.router import create_router
from .protection.service import ProtectionService


def create_app() -> FastAPI:
    settings = get_settings()

    database = LocalDatabaseGateway(
        real_database_url=settings.real_database_url,
        honeypot_database_url=settings.honeypot_database_url,
    )

    protection_service = ProtectionService(
        database=database,
    )

    app = FastAPI(
        title="PhantomLayer Agent",
        version=settings.agent_version,
        description=(
            "Customer-side PhantomLayer protection agent"
        ),
    )

    app.include_router(
        create_router(protection_service)
    )

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "PhantomLayer Agent",
        }

    return app


app = create_app()