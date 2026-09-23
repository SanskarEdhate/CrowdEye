import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.database.supabase import get_supabase_client

logger = logging.getLogger("crowdeye.services.density")

# In-memory fallback if migration 004 is not yet executed in Supabase
_density_jobs_cache: Dict[str, Dict[str, Any]] = {}
_density_results_cache: Dict[str, Dict[str, Any]] = {}


class DensityService:
    """
    Service layer for managing crowd density jobs, zone configurations,
    and persisting 5-second interval density summaries into Supabase.
    """

    @classmethod
    def create_density_job(cls, video_name: str) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        client = get_supabase_client()

        job_record = {
            "id": job_id,
            "video_name": video_name,
            "status": "queued",
            "progress": 0,
            "created_at": now
        }

        # Cache locally
        _density_jobs_cache[job_id] = job_record

        if client:
            try:
                client.table("density_jobs").insert(job_record).execute()
            except Exception as e:
                logger.warning(f"Supabase density_jobs insert error (will use local fallback): {e}")

        return job_id

    @classmethod
    def update_density_job(
        cls,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        completed_at: Optional[str] = None
    ) -> bool:
        client = get_supabase_client()
        updates: Dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
        if progress is not None:
            updates["progress"] = progress
        if completed_at is not None:
            updates["completed_at"] = completed_at

        # Update in-memory cache
        if job_id in _density_jobs_cache:
            _density_jobs_cache[job_id].update(updates)

        if client and updates:
            try:
                client.table("density_jobs").update(updates).eq("id", job_id).execute()
                return True
            except Exception as e:
                logger.debug(f"Failed to update Supabase density_jobs: {e}")
        return False

    @classmethod
    def get_density_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        if client:
            try:
                res = client.table("density_jobs").select("*").eq("id", job_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.debug(f"Query density_jobs failed, checking memory cache: {e}")

        return _density_jobs_cache.get(job_id)

    @classmethod
    def save_density_result(
        cls,
        job_id: str,
        zones: List[Dict[str, Any]],
        heatmap_points: List[Dict[str, Any]],
        csrnet_data: Optional[Dict[str, Any]] = None
    ):
        """
        Stores structured density result for GET /density/result/{job_id}.
        """
        _density_results_cache[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "zones": zones,
            "heatmap": heatmap_points,
            "csrnet": csrnet_data
        }

    @classmethod
    def get_density_result(cls, job_id: str) -> Optional[Dict[str, Any]]:
        return _density_results_cache.get(job_id)

    @classmethod
    def batch_insert_density_telemetry(cls, records: List[Dict[str, Any]]) -> bool:
        """
        Persists 5-second interval density telemetry into Supabase crowd_density.
        Rate-limited: never stores per-frame data or raw image files.
        """
        if not records:
            return True

        client = get_supabase_client()
        if not client:
            return False

        # Resolve fallback camera if needed
        default_cam_id = None
        try:
            cams = client.table("cameras").select("id").limit(1).execute()
            if cams.data and len(cams.data) > 0:
                default_cam_id = cams.data[0]["id"]
        except Exception:
            pass

        sanitized_records = []
        for r in records:
            cid = r.get("camera_id")
            if not cid or not str(cid).strip() or len(str(cid).strip()) != 36:
                cid = default_cam_id

            sanitized_records.append({
                "camera_id": cid,
                "zone_name": r["zone_name"],
                "people_count": r["people_count"],
                "density_score": r["density_score"],
                "density_level": r["density_level"],
                "timestamp": r.get("timestamp", datetime.utcnow().isoformat())
            })

        try:
            client.table("crowd_density").insert(sanitized_records).execute()
            logger.info(f"Persisted {len(sanitized_records)} crowd_density records to Supabase.")
            return True
        except Exception as e:
            logger.warning(f"Error inserting crowd_density records: {e}")
            return False

