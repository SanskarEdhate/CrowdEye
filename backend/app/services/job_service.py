import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.job import JobStatus

logger = logging.getLogger("crowdeye.services.job")

# In-memory storage for Phase 2 (without requiring external Redis/Celery)
_jobs: Dict[str, Dict[str, Any]] = {}


class JobService:
    """
    Manages in-memory video processing jobs, state tracking, and progress metrics.
    """

    @staticmethod
    def create_job(filename: str, camera_id: Optional[str] = None) -> str:
        """
        Registers a new video processing job in queued state.
        """
        job_id = uuid.uuid4().hex[:12]
        _jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "camera_id": camera_id,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        logger.info(f"Created job {job_id} for file '{filename}'")
        return job_id

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a job by its ID.
        """
        return _jobs.get(job_id)

    @staticmethod
    def update_job(
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Updates job status, progress, results, or errors.
        """
        job = _jobs.get(job_id)
        if not job:
            return False

        if status is not None:
            job["status"] = status
        if progress is not None:
            job["progress"] = min(max(progress, 0), 100)
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error

        job["updated_at"] = datetime.utcnow().isoformat()
        return True

    @staticmethod
    def list_jobs() -> Dict[str, Dict[str, Any]]:
        """
        Returns all registered jobs.
        """
        return _jobs
