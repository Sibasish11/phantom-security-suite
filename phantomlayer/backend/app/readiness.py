"""Read-time readiness: a stored ACTIVE flag is never proof of protection."""
import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.control_plane import Agent, Domain, Organization, OrganizationStatus

HEARTBEAT_TTL_SECONDS = 90


def agent_status(agent, now=None):
    now = now or datetime.now(timezone.utc)
    if not agent.last_heartbeat_at:
        return "pending"
    heartbeat = agent.last_heartbeat_at.replace(tzinfo=timezone.utc) if agent.last_heartbeat_at.tzinfo is None else agent.last_heartbeat_at
    if (now - heartbeat).total_seconds() > HEARTBEAT_TTL_SECONDS:
        return "offline"
    if agent.status.value == "pending":
        return "connecting"
    if agent.status.value == "healthy" and not (agent.real_db_reachable and agent.honeypot_db_reachable):
        return "degraded"
    return agent.status.value


def integration_ready(agent):
    try:
        return json.loads(agent.metadata_json or "{}").get("integration_ready") is True
    except (ValueError, TypeError):
        return False


def protection_readiness(db, protection):
    domain = db.get(Domain, protection.domain_id)
    org = db.get(Organization, protection.organization_id)
    agents = db.execute(select(Agent).where(
        Agent.organization_id == protection.organization_id,
        Agent.domain_id == protection.domain_id,
    )).scalars().all()
    blockers = []
    if not protection.enabled:
        blockers.append("Protection is paused; protected requests fail closed")
    if not org or org.status != OrganizationStatus.ACTIVE:
        blockers.append("Organization is not active")
    if not domain or domain.organization_id != protection.organization_id or not domain.verified:
        blockers.append("Domain ownership is not verified")
    if protection.layer.value not in {"api", "full"}:
        blockers.append("This layer requires its own data-path adapter; PhantomBank implements API protection")
    ready = [a for a in agents if agent_status(a) == "healthy" and integration_ready(a)]
    if not ready:
        if not agents:
            blockers.append("Register and install a customer-side agent")
        else:
            agent = max(agents, key=lambda a: a.last_heartbeat_at or a.registered_at)
            state = agent_status(agent)
            if state != "healthy":
                blockers.append(f"Agent is {state}; a healthy heartbeat within 90 seconds is required")
            if not agent.real_db_reachable:
                blockers.append("Real database is not reachable from the agent")
            if not agent.honeypot_db_reachable:
                blockers.append("Honeypot database is not reachable from the agent")
            if not integration_ready(agent):
                blockers.append("Install the request-routing adapter, not only a health probe")
    if not blockers:
        state = "active"
    elif not protection.enabled:
        state = "paused"
    elif any(agent_status(a) in {"degraded", "offline"} for a in agents):
        state = "degraded"
    else:
        state = "connecting" if agents else "configuring"
    return state, blockers
