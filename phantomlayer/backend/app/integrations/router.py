"""Decision-only contract for authenticated customer-side proxies.

No customer SQL, database connection strings, records, credentials or raw HTTP
payloads cross this boundary. Agent identity supplies organization/domain;
operation names are a closed allowlist. AI never participates in routing.
"""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import func, select, text

from app.database import get_sync_control_db_manager
from app.honeypot.service import honeypot_session_manager, STAGE_RANKS
from app.honeypot.schemas import AttackStage
from app.incident_analysis.service import incident_service
from app.integrations.models import IntegrationDecisionRecord
from app.integrations.schemas import BankDecisionRequest, BankDecisionResponse, BankObserveRequest, BankObserveResponse
from app.models.control_plane import (Agent, Domain, Organization, OrganizationStatus,
                                     AttackSession, AttackSessionInteraction,
                                     ProtectionConfiguration, ProtectionLayer)
from app.risk.engine import risk_scoring_engine
from app.risk.schemas import RiskAssessmentRequest
from app.security_context import TrustedContext, use_context
from app.security_logging.schemas import EventType, EventSource, SecurityEvent
from app.security_logging.service import EventStore

router = APIRouter(prefix="/integrations/bank", tags=["integrations"])
SENSITIVE = {"get_customers", "enumerate_customers", "enumerate_accounts", "enumerate_transactions", "probe_admin", "credential_probe"}
RECON = {"list_tables", "enumerate_api"}


@router.get("/identity")
def integration_identity(request: Request, x_agent_id: str | None = Header(default=None),
                         x_agent_token: str | None = Header(default=None)):
    context = _authenticate_agent(x_agent_id, x_agent_token, request)
    with get_sync_control_db_manager().session() as db:
        domain = db.get(Domain, context.domain_id)
        return {"agent_id": str(context.agent_id), "organization_id": str(context.organization_id),
                "domain_id": str(context.domain_id), "domain": domain.domain}


def _authenticate_agent(agent_id_header, agent_token, request: Request) -> TrustedContext:
    invalid = HTTPException(401, "Invalid integration credentials", headers={"WWW-Authenticate": "Agent"})
    if not agent_id_header or not agent_token:
        raise invalid
    try:
        agent_id = UUID(agent_id_header)
    except ValueError:
        raise invalid
    with get_sync_control_db_manager().session() as db:
        agent = db.get(Agent, agent_id)
        if agent is None or not secrets.compare_digest(
            agent.token_hash, hashlib.sha256(agent_token.encode()).hexdigest()
        ):
            raise invalid
        domain = db.get(Domain, agent.domain_id) if agent.domain_id else None
        organization = db.get(Organization, agent.organization_id)
        if (domain is None or not domain.verified or domain.organization_id != agent.organization_id
                or organization is None or organization.status != OrganizationStatus.ACTIVE):
            raise invalid
        protection = db.execute(select(ProtectionConfiguration.id).where(
            ProtectionConfiguration.organization_id == agent.organization_id,
            ProtectionConfiguration.domain_id == domain.id,
            ProtectionConfiguration.enabled.is_(True),
            ProtectionConfiguration.layer.in_([ProtectionLayer.API, ProtectionLayer.FULL]),
        ).limit(1)).scalar_one_or_none()
        if protection is None:
            raise HTTPException(503, "No enabled API protection for this agent")
        return TrustedContext(agent.organization_id, domain.id, agent.id,
                              request.client.host if request.client else None)


def _internal_session_id(agent_id: UUID, session_id: str) -> str:
    return f"bank:{agent_id}:{hashlib.sha256(session_id.encode()).hexdigest()[:32]}"


def _stage(operation: str, previous: str, count: int) -> str:
    stage = previous if previous != "normal" else "reconnaissance"
    if operation == "credential_probe":
        candidate = "credential_access"
    elif operation in SENSITIVE and count >= 2 and previous in {'enumeration', 'exploration', 'exfiltration'}:
        candidate = "exfiltration"
    elif operation in SENSITIVE:
        candidate = "enumeration"
    else:
        candidate = "reconnaissance"
    ranks = {item.value: rank for item, rank in STAGE_RANKS.items()}
    return candidate if ranks.get(candidate, 0) >= ranks.get(stage, 0) else stage


def _add_event(db, context, event_type, session_id, operation, score, target, **kwargs):
    event = SecurityEvent(
        organization_id=context.organization_id, domain_id=context.domain_id,
        agent_id=context.agent_id, session_id=session_id,
        event_type=event_type, source=EventSource.ROUTING,
        operation=operation, original_target="real", final_target=target,
        risk_score=score, severity=risk_scoring_engine._calculate_severity(score).value,
        suspicious=target == "honeypot", **kwargs,
    )
    db.add(EventStore._to_record(event))


