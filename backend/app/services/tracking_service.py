import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.database.supabase import get_supabase_client

logger = logging.getLogger("crowdeye.services.tracking")

# In-memory fallback if database migration 003 hasn't been executed yet
_tracking_jobs_cache: Dict[str, Dict[str, Any]] = {}


class TrackingService:
    """
    Manages tracking jobs in the Supabase 'tracking_jobs' table
    and persists batched movement telemetry into 'person_tracking'.
    """

    @classmethod
    def create_tracking_job(cls, video_name: str) -> str:
        """
        Creates a new tracking job record in Supabase tracking_jobs table.
        """
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        client = get_supabase_client()

        job_record = {
            "id": job_id,
            "video_name": video_name,
            "status": "queued",
            "progress": 0,
            "total_people": 0,
            "created_at": now
        }

        # Cache locally as fallback
        _tracking_jobs_cache[job_id] = job_record.copy()

        if client:
            try:
                res = client.table("tracking_jobs").insert(job_record).execute()
                logger.info(f"Created Supabase tracking_job record: {job_id}")
                return job_id
            except Exception as exc:
                logger.warning(
                    f"Supabase tracking_jobs insert error (will use local fallback): {exc}"
                )
                return job_id

        return job_id

    @classmethod
    def get_tracking_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves tracking job record from Supabase (or local fallback).
        """
        client = get_supabase_client()
        if client:
            try:
                res = client.table("tracking_jobs").select("*").eq("id", job_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        return _tracking_jobs_cache.get(job_id)

    @classmethod
    def update_tracking_job(
        cls,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total_people: Optional[int] = None,
        completed: bool = False
    ) -> bool:
        """
        Updates status, progress percentage, and person count for a tracking job.
        """
        now = datetime.utcnow().isoformat()
        update_data: Dict[str, Any] = {}

        if status:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = min(max(progress, 0), 100)
        if total_people is not None:
            update_data["total_people"] = total_people
        if completed:
            update_data["completed_at"] = now

        # Update cache
        if job_id in _tracking_jobs_cache:
            _tracking_jobs_cache[job_id].update(update_data)

        client = get_supabase_client()
        if client and update_data:
            try:
                client.table("tracking_jobs").update(update_data).eq("id", job_id).execute()
                return True
            except Exception as exc:
                logger.warning(f"Failed to update Supabase tracking_jobs: {exc}")
                return False

        return True

    @classmethod
    def batch_insert_movements(
        cls,
        camera_id: Optional[str],
        movements: List[Dict[str, Any]]
    ) -> int:
        """
        Persists a 5-second movement summary batch into Supabase person_tracking table.

        movements list item:
        {
            "person_id": int,
            "x_position": float,
            "y_position": float,
            "direction": str,
            "speed": float,
            "timestamp": str (iso)
        }
        """
        if not movements:
            return 0

        client = get_supabase_client()
        if not client:
            logger.warning("Supabase not available for person_tracking batch insert.")
            return 0

        # Resolve camera_id if missing
        target_camera_id = camera_id
        if not target_camera_id:
            try:
                cams = client.table("cameras").select("id").limit(1).execute()
                if cams.data and len(cams.data) > 0:
                    target_camera_id = cams.data[0]["id"]
            except Exception:
                pass

        records = []
        for m in movements:
            records.append({
                "camera_id": target_camera_id,
                "person_id": m["person_id"],
                "x_position": m["x_position"],
                "y_position": m["y_position"],
                "direction": m["direction"],
                "speed": m["speed"],
                "timestamp": m.get("timestamp", datetime.utcnow().isoformat())
            })

        try:
            res = client.table("person_tracking").insert(records).execute()
            count = len(res.data) if res.data else len(records)
            logger.info(f"Inserted {count} movement records into Supabase person_tracking.")
            return count
        except Exception as exc:
            logger.error(f"Error inserting person_tracking records: {exc}")
            return 0
