import uuid
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.job import JobStatus

logger = logging.getLogger("crowdeye.services.job")

# Persistent and in-memory storage for video processing jobs
JOBS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "videos" / "jobs.json"
_jobs: Dict[str, Dict[str, Any]] = {}


def _load_jobs_from_disk():
    global _jobs
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    _jobs.update(saved)
        except Exception as e:
            logger.warning(f"Could not load jobs from {JOBS_FILE}: {e}")


def _save_jobs_to_disk():
    try:
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(_jobs, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save jobs to {JOBS_FILE}: {e}")


# Pre-load existing jobs on module import
_load_jobs_from_disk()


class JobService:
    """
    Manages video processing jobs, state tracking, progress metrics, and persistent storage.
    """

    @staticmethod
    def create_job(filename: str, camera_id: Optional[str] = None) -> str:
        """
        Registers a new video processing job in queued state.
        """
        _load_jobs_from_disk()
        job_id = uuid.uuid4().hex[:12]
        _jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "camera_id": camera_id,
            "status": JobStatus.QUEUED.value,
            "progress": 0,
            "current_count": 0,
            "current_frame": 0,
            "total_frames": 0,
            "boxes": [],
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        _save_jobs_to_disk()
        logger.info(f"Created job {job_id} for file '{filename}'")
        return job_id

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a job by its ID.
        """
        if job_id not in _jobs:
            _load_jobs_from_disk()
        return _jobs.get(job_id)

    @staticmethod
    def update_job(
        job_id: str,
        status: Optional[Any] = None,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Updates job status, progress, results, or errors.
        """
        job = JobService.get_job(job_id)
        if not job:
            return False

        if status is not None:
            job["status"] = status.value if hasattr(status, "value") else str(status)
        if progress is not None:
            job["progress"] = min(max(int(progress), 0), 100)
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error

        for k, v in kwargs.items():
            job[k] = v

        job["updated_at"] = datetime.utcnow().isoformat()
        _save_jobs_to_disk()
        return True

    @staticmethod
    def list_jobs() -> Dict[str, Dict[str, Any]]:
        """
        Returns all registered jobs.
        """
        _load_jobs_from_disk()
        return _jobs
