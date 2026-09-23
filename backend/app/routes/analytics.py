from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, List, Optional
from app.services.analytics_service import AnalyticsService
from app.auth.security import require_operator

router = APIRouter(tags=["Analytics & Timeline"])


@router.get("/analytics/timeline", response_model=Dict[str, Any])
@router.get("/api/v1/analytics/timeline", response_model=Dict[str, Any])
def get_aggregated_timeline(
    camera_id: Optional[str] = Query(None, description="Optional camera filter"),
    window_minutes: int = Query(30, ge=5, le=1440, description="Window in minutes to aggregate"),
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    TASK 13: Aggregates 5-second raw crowd telemetry into 1-minute averages.
    Returns timeseries for:
    - People count timeline
    - Risk score timeline
    """
    return AnalyticsService.get_aggregated_timeline(camera_id=camera_id, window_minutes=window_minutes)


@router.get("/analytics/zones", response_model=List[Dict[str, Any]])
@router.get("/api/v1/analytics/zones", response_model=List[Dict[str, Any]])
def get_zone_comparison(
    camera_id: Optional[str] = Query(None, description="Optional camera filter"),
    user: Dict[str, Any] = Depends(require_operator)
):
    """
    TASK 13: Zone comparison analytics across venue sectors.
    """
    return AnalyticsService.get_zone_comparison(camera_id=camera_id)
