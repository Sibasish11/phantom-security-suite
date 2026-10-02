"""Authenticated boundary for the legacy structured demonstration gateway."""
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_sync_control_db_manager
from app.models.control_plane import Domain
from app.security_context import TrustedContext, use_context


async def gateway_identity(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    x_domain_id: UUID | None = Header(default=None),
):
    # These routes execute the repository's shared synthetic catalog, not a
    # tenant production database. Production integrations use agent credentials
    # and the bank decision API, which never connects to customer databases.
    if not settings.demo_mode:
        raise HTTPException(403, "Structured demo gateway is disabled")
    with get_sync_control_db_manager().session() as db:
        query = select(Domain).where(
            Domain.organization_id == user.organization_id,
            Domain.verified.is_(True),
        )
        if x_domain_id:
            query = query.where(Domain.id == x_domain_id)
        domains = db.execute(query.order_by(Domain.created_at).limit(2)).scalars().all()
        if not domains:
            raise HTTPException(404, "Verified domain not found")
        if not x_domain_id and len(domains) != 1:
            raise HTTPException(422, "Select an owned verified domain with X-Domain-ID")
        context = TrustedContext(
            organization_id=user.organization_id,
            domain_id=domains[0].id,
            client_ip=request.client.host if request.client else None,
        )
    with use_context(context):
        yield context
