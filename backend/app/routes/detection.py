import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, status
from app.models.job import JobStatus, JobCreateResponse, JobStatusResponse, JobResultResponse
from app.services.job_service import JobService
from app.jobs.processor import run_video_processing_job

router = APIRouter(tags=["AI Person Detection"])

# Directory to stage incoming video uploads
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "videos" / "input"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/detection/video", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video_for_detection(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file (MP4, AVI, MOV) for person detection"),
    camera_id: Optional[str] = Form(None, description="Optional associated Camera UUID")
):
    """
    API 1: Accepts a video file, schedules asynchronous background YOLOv8 detection,
    and returns a unique job_id for status polling.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No video file provided.")

    # Generate job ID and register in JobService
    job_id = JobService.create_job(filename=file.filename, camera_id=camera_id)

    # Save uploaded file to staging folder
    file_ext = Path(file.filename).suffix or ".mp4"
    staged_path = UPLOAD_DIR / f"{job_id}{file_ext}"

    try:
        with open(staged_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        JobService.update_job(job_id, status=JobStatus.FAILED, error=f"File save error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {str(e)}")

    # Enqueue background task
    background_tasks.add_task(
        run_video_processing_job,
        job_id=job_id,
        video_path=str(staged_path),
        camera_id=camera_id
    )

    return JobCreateResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/detection/status/{job_id}", response_model=JobStatusResponse)
def get_detection_status(job_id: str):
    """
    API 2: Polls the current processing status, percentage progress, live count, and frame boxes.
    """
    job = JobService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress", 0),
        current_count=job.get("current_count", 0),
        current_frame=job.get("current_frame", 0),
        total_frames=job.get("total_frames", 0),
        boxes=job.get("boxes", []),
        message=job.get("error")
    )


@router.get("/detection/result/{job_id}", response_model=JobResultResponse)
def get_detection_result(job_id: str):
    """
    API 3: Retrieves the final detection result and crowd headcounts for a completed job.
    """
    job = JobService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if str(job["status"]) in ("queued", "processing"):
        return JobResultResponse(
            job_id=job_id,
            status=job["status"],
            people_count=job.get("current_count", 0),
            total_frames=job.get("total_frames", 0),
            error="Processing in progress. Please continue polling."
        )

    if str(job["status"]) == "failed":
        return JobResultResponse(
            job_id=job_id,
            status=JobStatus.FAILED,
            people_count=0,
            error=job.get("error", "Unknown processing error")
        )

    res = job.get("result") or {}
    return JobResultResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        people_count=res.get("people_count", 0),
        average_people=res.get("average_people", 0),
        max_people=res.get("max_people", 0),
        total_frames=res.get("total_frames", 0),
        duration=res.get("duration", 0),
        camera_id=res.get("camera_id"),
        supabase_logged=res.get("supabase_logged", False),
        sample_frames=res.get("sample_frames", []),
        initial_boxes=res.get("initial_boxes", [])
    )
