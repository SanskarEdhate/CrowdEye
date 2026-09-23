import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, status
from app.services.density_service import DensityService
from app.jobs.density_worker import run_density_worker

router = APIRouter(tags=["Crowd Density & Heatmaps"])

DENSITY_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "videos" / "input"
DENSITY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/density/start", status_code=status.HTTP_202_ACCEPTED)
async def start_density_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CCTV/Event video recording for crowd density estimation"),
    camera_id: Optional[str] = Form(None, description="Optional associated Camera UUID")
):
    """
    API 1: Accepts a video recording, registers a density_jobs task,
    and initiates the asynchronous Phase 4 density + heatmap worker.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No video file provided.")

    job_id = DensityService.create_density_job(video_name=file.filename)

    file_ext = Path(file.filename).suffix or ".mp4"
    staged_path = DENSITY_UPLOAD_DIR / f"density_{job_id}{file_ext}"

    try:
        with open(staged_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        DensityService.update_density_job(job_id, status="failed")
        raise HTTPException(status_code=500, detail=f"Failed to stage video file: {exc}")

    background_tasks.add_task(
        run_density_worker,
        job_id=job_id,
        video_path=str(staged_path),
        camera_id=camera_id
    )

    return {
        "job_id": job_id,
        "status": "queued"
    }


@router.get("/density/status/{job_id}")
def get_density_status(job_id: str):
    """
    API 2: Returns processing status and percentage progress of a density job.
    """
    job = DensityService.get_density_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Density job not found.")

    return {
        "job_id": job.get("id", job_id),
        "status": job.get("status", "unknown"),
        "progress": job.get("progress", 0)
    }


@router.get("/density/result/{job_id}")
def get_density_result(job_id: str):
    """
    API 3: Returns zone-based density scores, levels, capacities, and dynamic heatmap points.
    """
    job = DensityService.get_density_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Density job not found.")

    if job.get("status") != "completed":
        return {
            "job_id": job_id,
            "status": job.get("status"),
            "progress": job.get("progress", 0),
            "message": "Density estimation is still in progress."
        }

    cached_result = DensityService.get_density_result(job_id)
    if not cached_result:
        raise HTTPException(status_code=404, detail="Density results could not be retrieved.")

    # Format zone outputs matching specification
    formatted_zones = []
    for z in cached_result.get("zones", []):
        formatted_zones.append({
            "zone": z.get("zone"),
            "people": z.get("people_count", 0),
            "density": z.get("density_level", "LOW"),
            "score": z.get("density_score", 0.0),
            "capacity": z.get("capacity", 100)
        })

    return {
        "job_id": job_id,
        "status": "completed",
        "zones": formatted_zones,
        "heatmap": cached_result.get("heatmap", []),
        "csrnet": cached_result.get("csrnet")
    }
