import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from app.database.supabase import get_supabase_client

# Ensure ai package is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("crowdeye.services.detection")


class DetectionService:
    """
    Coordinates AI video inference and persists final telemetry into Supabase.
    """

    @staticmethod
    def log_detection_to_supabase(
        people_count: int,
        camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inserts the final video processing detection result into public.crowd_logs.

        Per Phase 2 specification:
        - density: NULL
        - risk_score: NULL
        - status: "DETECTED"
        """
        client = get_supabase_client()
        if not client:
            logger.warning("Supabase client not available. Skipping crowd_logs insertion.")
            return {"logged": False, "reason": "supabase_not_configured"}

        target_camera_id = camera_id

        # If camera_id was not provided, locate an active camera from database
        if not target_camera_id:
            try:
                cams = client.table("cameras").select("id").limit(1).execute()
                if cams.data and len(cams.data) > 0:
                    target_camera_id = cams.data[0]["id"]
            except Exception as e:
                logger.error(f"Error fetching default camera: {e}")

        if not target_camera_id:
            logger.warning("No camera ID available for crowd_logs record.")
            return {"logged": False, "reason": "no_camera_found"}

        payload = {
            "camera_id": target_camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "density": None,
            "risk_score": None,
            "status": "DETECTED"
        }

        try:
            res = client.table("crowd_logs").insert(payload).execute()
            logger.info(f"Logged detection result ({people_count} people) to Supabase crowd_logs: {res.data}")
            return {"logged": True, "record": res.data[0] if res.data else None}
        except Exception as exc:
            # Handle possible NOT NULL constraint if migration 002 hasn't been run yet
            err_str = str(exc)
            if "23502" in err_str or "not-null constraint" in err_str.lower():
                logger.warning("Falling back to 0.0 for density/risk_score due to NOT NULL constraint.")
                payload["density"] = 0.0
                payload["risk_score"] = 0.0
                try:
                    res = client.table("crowd_logs").insert(payload).execute()
                    return {"logged": True, "record": res.data[0] if res.data else None, "note": "fallback_0.0"}
                except Exception as fallback_exc:
                    logger.error(f"Failed crowd_logs fallback insertion: {fallback_exc}")
                    return {"logged": False, "error": str(fallback_exc)}

            logger.error(f"Failed to insert crowd log into Supabase: {exc}")
            return {"logged": False, "error": str(exc)}