@router.post("/decision", response_model=BankDecisionResponse)
def decide_bank_request(body: BankDecisionRequest, request: Request,
                        x_agent_id: str | None = Header(default=None),
                        x_agent_token: str | None = Header(default=None)):
    context = _authenticate_agent(x_agent_id, x_agent_token, request)
    sid = _internal_session_id(context.agent_id, body.session_id)
    with get_sync_control_db_manager().session() as db:
        # Transaction-level per-session lock: risk/pinning works across workers,
        # restarts, and simultaneous requests before observation has arrived.
        lock_key = int.from_bytes(hashlib.sha256(sid.encode()).digest()[:8], "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        history = db.execute(select(func.max(IntegrationDecisionRecord.risk_score),
            func.count(IntegrationDecisionRecord.decision_id)).where(
                IntegrationDecisionRecord.session_id == sid,
                IntegrationDecisionRecord.agent_id == context.agent_id,
                IntegrationDecisionRecord.target == "honeypot",
            )).one()
        previous_risk, suspicious_count = history
        assessment = risk_scoring_engine.assess(RiskAssessmentRequest(
            target="real", operation=body.operation, session_history_count=suspicious_count,
        ))
        suspicious_operation = body.operation in SENSITIVE | RECON
        target = "honeypot" if suspicious_count or suspicious_operation else "real"
        score = max(assessment.risk_score, previous_risk or 0)
        if suspicious_count and suspicious_operation:
            score = min(100, max(score, (previous_risk or 0) + 10))
        attack = db.execute(select(AttackSession).where(AttackSession.session_id == sid)).scalar_one_or_none()
        stage = "normal"
        if target == "honeypot":
            if attack is None:
                attack = AttackSession(session_id=sid, organization_id=context.organization_id,
                    domain_id=context.domain_id, client_ip=body.client_ip or context.client_ip,
                    metadata_json=json.dumps({"agent_id": str(context.agent_id), "source": "bank_proxy"}))
                db.add(attack)
                db.flush()
            if attack.organization_id != context.organization_id or attack.domain_id != context.domain_id:
                raise HTTPException(404, "Integration session not found")
            stage = _stage(body.operation, attack.attack_stage, suspicious_count)
        rules = [rule.model_dump(mode="json") for rule in assessment.triggered_rules]
        reason = "Session pinned to deception" if suspicious_count else "Deterministic operation policy"
        decision = IntegrationDecisionRecord(decision_id=uuid4(), organization_id=context.organization_id,
            agent_id=context.agent_id, session_id=sid, operation=body.operation,
            target=target, risk_score=score)
        db.add(decision)
        telemetry_sid = sid if target == "honeypot" else None
        _add_event(db, context, EventType.REQUEST_ANALYZED, telemetry_sid, body.operation, score, target,
            triggered_rules=rules, reasons=assessment.reasons, confidence=assessment.confidence,
            confidence_level=assessment.confidence_level.value,
            metadata={"decision_id": str(decision.decision_id), "attack_stage": stage})
        _add_event(db, context, EventType.ROUTING_DECISION, telemetry_sid, body.operation, score, target,
            routing_decision=f"routed_to_{target}", routing_reason=reason)
        if suspicious_operation:
            _add_event(db, context, EventType.SUSPICIOUS_REQUEST, telemetry_sid, body.operation, score, target,
                       triggered_rules=rules, reasons=assessment.reasons)
        db.commit()
        return BankDecisionResponse(decision_id=decision.decision_id, session_id=sid,
            target=target, risk_score=score, attack_stage=stage,
            triggered_rules=[rule.rule.value for rule in assessment.triggered_rules])


@router.post("/observe", response_model=BankObserveResponse)
def observe_bank_request(body: BankObserveRequest, request: Request,
                         x_agent_id: str | None = Header(default=None),
                         x_agent_token: str | None = Header(default=None)):
    context = _authenticate_agent(x_agent_id, x_agent_token, request)
    with get_sync_control_db_manager().session() as db:
        decision = db.execute(select(IntegrationDecisionRecord).where(
            IntegrationDecisionRecord.decision_id == body.decision_id,
            IntegrationDecisionRecord.organization_id == context.organization_id,
            IntegrationDecisionRecord.agent_id == context.agent_id,
        ).with_for_update()).scalar_one_or_none()
        if decision is None or (body.session_id and body.session_id != decision.session_id):
            raise HTTPException(404, "Integration decision not found")
        if body.operation is not None and body.operation != decision.operation:
            raise HTTPException(422, "Observation operation does not match decision")
        sid, target = decision.session_id, decision.target
        if not decision.consumed:
            counts = body.exposed_entities if target == "honeypot" and body.success else {}
            if target == "real" and body.exposed_entities:
                raise HTTPException(422, "Real data cannot be reported as synthetic exposure")
            if target == "honeypot":
                attack = db.execute(select(AttackSession).where(
                    AttackSession.session_id == sid,
                    AttackSession.organization_id == context.organization_id,
                ).with_for_update()).scalar_one_or_none()
                if attack is None:
                    raise HTTPException(404, "Integration session not found")
                stage = _stage(decision.operation, attack.attack_stage, attack.interaction_count)
                attack.interaction_count += 1
                attack.attack_stage = stage
                attack.last_active_at = datetime.now(timezone.utc)
                entities = json.loads(attack.exposed_entities_json or "{}")
                totals = entities.setdefault("external_entity_counts", {})
                for entity, count in counts.items():
                    totals[entity] = totals.get(entity, 0) + count
                attack.exposed_entities_json = json.dumps(entities)
                db.add(AttackSessionInteraction(session_id=attack.id, event_id=decision.decision_id,
                    step=attack.interaction_count, operation=decision.operation, risk_score=decision.risk_score,
                    attack_stage=stage, success=body.success, entities_exposed_json=json.dumps(counts),
                    parameters_json="{}", details="Synthetic entity observations, counts only"))
                _add_event(db, context, EventType.HONEYPOT_INTERACTION, sid, decision.operation,
                    decision.risk_score, target, gateway_success=body.success,
                    metadata={"decision_id": str(decision.decision_id), "attack_stage": stage,
                              "result_count": body.response_count, "exposed_entities": counts})
            decision.consumed = True
            db.commit()
    if target == "honeypot":
        # Facts can be re-projected on a retry even if report creation failed
        # after the atomic observation commit. No duplicate interaction/event.
        with honeypot_session_manager._lock:
            honeypot_session_manager._sessions.pop(sid, None)
        with use_context(context):
            incident_service.ensure_incident(sid)
    return BankObserveResponse(accepted=True, session_id=sid, target=target)
