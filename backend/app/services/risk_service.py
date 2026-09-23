import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.database.supabase import get_supabase_client

logger = logging.getLogger("crowdeye.services.risk")

# In-memory fallbacks if Supabase migration 005 has not yet been executed
_risk_jobs_cache: Dict[str, Dict[str, Any]] = {}
_risk_results_cache: Dict[str, List[Dict[str, Any]]] = {}


class RiskService:
    """
    Service layer for managing crowd risk jobs, querying 10-second telemetry windows,
    and persisting explainable risk evaluations to Supabase crowd_risk.
    """

    @classmethod
    def create_risk_job(cls, camera_id: Optional[str] = None) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        client = get_supabase_client()

        # Sanitize camera_id
        valid_cam_id = camera_id if (camera_id and str(camera_id).strip() and len(str(camera_id).strip()) == 36) else None

        job_record = {
            "id": job_id,
            "camera_id": valid_cam_id,
            "status": "queued",
            "progress": 0,
            "created_at": now
        }

        _risk_jobs_cache[job_id] = job_record

        if client:
            try:
                client.table("risk_jobs").insert(job_record).execute()
            except Exception as e:
                logger.debug(f"Supabase risk_jobs insert error (local fallback active): {e}")

        return job_id

    @classmethod
    def update_risk_job(
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

        if job_id in _risk_jobs_cache:
            _risk_jobs_cache[job_id].update(updates)

        if client and updates:
            try:
                client.table("risk_jobs").update(updates).eq("id", job_id).execute()
                return True
            except Exception as e:
                logger.debug(f"Failed to update Supabase risk_jobs: {e}")
        return False

    @classmethod
    def get_risk_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        if client:
            try:
                res = client.table("risk_jobs").select("*").eq("id", job_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.debug(f"Query risk_jobs failed, checking memory cache: {e}")

        return _risk_jobs_cache.get(job_id)

    @classmethod
    def save_risk_result(cls, camera_id: str, zones_data: List[Dict[str, Any]]):
        """
        Stores structured risk result for GET /risk/result/{camera_id}.
        """
        key = camera_id or "default"
        _risk_results_cache[key] = zones_data

    @classmethod
    def get_risk_result(cls, camera_id: str) -> List[Dict[str, Any]]:
        key = camera_id or "default"
        if key in _risk_results_cache:
            return _risk_results_cache[key]

        # Check Supabase crowd_risk for latest evaluated records
        client = get_supabase_client()
        if client:
            try:
                query = client.table("crowd_risk").select("*").order("timestamp", desc=True).limit(6)
                if camera_id and len(str(camera_id).strip()) == 36:
                    query = query.eq("camera_id", camera_id)
                res = query.execute()
                if res.data and len(res.data) > 0:
                    formatted = []
                    for row in res.data:
                        formatted.append({
                            "zone": row.get("zone_name"),
                            "risk_score": int(round(row.get("risk_score", 0.0))),
                            "risk_level": row.get("risk_level", "LOW"),
                            "reason": row.get("risk_reason", []),
                            "features": {
                                "density": row.get("density_value", 0.0),
                                "speed": row.get("speed_value", 0.0),
                                "chaos": row.get("chaos_value", 0.0),
                                "growth": row.get("growth_value", 0.0)
                            }
                        })
                    return formatted
            except Exception as e:
                logger.debug(f"Failed to fetch crowd_risk from Supabase: {e}")

        return []

    @classmethod
    def fetch_recent_telemetry(cls, camera_id: Optional[str] = None, window_seconds: int = 10) -> Dict[str, Any]:
        """
        Fetches the last 10 seconds of telemetry from crowd_density and person_tracking.
        """
        client = get_supabase_client()
        recent_density = []
        recent_movements = []

        now = datetime.utcnow()
        cutoff = (now - timedelta(seconds=window_seconds)).isoformat()

        if client:
            try:
                # 1. Query crowd_density
                q_dens = client.table("crowd_density").select("*").gte("timestamp", cutoff).order("timestamp", desc=True)
                if camera_id and len(str(camera_id).strip()) == 36:
                    q_dens = q_dens.eq("camera_id", camera_id)
                res_dens = q_dens.execute()
                recent_density = res_dens.data or []
            except Exception as e:
                logger.debug(f"Failed to query recent crowd_density: {e}")

            try:
                # 2. Query person_tracking
                q_track = client.table("person_tracking").select("*").gte("timestamp", cutoff).order("timestamp", desc=True)
                if camera_id and len(str(camera_id).strip()) == 36:
                    q_track = q_track.eq("camera_id", camera_id)
                res_track = q_track.execute()
                recent_movements = res_track.data or []
            except Exception as e:
                logger.debug(f"Failed to query recent person_tracking: {e}")

        return {
            "density_records": recent_density,
            "movement_records": recent_movements
        }

    @classmethod
    def insert_risk_records(cls, records: List[Dict[str, Any]]) -> bool:
        """
        Persists risk evaluations to public.crowd_risk in Supabase.
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
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
                "risk_reason": r.get("risk_reason", []),
                "density_value": r.get("density_value", 0.0),
                "speed_value": r.get("speed_value", 0.0),
                "chaos_value": r.get("chaos_value", 0.0),
                "growth_value": r.get("growth_value", 0.0),
                "timestamp": r.get("timestamp", datetime.utcnow().isoformat())
            })

        try:
            client.table("crowd_risk").insert(sanitized_records).execute()
            logger.info(f"Persisted {len(sanitized_records)} crowd_risk records to Supabase.")
            return True
        except Exception as e:
            logger.warning(f"Error inserting crowd_risk records: {e}")
            return False
