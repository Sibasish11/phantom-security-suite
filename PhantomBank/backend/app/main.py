from __future__ import annotations

from contextlib import asynccontextmanager, suppress
import asyncio
import logging
import httpx
from decimal import Decimal, InvalidOperation
import ipaddress
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
import secrets
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from .auth import Session, sessions
from .config import settings
from .db import Database
from .gateway import (
    GatewayConflict,
    GatewayDatabaseError,
    GatewayError,
    GatewayResult,
    GatewayService,
    PhantomLayerDecisionClient,
    ProtectionUnavailable,
    SensitiveOperationDenied,
)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=200)


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_account_id: str = Field(min_length=1, max_length=100)
    beneficiary_id: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000"), decimal_places=2)
    reference: str = Field(default="Transfer", min_length=1, max_length=120)


real_database = Database(settings.real_database_url, "real")
honeypot_database = Database(settings.honeypot_database_url, "honeypot")
gateway = GatewayService(
    {"real": real_database, "honeypot": honeypot_database},
    PhantomLayerDecisionClient(),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Provisioning is separate from request routing. Runtime requests never connect to
    # either database without first receiving a PhantomLayer decision in GatewayService.
    real_database.init_schema()
    honeypot_database.init_schema()
    task = asyncio.create_task(agent_heartbeat())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def agent_heartbeat():
    """Outbound health metadata only; database rows never leave the bank."""
    if not settings.agent_id or not settings.agent_token:
        return
    from uuid import UUID
    try:
        UUID(settings.agent_id)
    except ValueError:
        return
    def reachable(database):
        try:
            database.fetchone('SELECT 1 AS ok')
            return True
        except Exception:
            return False
    while True:
        try:
            real_ok, honey_ok = await asyncio.gather(
                asyncio.to_thread(reachable, real_database),
                asyncio.to_thread(reachable, honeypot_database),
            )
            async with httpx.AsyncClient(timeout=4) as client:
                response = await client.post(f'{settings.phantomlayer_url}/agents/{settings.agent_id}/heartbeat',
                    headers={'X-Agent-Token': settings.agent_token}, json={
                        'status': 'healthy' if real_ok and honey_ok else 'degraded',
                        'real_db_reachable': real_ok, 'honeypot_db_reachable': honey_ok,
                        'telemetry_events_sent': 0,
                    })
                response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            logging.getLogger(__name__).warning('Agent heartbeat unavailable; protected requests remain fail-closed')
        await asyncio.sleep(30)


app = FastAPI(title="PhantomBank", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Idempotency-Key"],
)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="A trusted browser origin is required.")


def current_session(request: Request) -> Session:
    session = sessions.get(request.cookies.get("bank_session"))
    if not session:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return session


def write_session(request: Request) -> Session:
    check_origin(request)
    session = current_session(request)
    csrf = request.headers.get("x-csrf-token")
    if not csrf or csrf != session.csrf_token:
        raise HTTPException(status_code=403, detail="The request could not be verified.")
    return session


def public_result(result: GatewayResult) -> Any:
    return result.data


def public_security_result(operation: str, result: GatewayResult) -> Any:
    """Return the believable decoy surface without routing metadata.

    These operations are allowed only after PhantomLayer has selected the
    honeypot. The returned records are synthetic by construction; destination,
    risk, rules, and customer identity are never disclosed to the caller.
    """
    if operation in {"get_customers", "enumerate_accounts", "enumerate_transactions"}:
        records = result.data if isinstance(result.data, list) else []
        # Marker columns exist only for defender-side database comparison.
        public_records = [{key: value for key, value in row.items()
                           if key != "customer_marker"} for row in records]
        return {"count": len(public_records), "records": public_records}
    return result.data


