import queue
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("crowdeye.ai_worker.queue")


class VideoJobQueue:
    """
    Thread-safe Job Queue for camera feeds, video processing jobs, and synthetic streams.
    """

    def __init__(self, maxsize: int = 100):
        self._queue = queue.Queue(maxsize=maxsize)
        self._active_jobs: Dict[str, Dict[str, Any]] = {}
        self._completed_jobs: Dict[str, Dict[str, Any]] = {}

    def enqueue_job(self, job_dict: Dict[str, Any]) -> str:
        """
        Enqueues a camera or video job for AI Worker ingestion.
        """
        job_id = job_dict.get("job_id") or job_dict.get("id")
        self._active_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            **job_dict
        }
        self._queue.put(job_dict)
        logger.info(f"[VideoJobQueue] Enqueued job: {job_id}")
        return job_id

    def dequeue_job(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Retrieves the next available job, blocking up to timeout seconds.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def update_job_progress(self, job_id: str, progress: int, status: str = "processing"):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["progress"] = progress
            self._active_jobs[job_id]["status"] = status

    def complete_job(self, job_id: str, summary: Dict[str, Any]):
        if job_id in self._active_jobs:
            job = self._active_jobs.pop(job_id)
            job.update({
                "status": "completed",
                "progress": 100,
                "summary": summary
            })
            self._completed_jobs[job_id] = job
            logger.info(f"[VideoJobQueue] Job {job_id} marked as completed.")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]
        return self._completed_jobs.get(job_id)

    def active_job_count(self) -> int:
        return self._queue.qsize()


# Global queue singleton
video_queue = VideoJobQueue()
