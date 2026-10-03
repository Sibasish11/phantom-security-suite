from collections import Counter
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_sync_control_db_manager
from app.honeypot.service import honeypot_session_manager
from app.incident_analysis.service import IncidentService, incident_service
from app.models.control_plane import AttackSession, Organization, Domain
from app.security_logging.router import _event_to_response
from app.security_logging.schemas import EventType
from app.security_logging.service import event_store


router = APIRouter(
    tags=["security-dashboard"],
    dependencies=[Depends(get_current_user)],
)


def _severity(score: int) -> str:
    if score >= 76:
        return "CRITICAL"
    if score >= 51:
        return "HIGH"
    if score >= 31:
        return "MEDIUM"
    return "LOW"


def _incident_summary(report):
    payload = report.sanitized_payload
    return {
        "incident_id": str(report.report_id),
        "session_id": report.session_id,
        "status": report.status.value,
        "created_at": report.created_at.isoformat(),
        "risk_score": payload.max_risk_score if payload else 0,
        "severity": _severity(payload.max_risk_score if payload else 0),
        "attack_stage": payload.final_attack_stage if payload else None,
        "interaction_count": payload.total_interactions if payload else 0,
    }


def _find_report(incident_id: str, organization_id):
    try:
        report = incident_service.get_report_by_id(UUID(incident_id), organization_id)
    except ValueError:
        # Backwards-compatible session lookup, still tenant-scoped in service.
        report = incident_service.get_report(incident_id, organization_id)

    if report is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return report


def _owned_session_records(organization_id):
    """Read only session identifiers owned by this organization.

    The honeypot manager is also used by the gateway and intentionally exposes
    an unscoped process cache.  Dashboard statistics must establish ownership
    in SQL before consulting that cache.
    """

    try:
        db = get_sync_control_db_manager()
        with db.session() as session:
            return session.execute(
                select(AttackSession).where(
                    AttackSession.organization_id == organization_id,
                )
            ).scalars().all()
    except SQLAlchemyError:
        return []


@router.get("/organizations")
def organization_directory(current_user: CurrentUser = Depends(get_current_user)):
    # Organization-admin is not a platform-administrator role. Never expose a
    # cross-tenant directory just because a registered user has role=admin.
    with get_sync_control_db_manager().session() as db:
        organization = db.get(Organization, current_user.organization_id)
        if organization is None:
            raise HTTPException(404, "Organization not found")
        return [{"id": str(organization.id), "name": organization.name,
                 "slug": organization.slug, "status": organization.status.value,
                 "created_at": organization.created_at.isoformat()}]


