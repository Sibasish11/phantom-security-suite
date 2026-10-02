"""
Phase 11 – AI Incident Analysis: API Router

Tenant-scoped incident analysis endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import CurrentUser, get_current_user
from app.incident_analysis.client import IncidentAnalysisError
from app.incident_analysis.schemas import (
    AnalysisStatus,
    IncidentAnalysisRequest,
    IncidentReportDetailResponse,
    IncidentReportListResponse,
)
from app.incident_analysis.service import IncidentService, incident_service


router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["incident-analysis"],
)


@router.post(
    "/{session_id}/analyze",
    response_model=IncidentReportDetailResponse,
    status_code=200,
)
async def analyze_session(
    session_id: str,
    body: IncidentAnalysisRequest = IncidentAnalysisRequest(),
    force: bool = Query(
        default=False,
        description="Force re-analysis even if a report exists",
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Trigger AI incident analysis for a tenant-owned honeypot session.
    """

    if not incident_service._session_belongs_to_organization(
        session_id,
        current_user.organization_id,
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )

    force_flag = force or body.force_reanalysis

    try:
        report = await incident_service.analyze_session(
            session_id=session_id,
            force_reanalysis=force_flag,
            organization_id=current_user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    except IncidentAnalysisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI analysis failed: {exc}",
        )

    if report.status == AnalysisStatus.FAILED:
        raise HTTPException(
            status_code=503,
            detail=f"AI analysis failed: {report.error}",
        )

    return IncidentService.report_to_detail(report)


@router.get(
    "/{session_id}",
    response_model=IncidentReportDetailResponse,
)
async def get_incident_report(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Retrieve an incident report belonging to the authenticated organization.
    """

    report = incident_service.get_report(
        session_id,
        current_user.organization_id,
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No incident report found for session '{session_id}'.",
        )

    return IncidentService.report_to_detail(report)


@router.get(
    "",
    response_model=IncidentReportListResponse,
)
async def list_incident_reports(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    List only incident reports belonging to the authenticated organization.
    """

    reports = incident_service.list_reports(
        current_user.organization_id,
    )

    summaries = [
        IncidentService.report_to_summary(report)
        for report in reports
    ]

    return IncidentReportListResponse(
        reports=summaries,
        total=len(summaries),
    )