def set_session_cookies(response: Response, session: Session) -> None:
    response.set_cookie(
        "bank_session",
        sessions.signed_cookie(session.session_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "bank_csrf",
        session.csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie("bank_session", path="/")
    response.delete_cookie("bank_csrf", path="/")


@app.exception_handler(GatewayError)
async def gateway_error_handler(_: Request, exc: GatewayError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.public_message},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "PhantomBank"}


_login_attempts = OrderedDict()
_login_lock = Lock()


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    check_origin(request)
    with _login_lock:
        now = monotonic()
        peer = _client_ip(request)
        bucket = _login_attempts.setdefault(peer, deque())
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 60:
            raise HTTPException(429, 'Too many sign-in attempts. Please wait.', headers={'Retry-After':'60'})
        bucket.append(now)
        _login_attempts.move_to_end(peer)
        while len(_login_attempts) > 4096:
            _login_attempts.popitem(last=False)
    result = gateway.login(
        email=payload.email,
        password=payload.password,
        client_ip=_client_ip(request),
    )
    if not result.success or not result.data:
        raise HTTPException(status_code=401, detail="Email or password not recognised.")
    customer = result.data
    session = sessions.create(
        customer_id=customer["id"],
        full_name=customer["full_name"],
        email=customer["email"],
        target=result.target,
        phantom_session_id=(
            result.decision.request_session_id or result.decision.session_id
        ),
    )
    set_session_cookies(response, session)
    return {"user": {"full_name": session.full_name, "email": session.email}}


@app.get("/api/auth/session")
def session_info(request: Request) -> dict[str, Any]:
    session = current_session(request)
    result = gateway.execute(
        session=session, operation="get_profile", client_ip=_client_ip(request)
    )
    profile = public_result(result) or {}
    return {
        "user": {
            "full_name": profile.get("full_name", session.full_name),
            "email": profile.get("email", session.email),
        }
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, _: Session = Depends(write_session)):
    sessions.revoke(request.cookies.get("bank_session"))
    clear_session_cookies(response)
    return {"ok": True}


@app.get("/api/accounts")
def accounts(request: Request, session: Session = Depends(current_session)):
    return {"accounts": public_result(gateway.execute(session=session, operation="get_accounts", client_ip=_client_ip(request)))}


@app.get("/api/balance")
def balance(request: Request, session: Session = Depends(current_session)):
    return public_result(gateway.execute(session=session, operation="get_balance", client_ip=_client_ip(request)))


@app.get("/api/transactions")
def transactions(request: Request, limit: int = 50, session: Session = Depends(current_session)):
    return {"transactions": public_result(gateway.execute(session=session, operation="get_transactions", payload={"limit": limit}, client_ip=_client_ip(request)))}


@app.get("/api/beneficiaries")
def beneficiaries(request: Request, session: Session = Depends(current_session)):
    return {"beneficiaries": public_result(gateway.execute(session=session, operation="get_beneficiaries", client_ip=_client_ip(request)))}


@app.get("/api/cards")
def cards(request: Request, session: Session = Depends(current_session)):
    return {"cards": public_result(gateway.execute(session=session, operation="get_cards", client_ip=_client_ip(request)))}


@app.get("/api/profile")
def profile(request: Request, session: Session = Depends(current_session)):
    return {"profile": public_result(gateway.execute(session=session, operation="get_profile", client_ip=_client_ip(request)))}


@app.post("/api/transfers")
def create_transfer(
    payload: TransferRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    session: Session = Depends(write_session),
):
    if not idempotency_key or len(idempotency_key) > 120:
        raise HTTPException(status_code=400, detail="An idempotency key is required.")
    try:
        amount_cents = int((payload.amount * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Enter a valid amount.") from exc
    result = gateway.execute(
        session=session,
        operation="create_transfer",
        payload={
            "source_account_id": payload.source_account_id,
            "beneficiary_id": payload.beneficiary_id,
            "amount_cents": amount_cents,
            "reference": payload.reference,
            "idempotency_key": idempotency_key,
        },
        client_ip=_client_ip(request),
    )
    return {"transfer": public_result(result)}


SECURITY_ROUTES = {
    "list-tables": "list_tables",
    "enumerate-api": "enumerate_api",
    "customers": "get_customers",
    "accounts": "enumerate_accounts",
    "transactions": "enumerate_transactions",
    "probe-admin": "probe_admin",
    "credential-probe": "credential_probe",
}


@app.get("/api/security/{operation}")
def security_operation(operation: str, request: Request, session: Session = Depends(current_session)):
    mapped = SECURITY_ROUTES.get(operation)
    if not mapped:
        raise HTTPException(status_code=404, detail="Not found")
    result = gateway.execute(session=session, operation=mapped, client_ip=_client_ip(request))
    return {"result": public_security_result(mapped, result)}


@app.get("/internal/defender-evidence")
def defender_evidence(request: Request, limit: int = 50, x_demo_runner: str | None = Header(default=None)):
    """Local-only defender view; intentionally not part of the customer API."""
    if (not settings.demo_mode or not settings.defender_evidence_token or not x_demo_runner
            or not secrets.compare_digest(x_demo_runner, settings.defender_evidence_token)):
        raise HTTPException(status_code=404, detail="Not found")
    remote = _client_ip(request)
    try:
        local_request = remote in {"127.0.0.1", "::1", "localhost"} or ipaddress.ip_address(remote or "").is_private
    except ValueError:
        local_request = False
    if not local_request:
        raise HTTPException(status_code=403, detail="Local evidence only.")
    return {"evidence": gateway.evidence(limit)}
