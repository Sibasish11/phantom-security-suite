from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
import logging
from uuid import uuid4
from app.http_security import limit_auth_requests

from app.config import settings
from app.database import close_db_connections

from app.auth.router import router as auth_router
from app.detection.router import router as detection_router
from app.gateway.router import router as gateway_router
from app.risk.router import router as risk_router
from app.routing.router import router as routing_router
from app.security_logging.router import router as logging_router
from app.honeypot.router import router as honeypot_router
from app.incident_analysis.router import router as incident_router
from app.security_dashboard.router import router as security_dashboard_router
from app.domains.router import router as domains_router
from app.agent.router import router as agent_router
from app.protections.router import router as protections_router
from app.integrations.router import router as integrations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db_connections()


app = FastAPI(
    title="PhantomLayer",
    version="0.1.0",
    lifespan=lifespan,
)


app.middleware("http")(limit_auth_requests)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    reference = uuid4().hex
    # Do not log request bodies, headers, secrets or SQL statement parameters.
    logging.getLogger(__name__).error("request_failed reference=%s error_type=%s", reference, type(exc).__name__)
    return JSONResponse({"detail": "Internal server error", "reference": reference}, status_code=500)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


app.include_router(auth_router)
app.include_router(gateway_router)
app.include_router(detection_router)
app.include_router(risk_router)
app.include_router(routing_router)
app.include_router(logging_router)
app.include_router(honeypot_router)
app.include_router(incident_router)
app.include_router(security_dashboard_router)
app.include_router(domains_router)
app.include_router(agent_router)
app.include_router(protections_router)
app.include_router(integrations_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PhantomLayer",
    }