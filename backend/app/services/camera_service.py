import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.database.supabase import get_supabase_client
from app.websocket.tracking_socket import realtime_manager

logger = logging.getLogger("crowdeye.services.camera")

# In-memory storage fallback for cameras
_cameras_cache: Dict[str, Dict[str, Any]] = {}


def _is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


class CameraService:
    """
    Camera Management Service for CrowdEye AI Security Operations.
    - Manages camera metadata: location, status, zone_config.
    - Preserves existing: id, event_id, camera_name, zone, stream_url.
    - Broadcasts realtime WebSocket event: 'camera_status'.
    """

    @classmethod
    def get_cameras(cls) -> List[Dict[str, Any]]:
        """
        Retrieves all cameras. If Supabase is connected, reads from public.cameras.
        Otherwise provides populated in-memory cache.
        """
        client = get_supabase_client()
        if client:
            try:
                res = client.table("cameras").select("*").order("camera_name").execute()
                if res.data and len(res.data) > 0:
                    results = []
                    for row in res.data:
                        cid = str(row.get("id"))
                        cam = {
                            "id": cid,
                            "event_id": row.get("event_id"),
                            "camera_name": row.get("camera_name", f"Cam {cid[:4]}"),
                            "zone": row.get("zone", "Zone A"),
                            "stream_url": row.get("stream_url", ""),
                            "location": row.get("location") or "Main Concourse",
                            "status": row.get("status") or "ACTIVE",
                            "zone_config": row.get("zone_config") or {},
                            "people_count": row.get("people_count", 0),
                            "density": row.get("density", 0.0),
                            "risk_level": row.get("risk_level", "LOW")
                        }
                        # Update cache
                        _cameras_cache[cid] = cam
                        results.append(cam)
                    return results
            except Exception as e:
                logger.debug(f"Failed to query Supabase cameras: {e}")

        # Fallback to cache
        if not _cameras_cache:
            cls._seed_default_cameras()

        return list(_cameras_cache.values())

    @classmethod
    def get_camera(cls, camera_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single camera by ID.
        """
        if camera_id in _cameras_cache:
            return _cameras_cache[camera_id]

        client = get_supabase_client()
        if client and _is_valid_uuid(camera_id):
            try:
                res = client.table("cameras").select("*").eq("id", camera_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                logger.debug(f"Error querying camera {camera_id}: {e}")

        return None

    @classmethod
    def create_camera(
        cls,
        camera_name: str,
        zone: str = "Zone A",
        location: Optional[str] = "Main Concourse",
        stream_url: Optional[str] = "",
        status: str = "ACTIVE",
        zone_config: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ADMIN ONLY: Creates a new camera record.
        """
        camera_id = str(uuid.uuid4())
        client = get_supabase_client()

        # Resolve valid event_id if possible
        valid_event_id = event_id if _is_valid_uuid(event_id) else None
        if not valid_event_id and client:
            try:
                evts = client.table("events").select("id").limit(1).execute()
                if evts.data and len(evts.data) > 0:
                    valid_event_id = evts.data[0]["id"]
            except Exception:
                pass

        cam_record = {
            "id": camera_id,
            "event_id": valid_event_id,
            "camera_name": camera_name,
            "zone": zone,
            "stream_url": stream_url or "",
            "location": location or "General Arena",
            "status": status.upper() if status else "ACTIVE",
            "zone_config": zone_config or {"grid": "2x2", "homography_calibrated": True},
            "people_count": 0,
            "density": 0.0,
            "risk_level": "LOW"
        }

        # Cache locally
        _cameras_cache[camera_id] = cam_record

        # Persist to Supabase
        if client:
            try:
                db_record = {
                    "id": camera_id,
                    "event_id": valid_event_id,
                    "camera_name": camera_name,
                    "zone": zone,
                    "stream_url": stream_url or "",
                    "location": location,
                    "status": status.upper() if status else "ACTIVE",
                    "zone_config": zone_config or {}
                }
                client.table("cameras").insert(db_record).execute()
                logger.info(f"Created camera {camera_id} in Supabase.")
            except Exception as e:
                logger.debug(f"Failed to insert camera in Supabase (cached in-memory): {e}")

        # Broadcast camera creation event
        realtime_manager.sync_broadcast_event(
            "camera_status",
            {
                "camera_id": camera_id,
                "camera_name": camera_name,
                "status": status.upper(),
                "action": "created"
            },
            topic=f"camera:{camera_id}"
        )

        return cam_record

    @classmethod
    def update_camera(cls, camera_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ADMIN ONLY: Modifies camera attributes (location, status, zone_config, etc.)
        Broadcasts 'camera_status' over WebSocket.
        """
        target = _cameras_cache.get(camera_id)
        client = get_supabase_client()

        # Clean sanitized updates
        sanitized = {}
        for key in ["camera_name", "location", "status", "stream_url", "zone", "zone_config"]:
            if key in updates and updates[key] is not None:
                if key == "status":
                    sanitized[key] = str(updates[key]).upper()
                else:
                    sanitized[key] = updates[key]

        if not sanitized:
            return target

        if target:
            target.update(sanitized)
        else:
            target = {"id": camera_id, **sanitized}
            _cameras_cache[camera_id] = target

        if client and _is_valid_uuid(camera_id):
            try:
                client.table("cameras").update(sanitized).eq("id", camera_id).execute()
                logger.info(f"Updated camera {camera_id} in Supabase.")
            except Exception as e:
                logger.debug(f"Failed to update camera in Supabase: {e}")

        # -------------------------------------------------------------
        # TASK 9: REALTIME WEBSOCKET BROADCAST
        # Broadcast 'camera_status'
        # -------------------------------------------------------------
        ws_payload = {
            "event": "camera_status",
            "camera_id": camera_id,
            "status": target.get("status", "ACTIVE"),
            "camera_name": target.get("camera_name", f"Camera {camera_id[:4]}"),
            "location": target.get("location", "")
        }
        realtime_manager.sync_broadcast_event("camera_status", ws_payload, topic=f"camera:{camera_id}")
        realtime_manager.sync_broadcast_event("camera_status", ws_payload, topic="alerts")

        return target

    @classmethod
    def update_camera_telemetry(cls, camera_id: str, people_count: int, density: float, risk_level: str):
        """
        Updates live telemetry values on camera card.
        """
        if camera_id in _cameras_cache:
            _cameras_cache[camera_id]["people_count"] = people_count
            _cameras_cache[camera_id]["density"] = density
            _cameras_cache[camera_id]["risk_level"] = risk_level

    @classmethod
    def _seed_default_cameras(cls):
        """Seeds initial 4 cameras for venue operations."""
        sample_cameras = [
            {
                "id": "11111111-1111-1111-1111-111111111101",
                "camera_name": "Gate North Turnstiles",
                "zone": "Zone A",
                "location": "North Entrance Gates",
                "stream_url": "rtsp://live.crowdeye.internal/cam01",
                "status": "ACTIVE",
                "people_count": 840,
                "density": 3.8,
                "risk_level": "CRITICAL",
                "zone_config": {"grid": "2x2"}
            },
            {
                "id": "11111111-1111-1111-1111-111111111102",
                "camera_name": "Concourse East Boulevard",
                "zone": "Zone B",
                "location": "East Promenade & Food Stalls",
                "stream_url": "rtsp://live.crowdeye.internal/cam02",
                "status": "ACTIVE",
                "people_count": 420,
                "density": 1.9,
                "risk_level": "MEDIUM",
                "zone_config": {"grid": "2x2"}
            },
            {
                "id": "11111111-1111-1111-1111-111111111103",
                "camera_name": "Front Stage Arena Pit",
                "zone": "Zone C",
                "location": "Main Stage Ground Floor",
                "stream_url": "rtsp://live.crowdeye.internal/cam03",
                "status": "ACTIVE",
                "people_count": 1150,
                "density": 4.2,
                "risk_level": "CRITICAL",
                "zone_config": {"grid": "3x2"}
            },
            {
                "id": "11111111-1111-1111-1111-111111111104",
                "camera_name": "Emergency Exit Stairwell A",
                "zone": "Zone D",
                "location": "West Emergency Evacuation Shaft",
                "stream_url": "rtsp://live.crowdeye.internal/cam04",
                "status": "ACTIVE",
                "people_count": 90,
                "density": 0.8,
                "risk_level": "LOW",
                "zone_config": {"grid": "2x2"}
            }
        ]
        for c in sample_cameras:
            _cameras_cache[c["id"]] = c
