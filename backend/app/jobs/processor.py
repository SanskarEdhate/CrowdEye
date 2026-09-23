import os
import sys
import logging
from pathlib import Path
from typing import Optional
from app.models.job import JobStatus
from app.services.job_service import JobService
from app.services.detection_service import DetectionService

# Ensure ai directory is accessible
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("crowdeye.jobs.processor")


def run_video_processing_job(
    job_id: str,
    video_path: str,
    camera_id: Optional[str] = None
) -> None:
    """
    Background worker task executed by FastAPI BackgroundTasks.
    Processes video via YOLOv8, calculates crowd metrics, and inserts into Supabase.
    """
    logger.info(f"[Job {job_id}] Starting background video processing: {video_path}")
    JobService.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    try:
        from ai.detection.video_processor import process_video

        def on_progress(percent: int, current_count: int):
            # Scale progress 5% -> 90%
            scaled = 5 + int(percent * 0.85)
            JobService.update_job(job_id, progress=scaled)

        # Execute headless video inference
        summary = process_video(
            video_path=video_path,
            progress_callback=on_progress,
            frame_stride=2  # Process every 2nd frame for optimal hackathon throughput
        )

        JobService.update_job(job_id, progress=92)

        # Insert final aggregate result into Supabase crowd_logs
        people_count = summary.get("max_people") if summary.get("max_people", 0) > 0 else summary.get("average_people", 0)
        log_res = DetectionService.log_detection_to_supabase(
            people_count=people_count,
            camera_id=camera_id
        )

        result_payload = {
            "people_count": people_count,
            "average_people": summary.get("average_people", 0),
            "max_people": summary.get("max_people", 0),
            "total_frames": summary.get("total_frames", 0),
            "duration": summary.get("duration", 0),
            "camera_id": camera_id,
            "supabase_logged": log_res.get("logged", False)
        }

        # Mark job as completed
        JobService.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result_payload
        )
        logger.info(f"[Job {job_id}] Completed successfully: {result_payload}")

    except Exception as exc:
        logger.error(f"[Job {job_id}] Failed with exception: {exc}", exc_info=True)
        JobService.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(exc)
        )
