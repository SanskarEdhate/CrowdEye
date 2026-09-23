from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.alert_service import AlertService
from app.auth.auth import require_operator
from app.config.rate_limiter import limiter

router = APIRouter(tags=["Alert Management"])


class RiskEvaluationInput(BaseModel):
    camera_id: Optional[str] = None
    camera_name: Optional[str] = None
    zone: Optional[str] = "Zone A"
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: Optional[str] = None
    reasons: Optional[List[str]] = Field(default_factory=list)


@router.get("/alerts", response_model=List[Dict[str, Any]])
@router.get("/api/v1/alerts", response_model=List[Dict[str, Any]])
@limiter.limit("300/minute")
def get_alerts(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, ACKNOWLEDGED, RESOLVED"),
    camera_id: Optional[str] = Query(None, description="Filter by camera UUID"),
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    TASK 8: Retrieve alerts history and active alerts.
    Accessible to: ADMIN and OPERATOR.
    """
    return AlertService.get_alerts(status=status, camera_id=camera_id)


@router.put("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
@router.put("/api/v1/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
@limiter.limit("300/minute")
def resolve_alert(
    request: Request,
    alert_id: str,
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    TASK 8: Resolve an active incident alert.
    Accessible to: ADMIN and OPERATOR.
    Updates alert status to 'RESOLVED' and broadcasts 'alert_resolved' over WebSocket.
    """
    resolved_by = f"{user.get('role', 'OPERATOR').lower()}:{user.get('email', 'staff')}"
    resolved = AlertService.resolve_alert(alert_id, resolved_by=resolved_by)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return resolved


@router.post("/alerts/evaluate", response_model=List[Dict[str, Any]])
@router.post("/api/v1/alerts/evaluate", response_model=List[Dict[str, Any]])
def evaluate_risk_alert(
    payload: RiskEvaluationInput,
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    Evaluates a risk score input against Phase 6 safety rules:
    - LOW (<=30): No alert
    - MEDIUM (31-60): Monitoring only (no alert)
    - HIGH (61-80): WARNING alert
    - CRITICAL (81-100): CRITICAL alert
    Enforces duplicate active protection.
    """
    result = AlertService.evaluate_and_create_alert(
        risk_input={
            "zone": payload.zone,
            "risk_score": payload.risk_score,
            "risk_level": payload.risk_level,
            "reasons": payload.reasons
        },
        camera_id=payload.camera_id,
        camera_name=payload.camera_name
    )
    return result
