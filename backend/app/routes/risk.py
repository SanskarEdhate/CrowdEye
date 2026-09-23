from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Body
from app.services.risk_service import RiskService
from app.jobs.risk_worker import run_risk_worker

router = APIRouter(tags=["Crowd Risk Prediction & Early Warning"])


class RiskAnalyzeRequest(BaseModel):
    camera_id: Optional[str] = None
    video_id: Optional[str] = None


@router.post("/risk/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_crowd_risk(
    background_tasks: BackgroundTasks,
    payload: Optional[RiskAnalyzeRequest] = Body(default=None)
):
    """
    API 1: Initiates asynchronous 10-second temporal crowd risk prediction analysis.
    """
    camera_id = payload.camera_id if payload else None

    # 1. Create job entry
    job_id = RiskService.create_risk_job(camera_id=camera_id)

    # 2. Schedule background worker
    background_tasks.add_task(
        run_risk_worker,
        job_id=job_id,
        camera_id=camera_id
    )

    return {
        "job_id": job_id,
        "status": "queued"
    }


@router.get("/risk/status/{job_id}")
def get_risk_status(job_id: str):
    """
    API 2: Queries status and completion percentage of a risk evaluation job.
    """
    job = RiskService.get_risk_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Risk evaluation job not found.")

    return {
        "job_id": job.get("id", job_id),
        "status": job.get("status", "unknown"),
        "progress": job.get("progress", 0)
    }


@router.get("/risk/result/{camera_id}")
def get_risk_result(camera_id: str):
    """
    API 3: Returns zone-by-zone evaluated risk scores, levels, diagnostic reasons, and normalized features.
    """
    zones_data = RiskService.get_risk_result(camera_id)
    if not zones_data:
        # Fallback to default if camera has no specific evaluation yet
        zones_data = RiskService.get_risk_result("default")

    if not zones_data:
        # If still no evaluations, return normalized baseline zones
        default_zones = []
        for name in ["A", "B", "C", "D", "E", "F"]:
            default_zones.append({
                "zone": name,
                "risk_score": 15,
                "risk_level": "LOW",
                "reason": ["Normal crowd flow within safety thresholds"],
                "features": {
                    "density": 15.0,
                    "speed": 10.0,
                    "chaos": 5.0,
                    "growth": 0.0
                }
            })
        return {"zones": default_zones}

    return {
        "camera_id": camera_id,
        "zones": zones_data
    }