@router.get("/incidents")
async def list_incidents(
    limit: int = Query(100, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    reports = sorted(
        incident_service.list_reports(current_user.organization_id),
        key=lambda report: report.created_at,
        reverse=True,
    )
    items = [_incident_summary(report) for report in reports[:limit]]
    return {"incidents": items, "total": len(reports), "limit": limit}


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    report = _find_report(incident_id, current_user.organization_id)
    detail = IncidentService.report_to_detail(report).model_dump(mode="json")
    detail["incident_id"] = detail.pop("report_id")
    detail["summary"] = _incident_summary(report)
    session = honeypot_session_manager.get_session(report.session_id, current_user.organization_id)
    detail["source"] = session.client_ip if session and session.client_ip else "Unknown source"
    detail["routing_decisions"] = ["honeypot"] if session and session.interaction_count else []
    with get_sync_control_db_manager().session() as db:
        record = db.execute(select(AttackSession).where(AttackSession.session_id == report.session_id,
            AttackSession.organization_id == current_user.organization_id)).scalar_one_or_none()
        if record:
            org = db.get(Organization, current_user.organization_id)
            domain = db.get(Domain, record.domain_id) if record.domain_id else None
            detail['customer_context'] = {'organization_id': str(org.id), 'organization': org.name,
                'domain': domain.domain if domain else None,
                'agent_id': json.loads(record.metadata_json or '{}').get('agent_id')}
    return detail


@router.get("/incidents/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    report = _find_report(incident_id, current_user.organization_id)
    session = honeypot_session_manager.get_session(
        report.session_id,
        organization_id=current_user.organization_id,
    )

    if session is None:
        return {
            "incident_id": str(report.report_id),
            "session_id": report.session_id,
            "timeline": [],
        }

    evidence = event_store.get_by_session(report.session_id, 1000, organization_id=current_user.organization_id)
    decisions = {event.metadata.get('decision_id'): event for event in evidence
                 if event.event_type == EventType.REQUEST_ANALYZED}
    timeline = [
        {
            "step": interaction.step,
            "timestamp": interaction.timestamp.isoformat(),
            "operation": interaction.operation,
            "attack_stage": interaction.attack_stage.value,
            "risk_score": interaction.risk_score,
            "success": interaction.success,
            "routing_target": "HONEYPOT",
            "original_target": "real",
            "final_target": "honeypot",
            "triggered_rules": [rule.get('rule') for rule in decisions[str(interaction.event_id)].triggered_rules]
                if str(interaction.event_id) in decisions else [],
            "routing_reason": "Deterministic operation policy; suspicious sessions remain pinned to deception",
            "synthetic_exposure_counts": {
                key: len(value) if isinstance(value, list) else value
                for key, value in interaction.entities_exposed.items()
            },
        }
        for interaction in session.interactions
    ]
    return {
        "incident_id": str(report.report_id),
        "session_id": report.session_id,
        "timeline": timeline,
    }


@router.get("/security/events")
async def security_events(
    limit: int = Query(100, ge=1, le=1000),
    session_id: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    organization_id = current_user.organization_id
    if session_id:
        events = event_store.get_by_session(
            session_id,
            limit,
            organization_id=organization_id,
        )
    else:
        events = event_store.get_recent(limit, organization_id=organization_id)

    return {
        "events": [_event_to_response(event).model_dump(mode="json") for event in events],
        "total": len(events),
    }


@router.get("/security/events/recent")
async def recent_security_events(
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    events = event_store.get_recent(limit, organization_id=current_user.organization_id)
    return {
        "events": [_event_to_response(event).model_dump(mode="json") for event in events],
        "total": len(events),
    }


@router.get("/security/stats")
async def security_stats(current_user: CurrentUser = Depends(get_current_user)):
    organization_id = current_user.organization_id
    reports = incident_service.list_reports(organization_id)
    events = event_store.get_all(organization_id=organization_id)
    session_records = _owned_session_records(organization_id)

    scores = [
        report.sanitized_payload.max_risk_score
        for report in reports
        if report.sanitized_payload
    ]
    rules = Counter(
        rule.get("rule", "unknown")
        for event in events
        for rule in event.triggered_rules
        if rule.get("rule")
    )
    stages = Counter(record.attack_stage for record in session_records)
    routing_events = [
        event for event in events if event.event_type == EventType.ROUTING_DECISION
    ]
    honeypot_interactions = [
        event for event in events if event.event_type == EventType.HONEYPOT_INTERACTION
    ]
    blocked_events = [
        event for event in events if event.event_type == EventType.GATEWAY_FAILURE
    ]

    return {
        "total_incidents": len(reports),
        "critical_incidents": sum(score >= 76 for score in scores),
        "high_risk_incidents": sum(51 <= score < 76 for score in scores),
        "active_honeypot_sessions": len(session_records),
        "active_honeypots": len({event.session_id for event in honeypot_interactions if event.session_id}),
        "honeypot_interactions": len(honeypot_interactions),
        "requests_routed_to_honeypot": sum(event.final_target == "honeypot" for event in routing_events),
        "requests_routed_to_real": sum(event.final_target == "real" for event in routing_events),
        "blocked_requests": len(blocked_events),
        "attack_stages": dict(stages),
        "top_triggered_rules": [
            {"rule": rule, "count": count} for rule, count in rules.most_common(10)
        ],
        "recent_suspicious_activity": [
            _event_to_response(event).model_dump(mode="json")
            for event in event_store.get_by_type(
                EventType.SUSPICIOUS_REQUEST,
                10,
                organization_id=organization_id,
            )
        ],
    }
