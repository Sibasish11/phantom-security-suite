from fastapi import APIRouter, HTTPException

from app.risk.engine import risk_scoring_engine
from app.risk.schemas import RiskAssessment, RiskAssessmentRequest, RiskHealthResponse

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/health", response_model=RiskHealthResponse)
async def risk_health():
    return RiskHealthResponse(
        service="PhantomLayer Risk Scoring Engine",
        status="healthy",
        scoring_method="deterministic_weighted",
        confidence_thresholds={
            "LOW": 0.0,
            "MEDIUM": 0.4,
            "HIGH": 0.65,
            "VERY_HIGH": 0.85,
        },
    )


@router.post("/assess", response_model=RiskAssessment)
async def assess_risk(request: RiskAssessmentRequest):
    try:
        result = risk_scoring_engine.assess(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")