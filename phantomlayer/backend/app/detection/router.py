from fastapi import APIRouter, HTTPException

from app.detection.engine import detection_engine
from app.detection.schemas import DetectionRequest, DetectionResult

router = APIRouter(prefix="/detection", tags=["detection"])


@router.post("/analyze", response_model=DetectionResult)
async def analyze_request(request: DetectionRequest):
    try:
        result = detection_engine.analyze(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection analysis failed: {str(e)}")


@router.get("/health")
async def detection_health():
    return {
        "service": "PhantomLayer Detection Engine",
        "status": "healthy",
        "rules_loaded": [
            "RULE_SENSITIVE_DATA_ACCESS",
            "RULE_ENUMERATION",
            "RULE_INVALID_OPERATION",
            "RULE_HONEYPOT_TARGET",
            "RULE_RECONNAISSANCE",
        ],
    }