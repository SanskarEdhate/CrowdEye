import os
import sys
import logging
from pathlib import Path
from typing import Optional
from app.models.job import JobStatus
from app.services.job_service import JobService
from app.services.detection_service import DetectionService

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
    Processes video via YOLOv8, calculates crowd metrics, tracks per-frame boxes, and persists state.
    """
    logger.info(f"[Job {job_id}] Starting background video processing: {video_path}")
    JobService.update_job(job_id, status=JobStatus.PROCESSING, progress=5)

    try:
        import time
        import importlib
        import ai.detection.yolo_detector
        import ai.detection.video_processor
        importlib.reload(ai.detection.yolo_detector)
        importlib.reload(ai.detection.video_processor)
        from ai.detection.video_processor import process_video

        def on_progress(percent: int, current_count: int, frame_idx: int = 0, total_f: int = 0, boxes = None):
            scaled = 5 + int(percent * 0.90)
            JobService.update_job(
                job_id,
                progress=scaled,
                current_count=current_count,
                current_frame=frame_idx,
                total_frames=total_f,
                boxes=boxes or []
            )

        # Execute headless video inference
        t_infer_start = time.time()
        summary = process_video(
            video_path=video_path,
            progress_callback=on_progress
        )
        logger.info(f"[Job {job_id}] Headless process_video took: {time.time() - t_infer_start:.2f}s")

        JobService.update_job(job_id, progress=95)

        # Insert final aggregate result into Supabase crowd_logs if possible
        people_count = summary.get("max_people") if summary.get("max_people", 0) > 0 else summary.get("average_people", 0)
        log_res = {}
        try:
            log_res = DetectionService.log_detection_to_supabase(
                people_count=people_count,
                camera_id=camera_id
            )
        except Exception:
            pass

        supabase_logged = False
        if isinstance(log_res, dict):
            supabase_logged = log_res.get("logged", False)

        result_payload = {
            "people_count": people_count,
            "average_people": summary.get("average_people", 0),
            "max_people": summary.get("max_people", 0),
            "total_frames": summary.get("total_frames", 0),
            "duration": summary.get("duration", 0),
            "camera_id": camera_id,
            "supabase_logged": supabase_logged,
            "sample_frames": summary.get("sample_frames", []),
            "initial_boxes": summary.get("initial_boxes", [])
        }

        # Mark job as completed with all rich metrics
        JobService.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_count=summary.get("average_people", 0),
            current_frame=summary.get("total_frames", 0),
            total_frames=summary.get("total_frames", 0),
            boxes=summary.get("initial_boxes", []),
            result=result_payload
        )
        logger.info(f"[Job {job_id}] Completed successfully: Peak={summary.get('max_people')}, Avg={summary.get('average_people')}")

    except Exception as exc:
        logger.error(f"[Job {job_id}] Failed with exception: {exc}", exc_info=True)
        JobService.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(exc)
        )
